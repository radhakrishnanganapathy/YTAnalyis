# YouTube Comment Analysis & Viewer Opinion Tool

## Project Overview
This project aims to build a comprehensive YouTube data analysis tool that scrapes video metadata, comments, and replies using the YouTube Data API v3. The data is stored in a PostgreSQL database and visualized through a Streamlit interface. Key features include tracking viewer opinions, analyzing specific comment poll replies, and managing data scraping status.

## Tech Stack
- **UI Framework**: Streamlit
- **Database**: PostgreSQL
- **API**: YouTube Data API v3
- **Language**: Python

## Data Model (PostgreSQL)

### 1. Channels
- **`channels` (Static)**:
    - `channel_id` (PK): Unique ID of the channel.
    - `channel_name`: Name of the channel.
    - `published_at`: Date and time the channel was created.
    - `created_at`: Metadata for database insertion.
- **`channel_stats` (Dynamic)**:
    - `channel_id` (FK): Links to `channels`.
    - `subscribers_count`: Current subscriber count.
    - `total_video_count`: Total number of videos uploaded.
    - `total_view_count`: Total views across the channel.
    - `description`: Channel description.
    - `profile_picture`: URL to the profile image.
    - `banner_image`: URL to the banner image.
    - `last_scraped_at`: Timestamp of the last data update.

### 2. Videos
- **`videos` (Static)**:
    - `video_id` (PK): Unique ID of the video.
    - `channel_id` (FK): Links to `channels`.
    - `video_title`: Title of the video.
    - `published_at`: Date and time the video was published.
    - `video_category`: Category (e.g., entertainment, cinema, politics, etc.).
    - `format_type`: Whether it's a 'video' or 'shorts'.
- **`video_stats` (Dynamic)**:
    - `video_id` (FK): Links to `videos`.
    - `view_count`: Current view count.
    - `like_count`: Total likes.
    - `comment_count`: Total number of comments.
    - `description`: Video description.
    - `tags`: Array of video tags.
    - `hashtags`: Array of hashtags used.
    - `last_scraped_at`: Timestamp of the last data update.

### 3. Comments & Replies
- **`comments`**:
    - `comment_id` (PK): Unique ID of the comment.
    - `video_id` (FK): Links to `videos`.
    - `user_id`: ID of the user who commented.
    - `comment_text`: The content of the comment.
    - `comment_published_at`: Original publish time.
    - `scraped_at`: When the comment was captured.
- **`comment_replies`**:
    - `reply_id` (PK): Unique ID of the reply.
    - `main_comment_id` (FK): Links to the parent comment in `comments`.
    - `video_id` (FK): Links to `videos`.
    - `user_id`: ID of the user who replied.
    - `reply_text`: Content of the reply.
    - `reply_published_at`: Original publish time.
    - `scraped_at`: When the reply was captured.
- **`comment_likes`**:
    - `comment_id` (PK, FK): Links to `comments`.
    - `video_id` (FK): Links to `videos`.
    - `like_count`: Total likes for the specific comment.
    - `scraped_at`: Timestamp of the reading.

### 4. Tracking
- **`tracking`**:
    - `track_id` (PK): Auto-incremented ID.
    - `track_type`: Enum ('video', 'channel', 'comment', 'reply').
    - `target_id`: ID of the item being tracked.
    - `name`: Human-readable name (e.g., video title or channel name).
    - `start_date`: When tracking was initiated.
    - `planned_end_date`: Target end date for tracking.
    - `actual_end_date`: When tracking actually finished.
    - `status`: Enum ('todo', 'process', 'cancel', 'done').
    - `description`: Additional notes or context.

## Key Features

### 1. Opinion Analysis (Comment Scraping)
- Scrape all comments for a specific channel's video (e.g., Madan Gowri).
- Perform sentiment or opinion analysis on viewer comments.

### 2. Poll & Reply Analysis
- Targeted scraping of replies for a specific "poll comment" (e.g., World Cup T20 predictions).
- **Duplicate Removal**: Automatically filter out multiple replies from the same user ID to ensure "one user, one vote" accuracy.
- Analysis of reply patterns and options provided in the poll.

### 3. Comprehensive Metadata Extraction
- Manual input for video type if not auto-detected.
- Support for both standard videos and YouTube Shorts.
- Tracking of historical stats across multiple scrapings.

### 4. Progress Tracking
- A centralized board to manage ongoing scraping tasks.
- Status updates (Process, Todo, Cancel, Done) for better workflow management.
