import streamlit as st
import psycopg2
import pandas as pd
from dotenv import load_dotenv
from functions import ChannelScraper
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
menu = st.sidebar.radio("Menu", ["Dashboard", "Channels"])

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