# main.py
import tkinter as tk
from camera_module import CameraManager
from face_recognition_module import FaceRecognitionManager
from locker_control_module import LockerManager
from ui_module import LockerAccessUI

def main():
    # Initialize root window
    root = tk.Tk()
    root.configure(bg="black")
    root.title("Face Locker System")
    root.attributes('-fullscreen', True)

    # Predefine modules
    camera_manager = None
    locker_manager = None

    try:
        print("🧠 UI Module - Running version from March 31, 2025")

        # Try initializing camera
        try:
            camera_manager = CameraManager()
        except Exception as cam_error:
            print(f"⚠️ Failed to initialize camera: {cam_error}")
            camera_manager = None  # Fallback

        face_recognizer = FaceRecognitionManager()
        locker_manager = LockerManager()

        # Create UI even if camera is None
        app = LockerAccessUI(
            root,
            camera_manager,
            face_recognizer,
            locker_manager
        )

        root.mainloop()

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        if camera_manager:
            camera_manager.stop()
        if locker_manager:
            locker_manager.cleanup()

if __name__ == "__main__":
    main()
