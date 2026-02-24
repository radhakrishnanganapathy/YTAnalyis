import psycopg2
from psycopg2.extras import RealDictCursor
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime
import pandas as pd
import os
class ChannelScraperError(Exception):
    pass

def get_channels(db_config: dict, category_filter=None):
    conn = psycopg2.connect(**db_config)
    query = """
        SELECT c.channel_id,
               c.channel_name,
               c.category,
               c.published_at,
               cs.subscribers_count,
               cs.total_video_count,
               cs.total_view_count,
               cs.profile_picture
        FROM channels c
        LEFT JOIN channel_stats cs
        ON c.channel_id = cs.channel_id
    """

    if category_filter and category_filter != "All":
        query += f" WHERE c.category = '{category_filter}'"

    df = pd.read_sql(query, conn)
    conn.close()
    return df

def get_channel_categories(db_config: dict):
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT enumlabel
        FROM pg_enum
        JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
        WHERE pg_type.typname = 'video_category_enum'
        ORDER BY enumsortorder;
    """)

    categories = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return categories

def delete_channel(channel_id: str, db_config: dict):
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM channels WHERE channel_id = %s", (channel_id,))
    cursor.execute("DELETE FROM channel_stats WHERE channel_id = %s", (channel_id,))

    conn.commit()
    cursor.close()
    conn.close()

def scrape_channel(
    api_key: str,
    db_config: dict,
    channel_id: str = None,
    username: str = None,
    category: str = None
):
    """
    Scrape a YouTube channel by channel_id or username.
    Inserts into channels if not exists.
    Updates channel_stats always.
    """

    if not channel_id and not username:
        raise ValueError("Provide either channel_id or username")

    # Initialize YouTube API
    try:
        youtube = build("youtube", "v3", developerKey=api_key)
    except Exception as e:
        raise ChannelScraperError("Invalid API key or API initialization failed") from e

    try:
        if channel_id:
            request = youtube.channels().list(
                part="snippet,statistics,brandingSettings",
                id=channel_id
            )
        else:
            request = youtube.channels().list(
                part="snippet,statistics,brandingSettings",
                forUsername=username
            )

        response = request.execute()

    except HttpError as e:
        if e.resp.status == 403:
            if "quotaExceeded" in str(e):
                raise ChannelScraperError("API quota exceeded")
            else:
                raise ChannelScraperError("Invalid API key or access forbidden")
        elif e.resp.status == 400:
            raise ChannelScraperError("Invalid channel ID or username")
        else:
            raise ChannelScraperError(f"YouTube API error: {str(e)}")

    # Channel not found
    if not response.get("items"):
        raise ChannelScraperError("Channel not found (wrong ID or username)")

    data = response["items"][0]

    # Extract fields
    channel_id = data["id"]
    snippet = data["snippet"]
    stats = data["statistics"]
    branding = data.get("brandingSettings", {})

    channel_name = snippet["title"]
    published_at = snippet.get("publishedAt")
    description = snippet.get("description")
    profile_picture = snippet["thumbnails"]["high"]["url"]

    banner_image = (
        branding.get("image", {}).get("bannerExternalUrl")
    )

    subscribers_count = int(stats.get("subscriberCount", 0))
    total_video_count = int(stats.get("videoCount", 0))
    total_view_count = int(stats.get("viewCount", 0))

    # Convert published_at to datetime
    if published_at:
        published_at = datetime.fromisoformat(
            published_at.replace("Z", "+00:00")
        )

    # Connect to PostgreSQL
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Check if channel exists
        cursor.execute(
            "SELECT channel_id FROM channels WHERE channel_id = %s",
            (channel_id,)
        )
        exists = cursor.fetchone()

        # Insert if not exists
        if not exists:
            cursor.execute(
                """
                INSERT INTO channels (channel_id, channel_name, published_at, category)
                VALUES (%s, %s, %s, %s)
                """,
                (channel_id, channel_name, published_at, category)
            )

        # Upsert channel_stats
        cursor.execute(
            """
            INSERT INTO channel_stats (
                channel_id,
                subscribers_count,
                total_video_count,
                total_view_count,
                description,
                profile_picture,
                banner_image,
                last_scraped_at
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (channel_id)
            DO UPDATE SET
                subscribers_count = EXCLUDED.subscribers_count,
                total_video_count = EXCLUDED.total_video_count,
                total_view_count = EXCLUDED.total_view_count,
                description = EXCLUDED.description,
                profile_picture = EXCLUDED.profile_picture,
                banner_image = EXCLUDED.banner_image,
                last_scraped_at = EXCLUDED.last_scraped_at
            """,
            (
                channel_id,
                subscribers_count,
                total_video_count,
                total_view_count,
                description,
                profile_picture,
                banner_image,
                datetime.utcnow()
            )
        )

        conn.commit()

    except Exception as db_error:
        conn.rollback()
        raise ChannelScraperError(f"Database error: {str(db_error)}")

    finally:
        cursor.close()
        conn.close()

    return {
        "channel_id": channel_id,
        "channel_name": channel_name,
        "subscribers": subscribers_count,
        "videos": total_video_count,
        "views": total_view_count,
        "status": "success"
    }