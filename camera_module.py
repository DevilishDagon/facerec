# camera_module.py
import cv2
import time
import traceback
import numpy as np

class CameraManager:
    def __init__(self, width=800, height=480):
        """
        Initialize camera manager with retries
        
        :param width: Desired width of camera output
        :param height: Desired height of camera output
        """
        self.picam2 = None
        self.width = width
        self.height = height
        
        # Try to import picamera2 module
        try:
            from picamera2 import Picamera2
            from libcamera import controls
            self.Picamera2 = Picamera2
            self.controls = controls
            print("[CameraManager] Imported camera modules successfully")
        except ImportError as e:
            print(f"[CameraManager] Error importing camera modules: {e}")
            print("[CameraManager] Running in fallback mode")
            return
            
        for attempt in range(5):
            try:
                print(f"[CameraManager] Attempting camera init ({attempt + 1}/5)...")
                self.picam2 = self.Picamera2()
                time.sleep(1)  # Let system settle
                
                # Try to create a preview configuration
                config = self.picam2.create_preview_configuration(
                    main={"size": (640, 480), "format": "RGB888"}
                )
                
                self.picam2.configure(config)
                self.picam2.start(show_preview=False)
                
                # Take a test frame to confirm camera is working
                test_frame = self.picam2.capture_array()
                if test_frame is None or test_frame.size == 0:
                    raise RuntimeError("Camera returned empty frame")
                    
                print("[CameraManager] Camera initialized successfully")
                break
                
            except Exception as e:
                print(f"[CameraManager] Attempt {attempt + 1} failed: {e}")
                traceback.print_exc()
                
                # Close camera if it was opened
                if self.picam2:
                    try:
                        self.picam2.stop()
                    except:
                        pass
                    self.picam2 = None
                    
                time.sleep(2)  # Wait before retrying
        else:  # This executes if the loop completes without a break
            print("[CameraManager] Failed to initialize camera after 5 attempts")
            # Provide a fake camera for development/testing if real one isn't available
            self._use_fake_camera = True
            
    def _get_fake_frame(self):
        """Generate a fake frame with a placeholder message"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, "Camera Not Available", (50, 240), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        return frame
        
    def capture_frame(self, resize_factor=1.0):
        """
        Capture a frame from the camera
        
        :param resize_factor: Factor to resize the frame (1.0 = no resize)
        :return: Frame as NumPy array or None if failed
        """
        try:
            # If camera failed to initialize, return a fake frame
            if not self.picam2:
                if hasattr(self, '_use_fake_camera') and self._use_fake_camera:
                    frame = self._get_fake_frame()
                else:
                    return None
            else:
                # Get frame from the camera
                frame = self.picam2.capture_array()
                
            # Check if frame is valid
            if frame is None or frame.size == 0:
                print("[CameraManager] Empty frame captured")
                return None
                
            # Resize if needed
            if resize_factor != 1.0:
                height, width = frame.shape[:2]
                new_height = int(height * resize_factor)
                new_width = int(width * resize_factor)
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
                
            return frame
            
        except Exception as e:
            print(f"[CameraManager] Failed to capture frame: {e}")
            traceback.print_exc()
            return None
            
    def stop(self):
        """Stop the camera and release resources"""
        if self.picam2:
            try:
                self.picam2.stop()
                print("[CameraManager] Camera stopped")
            except Exception as e:
                print(f"[CameraManager] Error stopping camera: {e}")
                traceback.print_exc()
