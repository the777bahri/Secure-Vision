import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["ORT_LOG_SEVERITY_LEVEL"] = "3"
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, message="`rcond` parameter will change")

import cv2
import threading
import time
import numpy as np
import logging
import queue
import pygame
import torch
from ultralytics import YOLO
from sklearn.metrics.pairwise import cosine_similarity
from insightface.app import FaceAnalysis

# === Sound ===
pygame.mixer.init()
alert_sound = pygame.mixer.Sound("sounds/warning.wav")


# === Logging ===
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    filename='app.log',
    filemode='w'
)

# === Device selection ===
if torch.backends.mps.is_available():
    power = torch.device("mps")
elif torch.cuda.is_available():
    power = torch.device("cuda:0")
else:
    power = torch.device("cpu")
print(f"Using device: {power}")

class MultiPersonFaceRecognitionApp:
    def __init__(self, stream_url=0):
        self.model = YOLO("yolo models/new_best12n.pt")
        self.TRACK_CFG = "bytrack/bytetrack.yaml"
        self.max_frames_before_rechecking = 250

        # === InsightFace ===
        MODEL_DIR = os.path.abspath("face_models")
        self.face_app = FaceAnalysis(name="buffalo_l",root=MODEL_DIR,allowed_modules=["detection", "recognition"])
        self.face_app.prepare(ctx_id=0)
        self.face_app.det_size = (640, 640)

        self.known_face_encodings, self.known_face_names = self.load_known_faces("face_data")
        self.person_ids = {name: idx for idx, name in enumerate(sorted(set(self.known_face_names)))}
        logging.info(f"Loaded {len(self.known_face_encodings)} encodings for {len(self.person_ids)} persons: {list(self.person_ids.keys())}")

        self.frame_queue = queue.Queue(maxsize=5)
        self.results_queue = queue.Queue(maxsize=5)
        self.stop_event = threading.Event()
        self.display_scale = 1.0

        # Initialize video capture
        try:
            self.cap = cv2.VideoCapture(stream_url)
            if not self.cap.isOpened():
                logging.warning("Cannot open video source, will use frame queue only")
                self.cap = None
        except Exception as e:
            logging.warning(f"Failed to initialize video capture: {e}")
            self.cap = None

        self.detection_queue = queue.Queue()

    def load_known_faces(self, data_root):
        encodings, names = [], []
        for person_name in os.listdir(data_root):
            folder = os.path.join(data_root, person_name)
            if not os.path.isdir(folder):
                continue
            for file in os.listdir(folder):
                if file.startswith("encoding_") and file.endswith(".npy"):
                    enc = np.load(os.path.join(folder, file))
                    encodings.append(enc)
                    names.append(person_name)
        return np.array(encodings), names

    def recognize_face(self, frame):
        try:
            resized = cv2.resize(frame, (640, 640))
            faces = self.face_app.get(resized)

            if not faces:
                return "Unknown"

            face = faces[0]
            emb = face.embedding.reshape(1, -1)

            if len(self.known_face_encodings) == 0:
                return "Unknown"

            sims = cosine_similarity(emb, self.known_face_encodings)[0]
            best_idx = np.argmax(sims)
            if sims[best_idx] > 0.35:
                return self.known_face_names[best_idx]

            return "Unknown"
        except Exception as e:
            logging.error(f"Face recognition failed: {e}")
            return "Unknown"

    def frame_grabber(self):
        logging.info("Frame grabber thread started.")
        while not self.stop_event.is_set():
            try:
                if self.cap is not None:
                    ret, frame = self.cap.read()
                    if not ret:
                        time.sleep(0.1)
                        continue
                    frame = cv2.resize(frame, (640, 640))
                    if not self.frame_queue.full():
                        self.frame_queue.put(frame)
                else:
                    # If no video capture, just wait for frames from the queue
                    time.sleep(0.1)
            except Exception as e:
                logging.error(f"Frame grabber error: {e}")
                time.sleep(0.1)
        logging.info("Frame grabber thread stopped.")


    def get_face_embedding(self, frame):
        try:
            resized = cv2.resize(frame, (640, 640))
            faces = self.face_app.get(resized)
            if not faces:
                return None
            return faces[0].embedding.reshape(1, -1)
        except Exception as e:
            logging.error(f"Embedding extraction failed: {e}")
            return None

    def is_same_person(self, emb1, emb2, threshold=0.35):
        if emb1 is None or emb2 is None:
            return False
        sim = cosine_similarity(emb1, emb2)[0][0]
        return sim >= threshold


    def processing_worker(self):
        logging.info("Processing thread started.")
        tracked_faces = {}
        frame_idx = 0
        prev_time = time.time()

        while not self.stop_event.is_set():
            try:
                frame = self.frame_queue.get(timeout=1)
            except queue.Empty:
                continue

            results = self.model.track(
                frame,
                persist=True,
                conf=0.25,
                iou=0.20,
                tracker=self.TRACK_CFG,
                verbose=False,
                device=power
            )[0]

            display_frame = frame.copy()
            # FPS calc
            current_time = time.time()
            fps = 1.0 / (current_time - prev_time) if current_time > prev_time else 0
            prev_time = current_time
            cv2.putText(display_frame, f"FPS: {fps:.1f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 255), 2)

            unknown_present = False

            if results.boxes is not None and results.boxes.id is not None:
                boxes = results.boxes.xyxy.cpu().numpy().astype(int)
                ids = results.boxes.id.int().cpu().tolist()
                confs = results.boxes.conf.cpu().numpy()

                for box, track_id, conf in zip(boxes, ids, confs):
                    x1, y1, x2, y2 = box
                    face_crop = frame[y1:y2, x1:x2]
                    new_emb = self.get_face_embedding(face_crop)

                    if track_id not in tracked_faces:
                        # first time seeing this track
                        name = self.recognize_face(face_crop)
                        tracked_faces[track_id] = {
                            'name': name,
                            'embedding': new_emb,
                            'last_checked': frame_idx
                        }

                    else:
                        stored = tracked_faces[track_id]
                        # if face appearance changed, re-id
                        if not self.is_same_person(new_emb, stored['embedding']):
                            logging.info(f"ID {track_id}: embedding mismatch → re-recognize")
                            name = self.recognize_face(face_crop)
                            tracked_faces[track_id] = {
                                'name': name,
                                'embedding': new_emb,
                                'last_checked': frame_idx
                            }
                        # else if still unknown and enough frames passed, retry
                        elif (stored['name'] == 'Unknown' and
                            frame_idx - stored['last_checked'] >= self.max_frames_before_rechecking):
                            name = self.recognize_face(face_crop)
                            stored['name'] = name
                            stored['embedding'] = new_emb
                            stored['last_checked'] = frame_idx
                        else:
                            name = stored['name']

                    if name == "Unknown":
                        unknown_present = True

                    try:
                        self.detection_queue.put_nowait((name, time.time()))
                    except queue.Full:
                        pass

                    # draw box & label
                    label = f"ID:{track_id} {name} ({conf:.2f})"
                    color = (0,255,0) if name!="Unknown" else (0,0,255)
                    cv2.rectangle(display_frame, (x1,y1),(x2,y2), color, 2)
                    cv2.putText(display_frame, label, (x1, y1-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # play alert if unknown present every N frames
            if frame_idx % self.max_frames_before_rechecking == 0 and unknown_present:
                alert_sound.play()
                print("⚠️⚠️⚠️ALERT: Unknown person detected!")

            frame_idx += 1
            if not self.results_queue.full():
                self.results_queue.put(display_frame)

        logging.info("Processing thread stopped.")


    def run(self):
        grabber = threading.Thread(target=self.frame_grabber, daemon=True)
        processor = threading.Thread(target=self.processing_worker, daemon=True)
        grabber.start()
        processor.start()

        while not self.stop_event.is_set():
            try:
                display_frame = self.results_queue.get(timeout=0.1)
                display_frame = cv2.resize(display_frame, (640, 640))
                cv2.imshow("Multi-Person Face Recognition", display_frame)
            except queue.Empty:
                continue

            if cv2.waitKey(1) == ord('q') or cv2.getWindowProperty("Multi-Person Face Recognition", cv2.WND_PROP_VISIBLE) < 1:
                self.stop_event.set()
                break

        self.cap.release()
        cv2.destroyAllWindows()
        logging.info("Application exited cleanly.")

if __name__ == "__main__":
    print("Welcome to Multi-Person Face Recognition App")
    cam_choice = input("Select camera source:\n1. Local webcam\n2. IP camera URL\nEnter 1 or 2: ").strip()
    stream_url = 0 if cam_choice != "2" else input("Enter the IP camera/video stream URL: ").strip()
    app = MultiPersonFaceRecognitionApp(stream_url)
    app.run()