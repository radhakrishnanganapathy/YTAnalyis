import streamlit as st
import psycopg2
import pandas as pd
from dotenv import load_dotenv
from functions import ChannelScraper
from functions import VideoScraper
import os
load_dotenv()

# ==============================
# PAGE CONFIG
# ==============================
st.set_page_config(
    page_title="YT Analytics",
    layout="wide"
)

# ==============================
# DB CONFIG
# ==============================
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT")
}

YT_API_KEY = os.getenv("YT_API_KEY")


# ==============================
# SIDEBAR
# ==============================
st.sidebar.title("📊 YT Analytics")
menu = st.sidebar.radio("Menu", ["Dashboard", "Channels","Videos", "Comments"])

# ==============================
# DASHBOARD PAGE
# ==============================
if menu == "Dashboard":
    st.title("Dashboard")
    st.info("Welcome to YouTube Analytics Platform 🚀")

# ==============================
# CHANNEL PAGE
# ==============================
if menu == "Channels":

    col1, col2 = st.columns([8, 1])

    with col1:
        st.title("Channels")

    with col2:
        if st.button("➕ Add"):
            st.session_state.show_add_channel = True

    st.divider()
    categories = ChannelScraper.get_channel_categories(db_config=DB_CONFIG)
    # Category Filter
    category_filter = st.selectbox(
        "Filter by Category",
        ["All"] + categories
    )

    df = ChannelScraper.get_channels(category_filter=category_filter, db_config=DB_CONFIG)

    st.write(f"Total Channels: {len(df)}")

    # Sort by subscribers (optional but recommended)
    if not df.empty:
        df = df.sort_values("subscribers_count", ascending=False)

    st.divider()

    # ==============================
    # TABLE HEADER
    # ==============================
    header_cols = st.columns([1, 3, 2, 2, 2, 2, 2, 1])

    headers = [
        "Profile",
        "Channel Name",
        "Category",
        "Subscribers",
        "Videos",
        "Views",
        "Published",
        "Action"
    ]

    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    st.divider()



    # ==============================
    # TABLE ROWS
    # ==============================
    for _, row in df.iterrows():

        cols = st.columns([1, 3, 2, 2, 2, 2, 2, 1])

        # Profile Picture
        if row["profile_picture"]:
            cols[0].image(row["profile_picture"], width=50)
        else:
            cols[0].write("-")

        # Channel Name
        cols[1].write(row["channel_name"])

        # Category
        cols[2].write(row["category"])

        # Subscribers
        subs = row["subscribers_count"] or 0
        cols[3].write(f"{subs:,}")

        # Videos
        vids = row["total_video_count"] or 0
        cols[4].write(f"{vids:,}")

        # Views
        views = row["total_view_count"] or 0
        cols[5].write(f"{views:,}")

        # Published Date
        cols[6].write(row["published_at"])

        # Delete Button
        if cols[7].button("🗑", key=f"delete_{row['channel_id']}"):
            ChannelScraper.delete_channel(row["channel_id"], db_config=DB_CONFIG)
            st.success("Channel deleted successfully")
            st.rerun()

        st.divider()


    # ==============================
    # ADD CHANNEL FORM
    # ==============================
    if st.session_state.get("show_add_channel"):

        with st.form("add_channel_form"):
            st.subheader("Add New Channel")
            categories = ChannelScraper.get_channel_categories(db_config=DB_CONFIG)


            channel_input = st.text_input(
                "Channel ID or Username"
            )

            category = st.selectbox(
                "Channel Category",
                categories
            )

            submitted = st.form_submit_button("Scrape Channel")

            if submitted:
                if not channel_input:
                    st.error("Channel ID or Username required")
                else:
                    # Here later we call scraper function
                    channel = ChannelScraper.scrape_channel(
                        api_key=YT_API_KEY,
                        db_config=DB_CONFIG,
                        channel_id=channel_input,
                        category=category
                    )
                    st.success("Scraping will be implemented next 🚀")
                    st.session_state.show_add_channel = False



