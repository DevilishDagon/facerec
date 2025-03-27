import cv2
import tkinter as tk
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
        
        # Get screen resolution
        root = tk.Tk()
        self.screen_width = root.winfo_screenwidth()
        self.screen_height = root.winfo_screenheight()
        root.destroy()
    
    def capture_frame(self, resize_factor=1.0):
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
    
    def display_full_screen(self, frame):
        """
        Display frame in full-screen mode
        
        :param frame: Frame to display
        """
        # Resize frame to full screen
        full_screen_frame = cv2.resize(frame, (self.screen_width, self.screen_height))
        
        # Create full-screen window
        cv2.namedWindow('Camera Feed', cv2.WINDOW_NORMAL)
        cv2.setWindowProperty('Camera Feed', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        
        # Show the frame
        cv2.imshow('Camera Feed', full_screen_frame)
    
    def run_camera(self):
        """
        Continuously capture and display frames
        """
        try:
            while True:
                # Capture frame
                frame = self.capture_frame()
                
                # Display full-screen
                self.display_full_screen(frame)
                
                # Wait for 'q' key to quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            # Clean up
            cv2.destroyAllWindows()
            self.stop()
    
    def stop(self):
        """
        Stop the camera
        """
        self.picam2.stop()

# Example usage
if __name__ == "__main__":
    camera = CameraManager()
    camera.run_camera()
