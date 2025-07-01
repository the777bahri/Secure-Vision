import os
import cv2
import datetime
import threading
import streamlit as st
from human_face.securevision import MultiPersonFaceRecognitionApp
from ui.services.main import save_detection

def show_video_feed():
    # Session Stores
    if "run_stream" not in st.session_state:
        st.session_state.run_stream = False
    if 'video_source_registry' not in st.session_state:
        st.session_state.video_source_registry = []

    st.title("🎥 Live Video Feed Monitoring")

    st.markdown("---")
    st.markdown("### Video Source Configuration")

    # Register a new video source
    video_source_name = st.text_input("Enter Video Source Name")
    video_source_type = st.selectbox("Select Video Source Type:", ["Webcam", "IP/Video URL"])
    if video_source_type == "Webcam":
        video_source_input = 0  # Default webcam index
    else:
        video_source_input = st.text_input("Enter IP/Video URL:", value="http:172.19.120.105:8080/video")

    if st.button("Add Source"):
        if video_source_name:
            if (video_source_name not in
                    [video_source["name"] for video_source in st.session_state.video_source_registry]):
                st.session_state.video_source_registry.append({
                    "name": video_source_name,
                    "source_type": video_source_type,
                    "source_input": video_source_input
                })
                st.success(f"'{video_source_name}' added successfully.")
            else:
                st.warning("A source with this name already exists.")
        else:
            st.error("Please enter a valid video source name.")

    if st.session_state.video_source_registry:
        delete_source_name = st.selectbox(
            "Select Source to Delete",
            [video_source["name"] for video_source in st.session_state.video_source_registry],
            key="delete_source_select"
        )
        if st.button("Delete Selected Source"):
            st.session_state.video_source_registry = [
                source for source in st.session_state.video_source_registry
                if source["name"] != delete_source_name
            ]
            st.success(f"'{delete_source_name}' deleted successfully.")


    # Camera and Drone Selection
    st.markdown("---")
    st.markdown("### Video and Drone Control")
    video_col_one, video_col_two = st.columns(2)
    drone_col_one, drone_col_two = st.columns(2)

    available_video_sources = video_col_one.selectbox(
        "Cameras:",
        [video_source["name"] for video_source in st.session_state.video_source_registry]
    )
    selected_angles = video_col_two.multiselect(
        "Angles:",
        ["Angle 1", "Angle 2", "Angle 3", "Angle 4"],
        default = ["Angle 1"]
    )
    selected_drones = drone_col_one.multiselect(
        "Drones:",
        ["Drone 1", "Drone 2", "Drone 3", "Drone 4", "Drone 5"],
        default = ["Drone 1"]
    )
    selected_areas = drone_col_two.multiselect(
        "Available Areas:",
        ["Area 1", "Area 2", "Area 3", "Area 4", "Area 5"],
        default = ["Area 4"]
    )

    # Live Feed & Log Split View
    st.markdown("---")
    if st.button("🟢 Start Live Video Feed"):
        run_stream = True
        if st.button(" 🔴 Stop Live Video Feed"):
            run_stream = False
    else:
        run_stream = False
    image_placeholder = st.empty()
    detection_placeholder = st.empty()

    if run_stream:
        selected_source = next(
            (source for source in st.session_state.video_source_registry if
             source["name"] == available_video_sources),
            None
        )
        st.info(f"Streaming video from {selected_source['source_type']}...")

        if selected_source:
            if selected_source["source_type"] == "Webcam":
                stream_source = int(selected_source["source_input"])
            else:
                stream_source = selected_source["source_input"]

            # Run the video processing app
            app = MultiPersonFaceRecognitionApp(stream_url = stream_source)
            grabber_thread = threading.Thread(target = app.frame_grabber, daemon = True)
            processor_thread = threading.Thread(target = app.processing_worker, daemon = True)
            grabber_thread.start()
            processor_thread.start()
            try:
                while run_stream:
                    try:
                        frame = app.results_queue.get(timeout = 0.1)
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        image_placeholder.image(frame_rgb, channels = "RGB", width = 640)

                        try:
                            person_name, ts = app.detection_queue.get_nowait()
                            save_detection(person_name, ts, selected_source["name"])
                            ts_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                            detection_placeholder.warning(
                                f"🚨 POI Detected: {person_name} at {selected_source['name']} — {ts_str}")
                        except Exception:
                            pass
                    except Exception:
                        continue
            except Exception as e:
                st.error(f"Stream error: {e}")
            finally:
                app.stop_event.set()
                app.cap.release()
                st.success("Video feed stopped.")
        else:
            st.error("Video Source not valid.")
    else:
        st.info("Tick the checkbox above to start the live feed.")

    # Application logs
    st.markdown("---")
    if st.button("🔄 Refresh Logs"):
        st.rerun()

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Static log entries
    static_logs = [
        f"[{now}] Live Feed Initialized",
        f"[{now}] Monitoring... | Angles: {', '.join(selected_angles)}",
        f"[{now}] Awaiting detection..."
    ]

    # Load log entries from app.log
    log_file_path = "app.log"
    dynamic_logs = []
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, "r") as f:
                dynamic_logs = f.readlines()
        except Exception as e:
            dynamic_logs = [f"[ERROR] Failed to read log file: {e}"]
    else:
        dynamic_logs = ["[INFO] No log file found."]

    # Combine and limit to last 20 entries
    combined_logs = static_logs + [line.strip() for line in dynamic_logs]
    combined_logs = combined_logs[-20:]

    # Display logs in code block
    st.code("\n".join(combined_logs), language = "text")
