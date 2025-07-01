import streamlit as st
from ui.views.login import show_login
from ui.views.dashboard.navigation import show_app

st.set_page_config(page_title = "Secure Vision", layout = "wide")

# Session State Setup
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False 
if 'username' not in st.session_state:
    st.session_state.username = ""
# Add initialization for video_source_registry
if 'video_source_registry' not in st.session_state:
    st.session_state.video_source_registry = []

def main():
    if not st.session_state.logged_in:
        show_login()
    else:
        show_app()

if __name__ == "__main__":
    main()