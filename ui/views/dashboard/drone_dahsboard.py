import streamlit as st
import pygame
from djitellopy import Tello
import threading
import queue
from drone.drone import Drone
import cv2
import numpy as np
import os
import datetime
import time
import socket
import subprocess
from human_face.securevision import MultiPersonFaceRecognitionApp
from ui.services.main import save_detection

def cleanup_port_11111():
    """Ultra-aggressive cleanup of port 11111 and all djitellopy resources"""
    print("[CLEANUP] Starting aggressive port 11111 cleanup...")
    
    try:
        # Method 1: Kill ALL Python processes that might have djitellopy
        try:
            result = subprocess.run(['wmic', 'process', 'where', 'name="python.exe"', 'get', 'processid,commandline'], 
                                  capture_output=True, text=True, timeout=10)
            lines = result.stdout.split('\n')
            for line in lines:
                if 'djitellopy' in line.lower() or 'tello' in line.lower():
                    try:
                        pid = line.split()[-1].strip()
                        if pid.isdigit():
                            subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True, timeout=5)
                            print(f"[CLEANUP] Killed djitellopy process {pid}")
                    except:
                        pass
        except:
            pass
            
        # Method 2: Force close anything using port 11111
        for attempt in range(3):
            try:
                result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=10)
                lines = result.stdout.split('\n')
                killed_any = False
                for line in lines:
                    if ':11111' in line and ('UDP' in line or 'LISTENING' in line):
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1].strip()
                            try:
                                subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True, timeout=5)
                                print(f"[CLEANUP] Force-killed process {pid} using port 11111")
                                killed_any = True
                            except:
                                pass
                if not killed_any:
                    break  # No more processes to kill
                time.sleep(2)  # Wait between attempts
            except:
                break
                
        # Method 3: Try socket binding test with SO_REUSEADDR and permission handling
        for attempt in range(3):  # Reduced attempts to avoid long waits
            try:
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                test_sock.settimeout(1)
                test_sock.bind(('', 11111))
                test_sock.close()
                print(f"[CLEANUP] Port 11111 is now free (attempt {attempt + 1})")
                break
            except socket.error as e:
                error_code = getattr(e, 'errno', None) or getattr(e, 'winerror', None)
                if error_code == 10013:  # Permission denied
                    print(f"[CLEANUP] Permission denied for port 11111 - this is normal on Windows")
                    break  # Don't keep retrying permission errors
                elif attempt < 2:
                    print(f"[CLEANUP] Port still busy, waiting... (attempt {attempt + 1})")
                    time.sleep(2)  # Shorter wait
                else:
                    print(f"[CLEANUP] Port 11111 still busy after all attempts: {e}")
                    
        # Method 4: Clear any remaining cv2 resources
        try:
            cv2.destroyAllWindows()
        except:
            pass
            
        print("[CLEANUP] Port cleanup completed")
        time.sleep(1)  # Final settle time
        
    except Exception as e:
        print(f"[CLEANUP ERROR] Cleanup failed: {e}")


