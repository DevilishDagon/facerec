import tkinter as tk
from camera_module import CameraManager
from face_recognition_module import FaceRecognitionManager
from locker_control_module import LockerManager
from ui_module import LockerAccessUI
import traceback

def main():
    log_file = "/home/hades/facerec.log"
    try:
        with open(log_file, "a") as f:
            f.write("[main.py] Launching UI...\n")

        root = tk.Tk()
        root.configure(bg="black")
        root.title("Face Locker System")
        root.attributes('-fullscreen', True)

        camera_manager = CameraManager()
        if not camera_manager.picam2:
            raise RuntimeError("Camera failed to initialize.")

        face_recognizer = FaceRecognitionManager()
        locker_manager = LockerManager()

        app = LockerAccessUI(root, camera_manager, face_recognizer, locker_manager)
        root.mainloop()

    except Exception as e:
        with open(log_file, "a") as f:
            f.write(f"[main.py ERROR] {e}\n")
            f.write(traceback.format_exc())

    finally:
        if 'camera_manager' in locals():
            camera_manager.stop()
        if 'locker_manager' in locals():
            locker_manager.cleanup()

if __name__ == "__main__":
    main()
