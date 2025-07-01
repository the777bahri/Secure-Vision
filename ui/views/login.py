import streamlit as st
from ui.services.main import login
from PIL import Image

def show_login():
    # Logo
    st.title("🛡️ Secure Vision")

    # Login Form
    st.title("🔐 Login")
    st.write("Enter your credentials to access the System.")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type = "password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if login(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password")

    st.markdown("---")
    # About Section
    with st.expander("Click to know more About Us"):
        st.title("📘 About Secure Vision")
        st.markdown("""
        ## 🔍 Secure Vision – AI-Powered Human Detection System

        **Secure Vision** is a Streamlit-based intelligent surveillance platform simulating real-time  
        human detection and event monitoring using deep learning. Developed for the *Deep  
        Learning and Convolutional Neural Networks (42028)* subject at UTS, it blends CV and UI/UX to showcase a  
        full-stack AI deployment. 🚀

        ### 🌟 Project Highlights
        - **Model:** YOLOv12n trained on combined datasets (Kaggle, Roboflow, and UTS Building 10 images) 📷
        - **Preprocessing:** Resize (640×640), grayscale (10%), CLAHE, noise, rotation, flipping 🎛️
        - **Augmentation:** Horizontal & vertical flipping, rotation (90°, 180°, 270°, ±10°), grayscale, noise, CLAHE 🌀
        - **Training:** 500 epochs (early stopping at epoch 389), AdamW optimizer, mAP@0.5 = 0.964, mAP@0.5:0.95 = 0.794 📈
        - **Performance:** F1 = 0.93, Precision peaks at 1.00 (at confidence 0.909), Mean Precision = 0.933, Mean Recall = 0.919 ⚡
        - **Frontend:** Streamlit + OpenCV + multithreading 🖥️🔀

        ### 🛠️ How It Works
        1. **Detection**: YOLOv12n detects humans in live feeds. 👀
        2. **Tracking**: ByteTrack tracks individuals consistently across frames. 🎯
        3. **Recognition**: InsightFace matches detected faces to known users. 🧑‍🤝‍🧑
        4. **Action**: Alerts, drone simulation, and logs are updated in the dashboard. 🔔📋

        ### 🚀 Future Work
        - 🤖 Integrating drone functionalities for extended surveillance and response.
        - 📂 Logging unknown individuals’ faces into a dataset for future tracking, even across rooms, buildings, or facilities.
        - 📹 Supporting simultaneous multi-camera streams instead of one feed at a time.
        """)


        st.subheader("👨‍💻 Team: Brown Cookies")

        first_col, second_col, third_col = st.columns(3)
        with first_col:
            st.markdown("""
                - ID: `13384589`  
                - 📧 [Abdullah](mailto:Abdullah.I.Bahri@student.uts.edu.au)
                """)
        with second_col:
            st.markdown("""
                - ID: `25176811`  
                - 📧 [Rajesh](mailto:Hayrambhrajesh.monga@student.uts.edu.au)
                """)
        with third_col:
            st.markdown("""
                - ID: `25093295`  
                - 📧 [Yohan](mailto:Yohan.EdiriweeraArakkattuPatabandige@student.uts.edu.au)
                """)
        team_img = Image.open("ui/images/team.png")
        st.image(team_img, caption = "Brown Cookies Team")

    st.markdown("---")
    st.info("📌 Developed for UTS 42028 – Deep Learning and CNNs (Autumn 2025).")
