# main.py
import tkinter as tk
from camera_module import CameraManager
from face_recognition_module import FaceRecognitionManager
from locker_control_module import LockerManager
from ui_module import LockerAccessUI

def main():
    # Initialize root window
    root = tk.Tk()
    root.configure(bg="red")  # Make it obvious
    root.title("Face Locker System")

    # Predefine variables to avoid UnboundLocalError
    camera_manager = None
    locker_manager = None

    try:
        print("🧠 UI Module - Running version from March 31, 2025")

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
        # Cleanup resources safely
        if camera_manager:
            camera_manager.stop()
        if locker_manager:
            locker_manager.cleanup()

if __name__ == "__main__":
    main()
