import av
import cv2
import numpy as np
import os
import json
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase
import streamlit as st
from insightface.app import FaceAnalysis


# --- Video Processor Class ---
class FaceRegistrationProcessor(VideoProcessorBase):
    def __init__(self, person_name):
        self.person_name = person_name
        self.save_dir = os.path.join("face_data", self.person_name.replace(" ", "_"))
        os.makedirs(self.save_dir, exist_ok=True)
        self.frame_count = 0
        self.max_frames = 5  # Collect 5 frames
        self.model_dir = os.path.abspath("face_models")
        self.app = FaceAnalysis(
            name="buffalo_l",
            root=self.model_dir,
            allowed_modules=["detection", "landmark_2d_106", "recognition"]
        )
        self.app.prepare(ctx_id=0)
        self.saved = False

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")

        faces = self.app.get(img)
        if faces and self.frame_count < self.max_frames:
            face = faces[0]
            embedding = face.embedding
            bbox = face.bbox.astype(int)
            cv2.rectangle(img, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)

            # Save data
            np.save(os.path.join(self.save_dir, f"encoding_{self.frame_count}.npy"), embedding)
            landmarks = {f"p{i}": [int(x), int(y)] for i, (x, y) in enumerate(face.landmark_2d_106)}
            with open(os.path.join(self.save_dir, f"landmarks_{self.frame_count}.json"), "w") as f:
                json.dump(landmarks, f)
            cv2.imwrite(os.path.join(self.save_dir, f"face_{self.frame_count}.jpg"), img)
            self.frame_count += 1
            print(f"Saved frame {self.frame_count}/5")

        # If enough frames, mark as done
        if self.frame_count >= self.max_frames and not self.saved:
            print(f"[INFO] Registration complete for {self.person_name}")
            self.saved = True

        return av.VideoFrame.from_ndarray(img, format="bgr24")
