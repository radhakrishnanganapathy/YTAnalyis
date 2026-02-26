import psycopg2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime
import pandas as pd
import re

class VideoScraperError(Exception):
    pass

def parse_duration(duration_str):
    """Parses ISO 8601 duration string into seconds."""
    pattern = re.compile(r'P(?:(?P<days>\d+)D)?T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?')
    match = pattern.match(duration_str)
    if not match:
        return 0
    
    parts = match.groupdict()
    days = int(parts['days'] or 0)
    hours = int(parts['hours'] or 0)
    minutes = int(parts['minutes'] or 0)
    seconds = int(parts['seconds'] or 0)
    
    return days * 86400 + hours * 3600 + minutes * 60 + seconds

def select_video_category(channel_id: str, db_config: dict):
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT category FROM channels WHERE channel_id = %s", (channel_id,))
    category = cursor.fetchone()
    cursor.close()
    conn.close()
    if category:
        return category[0]
    return None

def select_channel_name(db_config: dict):
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id, channel_name FROM channels")
    channel_names = cursor.fetchall()
    cursor.close()
    conn.close()
    if not channel_names:
        return {}
    return {name: cid for cid, name in channel_names}

def get_videos(db_config: dict, channel_id=None):
    conn = psycopg2.connect(**db_config)
    query = """
        SELECT v.video_id,
               v.video_title,
               v.published_at,
               c.channel_name,
               v.video_category,
               v.format_type,
               v.duration,
               vs.view_count,
               vs.like_count,
               vs.comment_count
        FROM videos v
        LEFT JOIN video_stats vs
        ON v.video_id = vs.video_id
        LEFT JOIN channels c
        ON v.channel_id = c.channel_id
    """

    if channel_id and channel_id != "All":
        query += f" WHERE v.channel_id = '{channel_id}' order by v.published_at desc"

    df = pd.read_sql(query, conn)
    conn.close()
    return df

def scrape_video_by_id(
    *,
    video_id: str,
    api_key: str,
    db_config: dict,
    category: str
):
    """Scrapes YouTube video details by ID and saves to Database."""
    
    try:
        # 1. Initialize YouTube API
        youtube = build("youtube", "v3", developerKey=api_key)
        
        # 2. Call YouTube API
        request = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=video_id
        )
        response = request.execute()
        
    except HttpError as e:
        raise VideoScraperError(f"YouTube API Error: {e.reason}")
    except Exception as e:
        raise VideoScraperError(f"Failed to connect to YouTube API: {str(e)}")

    if not response.get("items"):
        raise VideoScraperError(f"Video not found: {video_id}")

    video_data = response["items"][0]
    snippet = video_data["snippet"]
    stats = video_data["statistics"]
    content_details = video_data["contentDetails"]

    # Extract fields
    video_title = snippet["title"]
    channel_id = snippet["channelId"]
    published_at_str = snippet["publishedAt"]
    published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))

    description = snippet.get("description", "")
    tags = snippet.get("tags", [])
    
    # Process Duration and Type
    duration_str = content_details.get("duration", "PT0S")
    duration_seconds = parse_duration(duration_str)
    
    # Requirement: less than 60sec in shorts, greater than 60 in videos
    format_type = "shorts" if duration_seconds <= 60 else "video"

    view_count = int(stats.get("viewCount", 0))
    like_count = int(stats.get("likeCount", 0))
    comment_count = int(stats.get("commentCount", 0))

    # 3. Save to Database
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # Check if video exists
        cursor.execute("SELECT video_id FROM videos WHERE video_id = %s", (video_id,))
        exists = cursor.fetchone()

        if not exists:
            # Insert into videos
            cursor.execute(
                """
                INSERT INTO videos (
                    video_id, channel_id, video_title, published_at, 
                    video_category, format_type, duration
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (video_id, channel_id, video_title, published_at, category, format_type, duration_seconds)
            )
        else:
            # Update videos (in case category or title changed)
            cursor.execute(
                """
                UPDATE videos SET
                    video_title = %s,
                    video_category = %s,
                    format_type = %s,
                    duration = %s
                WHERE video_id = %s
                """,
                (video_title, category, format_type, duration_seconds, video_id)
            )

        # Upsert video_stats
        cursor.execute(
            """
            INSERT INTO video_stats (
                video_id, view_count, comment_count, like_count, 
                description, tags, last_scraped_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (video_id)
            DO UPDATE SET
                view_count = EXCLUDED.view_count,
                comment_count = EXCLUDED.comment_count,
                like_count = EXCLUDED.like_count,
                description = EXCLUDED.description,
                tags = EXCLUDED.tags,
                last_scraped_at = NOW()
            """,
            (video_id, view_count, comment_count, like_count, description, tags)
        )

        conn.commit()
    except Exception as db_error:
        if conn:
            conn.rollback()
        raise VideoScraperError(f"Database error: {str(db_error)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return {
        "video_id": video_id,
        "title": video_title,
        "channel_id": channel_id,
        "duration": duration_seconds,
        "format": format_type
    }

def scrape_channel_videos(
    api_key: str,
    db_config: dict,
    channel_id: str,
    video_type: str, # "video" or "shorts"
    max_pages: int,
    max_videos_per_page: int
):
    """Scrapes multiple videos from a channel with pagination and type validation."""
    
    # 1. First, get the Channel's category from our DB to assign to all its videos
    category = select_video_category(channel_id, db_config)
    if not category:
        # Fallback if channel not in DB yet, though it should be
        category = "Other"

    try:
        youtube = build("youtube", "v3", developerKey=api_key)
        
        # 2. Get the 'Uploads' playlist ID for this channel
        ch_response = youtube.channels().list(
            part="contentDetails",
            id=channel_id
        ).execute()
        
        if not ch_response.get("items"):
            raise VideoScraperError(f"Channel not found: {channel_id}")
            
        uploads_playlist_id = ch_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        
        # 3. Pagination Logic
        next_page_token = None
        total_scraped = 0
        pages_processed = 0
        
        # Limit maxResults to 50 (YouTube API limit)
        max_results = min(max_videos_per_page, 50)
        
        while pages_processed < max_pages:
            # Fetch video IDs from playlist
            pl_request = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=max_results,
                pageToken=next_page_token
            )
            pl_response = pl_request.execute()
            
            video_ids = [item["contentDetails"]["videoId"] for item in pl_response.get("items", [])]
            
            if not video_ids:
                break
                
            # Fetch full details for these videos to check duration
            v_request = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids)
            )
            v_response = v_request.execute()
            
            for video_data in v_response.get("items", []):
                v_id = video_data["id"]
                content_details = video_data["contentDetails"]
                duration_str = content_details.get("duration", "PT0S")
                duration_seconds = parse_duration(duration_str)
                
                # Validation Logic:
                # Video: > 60 seconds
                # Shorts: <= 60 seconds
                is_match = False
                if video_type == "shorts" and duration_seconds <= 60:
                    is_match = True
                elif video_type == "video" and duration_seconds > 60:
                    is_match = True
                
                if is_match:
                    # Reuse the existing scrape logic for DB insertion
                    # Note: We call it with already fetched data or just call the function by ID
                    # To keep it simple, we just call our existing function
                    scrape_video_by_id(
                        video_id=v_id,
                        api_key=api_key,
                        db_config=db_config,
                        category=category
                    )
                    total_scraped += 1
            
            next_page_token = pl_response.get("nextPageToken")
            pages_processed += 1
            
            if not next_page_token:
                break
                
        return total_scraped

    except Exception as e:
        raise VideoScraperError(f"Channel Scrape Failed: {str(e)}")