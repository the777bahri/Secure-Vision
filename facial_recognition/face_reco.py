import os
import warnings
import cv2
import numpy as np
import json
from insightface.app import FaceAnalysis
import torch

# Fixes for ONNX runtime
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["ORT_LOG_SEVERITY_LEVEL"] = "3"
warnings.filterwarnings("ignore", category=FutureWarning, message="`rcond` parameter will change")

class FaceDataCollector:
    def __init__(self, model_dir, ctx_id):
        self.model_dir = os.path.abspath(model_dir)
        self.app = FaceAnalysis(
            name="buffalo_l",
            root=self.model_dir,
            allowed_modules=["detection", "landmark_2d_106", "recognition"]
        )
        self.app.prepare(ctx_id=ctx_id)

    def _detect_and_draw(self, frame):
        frame = cv2.resize(frame, (512, 512))
        faces = self.app.get(frame)

        if not faces:
            return frame, None, None, None

        face = faces[0]
        embedding = face.embedding
        bbox = face.bbox.astype(int)

        # Draw bounding box
        cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)

        # Draw 106-point landmarks
        if hasattr(face, "landmark_2d_106") and face.landmark_2d_106 is not None:
            for pt in face.landmark_2d_106.astype(int):
                cv2.circle(frame, tuple(pt), 1, (255, 255, 0), -1)

            # Convert landmarks to dict format
            landmarks = {f"p{i}": [int(x), int(y)] for i, (x, y) in enumerate(face.landmark_2d_106)}
        else:
            landmarks = None

        return frame, embedding, landmarks, bbox.tolist()

    def start(self, video_source=0, person_name=None):
        if not person_name:
            person_name = input("👤 Enter your full name: ").strip()

        instructions = [
            "Look directly at the camera",
            "Look slightly to the LEFT.",
            "Look slightly to the RIGHT.",
            "Look slightly UP.",
            "Look slightly DOWN.",
        ]

        save_dir = os.path.join("face_data", person_name.replace(" ", "_"))
        os.makedirs(save_dir, exist_ok=True)
        print(f"[INFO] Saving face data to: {os.path.abspath(save_dir)}")

        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            print(f"[ERROR] Failed to open video source: {video_source}")
            return

        index = 0
        for instruction in instructions:
            print(f"\n👉 {instruction}")
            print("Press [Enter] to capture this pose.")
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("[ERROR] Failed to grab frame.")
                    continue

                display_frame, embedding, landmarks, bbox = self._detect_and_draw(frame)
                cv2.imshow("Face Scanner", display_frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or cv2.getWindowProperty("Face Scanner", cv2.WND_PROP_VISIBLE) < 1:
                    print("[INFO] Exiting early...")
                    cap.release()
                    cv2.destroyAllWindows()
                    return

                if key == 13 or key == 10:  # Enter
                    if embedding is not None and landmarks is not None:
                        np.save(os.path.join(save_dir, f"encoding_{index}.npy"), embedding)
                        with open(os.path.join(save_dir, f"landmarks_{index}.json"), "w") as f:
                            json.dump(landmarks, f)
                        cv2.imwrite(os.path.join(save_dir, f"face_{index}.jpg"), display_frame)
                        print(f"[✅] Saved data for index {index}.")
                        index += 1
                        break
                    else:
                        print("[⚠️] No valid face detected. Adjust your pose and try again.")

        cap.release()
        cv2.destroyAllWindows()
        print("\n[INFO] Data collection complete. You may now close the window or proceed with the next step.")

# Run the collector
if __name__ == "__main__":
    model_dir=os.path.join("face_models")
    # Detect device
    if torch.backends.mps.is_available():
        ctx_id = -1  # Use Metal Performance Shaders (MPS) for Apple M chips
        print("[INFO] Using Apple MPS (Metal Performance Shaders).")
    elif torch.cuda.is_available():
        ctx_id = 0  # Use CUDA if available
        print("[INFO] Using CUDA.")
    else:
        ctx_id = 0  # Fallback to CPU
        print("[INFO] Using CPU.")

    collector = FaceDataCollector(model_dir, ctx_id=0)

    print("💡 Press [Enter] to use webcam or enter a video stream URL.")
    source_input = input("🔗 Enter video source (URL or leave blank for webcam): ").strip()
    video_source = source_input if source_input else 0

    collector.start(video_source)
