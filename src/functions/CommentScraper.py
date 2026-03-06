import psycopg2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime
import pandas as pd

class CommentScraperError(Exception):
    pass

def scrape_comments(
    *,
    api_key: str,
    db_config: dict,
    video_id: str,
    max_pages: int = 1,
    max_results_per_page: int = 20
):
    """Scrapes comments for a YouTube video and saves to database."""
    try:
        # 1. Initialize YouTube API
        youtube = build("youtube", "v3", developerKey=api_key)
        
        # 2. Fetch Comments
        next_page_token = None
        pages_processed = 0
        total_scraped = 0
        
        while pages_processed < max_pages:
            request = youtube.commentThreads().list(
                part="snippet", 
                videoId=video_id,
                maxResults=min(max_results_per_page, 100),
                pageToken=next_page_token,
                textFormat="plainText"
            )
            response = request.execute()
            
            items = response.get("items", [])
            if not items:
                break
                
            # Connect to database
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            
            for item in items:
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                comment_id = item["id"]
                user_id = snippet.get("authorChannelId", {}).get("value", "")
                user_name = snippet.get("authorDisplayName", "Unknown")
                comment_text = snippet.get("textDisplay", "")
                like_count = int(snippet.get("likeCount", 0))
                reply_count = int(item["snippet"].get("totalReplyCount", 0))
                published_at_str = snippet.get("publishedAt")
                published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                
                # Insert or Update Comment
                cursor.execute(
                    """
                    INSERT INTO comments (
                        comment_id, video_id, user_id, user_name, 
                        comment_text, like_count, reply_count, 
                        comment_published_at, scraped_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (comment_id)
                    DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        user_name = EXCLUDED.user_name,
                        comment_text = EXCLUDED.comment_text,
                        like_count = EXCLUDED.like_count,
                        reply_count = EXCLUDED.reply_count,
                        comment_published_at = EXCLUDED.comment_published_at,
                        scraped_at = NOW()
                    """,
                    (comment_id, video_id, user_id, user_name, comment_text, like_count, reply_count, published_at)
                )
                total_scraped += 1
                
            conn.commit()
            cursor.close()
            conn.close()
            
            next_page_token = response.get("nextPageToken")
            pages_processed += 1
            
            if not next_page_token:
                break
                
        return total_scraped
        
    except HttpError as e:
        raise CommentScraperError(f"YouTube API Error: {e.reason}")
    except Exception as e:
        raise CommentScraperError(f"Failed to scrape comments: {str(e)}")

def get_comments(db_config: dict, video_id: str = None):
    """Retrieves comments from database for a specific video or all."""
    conn = psycopg2.connect(**db_config)
    
    query = """
        SELECT c.comment_id, c.video_id, v.video_title, c.user_id, c.user_name, 
               c.comment_text, c.like_count, c.reply_count, c.comment_published_at
        FROM comments c
        LEFT JOIN videos v ON c.video_id = v.video_id
    """
    
    params = []
    if video_id:
        query += " WHERE c.video_id = %s"
        params.append(video_id)
        
    query += " ORDER BY c.comment_published_at DESC"
    
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def scrape_replies(
    *,
    api_key: str,
    db_config: dict,
    main_comment_id: str,
    max_pages: int = 1,
    max_results_per_page: int = 20
):
    """Scrapes replies for a specific YouTube comment and saves to database."""
    try:
        # 1. Initialize YouTube API
        youtube = build("youtube", "v3", developerKey=api_key)
        
        # Get video_id for this main_comment_id from DB
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT video_id FROM comments WHERE comment_id = %s", (main_comment_id,))
        res = cursor.fetchone()
        if not res:
            cursor.close()
            conn.close()
            raise CommentScraperError(f"Main comment {main_comment_id} not found in database. Scrape parents first.")
        
        video_id = res[0]
        
        # 2. Fetch Replies
        next_page_token = None
        pages_processed = 0
        total_scraped = 0
        
        while pages_processed < max_pages:
            request = youtube.comments().list(
                part="snippet", 
                parentId=main_comment_id,
                maxResults=min(max_results_per_page, 100),
                pageToken=next_page_token,
                textFormat="plainText"
            )
            response = request.execute()
            
            items = response.get("items", [])
            if not items:
                break
                
            for item in items:
                snippet = item["snippet"]
                reply_id = item["id"]
                user_id = snippet.get("authorChannelId", {}).get("value", "")
                user_name = snippet.get("authorDisplayName", "Unknown")
                reply_text = snippet.get("textDisplay", "")
                published_at_str = snippet.get("publishedAt")
                published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                
                # Insert or Update Reply
                cursor.execute(
                    """
                    INSERT INTO comment_replies (
                        reply_id, main_comment_id, video_id, user_id, user_name,
                        reply_text, reply_published_at, scraped_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (reply_id)
                    DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        user_name = EXCLUDED.user_name,
                        reply_text = EXCLUDED.reply_text,
                        reply_published_at = EXCLUDED.reply_published_at,
                        scraped_at = NOW()
                    """,
                    (reply_id, main_comment_id, video_id, user_id, user_name, reply_text, published_at)
                )
                total_scraped += 1
                
            conn.commit()
            
            next_page_token = response.get("nextPageToken")
            pages_processed += 1
            
            if not next_page_token:
                break
        
        cursor.close()
        conn.close()
        return total_scraped
        
    except HttpError as e:
        raise CommentScraperError(f"YouTube API Error: {e.reason}")
    except Exception as e:
        raise CommentScraperError(f"Failed to scrape replies: {str(e)}")

def get_replies(db_config: dict, main_comment_id: str = None):
    """Retrieves replies from database for a specific comment or all."""
    conn = psycopg2.connect(**db_config)
    
    query = """
        SELECT r.reply_id, r.main_comment_id, c.comment_text as parent_comment, 
               r.video_id, v.video_title, r.user_id, r.user_name,
               r.reply_text, r.reply_published_at
        FROM comment_replies r
        LEFT JOIN comments c ON r.main_comment_id = c.comment_id
        LEFT JOIN videos v ON r.video_id = v.video_id
    """
    
    params = []
    if main_comment_id:
        query += " WHERE r.main_comment_id = %s"
        params.append(main_comment_id)
        
    query += " ORDER BY r.reply_published_at DESC"
    
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df
