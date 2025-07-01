import cv2
import numpy as np

class ObjectTracker:
    def __init__(self):
        """Initialize object tracker, find a valid camera, and create trackbars."""
        self.frameWidth = 640
        self.frameHeight = 480
        self.deadZone = 100  # Area in the center where no movement is triggered
        self.cap = self.find_camera()  # Automatically find an available camera
        
        global imgContour

        # Create trackbars for HSV filtering
        self.createTrackbars()

    def find_camera(self):
        """Finds the first available camera index and initializes it."""
        for i in range(5):  # Check indexes 0 to 4
            cap = cv2.VideoCapture(i)
            if cap.read()[0]:  # If the camera index is valid
                print(f"[INFO] Using Camera {i}")
                cap.set(3, self.frameWidth)
                cap.set(4, self.frameHeight)
                return cap
        print("[ERROR] No camera found!")
        exit()  # Exit if no camera is detected

    def createTrackbars(self):
        """Create trackbars for HSV filtering and contour detection parameters."""
        cv2.namedWindow("HSV")
        cv2.resizeWindow("HSV", 640, 240)
        cv2.createTrackbar("HUE Min", "HSV", 19, 179, self.empty)
        cv2.createTrackbar("HUE Max", "HSV", 35, 179, self.empty)
        cv2.createTrackbar("SAT Min", "HSV", 107, 255, self.empty)
        cv2.createTrackbar("SAT Max", "HSV", 255, 255, self.empty)
        cv2.createTrackbar("VALUE Min", "HSV", 89, 255, self.empty)
        cv2.createTrackbar("VALUE Max", "HSV", 255, 255, self.empty)

        cv2.namedWindow("Parameters")
        cv2.resizeWindow("Parameters", 640, 240)
        cv2.createTrackbar("Threshold1", "Parameters", 166, 255, self.empty)
        cv2.createTrackbar("Threshold2", "Parameters", 171, 255, self.empty)
        cv2.createTrackbar("Area", "Parameters", 3750, 30000, self.empty)

    @staticmethod
    def empty(a):
        """Empty callback function for trackbars."""
        pass

    def getContours(self, img, imgContour):
        """Detects and draws contours on the image."""
        contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            areaMin = cv2.getTrackbarPos("Area", "Parameters")
            if area > areaMin:
                cv2.drawContours(imgContour, cnt, -1, (255, 0, 255), 7)
                peri = cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
                x, y, w, h = cv2.boundingRect(approx)
                cv2.rectangle(imgContour, (x, y), (x + w, y + h), (0, 255, 0), 5)

                cx = int(x + (w / 2))
                cy = int(y + (h / 2))

                if cx < int(self.frameWidth / 2) - self.deadZone:
                    cv2.putText(imgContour, "GO LEFT", (20, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 255), 3)
                elif cx > int(self.frameWidth / 2) + self.deadZone:
                    cv2.putText(imgContour, "GO RIGHT", (20, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 255), 3)
                elif cy < int(self.frameHeight / 2) - self.deadZone:
                    cv2.putText(imgContour, "GO UP", (20, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 255), 3)
                elif cy > int(self.frameHeight / 2) + self.deadZone:
                    cv2.putText(imgContour, "GO DOWN", (20, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 255), 3)

    def start_tracking(self):
        """Starts the video stream and object tracking process."""
        while True:
            _, img = self.cap.read()
            imgContour = img.copy()
            imgHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # Get HSV values from trackbars
            h_min = cv2.getTrackbarPos("HUE Min", "HSV")
            h_max = cv2.getTrackbarPos("HUE Max", "HSV")
            s_min = cv2.getTrackbarPos("SAT Min", "HSV")
            s_max = cv2.getTrackbarPos("SAT Max", "HSV")
            v_min = cv2.getTrackbarPos("VALUE Min", "HSV")
            v_max = cv2.getTrackbarPos("VALUE Max", "HSV")

            lower = np.array([h_min, s_min, v_min])
            upper = np.array([h_max, s_max, v_max])
            mask = cv2.inRange(imgHSV, lower, upper)
            result = cv2.bitwise_and(img, img, mask=mask)

            imgGray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
            threshold1 = cv2.getTrackbarPos("Threshold1", "Parameters")
            threshold2 = cv2.getTrackbarPos("Threshold2", "Parameters")
            imgCanny = cv2.Canny(imgGray, threshold1, threshold2)

            self.getContours(imgCanny, imgContour)

            # Display Results
            cv2.imshow("Tracking", imgContour)
            if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to exit
                break

        self.cap.release()
        cv2.destroyAllWindows()


# Run the object tracker
if __name__ == "__main__":
    tracker = ObjectTracker()
    tracker.start_tracking()
