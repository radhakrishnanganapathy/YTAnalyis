import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from dotenv import load_dotenv
from functions import ChannelScraper
from functions import VideoScraper
from functions import CommentScraper
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
menu = st.sidebar.radio("Menu", ["Dashboard", "Channels","Videos", "Comments", "Replays", "Analysis"])

# ==============================
# DASHBOARD PAGE
# ==============================
if menu == "Dashboard":
    st.title("Dashboard")
    st.info("Welcome to YouTube Analytics Platform , Lets Explore the YT 🚀")

# ==============================
# CHANNEL PAGE
# ==============================
if menu == "Channels":
    # Detail View Check
    if "selected_channel_id" in st.session_state and st.session_state.selected_channel_id:
        channel_id = st.session_state.selected_channel_id
        details = ChannelScraper.get_channel_details(channel_id, db_config=DB_CONFIG)
        
        if details:
            if st.button("⬅️ Back to Channels"):
                st.session_state.selected_channel_id = None
                st.rerun()
            
            # Refresh Button
            if st.button("🔄 Refresh Data"):
                with st.spinner("Refreshing..."):
                    try:
                        ChannelScraper.scrape_channel(
                            api_key=YT_API_KEY,
                            db_config=DB_CONFIG,
                            channel_id=channel_id,
                            category=details["category"]
                        )
                        st.success("Refreshed!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

            st.title(details["channel_name"])
            
            st.divider()
            
            # Description
            st.subheader("Description")
            st.write(details["description"])
            
            st.divider()
            
            # Keywords/Tags
            if details["keywords"]:
                st.subheader("Keywords")
                # Display keywords as tags
                tags_html = "".join([f'<span style="background-color: #444444; color: #ffffff; border-radius: 10px; padding: 5px 10px; margin: 5px; display: inline-block;">{k}</span>' for k in details["keywords"]])
                st.markdown(tags_html, unsafe_allow_html=True)
            
            st.stop() # Skip list view

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
    header_cols = st.columns([1, 3, 2, 2, 2, 2, 2, 1, 1])

    headers = [
        "Profile",
        "Channel Name",
        "Category",
        "Subscribers",
        "Videos",
        "Views",
        "Published",
        "View",
        "Delete"
    ]

    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    st.divider()

    # ==============================
    # TABLE ROWS
    # ==============================
    for _, row in df.iterrows():

        cols = st.columns([1, 3, 2, 2, 2, 2, 2, 1, 1])

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

        # View Button
        if cols[7].button("👁️", key=f"view_{row['channel_id']}"):
            st.session_state.selected_channel_id = row['channel_id']
            st.rerun()

        # Delete Button
        if cols[8].button("🗑", key=f"delete_{row['channel_id']}"):
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
    # Video Detail View
    if "selected_video_id" in st.session_state and st.session_state.selected_video_id:
        video_id = st.session_state.selected_video_id
        
        # We need a function to get video details
        conn = psycopg2.connect(**DB_CONFIG)
        curr = conn.cursor(cursor_factory=RealDictCursor)
        curr.execute("""
            SELECT v.*, vs.*, c.channel_name 
            FROM videos v 
            JOIN video_stats vs ON v.video_id = vs.video_id 
            JOIN channels c ON v.channel_id = c.channel_id
            WHERE v.video_id = %s
        """, (video_id,))
        v_details = curr.fetchone()
        curr.close()
        conn.close()
        
        if v_details:
            if st.button("⬅️ Back to Videos"):
                st.session_state.selected_video_id = None
                st.rerun()
            
            st.title(v_details["video_title"])
            
            st.divider()
            
            # Description
            st.subheader("Description")
            st.text_area("Description", v_details["description"], height=400, disabled=True)
            
            st.divider()
            
            # Tags and Hashtags
            col_tags, col_hash = st.columns(2)
            with col_tags:
                st.subheader("Tags")
                if v_details["tags"]:
                    tags_html = "".join([f'<span style="background-color: #01579b; color: #ffffff; border-radius: 10px; padding: 5px 10px; margin: 5px; display: inline-block;">{t}</span>' for t in v_details["tags"]])
                    st.markdown(tags_html, unsafe_allow_html=True)
                else:
                    st.write("No tags")
            
            with col_hash:
                st.subheader("Hashtags")
                if v_details["hashtags"]:
                    hash_html = "".join([f'<span style="background-color: #4a148c; color: #ffffff; border-radius: 10px; padding: 5px 10px; margin: 5px; display: inline-block;">{h}</span>' for h in v_details["hashtags"]])
                    st.markdown(hash_html, unsafe_allow_html=True)
                else:
                    st.write("No hashtags")
            
            st.stop()

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
    header_cols = st.columns([4, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1])

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
        "View",
        "Action"
    ]

    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    st.divider()

    # ==============================
    # TABLE ROWS
    # ==============================
    for _, row in df.iterrows():
        cols = st.columns([4, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1])
        
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
        
        # View Button
        if cols[9].button("👁️", key=f"v_view_{row['video_id']}"):
            st.session_state.selected_video_id = row['video_id']
            st.rerun()

        if cols[10].button("🗑", key=f"del_vid_{row['video_id']}"):
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

