import os
import warnings
import cv2
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from insightface.app import FaceAnalysis

# ONNX runtime fixes
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["ORT_LOG_SEVERITY_LEVEL"] = "3"
warnings.filterwarnings("ignore", category=FutureWarning)

class FaceRecognizer:
    def __init__(self, model_dir="face_models", face_data_dir="face_data", ctx_id=0, threshold=0.45):
        self.model_dir = os.path.abspath(model_dir)
        self.face_data_dir = face_data_dir
        self.ctx_id = ctx_id
        self.threshold = threshold
        self.known_encodings = []
        self.known_names = []

        # Load InsightFace with detection + recognition
        self.app = FaceAnalysis(
            name="buffalo_l",
            root=self.model_dir,
            allowed_modules=["detection", "recognition"]
        )
        self.app.prepare(ctx_id=self.ctx_id)

        self.load_known_faces()

    def load_known_faces(self):
        print("[INFO] Loading known face encodings...")
        for person in os.listdir(self.face_data_dir):
            person_folder = os.path.join(self.face_data_dir, person)
            if not os.path.isdir(person_folder):
                continue
            for file in os.listdir(person_folder):
                if file.startswith("encoding_") and file.endswith(".npy"):
                    path = os.path.join(person_folder, file)
                    encoding = np.load(path)
                    self.known_encodings.append(encoding)
                    self.known_names.append(person)
        print(f"[INFO] Loaded {len(self.known_encodings)} encodings for {len(set(self.known_names))} people.")

    def recognize(self, face_embedding):
        if not self.known_encodings:
            return "Unknown"

        face_embedding = face_embedding.reshape(1, -1)
        similarities = cosine_similarity(face_embedding, self.known_encodings)[0]
        best_index = np.argmax(similarities)
        if similarities[best_index] >= self.threshold:
            return self.known_names[best_index]
        return "Unknown"

    def annotate_frame(self, frame, face, name):
        bbox = face.bbox.astype(int)
        x1, y1, x2, y2 = bbox
        color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    def start_inference(self, source=0):
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            print("[ERROR] Cannot open video source.")
            return

        print("[INFO] Press 'q' to quit.")
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            faces = self.app.get(frame)
            for face in faces:
                name = "Unknown"
                if face.embedding is not None:
                    name = self.recognize(face.embedding)
                self.annotate_frame(frame, face, name)

            cv2.imshow("Face Recognition", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or cv2.getWindowProperty("Face Recognition", cv2.WND_PROP_VISIBLE) < 1:
                print("[INFO] Exiting...")
                break

        cap.release()
        cv2.destroyAllWindows()


# Run inference
if __name__ == "__main__":
    recognizer = FaceRecognizer(
        model_dir="face_models",       # Must contain buffalo_l
        face_data_dir="face_data",     # Must contain subfolders with saved .npy files
        ctx_id=0,                      # 0 = GPU, -1 = CPU
        threshold=0.45                 # Similarity threshold
    )

    print("💡 Press [Enter] to use webcam or provide a stream URL.")
    source_input = input("🔗 Enter video source (or leave blank for webcam): ").strip()
    video_source = source_input if source_input else 0

    recognizer.start_inference(video_source)
