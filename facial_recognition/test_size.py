import os
import cv2
from insightface.app import FaceAnalysis

# Safe setup for ONNX runtime
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["ORT_LOG_SEVERITY_LEVEL"] = "3"

class InsightFaceViewer:
    def __init__(self):
        # Update to your correct model folder
        self.model_root = os.path.join("face_models", "models")  # face_models\models
        self.ctx_id = 0  # 0 = GPU, -1 = CPU
        self.app = None
        self.active_modules = set()
        self.module_keys = {
            "1": "detection",
            "2": "landmark_2d_106",
            "3": "landmark_3d_68",
            "4": "genderage",
            "5": "recognition"
        }

    def load_models(self):
        modules = sorted(self.active_modules)
        if "detection" not in modules and modules:
            modules.insert(0, "detection")

        print(f"[INFO] Loading modules: {modules}")
        self.app = FaceAnalysis(
            name="buffalo_l",
            root=self.model_root,
            allowed_modules=modules
        )
        self.app.prepare(ctx_id=self.ctx_id, det_size=(640, 640))
        print("[INFO] Ready. Modules loaded:", list(self.app.models.keys()))

    def toggle_module(self, key):
        module = self.module_keys[key]
        if module in self.active_modules:
            self.active_modules.remove(module)
            print(f"[–] Disabled: {module}")
        else:
            self.active_modules.add(module)
            print(f"[+] Enabled: {module}")

        if self.active_modules:
            self.load_models()
        else:
            self.app = None
            print("[INFO] All models disabled. Showing raw webcam feed.")

    def draw_face(self, frame, face):
        x1, y1, x2, y2 = face.bbox.astype(int)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        if hasattr(face, "kps") and face.kps is not None:
            for (x, y) in face.kps.astype(int):
                cv2.circle(frame, (x, y), 2, (0, 0, 255), -1)

        if hasattr(face, "landmark_2d_106") and face.landmark_2d_106 is not None:
            for (x, y) in face.landmark_2d_106.astype(int):
                cv2.circle(frame, (x, y), 1, (255, 255, 0), -1)

        if hasattr(face, "landmark_3d_68") and face.landmark_3d_68 is not None:
            for (x, y, _) in face.landmark_3d_68.astype(int):
                cv2.circle(frame, (x, y), 1, (0, 255, 255), -1)

        if hasattr(face, "gender") and hasattr(face, "age"):
            if face.gender is not None and face.age is not None:
                gender = "M" if face.gender == 1 else "F"
                label = f"{gender}, {int(face.age)}"
                cv2.putText(frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    def run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[ERROR] Cannot open webcam.")
            return

        print("\n🎮 [COMMANDS]")
        print(" 1 – Toggle detection (5-point landmarks)")
        print(" 2 – Toggle 106-point landmarks")
        print(" 3 – Toggle 68-point 3D landmarks")
        print(" 4 – Toggle gender/age")
        print(" 5 – Toggle recognition")
        print(" q – Quit\n")

        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            if self.app:
                faces = self.app.get(frame)
                for face in faces:
                    self.draw_face(frame, face)

            cv2.imshow("🧠 InsightFace Viewer – [1-5 toggle, q quit]", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif chr(key) in self.module_keys:
                self.toggle_module(chr(key))

        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    viewer = InsightFaceViewer()
    viewer.run()