# ==============================
# COMMENTS PAGE
# ==============================
if menu == "Comments":
    st.title("Comments")
    
    # 1. Scraping Section
    with st.expander("➕ Scrape Comments", expanded=not st.session_state.get("show_comments_list", True)):
        with st.form("scrape_comments_form"):
            col1, col2, col3 = st.columns([2, 1, 1])
            video_id_input = col1.text_input("Enter Video ID")
            max_pages = col2.number_input("Max Pages", min_value=1, value=1)
            max_results_per_page = col3.number_input("Max Results / Page", min_value=1, value=20)
            
            submit_scrape = st.form_submit_button("Start Scraping")
            
            if submit_scrape:
                if not video_id_input:
                    st.error("Video ID is required")
                else:
                    with st.spinner("Scraping comments..."):
                        try:
                            scraped_count = CommentScraper.scrape_comments(
                                api_key=YT_API_KEY,
                                db_config=DB_CONFIG,
                                video_id=video_id_input,
                                max_pages=max_pages,
                                max_results_per_page=max_results_per_page
                            )
                            st.success(f"Successfully scraped {scraped_count} comments!")
                            st.session_state.show_comments_list = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error scraping comments: {str(e)}")

    # 2. Filter Section
    st.divider()
    
    # Selection for filtering by video
    # We can get a list of videos that have comments in our DB
    conn = psycopg2.connect(**DB_CONFIG)
    curr = conn.cursor()
    curr.execute("SELECT DISTINCT v.video_id, v.video_title FROM comments c JOIN videos v ON c.video_id = v.video_id")
    videos_with_comments = curr.fetchall()
    curr.close()
    conn.close()
    
    video_options = {"All Videos": None}
    for vid_id, vid_title in videos_with_comments:
        video_options[vid_title] = vid_id
        
    selected_video_title = st.selectbox("View Comments for Video:", list(video_options.keys()))
    selected_video_id = video_options[selected_video_title]
    
    # 3. List Comments
    comments_df = CommentScraper.get_comments(DB_CONFIG, video_id=selected_video_id)
    
    st.write(f"Showing **{len(comments_df)}** comments")
    
    if not comments_df.empty:
        # Table Header
        header_cols = st.columns([1, 2, 2, 4, 1, 1, 2])
        headers = ["Username", "Comment ID", "Video", "Comment", "Likes", "Replies", "Published At"]
        for col, h in zip(header_cols, headers):
            col.markdown(f"**{h}**")
        st.divider()
        
        # Table Rows
        for _, row in comments_df.iterrows():
            cols = st.columns([1, 2, 2, 4, 1, 1, 2])
            cols[0].write(row["user_name"])
            cols[1].code(row["comment_id"])
            cols[2].write(row["video_title"])
            cols[3].write(row["comment_text"])
            cols[4].write(f"{row['like_count']:,}")
            cols[5].write(f"{row['reply_count']:,}")
            cols[6].write(row["comment_published_at"].strftime("%Y-%m-%d %H:%M") if row["comment_published_at"] else "-")
            st.divider()
    else:
        st.info("No comments found for the selected filter.")

