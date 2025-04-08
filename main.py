# main.py
import tkinter as tk
import os
import sys
import time
import traceback
from datetime import datetime

def setup_logging():
    """Setup logging to file"""
    log_dir = os.path.expanduser("~/logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "facerec.log")
    return log_file

def log_message(log_file, message):
    """Log a message to file with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def main():
    log_file = setup_logging()
    log_message(log_file, "[main.py] Starting application...")
    
    try:
        # Import modules (after logging setup to catch any import errors)
        from camera_module import CameraManager
        from face_recognition_module import FaceRecognitionManager
        from locker_control_module import LockerManager
        from ui_module import LockerAccessUI
        
        log_message(log_file, "[main.py] Modules imported successfully")
        
        # Initialize root window
        root = tk.Tk()
        root.configure(bg="black")
        root.title("Face Locker System")
        root.geometry("800x480+100+100")  # Normal window placed at (100,100)
        root.lift()                     # Bring window to front
        root.attributes('-topmost', True)  # Force it to stay on top
        root.after_idle(root.attributes, '-topmost', False)  # Let others be on top later
        root.attributes('-fullscreen', True)
        
        log_message(log_file, "[main.py] Initializing camera...")
        camera_manager = None
        try:
            camera_manager = CameraManager()
            if not camera_manager.picam2:
                raise RuntimeError("Camera failed to initialize properly")
            log_message(log_file, "[main.py] Camera initialized successfully")
        except Exception as e:
            log_message(log_file, f"[main.py] Camera error: {e}")
            if camera_manager:
                camera_manager.stop()
            raise
        
        log_message(log_file, "[main.py] Initializing face recognition...")
        face_recognizer = FaceRecognitionManager()
        
        log_message(log_file, "[main.py] Initializing locker manager...")
        locker_manager = LockerManager()
        
        log_message(log_file, "[main.py] Starting UI...")
        app = LockerAccessUI(root, camera_manager, face_recognizer, locker_manager)
        
        log_message(log_file, "[main.py] Entering main loop")
        root.mainloop()
        log_message(log_file, "[main.py] Main loop ended")
        
    except Exception as e:
        error_trace = traceback.format_exc()
        log_message(log_file, f"[main.py ERROR] {e}\n{error_trace}")
        
        # Try to show a message box if tkinter is working
        try:
            import tkinter.messagebox as msgbox
            msgbox.showerror("Critical Error", f"Application crashed: {e}")
        except:
            pass
    finally:
        log_message(log_file, "[main.py] Cleaning up resources")
        if 'camera_manager' in locals() and camera_manager:
            try:
                camera_manager.stop()
                log_message(log_file, "[main.py] Camera stopped")
            except Exception as e:
                log_message(log_file, f"[main.py] Error stopping camera: {e}")
        
        if 'locker_manager' in locals() and locker_manager:
            try:
                locker_manager.cleanup()
                log_message(log_file, "[main.py] Locker manager cleaned up")
            except Exception as e:
                log_message(log_file, f"[main.py] Error cleaning up locker manager: {e}")

if __name__ == "__main__":
    main()
