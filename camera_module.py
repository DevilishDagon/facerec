# camera_module.py
import cv2
from picamera2 import Picamera2
from libcamera import controls
import time

class CameraManager:
    def __init__(self, width=800, height=480):
        self.picam2 = None  # Start as None

        for attempt in range(5):
            try:
                print(f"[CameraManager] Attempting camera init ({attempt + 1}/5)...")
                self.picam2 = Picamera2()
                time.sleep(1)  # Let system settle

                config = self.picam2.create_preview_configuration(main={"size": (width, height)})
                self.picam2.configure(config)
                self.picam2.start()
                self.picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})

                print("[CameraManager] Camera initialized successfully.")
                break
            except Exception as e:
                print(f"[CameraManager] Attempt {attempt + 1} failed: {e}")
                time.sleep(2)
        else:
            raise RuntimeError("[CameraManager] Failed to initialize camera after 5 attempts.")

    def capture_frame(self, resize_factor=1.0):
        try:
            frame = self.picam2.capture_array()
            if resize_factor != 1.0:
                frame = cv2.resize(frame, (0, 0), fx=resize_factor, fy=resize_factor)
            return frame
        except Exception as e:
            print(f"[CameraManager] Failed to capture frame: {e}")
            return None

    def stop(self):
        if self.picam2:
            self.picam2.stop()
