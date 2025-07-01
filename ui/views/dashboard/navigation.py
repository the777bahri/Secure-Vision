import streamlit as st
from ui.views.dashboard.dashboard import show_dashboard
from ui.views.dashboard.video_feed import show_video_feed
from ui.views.dashboard.drone_dahsboard import show_drone
from ui.views.dashboard.face_registration import show_face_registration

def show_app():
    st.sidebar.markdown("## 🛡️ Secure Vision")

    st.sidebar.markdown("---")
    if st.sidebar.button("🏠 Dashboard"):
        st.session_state.page = "dashboard"
    if st.sidebar.button("📹 Video Feed"):
        st.session_state.page = "video"
    if st.sidebar.button("🚁 Drone Control"):
        st.session_state.page = "drone"
    if st.sidebar.button("🧠 Face Registration"):
        st.session_state.page = "face"
    if st.sidebar.button("🔓 Logout"):
        st.session_state.logged_in = False
        st.session_state.page = "dashboard"
        st.rerun()

    # Default page setup
    if "page" not in st.session_state:
        st.session_state.page = "dashboard"

    # Route to the selected page
    if st.session_state.page == "dashboard":
        show_dashboard()
    elif st.session_state.page == "video":
        show_video_feed()
    elif st.session_state.page == "drone":
        show_drone()
    elif st.session_state.page == "face":
        show_face_registration()
