import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}

def update_schema():
    conn = psycopg2.connect(**DB_CONFIG)
    curr = conn.cursor()
    
    # Update comments table
    curr.execute("ALTER TABLE comments ADD COLUMN IF NOT EXISTS user_name TEXT;")
    curr.execute("ALTER TABLE comments ADD COLUMN IF NOT EXISTS like_count BIGINT;")
    curr.execute("ALTER TABLE comments ADD COLUMN IF NOT EXISTS reply_count BIGINT;")
    
    conn.commit()
    curr.close()
    conn.close()
    print("Database schema updated successfully!")

if __name__ == "__main__":
    update_schema()
