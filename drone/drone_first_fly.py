import cv2
from djitellopy import Tello
from pynput.keyboard import Key, Listener

class Drone:
    def __init__(self):
        """Initialize the drone, set up connection, and start video streaming."""
        self.width = 320
        self.height = 320

        # Movement speeds (range: -100 to 100)
        self.SPEED = 30
        self.YAW_SPEED = 30
        self.ALTITUDE_SPEED = 30

        # Initialize the drone
        self.drone = Tello()
        self.drone.connect()
        print(f"[INFO] Connected to Tello Drone")
        print(f"[INFO] Battery Level: {self.drone.get_battery()}%")

        # Start video streaming
        self.drone.streamoff()
        self.drone.streamon()
        print("[INFO] Video streaming started.")

        self.listener = Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()

    def on_press(self, key):
        """Handle key press events for drone control."""
        try:
            if key == Key.up:
                print("[ACTION] Moving Forward")
                self.drone.send_rc_control(0, min(self.SPEED, 100), 0, 0)
            elif key == Key.down:
                print("[ACTION] Moving Backward")
                self.drone.send_rc_control(0, max(-self.SPEED, -100), 0, 0)
            elif key == Key.left:
                print("[ACTION] Moving Left")
                self.drone.send_rc_control(max(-self.SPEED, -100), 0, 0, 0)
            elif key == Key.right:
                print("[ACTION] Moving Right")
                self.drone.send_rc_control(min(self.SPEED, 100), 0, 0, 0)
            elif key == Key.space:
                print("[ACTION] Taking Off")
                self.drone.takeoff()
            elif key == Key.esc:
                print("[ACTION] Landing and Exiting")
                self.land_drone()
                self.listener.stop()  # Properly stop the keyboard listener
                return False  # Ensure listener exits
            elif key.char == 'e':
                print("[ACTION] Rotating Counter-Clockwise")
                self.drone.send_rc_control(0, 0, 0, max(-self.YAW_SPEED, -100))
            elif key.char == 'r':
                print("[ACTION] Rotating Clockwise")
                self.drone.send_rc_control(0, 0, 0, min(self.YAW_SPEED, 100))
            elif key.char == 'u':
                print("[ACTION] Moving Up")
                self.drone.send_rc_control(0, 0, min(self.ALTITUDE_SPEED, 100), 0)
            elif key.char == 'd':
                print("[ACTION] Moving Down")
                self.drone.send_rc_control(0, 0, max(-self.ALTITUDE_SPEED, -100), 0)
        except AttributeError:
            pass  # Ignore errors for non-character keys

    def on_release(self, key):
        """Stop drone movement when key is released."""
        print("[INFO] Stopping movement")
        self.drone.send_rc_control(0, 0, 0, 0)

    def land_drone(self):
        """Land the drone safely and exit."""
        self.drone.land()
        print("[INFO] Drone landed safely.")
        cv2.destroyAllWindows()
        print("[INFO] Program exited.")

    def start_drone(self):
        """Capture and display the video feed from the drone."""
        while True:
            frame_read = self.drone.get_frame_read()
            img = cv2.resize(frame_read.frame.copy(), (self.width, self.height))
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert to RGB for better visualization

            cv2.imshow("Tello Camera", rgb)

            if cv2.waitKey(1) & 0xFF == 27:  # ESC to land and exit
                self.land_drone()
                break
        cv2.destroyAllWindows()  # Ensure OpenCV windows close properly
        exit()  # Forcefully exit the script

# Run the drone program
if __name__ == "__main__":
    drone = Drone()
    drone.start_drone()
