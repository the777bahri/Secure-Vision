import os
import cv2
import json
import numpy as np
import streamlit as st
import pygame
import time
from facial_recognition.face_reco import FaceDataCollector
from ui.services.main import save_registration

# === Sound ===
pygame.mixer.init()
camera_sound = pygame.mixer.Sound("sounds/picture click.mp3")

# === Cache the model so it only loads once ===
@st.cache_resource
def load_collector(model_dir: str, ctx_id: int):
    return FaceDataCollector(model_dir=model_dir, ctx_id=ctx_id)

def submit():
    st.session_state.person_name_text = st.session_state.person_name_widget
    st.session_state.person_name_widget = ""

# === Face Registration Page ===
def show_face_registration():
    # Note: page config should be set in the main app, not inside this function
    st.title("📷 Face Registration")
    st.markdown("This app captures your face data directly from your browser for AI recognition.")

    # Initialize session state for camera, flags, and progress
    for key, default in [
        ("person_name_text", ""),
        ("cap", None),
        ("collector", None),
        ("index", 0),
        ("capture_pose", False),
        ("stop", False),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    instructions = [
        "😀 Look directly at the camera",
        "👈 Look slightly to the LEFT",
        "👉 Look slightly to the RIGHT",
        "👆 Look slightly UP",
        "👇 Look slightly DOWN",
    ]

    # Input: person's name
    st.text_input("Enter your full name to begin:", key="person_name_widget", on_change=submit)
    person_name = st.session_state.person_name_text

    # Once name is provided, prepare collector and camera
    if person_name != "":
        # create save directory
        save_dir = os.path.join("face_data", person_name.replace(" ", "_"))
        os.makedirs(save_dir, exist_ok=True)

        # load the InsightFace collector
        if st.session_state.collector is None:
            st.session_state.collector = load_collector(model_dir="face_models", ctx_id=0)
        collector = st.session_state.collector

        # open the camera once
        if st.session_state.cap is None:
            st.session_state.cap = cv2.VideoCapture(0)
        cap = st.session_state.cap

        # placeholders for video and messages
        frame_placeholder = st.empty()
        info_placeholder = st.empty()

        # control buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📸 Capture Pose"):
                st.session_state.capture_pose = True
                camera_sound.play()
        with col2:
            if st.button("🛑 Stop Registration"):
                st.session_state.stop = True

        # live loop
        while True:
            if st.session_state.stop:
                info_placeholder.success("Registration stopped.")
                break

            ret, frame = cap.read()
            if not ret:
                info_placeholder.error("Failed to read from webcam.")
                break

            # process frame
            draw_frame, embedding, landmarks, bbox = collector._detect_and_draw(frame)
            # ensure frame is 512x512 for display
            draw_frame = cv2.resize(draw_frame, (512, 512))
            frame_rgb = cv2.cvtColor(draw_frame, cv2.COLOR_BGR2RGB)
            # display at smaller size
            frame_placeholder.image(frame_rgb, channels="RGB", width=512)

            # show instruction or completion
            if st.session_state.index < len(instructions):
                info_placeholder.info(instructions[st.session_state.index])
            else:
                info_placeholder.success("✅ Face registration completed.")
                save_registration(person_name, st.session_state.index)
                break

            # handle capture
            if st.session_state.capture_pose:
                if embedding is not None and landmarks is not None:
                    # save embedding, landmarks, and image
                    np.save(os.path.join(save_dir, f"encoding_{st.session_state.index}.npy"), embedding)
                    with open(os.path.join(save_dir, f"landmarks_{st.session_state.index}.json"), "w") as f:
                        json.dump(landmarks, f)
                    cv2.imwrite(os.path.join(save_dir, f"face_{st.session_state.index}.jpg"), draw_frame)
                    info_placeholder.success(f"Pose {st.session_state.index + 1} saved.")
                    st.session_state.index += 1
                    if st.session_state.index >= len(instructions):
                        info_placeholder.success("Face registration completed.")
                else:
                    info_placeholder.warning("No valid face detected. Adjust your pose and try again.")

                # reset capture flag
                st.session_state.capture_pose = False

            # small delay to allow UI events
            time.sleep(0.01)

        # release camera when done
        cap.release()
        st.session_state.person_name_text = ""
        st.session_state.cap = None
        st.session_state.collector = None
        st.session_state.index = 0
        st.session_state.capture_pose = False
        st.session_state.stop = False
        st.rerun()
    else:
        st.warning("Please enter your name to begin registration.")
