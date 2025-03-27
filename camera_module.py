# camera_module.py
import cv2
from picamera2 import Picamera2
from libcamera import controls
import time

class CameraManager:
    def __init__(self, width=800, height=480):
        """
        Initialize the camera with specified resolution
        
        :param width: Camera frame width
        :param height: Camera frame height
        """
        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(main={"size": (width, height)})
        self.picam2.configure(config)
        self.picam2.start()
        self.picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
    
    def capture_frame(self, resize_factor=3.0):
        """
        Capture a frame from the camera
        
        :param resize_factor: Optional factor to resize the frame
        :return: Captured and optionally resized frame
        """
        # Capture frame
        frame = self.picam2.capture_array()
        
        # Resize if needed
        if resize_factor != 1.0:
            frame = cv2.resize(frame, (0, 0), fx=resize_factor, fy=resize_factor)
        
        return frame
    
    def stop(self):
        """
        Stop the camera
        """
        self.picam2.stop()
