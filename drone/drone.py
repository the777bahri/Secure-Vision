import cv2
import time
import pygame
from PIL import Image
from djitellopy import Tello
from ps4.ps4 import PS4Controller
import streamlit as st
import numpy as np
import socket
import errno

class Drone:
    def __init__(self):
        self.width = 200
        self.height = 150
        self.SPEED = 50
        self.YAW_SPEED = 50
        self.ALTITUDE_SPEED = 50
        self.in_air = False
        self.drone = None
        self.frame_read = None
        # Store previous control values to only send when changed
        self.prev_controls = {'lr': 0, 'fb': 0, 'ud': 0, 'yaw': 0}

        try:
            # Force cleanup any existing connections first
            self._force_cleanup_existing_connections()
            
            # Try to connect with retries and longer delays
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    print(f"[INIT] Attempting drone connection {attempt + 1}/{max_retries}...")
                    
                    # Create new Tello instance
                    self.drone = Tello()
                    self.drone.connect()
                    
                    battery = self.drone.get_battery()
                    print(f"[INFO] Connected to Tello Drone")
                    print(f"[INFO] Battery Level: {battery}%")
                    
                    # Only try to start stream after successful connection
                    self._restart_stream()
                    break
                    
                except Exception as e:
                    print(f"[WARNING] Connection attempt {attempt + 1} failed: {e}")
                    
                    # Clean up failed connection
                    if self.drone:
                        try:
                            self.drone.end()
                        except:
                            pass
                        self.drone = None
                    
                    if attempt < max_retries - 1:
                        # Wait longer between retries for port cleanup
                        wait_time = (attempt + 1) * 3  # Progressive backoff
                        print(f"[INFO] Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                    else:
                        raise Exception(f"Failed to connect to drone after {max_retries} attempts. Last error: {e}")

        except Exception as e:
            print(f"[INIT ERROR] Could not initialize drone: {e}")
            self.stop_stream()
            raise

    def _force_cleanup_existing_connections(self):
        """Force cleanup of any existing UDP connections on port 11111"""
        try:
            import subprocess
            import socket
            import errno
            
            # Method 1: Try to bind to port to check if it's free
            test_sock = None
            try:
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                test_sock.bind(('', 11111))
                test_sock.close()
                print("[CLEANUP] Port 11111 is available")
                return
            except socket.error as e:
                if test_sock:
                    test_sock.close()
                print(f"[CLEANUP] Port 11111 is busy: {e}")
            
            # Method 2: Force kill processes using the port
            try:
                result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=10)
                for line in result.stdout.split('\n'):
                    if ':11111' in line and 'UDP' in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1].strip()
                            try:
                                subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True, timeout=5)
                                print(f"[CLEANUP] Killed process {pid} using port 11111")
                            except:
                                pass
                                
                time.sleep(2)  # Allow time for cleanup
                
            except Exception as cleanup_err:
                print(f"[CLEANUP] Process cleanup failed: {cleanup_err}")
                
        except Exception as e:
            print(f"[CLEANUP ERROR] {e}")

    def _restart_stream(self):
        """Stop and restart the video stream safely with error handling."""
        max_stream_retries = 3
        
        for stream_attempt in range(max_stream_retries):
            try:
                if not self.drone:
                    raise Exception("No drone connection available")
                
                # Always try to turn off stream first
                try:
                    self.drone.streamoff()
                    time.sleep(2)  # Longer wait for stream to fully stop
                    print("[INFO] Video stream stopped")
                except Exception as e:
                    print(f"[STREAMOFF WARNING] {e}")

                # Wait before trying to start stream
                time.sleep(1)
                
                # Try to start stream with timeout protection
                try:
                    print(f"[INFO] Starting video stream (attempt {stream_attempt + 1}/{max_stream_retries})...")
                    self.drone.streamon()
                    time.sleep(2)  # Wait for stream to initialize
                    
                    # Get frame reader
                    self.frame_read = self.drone.get_frame_read()
                    if self.frame_read:
                        print("[INFO] Video streaming started successfully.")
                        return  # Success, exit retry loop
                    else:
                        raise Exception("Frame reader is None")
                        
                except Exception as e:
                    error_msg = str(e)
                    if "10048" in error_msg and stream_attempt < max_stream_retries - 1:
                        print(f"[STREAM RETRY] Port busy, waiting before retry {stream_attempt + 1}...")
                        time.sleep(5)  # Wait longer for port to clear
                        continue
                    else:
                        raise Exception(f"Stream start failed: {e}")
                        
            except Exception as e:
                if stream_attempt < max_stream_retries - 1:
                    print(f"[STREAM WARNING] Attempt {stream_attempt + 1} failed: {e}")
                    time.sleep(3)
                else:
                    print(f"[STREAM ERROR] All stream attempts failed: {e}")
                    raise

    def land_drone(self):
        try:
            self.drone.land()
            print("[INFO] Drone landed safely.")
        except Exception as e:
            print(f"[WARNING] Could not land drone cleanly: {e}")
        self.in_air = False
        self.stop_stream()

    def stop_stream(self):
        """Safely stop the video stream and clean up resources."""
        try:
            if self.drone:
                try:
                    self.drone.streamoff()
                    time.sleep(1)  # Give time for stream to stop
                except:
                    pass
                try:
                    self.drone.end()
                    time.sleep(2)  # Important: Wait for resources to be freed
                except:
                    pass
                print("[INFO] Stream stopped and drone disconnected.")
        except Exception as e:
            print(f"[ERROR] Stream cleanup failed: {e}")
        finally:
            self.drone = None
            self.frame_read = None
            cv2.destroyAllWindows()
            
            # Force cleanup of any remaining UDP connections
            try:
                # Try to bind to the port to ensure it's free
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                test_socket.bind(('', 11111))
                test_socket.close()
            except socket.error as e:
                if e.errno == errno.EADDRINUSE:
                    print("[WARNING] Port 11111 still in use, but continuing...")
                pass

    def __del__(self):
        """Ensure cleanup when object is destroyed."""
        self.stop_stream()

    def start_drone(self):
        ps4 = PS4Controller(deadzone=0.1)
        try:
            while True:
                pygame.event.pump()
                self._handle_controls(ps4)

                if self.frame_read and self.frame_read.frame is not None:
                    frame = cv2.resize(self.frame_read.frame.copy(), (self.width, self.height))
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    cv2.imshow("Tello Camera", rgb)

                if cv2.waitKey(1) & 0xFF == 27:
                    self.land_drone()
                    break

                time.sleep(0.03)
        except KeyboardInterrupt:
            self.land_drone()

    def start_drone_for_streamlit(self, placeholder=None, frame_callback=None):
        """Start the drone stream for Streamlit interface."""
        ps4 = PS4Controller(deadzone=0.1)
        frame_count = 0
        last_frame_time = time.time()
        max_retries = 3
        retry_count = 0

        # Ensure stream is running
        if not self.drone:
            print("[ERROR] Drone not initialized")
            return
        
        try:
            # Force stream to start
            self._restart_stream()
            print("[INFO] Stream initialized")
            
            while True:  # Changed from st.session_state.get("run_stream", False)
                try:
                    pygame.event.pump()
                    
                    # Debug PS4 controller state
                    if ps4.joystick:
                        button_state = ps4.joystick.get_button(0)
                        print(f"[DEBUG] PS4 Button 0 (X) state: {button_state}, in_air: {self.in_air}")
                    
                    self._handle_controls(ps4)

                    if self.frame_read and self.frame_read.frame is not None:
                        try:
                            frame = self.frame_read.frame
                            if frame is None or frame.size == 0:
                                print("[WARNING] Empty frame received.")
                                retry_count += 1
                                if retry_count >= max_retries:
                                    print("[ERROR] Too many empty frames, restarting stream...")
                                    self._restart_stream()
                                    retry_count = 0
                                continue

                            # Reset retry count on successful frame
                            retry_count = 0

                            # Calculate FPS and limit frame rate
                            current_time = time.time()
                            elapsed = current_time - last_frame_time
                            if elapsed < 0.033:  # Limit to ~30 FPS
                                time.sleep(0.033 - elapsed)
                            
                            # Resize the frame
                            frame = cv2.resize(frame.copy(), (self.width, self.height))
                            
                            # Convert BGR to RGB
                            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            
                            # Store the frame if callback provided
                            if frame_callback:
                                frame_callback(rgb)
                            
                            # Display the RGB frame
                            if placeholder:
                                placeholder.image(rgb, caption="Live Drone Feed", channels="RGB", use_container_width=True)
                            
                            frame_count += 1
                            last_frame_time = current_time
                            
                            # Print FPS every 30 frames
                            if frame_count % 30 == 0:
                                fps = 30 / (time.time() - last_frame_time)
                                print(f"[INFO] Current FPS: {fps:.1f}")
                                
                        except Exception as fe:
                            print(f"[FRAME ERROR] {fe}")
                            retry_count += 1
                            if retry_count >= max_retries:
                                print("[ERROR] Too many frame errors, restarting stream...")
                                self._restart_stream()
                                retry_count = 0
                            continue

                    time.sleep(0.02)
                except Exception as e:
                    print(f"[LOOP ERROR] {e}")
                    retry_count += 1
                    if retry_count >= max_retries:
                        raise
                    time.sleep(1)  # Wait before retrying
                    continue

        except Exception as e:
            print(f"[STREAM ERROR] Stream loop crashed: {e}")
        finally:
            self.stop_stream()

    def _handle_controls(self, ps4):
        try:
            if not ps4.joystick:
                print("[WARNING] PS4 controller not connected")
                return

            lx = ps4.joystick.get_axis(0)
            ly = ps4.joystick.get_axis(1)
            rx = ps4.joystick.get_axis(2)
            ry = ps4.joystick.get_axis(3)

            lr = int(lx * self.SPEED)
            fb = int(-ly * self.SPEED)
            ud = int(-ry * self.ALTITUDE_SPEED)
            yaw = int(rx * self.YAW_SPEED)

            # Only send RC commands if values have changed and drone is connected
            current_controls = {'lr': lr, 'fb': fb, 'ud': ud, 'yaw': yaw}
            if self.drone and current_controls != self.prev_controls:
                self.drone.send_rc_control(lr, fb, ud, yaw)
                # Only print when controls actually change significantly (not just noise/drift)
                if any(abs(current_controls[key]) > 5 for key in current_controls):
                    print(f"[CONTROL] RC: lr={lr}, fb={fb}, ud={ud}, yaw={yaw}")
                self.prev_controls = current_controls.copy()

            # Handle takeoff (X button)
            if ps4.joystick.get_button(0) and not self.in_air:
                print("[ACTION] Takeoff initiated")
                try:
                    if self.drone:
                        self.drone.takeoff()
                        self.in_air = True
                        print("[SUCCESS] Drone is now in air")
                        time.sleep(1)
                except Exception as e:
                    print(f"[ERROR] Takeoff failed: {e}")

            # Handle landing (Circle button)
            if ps4.joystick.get_button(1) and self.in_air:
                print("[ACTION] Landing initiated")
                self.land_drone()

        except Exception as e:
            print(f"[CONTROL ERROR] {e}")
