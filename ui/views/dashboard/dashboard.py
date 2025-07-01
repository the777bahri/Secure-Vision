import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import os
import shutil
import datetime
from streamlit_autorefresh import st_autorefresh

def show_dashboard():
    st.title("Dashboard Home")

    # get current timestamp
    now = datetime.datetime.now()
    key = f"dashboard_refresh_{now.strftime('%Y%m%d%H%M')}"  # Changes every minute
    st_autorefresh(interval = 60000, limit = None, key = key)
    col1, col2 = st.columns(2)
    col1.metric("Date", now.strftime("%Y-%m-%d"))
    col2.metric("Time", now.strftime("%H:%M"))

    # display current date and time
    col13, col14, col15 = st.columns(3)

    # Chart for detections over 24 hours
    st.header("POI Detection Metrics")
    log_path = "logs/detections.csv"

    if os.path.exists(log_path):
        df_log = pd.read_csv(log_path, names = ["Name", "Timestamp", "Camera"])
        df_log["Timestamp"] = pd.to_datetime(df_log["Timestamp"], unit = "s")
        df_log["Date"] = df_log["Timestamp"].dt.date
        df_log["Hour"] = df_log["Timestamp"].dt.hour

        today = datetime.date.today()
        df_today = df_log[df_log["Date"] == today]

        # Metrics
        total_detections = len(df_today)
        unique_pois = df_today["Name"].nunique()
        peak_hour = df_today["Hour"].value_counts().idxmax() if not df_today.empty else "N/A"

        col13.metric("Total Detections Today", total_detections)
        col14.metric("Unique POIs Today", unique_pois)
        col15.metric("Peak Detection Hour", peak_hour)

        # Timeline chart
        hourly_counts = df_today.groupby("Hour").size().reindex(range(24), fill_value = 0)
        df_timeline = pd.DataFrame({"Hour": hourly_counts.index, "Detections": hourly_counts.values})
        fig_timeline = px.area(df_timeline, x = "Hour", y = "Detections", title = "Detections Over 24 Hours")
        st.plotly_chart(fig_timeline, use_container_width = True)

        # POI frequency
        poi_counts = df_today["Name"].value_counts().nlargest(5)
        if not poi_counts.empty:
            df_poi = pd.DataFrame({"Person": poi_counts.index, "Detections": poi_counts.values})
            fig_poi_bar = px.bar(df_poi, x="Person", y="Detections", title="Top 5 POI Detections")
            st.plotly_chart(fig_poi_bar, use_container_width=True)
        else:
            st.info("No POI detections today.")
    else:
        st.warning("No detection logs found.")

    # Camera & Feed Insights
    st.header("Camera & Feed Insights")
    if os.path.exists(log_path):
        # Total number of cameras ever added
        all_cameras = set(source["name"] for source in st.session_state.video_source_registry)

        # Cameras used today
        camera_today = df_today["Camera"].unique() if not df_today.empty else []

        # Count metrics
        total_cameras = len(all_cameras)
        active_cameras = len(camera_today)
        inactive_cameras = (total_cameras - active_cameras) * -1

        col4, col5, col6 = st.columns(3)
        col4.metric("Total Cameras", total_cameras)
        col5.metric("Active Cameras", active_cameras)
        col6.metric("Inactive Cameras", inactive_cameras)

        # Detections per camera (today)
        camera_counts = df_today["Camera"].value_counts()
        if not camera_counts.empty:
            df_camera = pd.DataFrame({"Camera": camera_counts.index, "Events": camera_counts.values})
            fig_camera = px.bar(df_camera, x="Camera", y="Events", title="Detections Per Camera")
            st.plotly_chart(fig_camera, use_container_width=True)
        else:
            st.info("No camera detections today.")
    else:
        st.warning("No cameras registered.")

    ###Face Registration Stats ###
    st.header("Face Registration Stats")
    log_path = "logs/registrations.csv"
    if os.path.exists(log_path):
        df_reg = pd.read_csv(log_path, names = ["Name", "Poses", "Timestamp"])
        df_reg["Timestamp"] = pd.to_datetime(df_reg["Timestamp"], unit = "s")
        df_reg["Date"] = df_reg["Timestamp"].dt.date
        df_reg["Week"] = df_reg["Timestamp"].dt.isocalendar().week
        df_reg["Year"] = df_reg["Timestamp"].dt.year

        today = datetime.date.today()
        current_week = datetime.date.today().isocalendar()[1]
        current_year = datetime.date.today().year

        # Metrics
        total_users = df_reg["Name"].nunique()
        this_week = df_reg[(df_reg["Week"] == current_week) & (df_reg["Year"] == current_year)]["Name"].nunique()
        avg_poses = round(df_reg.groupby("Name")["Poses"].mean().mean(), 1)

        col7, col8, col9 = st.columns(3)
        col7.metric("Registered Users", total_users)
        col8.metric("This Week", this_week)
        col9.metric("Avg Poses per User", avg_poses)

        # Graph - Registrations over last 14 days
        last_14_days = pd.date_range(end = today, periods = 14)
        df_last14 = df_reg[df_reg["Date"].isin(last_14_days.date)]
        daily_counts = df_last14.groupby("Date").size().reindex(last_14_days.date, fill_value = 0).reset_index()
        daily_counts.columns = ["Date", "Registrations"]

        fig_reg = px.line(daily_counts, x = "Date", y = "Registrations", title = "New Registrations Over Last 2 Weeks")
        st.plotly_chart(fig_reg, use_container_width = True)
    else:
        st.warning("No face registrations found.")

    # ========================================
    # SECTION 5: Registered People Table & Deletion
    # ========================================
    st.markdown("---")
    st.header("Registered People in Database")
    base_dir = "face_data"

    def get_people():
        if os.path.isdir(base_dir):
            return sorted([d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))])
        return []

    people = get_people()
    if people:
        df_people = pd.DataFrame({
            'ID': list(range(1, len(people) + 1)),
            'Name': people
        }).set_index('ID')
        st.table(df_people)

        # Deletion UI
        person_to_delete = st.selectbox("Select person to delete:", people, key = "del_select")
        if st.button("Delete Selected Person", key = "del_btn"):
            try:
                shutil.rmtree(os.path.join(base_dir, person_to_delete))
                st.success(f"Deleted '{person_to_delete}' and all its data.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to delete '{person_to_delete}': {e}")
    else:
        st.info("No registered people found.")

    # ========================================
    # SECTION 6: GPS Location
    # ========================================
    st.markdown("---")
    st.header("Current GPS Location")
    try:
        from gps.gps import IPGeoLocator
        import folium
        from streamlit_folium import st_folium

        locator = IPGeoLocator("0")
        info = locator.get_map_info()
        ip = info.get('ip')
        coords = info.get('coordinates')
        if coords:
            lat, lon = map(float, coords.split(','))
        else:
            lat, lon = -33.8678, 151.2073

        col_map, col_info = st.columns([2, 1])
        with col_map:
            st.subheader("🗺️ Zone Map")
            m = folium.Map(location = [lat, lon], zoom_start = 16)
            folium.Marker(
                [lat, lon], popup = f"IP: {ip}", tooltip = "Detected Location"
            ).add_to(m)
            st_folium(m, width = 400, height = 300)

        with col_info:
            st.subheader("Location Details")
            st.write(f"**IP:** {ip}")
            if coords:
                st.write(f"**Coordinates:** {lat:.4f}, {lon:.4f}")
                if info.get('map_url'):
                    st.markdown(f"[Open in Google Maps]({info.get('map_url')})")
    except Exception as e:
        st.error(f"GPS module error: {e}")
