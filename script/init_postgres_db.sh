#!/bin/bash

# ==============================
# PostgreSQL Initialization Script
# ==============================

DB_NAME="youtube_analytics"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT="5432"

echo "🚀 Initializing PostgreSQL database..."

# Create database if not exists
psql -U $DB_USER -h $DB_HOST -p $DB_PORT -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
psql -U $DB_USER -h $DB_HOST -p $DB_PORT -c "CREATE DATABASE $DB_NAME"

echo "✅ Database checked/created."

# Run schema creation
psql -U $DB_USER -h $DB_HOST -p $DB_PORT -d $DB_NAME <<'EOF'

-- ==============================
-- ENUM TYPES
-- ==============================

DO $$ BEGIN
    CREATE TYPE video_category_enum AS ENUM (
        'entertainment','cinema','politics','infotainment',
        'news','vlog','education','sports',
        'kids','animals','photography','adult',
        'nature','cooking','art','others'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE video_format_enum AS ENUM ('video','shorts');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE track_type_enum AS ENUM ('video','channel','comment','reply');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE track_status_enum AS ENUM ('todo','process','cancel','done');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ==============================
-- CHANNEL TABLES
-- ==============================

CREATE TABLE IF NOT EXISTS channels (
    channel_id VARCHAR PRIMARY KEY,
    channel_name TEXT NOT NULL,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE channels ADD COLUMN IF NOT EXISTS category video_category_enum;

CREATE TABLE IF NOT EXISTS channel_stats (
    channel_id VARCHAR REFERENCES channels(channel_id) ON DELETE CASCADE,
    subscribers_count BIGINT,
    total_video_count BIGINT,
    total_view_count BIGINT,
    description TEXT,
    profile_picture TEXT,
    banner_image TEXT,
    last_scraped_at TIMESTAMP,
    PRIMARY KEY (channel_id)
);

-- ==============================
-- VIDEO TABLES
-- ==============================

CREATE TABLE IF NOT EXISTS videos (
    video_id VARCHAR PRIMARY KEY,
    channel_id VARCHAR REFERENCES channels(channel_id) ON DELETE CASCADE,
    video_title TEXT NOT NULL,
    published_at TIMESTAMP,
    video_category video_category_enum,
    format_type video_format_enum
);

CREATE TABLE IF NOT EXISTS video_stats (
    video_id VARCHAR REFERENCES videos(video_id) ON DELETE CASCADE,
    view_count BIGINT,
    like_count BIGINT,
    comment_count BIGINT,
    description TEXT,
    tags TEXT[],
    hashtags TEXT[],
    last_scraped_at TIMESTAMP,
    PRIMARY KEY (video_id)
);

-- ==============================
-- COMMENTS
-- ==============================

CREATE TABLE IF NOT EXISTS comments (
    comment_id VARCHAR PRIMARY KEY,
    video_id VARCHAR REFERENCES videos(video_id) ON DELETE CASCADE,
    user_id VARCHAR,
    comment_text TEXT,
    comment_published_at TIMESTAMP,
    scraped_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS comment_replies (
    reply_id VARCHAR PRIMARY KEY,
    main_comment_id VARCHAR REFERENCES comments(comment_id) ON DELETE CASCADE,
    video_id VARCHAR REFERENCES videos(video_id) ON DELETE CASCADE,
    user_id VARCHAR,
    reply_text TEXT,
    reply_published_at TIMESTAMP,
    scraped_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS comment_likes (
    comment_id VARCHAR PRIMARY KEY REFERENCES comments(comment_id) ON DELETE CASCADE,
    video_id VARCHAR REFERENCES videos(video_id) ON DELETE CASCADE,
    like_count BIGINT,
    scraped_at TIMESTAMP
);

-- ==============================
-- TRACKING TABLE
-- ==============================

CREATE TABLE IF NOT EXISTS tracking (
    track_id SERIAL PRIMARY KEY,
    track_type track_type_enum,
    target_id VARCHAR,
    name TEXT,
    start_date TIMESTAMP,
    planned_end_date TIMESTAMP,
    actual_end_date TIMESTAMP,
    status track_status_enum DEFAULT 'todo',
    description TEXT
);

-- ==============================
-- INDEXES (Performance Boost)
-- ==============================

CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id);
CREATE INDEX IF NOT EXISTS idx_comments_video_id ON comments(video_id);
CREATE INDEX IF NOT EXISTS idx_comment_replies_main_comment_id ON comment_replies(main_comment_id);
CREATE INDEX IF NOT EXISTS idx_tracking_target_id ON tracking(target_id);

EOF

echo "🎉 Database schema initialized successfully!"