# ==============================
# REPLAYS PAGE
# ==============================
if menu == "Replays":
    st.title("Reply Comments")
    
    # 1. Scraping Section
    with st.expander("➕ Scrape Replies", expanded=True):
        with st.form("scrape_replies_form"):
            col1, col2, col3 = st.columns([2, 1, 1])
            main_comment_id_input = col1.text_input("Enter Main Comment ID")
            max_pages = col2.number_input("Max Pages", min_value=1, value=1)
            max_results_per_page = col3.number_input("Max Results / Page", min_value=1, value=20)
            
            submit_scrape = st.form_submit_button("Start Scraping Replies")
            
            if submit_scrape:
                if not main_comment_id_input:
                    st.error("Main Comment ID is required")
                else:
                    with st.spinner("Scraping replies..."):
                        try:
                            scraped_count = CommentScraper.scrape_replies(
                                api_key=YT_API_KEY,
                                db_config=DB_CONFIG,
                                main_comment_id=main_comment_id_input,
                                max_pages=max_pages,
                                max_results_per_page=max_results_per_page
                            )
                            st.success(f"Successfully scraped {scraped_count} replies!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error scraping replies: {str(e)}")

    # 2. Filter Section
    st.divider()
    
    # Selection for filtering by parent comment
    conn = psycopg2.connect(**DB_CONFIG)
    curr = conn.cursor()
    curr.execute("""
        SELECT DISTINCT c.comment_id, LEFT(c.comment_text, 50) || '...' 
        FROM comment_replies r 
        JOIN comments c ON r.main_comment_id = c.comment_id
    """)
    comments_with_replies = curr.fetchall()
    curr.close()
    conn.close()
    
    parent_options = {"All Replies": None}
    for c_id, c_text in comments_with_replies:
        parent_options[f"{c_id} ({c_text})"] = c_id
        
    selected_parent_label = st.selectbox("View Replies for Comment:", list(parent_options.keys()))
    selected_parent_id = parent_options[selected_parent_label]
    
    # 3. List Replies
    replies_df = CommentScraper.get_replies(DB_CONFIG, main_comment_id=selected_parent_id)
    
    st.write(f"Showing **{len(replies_df)}** replies")
    
    if not replies_df.empty:
        # Table Header
        header_cols = st.columns([1, 2, 4, 4, 2])
        headers = ["Username", "Video", "Parent Comment", "Reply text", "Published At"]
        for col, h in zip(header_cols, headers):
            col.markdown(f"**{h}**")
        st.divider()
        
        # Table Rows
        for _, row in replies_df.iterrows():
            cols = st.columns([1, 2, 4, 4, 2])
            cols[0].write(row["user_name"])
            cols[1].write(row["video_title"])
            cols[2].write(row["parent_comment"])
            cols[3].write(row["reply_text"])
            cols[4].write(row["reply_published_at"].strftime("%Y-%m-%d %H:%M") if row["reply_published_at"] else "-")
            st.divider()
    else:
        st.info("No replies found for the selected filter.")

# ==============================
# ANALYSIS PAGE
# ==============================
if menu == "Analysis":
    st.title("📈 Channel Analysis")
    
    st.subheader("Video Publication Time Series")
    
    # Selection for channel
    channel_dict = VideoScraper.select_channel_name(db_config=DB_CONFIG)
    if not channel_dict:
        st.warning("No channels found in database. Please add a channel first.")
    else:
        col1, col2 = st.columns(2)
        
        selected_channel_name = col1.selectbox(
            "Select Channel",
            list(channel_dict.keys())
        )
        
        time_filter = col2.selectbox(
            "Time Filter",
            ["Last 7 Days", "One Month"]
        )
        
        # Map time filter to days
        days_map = {
            "Last 7 Days": 7,
            "One Month": 30
        }
        days = days_map[time_filter]
        
        channel_id = channel_dict[selected_channel_name]
        
        # Fetch data
        time_data_df = VideoScraper.get_publication_time_data(DB_CONFIG, channel_id, days)
        
        if not time_data_df.empty:
            # Metrics
            total_videos = len(time_data_df)
            unique_days = time_data_df['pub_date'].nunique()
            
            m1, m2 = st.columns(2)
            m1.metric("Total Videos (Period)", total_videos)
            m2.metric("Active Upload Days", unique_days)
            
            # Scatter Chart
            st.divider()
            st.write(f"Publication Time distribution for **{selected_channel_name}**")
            
            # We want X = pub_date, Y = pub_time
            # Streamlit's st.scatter_chart is great for this
            st.scatter_chart(
                time_data_df,
                x='pub_date',
                y='pub_time',
                size=100,
                color="#FF0000" # YouTube Red
            )
            
            st.caption("Y-axis represents the hour of the day (0-24).")
            
            # Breakdown Table
            with st.expander("Show Raw Data"):
                st.dataframe(time_data_df, use_container_width=True)
        else:
            st.info("No data available for the selected period.")
