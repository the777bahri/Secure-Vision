import pygame
import time

class PS4Controller:
    BUTTON_NAMES = {
        0: "X ❌ ",
        1: "Circle ⭕ ",
        2: "Square 🟥 ",
        3: "Triangle 🔼 ",
        4: "Share 💻 ",
        5: "PS Button 🎮 ",
        6: "Options ⚙️ ",
        7: "L3",
        8: "R3",
        9: "L1",
        10: "R1",
        11: "Up ⬆️ ",
        12: "Down ⬇️ ",
        13: "Left ⬅️ ",
        14: "Right ➡️ ",
        15: "Touchpad 🖱️"
    }

    AXIS_NAMES = {
        0: "Left Stick X 🕹️ ",
        1: "Left Stick Y 🕹️ ",
        2: "Right Stick X 🕹️ ",
        3: "Right Stick Y 🕹️ ",
        4: "L2 Trigger",
        5: "R2 Trigger"
    }

    def __init__(self, deadzone=0.05):
        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            raise RuntimeError("No PS4 controller detected.")

        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        print(f"Detected controller: {self.joystick.get_name()}")

        self.deadzone = deadzone
        self.prev_axes = [self.joystick.get_axis(i) for i in range(self.joystick.get_numaxes())]
        self.prev_buttons = [self.joystick.get_button(i) for i in range(self.joystick.get_numbuttons())]
        self.prev_hat = self.joystick.get_hat(0) if self.joystick.get_numhats() > 0 else None

    def _is_diff(self, a, b):
        if abs(a) < self.deadzone and abs(b) < self.deadzone:
            return False
        return abs(a - b) > self.deadzone

    def start(self):
        while True:
            pygame.event.pump()

            # Axes
            for i in range(self.joystick.get_numaxes()):
                value = self.joystick.get_axis(i)
                if self._is_diff(value, self.prev_axes[i]):
                    name = self.AXIS_NAMES.get(i, f"Axis {i}")
                    print(f"{name} moved: {round(value, 2)}")
                    self.prev_axes[i] = value

            # Buttons
            for i in range(self.joystick.get_numbuttons()):
                state = self.joystick.get_button(i)
                if state != self.prev_buttons[i]:
                    name = self.BUTTON_NAMES.get(i, f"Button {i}")
                    print(f"{name} {'pressed' if state else 'released'}")
                    self.prev_buttons[i] = state

            # D-Pad (Hat)
            if self.joystick.get_numhats() > 0:
                hat = self.joystick.get_hat(0)
                if hat != self.prev_hat:
                    print(f"D-Pad: {hat}")
                    self.prev_hat = hat

            time.sleep(0.01)


# Run the tracker
if __name__ == "__main__":
    try:
        controller = PS4Controller()
        controller.start()
    except RuntimeError as e:
        print(e)
