# main.py
import tkinter as tk
from camera_module import CameraManager
from face_recognition_module import FaceRecognitionManager
from locker_control_module import LockerManager
from ui_module import LockerAccessUI

def main():
    # Initialize root window
    root = tk.Tk()
    
    try:
        # Initialize modules
        camera_manager = CameraManager()
        face_recognizer = FaceRecognitionManager()
        locker_manager = LockerManager()
        
        # Create UI
        app = LockerAccessUI(
            root, 
            camera_manager, 
            face_recognizer, 
            locker_manager
        )
        
        # Start main loop
        root.mainloop()
    
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        # Cleanup resources
        camera_manager.stop()
        locker_manager.cleanup()

if __name__ == "__main__":
    main()