def show_drone():
    st.title("🛸 Drone Control Center")
    st.write("Control drones and view aerial footage.")

    # Session state for stream control
    if "run_stream" not in st.session_state:
        st.session_state.run_stream = False

    if "drone_instance" not in st.session_state:
        st.session_state.drone_instance = None
        
    # Add frame storage
    if "current_frame" not in st.session_state:
        st.session_state.current_frame = None

    # -------------------- Drone Connection Check --------------------
    def is_drone_connected(timeout=3):
        # Only check if we don't have an active drone instance
        if st.session_state.drone_instance and st.session_state.drone_instance.drone:
            try:
                battery = st.session_state.drone_instance.drone.get_battery()
                return True, battery
            except:
                # Instance exists but not responsive, clear it
                st.session_state.drone_instance = None
                
        # Quick ping test without creating persistent connection
        result = {'connected': False, 'battery': None}
        def try_connect():
            drone_test = None
            try:
                drone_test = Tello()
                drone_test.connect()
                result['battery'] = drone_test.get_battery()
                result['connected'] = True
            except Exception as e:
                print(f"[THREAD ERROR] Drone connection failed: {e}")
            finally:
                if drone_test:
                    try:
                        drone_test.end()
                    except:
                        pass
        try:
            t = threading.Thread(target=try_connect)
            t.daemon = True
            t.start()
            t.join(timeout=timeout)
            return result['connected'], result['battery']
        except Exception as e:
            print(f"[TOP-LEVEL ERROR] Drone check failed: {e}")
            return False, None

    # -------------------- PS4 Controller Check --------------------
    def is_controller_connected(timeout=2):
        result = {'connected': False, 'name': None}
        def try_check():
            try:
                pygame.init()
                pygame.joystick.init()
                if pygame.joystick.get_count() > 0:
                    joystick = pygame.joystick.Joystick(0)
                    joystick.init()
                    result['connected'] = True
                    result['name'] = joystick.get_name()
            except Exception as e:
                print(f"[THREAD ERROR] Controller check failed: {e}")
        try:
            import threading
            t = threading.Thread(target=try_check)
            t.daemon = True
            t.start()
            t.join(timeout=timeout)
            return result['connected'], result['name']
        except Exception as e:
            print(f"[TOP-LEVEL ERROR] Controller check crashed: {e}")
            return False, None

    # -------------------- Drone & Controller Status --------------------
    st.subheader("📶 Drone Connection")
    
    # Only check if we have an active drone instance
    if st.session_state.drone_instance and st.session_state.drone_instance.drone:
        try:
            battery = st.session_state.drone_instance.drone.get_battery()
            st.success("✅ Drone connected")
            st.write(f"🔋 Battery: {battery}%")
            connected = True
        except:
            st.error("❌ Drone connection lost")
            connected = False
    else:
        st.info("🔗 No active drone connection")
        connected = False

    st.subheader("🎮 PS4 Controller")
    controller_connected, controller_name = is_controller_connected()
    if controller_connected:
        st.success(f"✅ Controller connected: {controller_name}")
    else:
        st.error("❌ No PS4 controller detected")

    if not connected or not controller_connected:
        st.warning("🛑 Connect both the drone and controller to enable live control.")

    # -------------------- Refresh Button --------------------
    if st.button("🔄 Refresh"):
        # Stop everything first
        st.session_state.run_stream = False
        
        # Clean up drone instance
        if st.session_state.drone_instance:
            try:
                st.session_state.drone_instance.stop_stream()
            except:
                pass
            st.session_state.drone_instance = None
            
        # Aggressive port cleanup
        cleanup_port_11111()
        
        # Reset all session state related to video streaming
        st.session_state.current_frame = None
        if "stream_initialized" in st.session_state:
            del st.session_state.stream_initialized
        if "last_frame_time" in st.session_state:
            del st.session_state.last_frame_time
        
        st.success("✅ System refreshed - all resources cleaned up")
        time.sleep(1)
        st.rerun()

    # -------------------- Stream Toggle Control --------------------
    start_clicked = False
    stop_clicked = False
    restart_stream_clicked = False

    # Display buttons with enable/disable logic
    col1, col2, col3 = st.columns(3)
    with col1:
        if not st.session_state.run_stream:
            start_clicked = st.button("🟢 Start Live Control + Stream")
    with col2:
        if st.session_state.run_stream:
            stop_clicked = st.button("🔴 Stop Live Control + Stream")
    with col3:
        if st.session_state.run_stream:
            restart_stream_clicked = st.button("🔄 Restart Stream")

    # Handle button clicks
    if start_clicked:
        try:
            # Clear any existing state first
            st.session_state.run_stream = False
            st.session_state.current_frame = None
            
            # Clean up existing drone instance
            if st.session_state.drone_instance:
                try:
                    st.session_state.drone_instance.stop_stream()
                except:
                    pass
                st.session_state.drone_instance = None
                
            # Ultra-aggressive cleanup with longer wait
            with st.spinner("🧹 Cleaning up previous connections..."):
                cleanup_port_11111()
                time.sleep(5)  # Longer wait for Windows to release the port
            
            # Try to initialize the drone with more retries
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    with st.spinner(f"🛸 Connecting to drone (attempt {attempt + 1}/{max_retries})..."):
                        # Create new drone instance
                        st.session_state.drone_instance = Drone()
                        st.session_state.run_stream = True
                        st.success("✅ Drone stream started successfully!")
                        st.rerun()  # Refresh to show video
                        break
                        
                except Exception as e:
                    error_msg = str(e)
                    if "10048" in error_msg or "Address already in use" in error_msg:
                        if attempt < max_retries - 1:
                            st.warning(f"⚠️ Port 11111 busy (attempt {attempt + 1}). Retrying with deeper cleanup...")
                            cleanup_port_11111()
                            time.sleep(8)  # Even longer wait
                        else:
                            st.error("""
                            🚨 **Port 11111 permanently locked!** 
                            
                            **Quick Fix:** Run this in PowerShell as Administrator:
                            ```
                            Get-Process | Where-Object {$_.ProcessName -eq 'python'} | Stop-Process -Force
                            ```
                            
                            **Alternative:** Restart your computer to fully clear the port.
                            """)
                            st.session_state.run_stream = False
                    else:
                        if attempt < max_retries - 1:
                            st.warning(f"⚠️ Connection failed (attempt {attempt + 1}): {error_msg}")
                            time.sleep(3)
                        else:
                            st.error(f"❌ Failed to start drone after {max_retries} attempts: {error_msg}")
                            st.session_state.run_stream = False
                            
        except Exception as e:
            st.error(f"💥 Critical error starting drone: {e}")
            st.session_state.run_stream = False

    if stop_clicked:
        # Immediately stop the stream flag to prevent further processing
        st.session_state.run_stream = False
        st.session_state.current_frame = None
        st.session_state.last_frame_time = 0
        
        # Reset stream initialization flag
        if "stream_initialized" in st.session_state:
            del st.session_state.stream_initialized
            
        # Clean up drone app and face recognition
        if "drone_app" in st.session_state:
            st.session_state.drone_app.stop_event.set()
            # Clean up face recognition app
            if st.session_state.drone_app.face_recognition_app:
                try:
                    st.session_state.drone_app.face_recognition_app.stop_event.set()
                    if st.session_state.drone_app.face_recognition_app.cap:
                        st.session_state.drone_app.face_recognition_app.cap.release()
                except:
                    pass
            del st.session_state.drone_app
        
        # Stop the drone stream
        if st.session_state.drone_instance:
            try:
                with st.spinner("🛑 Stopping drone stream..."):
                    st.session_state.drone_instance.stop_stream()
                    st.session_state.drone_instance = None
                    time.sleep(2)  # Give time for proper cleanup
            except Exception as e:
                st.warning(f"[Stop Stream Error] {e}")
                st.session_state.drone_instance = None
        
        # Background cleanup (don't wait for it)
        try:
            cleanup_port_11111()
        except:
            pass
            
        st.success("🛑 Drone stream stopped successfully!")
        st.rerun()  # Refresh to update UI

    if restart_stream_clicked:
        # Restart the stream without fully stopping
        with st.spinner("🔄 Restarting stream..."):
            # Stop existing threads
            if "drone_app" in st.session_state:
                st.session_state.drone_app.stop_event.set()
                time.sleep(2)  # Let threads stop
            
            # Force stream restart on drone
            if st.session_state.drone_instance and st.session_state.drone_instance.drone:
                try:
                    st.session_state.drone_instance.drone.streamoff()
                    time.sleep(1)
                    st.session_state.drone_instance.drone.streamon()
                    time.sleep(2)
                    print("[RESTART] Drone stream restarted manually")
                except Exception as e:
                    print(f"[RESTART ERROR] {e}")
            
            # Recreate drone app with new threads
            if st.session_state.drone_instance:
                try:
                    st.session_state.drone_app = DroneStreamApp(st.session_state.drone_instance)
                    
                    # Initialize face recognition
                    if st.session_state.drone_app.init_face_recognition():
                        # Start drone-specific threads
                        grabber_thread = threading.Thread(target=st.session_state.drone_app.frame_grabber, daemon=True)
                        processor_thread = threading.Thread(target=st.session_state.drone_app.processing_worker, daemon=True)
                        control_thread = threading.Thread(target=st.session_state.drone_app.control_handler, daemon=True)
                        
                        grabber_thread.start()
                        processor_thread.start()
                        control_thread.start()
                        
                        st.success("✅ Stream restarted successfully!")
                    else:
                        st.error("❌ Failed to restart stream")
                except Exception as e:
                    st.error(f"❌ Restart failed: {e}")
            
        st.rerun()  # Refresh to show changes

    # -------------------- Live Video Stream Display --------------------
    if st.session_state.run_stream and st.session_state.drone_instance:
        st.markdown("---")
        st.subheader("📹 Live Drone Video Feed")
        
        # Create video placeholder  
        video_placeholder = st.empty()
        status_placeholder = st.empty()
        detection_placeholder = st.empty()
        
        drone_obj = st.session_state.drone_instance.drone
        
        # Initialize stream when drone is available and not already initialized
        if st.session_state.drone_instance and drone_obj and "stream_initialized" not in st.session_state:
            try:
                # More aggressive stream initialization
                with st.spinner("🎥 Initializing drone video stream..."):
                    # Ensure clean stream state
                    try:
                        drone_obj.streamoff()
                        time.sleep(1)
                    except:
                        pass
                    
                    # Start stream with retries
                    for attempt in range(3):
                        try:
                            drone_obj.streamon()
                            time.sleep(3)  # Longer wait for stream to stabilize
                            
                            # Test if we can get a frame
                            test_frame = drone_obj.get_frame_read()
                            if test_frame and test_frame.frame is not None:
                                st.session_state.stream_initialized = True
                                status_placeholder.success("✅ Video stream initialized successfully")
                                break
                            else:
                                raise Exception("No frame available after streamon")
                                
                        except Exception as e:
                            if attempt < 2:
                                status_placeholder.warning(f"⚠️ Stream init attempt {attempt + 1}/3 failed: {e}")
                                time.sleep(2)
                            else:
                                raise e
                                
            except Exception as stream_error:
                status_placeholder.error(f"❌ Stream initialization failed: {stream_error}")
                st.warning("💡 Try clicking 'Refresh' to clean up resources and retry")
                return
        elif not drone_obj and st.session_state.drone_instance:
            # Drone instance exists but connection is lost, show waiting message
            status_placeholder.info("🔄 Waiting for drone connection...")
        
        # Start drone processing app like video_feed.py with face recognition
        if "drone_app" not in st.session_state:
            # Create a drone processing app with face recognition capabilities
            class DroneStreamApp:
                def __init__(self, drone_instance):
                    self.drone_instance = drone_instance
                    self.results_queue = queue.Queue(maxsize=5)
                    self.detection_queue = queue.Queue()
                    self.control_queue = queue.Queue()
                    self.stop_event = threading.Event()
                    self.ps4_controller = None
                    # Initialize face recognition app with drone as stream source
                    self.face_recognition_app = None
                    # Track drone state
                    self.drone_is_flying = False
                    self.last_control_time = time.time()
                    
                def init_face_recognition(self):
                    """Initialize face recognition with drone stream"""
                    try:
                        # Create face recognition app without video capture (we'll feed frames manually)
                        self.face_recognition_app = MultiPersonFaceRecognitionApp(stream_url=None)
                        # We don't want it to use its own video capture
                        if self.face_recognition_app.cap:
                            self.face_recognition_app.cap.release()
                        self.face_recognition_app.cap = None
                        
                        # Start the face recognition app's processing thread
                        self.face_recognition_processing_thread = threading.Thread(
                            target=self.face_recognition_app.processing_worker, daemon=True
                        )
                        self.face_recognition_processing_thread.start()
                        
                        print("[INFO] Face recognition initialized for drone stream")
                        return True
                    except Exception as e:
                        print(f"[ERROR] Face recognition init failed: {e}")
                        return False
                        
                def frame_grabber(self):
                    """Grab frames from drone like video_feed.py"""
                    print("[INFO] Drone frame grabber started")
                    retry_count = 0
                    consecutive_failures = 0
                    
                    while not self.stop_event.is_set() and retry_count < 20:  # Increased retry limit
                        try:
                            if not self.drone_instance or not self.drone_instance.drone:
                                print("[WARNING] Drone instance not available")
                                break
                            
                            # Check if drone is still flying - stop video attempts if landed
                            if not self.drone_is_flying and time.time() - self.last_control_time > 10:
                                print("[INFO] Drone appears to have landed, stopping video grabber")
                                break
                            
                            # Ensure video stream is on with more robust checking
                            stream_ready = False
                            try:
                                # Check if stream is actually working
                                frame_read = self.drone_instance.drone.get_frame_read()
                                if frame_read and frame_read.frame is not None:
                                    stream_ready = True
                                elif self.drone_is_flying:  # Only try to start stream if flying
                                    print("[INFO] Stream not ready, attempting to start...")
                                    self.drone_instance.drone.streamon()
                                    time.sleep(2)
                                    consecutive_failures = 0  # Reset on successful streamon
                            except Exception as stream_error:
                                if self.drone_is_flying:  # Only log errors if supposed to be flying
                                    print(f"[ERROR] Stream check failed: {stream_error}")
                                    consecutive_failures += 1
                                    
                                    # If too many consecutive failures, try more aggressive recovery only if flying
                                    if consecutive_failures > 5 and self.drone_is_flying:
                                        print("[RECOVERY] Multiple stream failures, attempting full restart...")
                                        try:
                                            self.drone_instance.drone.streamoff()
                                            time.sleep(1)
                                            self.drone_instance.drone.streamon()
                                            time.sleep(3)
                                            consecutive_failures = 0
                                        except:
                                            pass
                                else:
                                    # If not flying, just break out of loop quietly
                                    break
                                
                                retry_count += 1
                                time.sleep(2)
                                continue
                            
                            # Get frame from drone
                            if stream_ready:
                                frame_read = self.drone_instance.drone.get_frame_read()
                                if frame_read and frame_read.frame is not None:
                                    frame = frame_read.frame.copy()
                                    
                                    if frame is not None and frame.size > 0:
                                        # Resize frame for face recognition (it expects 640x640)
                                        frame_resized = cv2.resize(frame, (640, 640))
                                        frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)

                                        
                                        # Put frame directly into face recognition app's frame_queue
                                        if self.face_recognition_app and not self.face_recognition_app.frame_queue.full():
                                            self.face_recognition_app.frame_queue.put(frame_rgb)
                                        
                                        # Reset counters on successful frame
                                        retry_count = 0
                                        consecutive_failures = 0
                                else:
                                    if self.drone_is_flying:
                                        print("[WARNING] No frame available from drone")
                                        consecutive_failures += 1
                                        if consecutive_failures > 10:
                                            retry_count += 1
                            
                            time.sleep(0.03)  # ~30 FPS
                            
                        except Exception as e:
                            if self.drone_instance is None or self.drone_instance.drone is None:
                                print("[INFO] Drone disconnected during frame grabbing")
                                break
                            print(f"[DRONE GRABBER ERROR] {e}")
                            consecutive_failures += 1
                            retry_count += 1
                            time.sleep(1)  # Longer wait on errors
                            continue
                    
                    print(f"[INFO] Drone frame grabber stopped (retry_count: {retry_count})")
                    
                def processing_worker(self):
                    """Process frames with face recognition like video_feed.py"""
                    if not self.face_recognition_app:
                        return
                        
                    while not self.stop_event.is_set():
                        try:
                            # Get processed frame from face recognition results_queue
                            processed_frame = self.face_recognition_app.results_queue.get(timeout=0.1)
                            
                            # Put processed frame in our results queue for display
                            if not self.results_queue.full():
                                self.results_queue.put(processed_frame)
                            
                            # Check for detections from face recognition detection_queue
                            try:
                                person_name, timestamp = self.face_recognition_app.detection_queue.get_nowait()
                                if not self.detection_queue.full():
                                    self.detection_queue.put((person_name, timestamp))
                            except queue.Empty:
                                pass
                            
                        except queue.Empty:
                            continue
                        except Exception as e:
                            print(f"[DRONE PROCESSING ERROR] {e}")
                            time.sleep(0.1)
                            continue
                    
                    print("[INFO] Drone processor stopped")
                    
                def control_handler(self):
                    """Handle PS4 controls separately - ALWAYS keep this running"""
                    from ps4.ps4 import PS4Controller
                    
                    try:
                        self.ps4_controller = PS4Controller(deadzone=0.1)
                        print("[INFO] PS4 Controller initialized")
                    except Exception as e:
                        print(f"[ERROR] PS4 init failed: {e}")
                        self.ps4_controller = None
                    
                    while not self.stop_event.is_set():
                        try:
                            if not self.drone_instance or not self.drone_instance.drone:
                                break
                            
                            # Handle PS4 controls continuously - INDEPENDENT of video stream
                            if self.ps4_controller and self.drone_instance.drone:
                                pygame.event.pump()
                                
                                # Check controller state to determine if drone is flying
                                # Get current axis values
                                if self.ps4_controller.joystick:
                                    lx = self.ps4_controller.joystick.get_axis(0)  # Left stick X
                                    ly = self.ps4_controller.joystick.get_axis(1)  # Left stick Y
                                    rx = self.ps4_controller.joystick.get_axis(2)  # Right stick X
                                    ry = self.ps4_controller.joystick.get_axis(3)  # Right stick Y
                                    
                                    # Check for active control input
                                    has_input = any([
                                        abs(lx) > 0.1,
                                        abs(ly) > 0.1,
                                        abs(rx) > 0.1,
                                        abs(ry) > 0.1,
                                    ])
                                    
                                    if has_input:
                                        self.last_control_time = time.time()
                                        if self.drone_instance.in_air:  # Check actual drone state
                                            self.drone_is_flying = True
                                    
                                    # Check for takeoff button (X button)
                                    if self.ps4_controller.joystick.get_button(0) and not self.drone_instance.in_air:
                                        self.drone_is_flying = True
                                        print("[STATE] Drone takeoff detected, enabling flying mode")
                                    
                                    # Check for landing button (Circle button) 
                                    if self.ps4_controller.joystick.get_button(1) and self.drone_instance.in_air:
                                        self.drone_is_flying = False
                                        print("[STATE] Drone landing detected, disabling flying mode")
                                
                                # Always update drone state based on actual drone status
                                if hasattr(self.drone_instance, 'in_air'):
                                    if not self.drone_instance.in_air and self.drone_is_flying:
                                        # Drone has landed but we still think it's flying
                                        self.drone_is_flying = False
                                        print("[STATE] Drone has landed, disabling recovery systems")
                                
                                self.drone_instance._handle_controls(self.ps4_controller)
                            
                            time.sleep(0.01)  # High frequency for responsive controls
                            
                        except Exception as e:
                            if self.drone_instance is None or self.drone_instance.drone is None:
                                break
                            print(f"[DRONE CONTROL ERROR] {e}")
                            time.sleep(0.1)
                            continue
                    
                    print("[INFO] Drone controller stopped")
            
            # Initialize drone app
            st.session_state.drone_app = DroneStreamApp(st.session_state.drone_instance)
            
            # Initialize face recognition
            if st.session_state.drone_app.init_face_recognition():
                # Start drone-specific threads (face recognition processing is already started)
                grabber_thread = threading.Thread(target=st.session_state.drone_app.frame_grabber, daemon=True)
                processor_thread = threading.Thread(target=st.session_state.drone_app.processing_worker, daemon=True)
                control_thread = threading.Thread(target=st.session_state.drone_app.control_handler, daemon=True)
                
                grabber_thread.start()
                processor_thread.start()
                control_thread.start()
                
                status_placeholder.info("🎮 Drone processor with face recognition started")
            else:
                # Fallback: Start simple video processing without face recognition
                status_placeholder.warning("⚠️ Face recognition failed, starting basic video stream...")
                
                # Add simple frame processor as fallback
                def simple_frame_processor():
                    while not st.session_state.drone_app.stop_event.is_set():
                        try:
                            if not st.session_state.drone_instance or not st.session_state.drone_instance.drone:
                                break
                            
                            frame_read = st.session_state.drone_instance.drone.get_frame_read()
                            if frame_read and frame_read.frame is not None:
                                frame = frame_read.frame.copy()
                                
                                if frame is not None and frame.size > 0:
                                    # Resize for display
                                    frame_resized = cv2.resize(frame, (640, 640))
                                    frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)

                                    
                                    # Put frame in results queue
                                    if not st.session_state.drone_app.results_queue.full():
                                        st.session_state.drone_app.results_queue.put(frame_rgb)
                            
                            time.sleep(0.03)  # ~30 FPS
                            
                        except Exception as e:
                            if st.session_state.drone_instance is None or st.session_state.drone_instance.drone is None:
                                break
                            print(f"[SIMPLE PROCESSOR ERROR] {e}")
                            time.sleep(0.1)
                            continue
                
                # Start fallback threads
                simple_thread = threading.Thread(target=simple_frame_processor, daemon=True)
                control_thread = threading.Thread(target=st.session_state.drone_app.control_handler, daemon=True)
                
                simple_thread.start()
                control_thread.start()
                
                status_placeholder.info("🎮 Basic drone video stream started (no face recognition)")
        
        # Smooth continuous streaming loop EXACTLY like video_feed.py
        try:
            app = st.session_state.drone_app
            
            # Add thread monitoring and automatic restart
            def check_and_restart_threads():
                """Check if threads are still alive and restart if needed"""
                try:
                    # Only do recovery if drone is supposed to be flying
                    if not hasattr(app, 'drone_is_flying') or not app.drone_is_flying:
                        return
                    
                    # Check if face recognition processing thread is alive
                    if hasattr(app, 'face_recognition_processing_thread'):
                        if not app.face_recognition_processing_thread.is_alive():
                            print("[RECOVERY] Face recognition thread died, restarting...")
                            app.face_recognition_processing_thread = threading.Thread(
                                target=app.face_recognition_app.processing_worker, daemon=True
                            )
                            app.face_recognition_processing_thread.start()
                    
                    # Check if stream needs to be restarted - only if flying
                    if st.session_state.drone_instance and st.session_state.drone_instance.drone and app.drone_is_flying:
                        try:
                            # Test if we can get a frame
                            frame_read = st.session_state.drone_instance.drone.get_frame_read()
                            if not frame_read or frame_read.frame is None:
                                print("[RECOVERY] Stream seems dead, attempting restart...")
                                st.session_state.drone_instance.drone.streamon()
                                time.sleep(2)
                        except Exception as e:
                            print(f"[RECOVERY ERROR] {e}")
                except Exception as e:
                    print(f"[THREAD CHECK ERROR] {e}")
            
            # Start the continuous streaming loop like video_feed.py
            try:
                frame_count = 0
                last_thread_check = time.time()
                
                while st.session_state.run_stream:
                    try:
                        # Check threads every 30 frames (~1 second)
                        frame_count += 1
                        if frame_count % 30 == 0 or time.time() - last_thread_check > 3:
                            check_and_restart_threads()
                            last_thread_check = time.time()
                        
                        # Check if drone connection is lost during streaming
                        if st.session_state.drone_instance and not st.session_state.drone_instance.drone:
                            status_placeholder.warning("🛬 Drone connection lost! Attempting to reconnect...")
                            
                            # Clean up background thread
                            if "drone_app" in st.session_state:
                                st.session_state.drone_app.stop_event.set()
                                del st.session_state.drone_app
                            
                            # Reset stream initialization
                            if "stream_initialized" in st.session_state:
                                del st.session_state.stream_initialized
                            
                            # Try to reinitialize
                            try:
                                st.session_state.drone_instance.__init__()
                                status_placeholder.success("✅ Drone reconnected! Controls active again.")
                                break  # Exit loop to restart
                            except Exception as reconnect_error:
                                status_placeholder.error(f"❌ Reconnection failed: {reconnect_error}")
                                break
                        
                        # Get frame from queue (same as video_feed.py)
                        try:
                            frame = app.results_queue.get(timeout=0.1)
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            
                            # Display frame continuously (same as video_feed.py)
                            video_placeholder.image(
                                frame_rgb,
                                caption="🛸 Live Drone Feed with Face Recognition",
                                channels="RGB",
                                width=640
                            )
                            
                            # Check for face detections (same as video_feed.py)
                            try:
                                person_name, ts = app.detection_queue.get_nowait()
                                save_detection(person_name, ts, "Drone Camera")
                                ts_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                                detection_placeholder.warning(
                                    f"🚨 POI Detected: {person_name} at Drone Camera — {ts_str}")
                            except queue.Empty:
                                pass
                            except Exception:
                                pass
                            
                            current_time = datetime.datetime.now().strftime('%H:%M:%S')
                            status_placeholder.success(f"📡 Face recognition streaming at {current_time}")
                            
                        except queue.Empty:
                            # No frame available, show waiting message
                            if hasattr(app, 'drone_is_flying') and app.drone_is_flying:
                                status_placeholder.warning("⚠️ Waiting for frames... (Stream may be recovering)")
                                
                                # Try to restart grabber if no frames for too long - only if flying
                                if frame_count > 100:  # No frames for ~3 seconds
                                    print("[RECOVERY] No frames received, attempting to restart grabber...")
                                    try:
                                        # Restart frame grabber thread
                                        grabber_thread = threading.Thread(target=app.frame_grabber, daemon=True)
                                        grabber_thread.start()
                                        frame_count = 0  # Reset counter
                                    except Exception as restart_error:
                                        print(f"[RESTART ERROR] {restart_error}")
                            else:
                                # Drone not flying, just show static message
                                status_placeholder.info("📡 Drone stream paused (not flying)")
                                frame_count = 0  # Reset counter to prevent unnecessary restarts
                            
                            continue
                            
                    except Exception as e:
                        # Handle other errors but continue streaming
                        status_placeholder.error(f"Frame error: {e}")
                        print(f"[STREAM ERROR] {e}")
                        continue
                        
            except Exception as stream_error:
                status_placeholder.error(f"Stream loop error: {stream_error}")
            finally:
                # Clean shutdown like video_feed.py
                if "drone_app" in st.session_state:
                    st.session_state.drone_app.stop_event.set()
                    # Also stop face recognition app
                    if st.session_state.drone_app.face_recognition_app:
                        try:
                            st.session_state.drone_app.face_recognition_app.stop_event.set()
                            if st.session_state.drone_app.face_recognition_app.cap:
                                st.session_state.drone_app.face_recognition_app.cap.release()
                        except:
                            pass
                status_placeholder.info("🛑 Video stream and face recognition stopped")
                
        except Exception as e:
            status_placeholder.error(f"Display error: {e}")
            
        # -------------------- Manual Controls Info --------------------
        st.markdown("---")
        st.subheader("🎮 Manual Controls")
        
        col_controls1, col_controls2 = st.columns(2)
        
        with col_controls1:
            st.markdown("""
            **Flight Controls:**
            - **Left Stick**: Move Left/Right, Forward/Backward
            - **Right Stick**: Altitude Up/Down, Rotate Left/Right
            - **X Button (❌)**: Takeoff
            - **Circle Button (⭕)**: Land
            """)
            
        with col_controls2:
            battery_status = "Unknown"
            if connected and battery:
                battery_status = f"{battery}%"
            
            st.markdown(f"""
            **Current Status:**
            - 🔋 Battery: {battery_status}
            - ✈️ Flight Mode: Manual Control
            - 📡 Stream: {'Active' if st.session_state.run_stream else 'Inactive'}
            - 🎮 Controller: {'Connected' if controller_connected else 'Disconnected'}
            - 👁️ Face Recognition: {'Active' if st.session_state.run_stream else 'Inactive'}
            """)
            
    else:
        if not st.session_state.run_stream:
            st.info("📺 Click 'Start Live Control + Stream' to begin video feed")

    # -------------------- Application logs --------------------
    st.markdown("---")
    st.subheader("📋 System Logs")
    
    if st.button("🔄 Refresh Logs"):
        st.rerun()

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Static log entries
    static_logs = [
        f"[{now}] Drone Control Center Initialized",
        f"[{now}] Video Stream: {'Active' if st.session_state.run_stream else 'Inactive'}",
        f"[{now}] Controller: {'Connected' if controller_connected else 'Disconnected'}",
        f"[{now}] Port 11111: {'In Use' if st.session_state.run_stream else 'Available'}",
        f"[{now}] Awaiting commands..."
    ]

    # Load log entries from app.log
    log_file_path = "app.log"
    dynamic_logs = []
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, "r") as f:
                dynamic_logs = f.readlines()[-10:]  # Last 10 entries
        except Exception as e:
            dynamic_logs = [f"[ERROR] Failed to read log file: {e}"]
    else:
        dynamic_logs = ["[INFO] No log file found."]

    # Combine and display logs
    combined_logs = static_logs + [line.strip() for line in dynamic_logs]
    st.code("\n".join(combined_logs), language="text")