# ==============================
# VIDEO PAGE
# ==============================
if menu == "Videos":

    col1, col2 = st.columns([8, 1])

    with col1:
        st.title("Videos")

    with col2:
        if st.button("➕ Add"):
            st.session_state.show_add_video = True

    st.divider()

    channel_dict = VideoScraper.select_channel_name(db_config=DB_CONFIG)
    channel_options = ["All"] + list(channel_dict.keys())

    # Category Filter
    selected = st.selectbox(
    "Filter by Channel",
    channel_options,
    )

    # Get channel_id for backend
    if selected != "All":
        selected_channel_id = channel_dict[selected]
    else:
        selected_channel_id = None
    st.divider()
    df = VideoScraper.get_videos(channel_id=selected_channel_id, db_config=DB_CONFIG)

    st.write(f"Total Videos: {len(df)}")


    # ==============================
    # TABLE HEADER
    # ==============================
    header_cols = st.columns([4, 1, 2, 1, 1, 1, 1, 1, 2, 1])

    headers = [
        "Video Title",
        "Category",
        "Channel Name",
        "Type",
        "Duration",
        "Views",
        "Likes",
        "Comments",
        "Published",
        "Action"
    ]

    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    st.divider()

    # ==============================
    # TABLE ROWS
    # ==============================
    for _, row in df.iterrows():
        cols = st.columns([4, 1, 2, 1, 1, 1, 1, 1, 2, 1])
        
        cols[0].write(row["video_title"])
        cols[1].write(row["video_category"])
        cols[2].write(row["channel_name"])
        cols[3].write(row["format_type"])
        
        # Duration format
        dur = row["duration"] or 0
        minutes = dur // 60
        secs = dur % 60
        cols[4].write(f"{minutes:02d}:{secs:02d}")
        
        cols[5].write(f"{int(row['view_count'] or 0):,}")
        cols[6].write(f"{int(row['like_count'] or 0):,}")
        cols[7].write(f"{int(row['comment_count'] or 0):,}")
        cols[8].write(row["published_at"].strftime("%Y-%m-%d %H:%M:%S") if row["published_at"] else "-")
        
        if cols[9].button("🗑", key=f"del_vid_{row['video_id']}"):
            # Add a delete function in VideoScraper if needed, or just run query
            msg = st.empty()
            try:
                conn = psycopg2.connect(**DB_CONFIG)
                curr = conn.cursor()
                curr.execute("DELETE FROM videos WHERE video_id = %s", (row["video_id"],))
                conn.commit()
                curr.close()
                conn.close()
                st.success("Video deleted")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

        st.divider()

    # ==============================
    # ADD VIDEO FORM
    # ==============================
    categories = ChannelScraper.get_channel_categories(db_config=DB_CONFIG)
    if st.session_state.get("show_add_video"):
        scrape_type = st.radio("Video Scrape Type", ["Single Video", "Entire Channel"], key="video_scrape_type")
        
        if scrape_type == "Single Video":
            with st.form("add_video_form"):
                st.subheader("Add New Video")
                video_input = st.text_input("Video ID", key="video_id_input")
                video_category = st.selectbox("Video Category", categories)
                
                submitted = st.form_submit_button("Scrape Video")

                if submitted:
                    if not video_input:
                        st.error("Video ID required")
                    else:
                        try:
                            result = VideoScraper.scrape_video_by_id(
                                api_key=YT_API_KEY,
                                db_config=DB_CONFIG,
                                video_id=video_input,
                                category=video_category
                            )
                            st.success(f"Successfully scraped: {result['title']}")
                            st.session_state.show_add_video = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
        
        elif scrape_type == "Entire Channel":
            st.info("Channel scraping to be implemented...")
            with st.form("add_video_form"):
                col1, col2 = st.columns(2)

                channel_id = col1.text_input("Channel ID")
                video_type = col2.selectbox(
                    "Video Type",
                    ["video", "shorts"]
                )

                col3, col4 = st.columns(2)
                max_pages = col3.number_input("Max Pages", min_value=1, value=1)
                max_videos_per_page = col4.number_input("Max Videos Per Page", min_value=1, value=10)

                submitted = st.form_submit_button("Scrape Channel")

                if submitted:
                    if not channel_id:
                        st.error("Channel ID required")
                    else:
                        try:
                            result = VideoScraper.scrape_channel_videos(
                                api_key=YT_API_KEY,
                                db_config=DB_CONFIG,
                                channel_id=channel_id,
                                video_type=video_type,
                                max_pages=max_pages,
                                max_videos_per_page=max_videos_per_page
                            )
                            st.success(f"Successfully scraped: {result['title']}")
                            st.session_state.show_add_video = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
            if st.button("Close"):
                st.session_state.show_add_video = False
                st.rerun()

