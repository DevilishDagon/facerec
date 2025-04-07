#ui_module.py
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import time
import cv2
import threading
import face_recognition
import face_recognition_module
from datetime import datetime

print("🧠 UI Module - Running version from March 31, 2025")

class VirtualKeyboard:
    def __init__(self, master, callback):
        """
        Initialize virtual keyboard
        
        :param master: Parent tkinter window
        :param callback: Function to call with keyboard input
        """
        self.window = tk.Toplevel(master)
        self.window.title("Virtual Keyboard")
        self.window.geometry("600x400")
        self.video_label = tk.Label(master, bg="black")
        self.video_label.pack(fill=tk.BOTH, expand=True)

        
        self.callback = callback
        self.input_var = tk.StringVar()
        
        self.input_entry = tk.Entry(self.window, textvariable=self.input_var, font=('Arial', 16))
        self.input_entry.pack(pady=20)
        
        keyboard_layout = [
            '1234567890',
            'QWERTYUIOP',
            'ASDFGHJKL',
            'ZXCVBNM'
        ]
        
        for row in keyboard_layout:
            frame = tk.Frame(self.window)
            frame.pack()
            for char in row:
                btn = tk.Button(frame, text=char, width=3, 
                                command=lambda c=char.lower(): self.add_char(c))
                btn.pack(side=tk.LEFT)
        
        # Special buttons
        special_frame = tk.Frame(self.window)
        special_frame.pack(pady=10)
        
        tk.Button(special_frame, text="Space", command=lambda: self.add_char(" ")).pack(side=tk.LEFT)
        tk.Button(special_frame, text="Backspace", command=self.backspace).pack(side=tk.LEFT)
        tk.Button(special_frame, text="Enter", command=self.confirm).pack(side=tk.LEFT)
        tk.Button(special_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT)
    
    def add_char(self, char):
        current = self.input_var.get()
        self.input_var.set(current + char)
    
    def backspace(self):
        current = self.input_var.get()
        self.input_var.set(current[:-1])
    
    def confirm(self):
        name = self.input_var.get().strip()
        if name:
            self.callback(name)
        self.window.destroy()
    
    def cancel(self):
        self.window.destroy()

class LockerAccessUI:
    def __init__(self, master, camera_manager, face_recognizer, locker_manager):
        self.master = master
        self.camera_manager = camera_manager
        self.face_recognizer = face_recognizer
        self.locker_manager = locker_manager

        master.title("Locker Access System")
        master.attributes('-fullscreen', True)
        master.geometry("800x480")
        master.configure(bg="black")

        # Top: Video Frame - Ensuring it fills the entire top space
        self.video_label = tk.Label(master, bg="black")
        self.video_label.place(x=0, y=0, width=master.winfo_width(), height=master.winfo_height() - 120)  # Top 75%

        # Bottom: Control Frame
        control_frame = tk.Frame(master, bg="black")
        control_frame.place(x=0, y=master.winfo_height() - 120, width=master.winfo_width(), height=120)  # Bottom 25%

        self.status_var = tk.StringVar()
        status_label = tk.Label(control_frame, textvariable=self.status_var,
                                font=('Arial', 14), bg="black", fg="white")
        status_label.pack(side=tk.TOP, fill=tk.X)

        self.create_buttons(control_frame)

        # Rest of your setup...
        self.recognized_faces = []
        self.recognition_lock = threading.Lock()
        self.last_recognition_time = datetime.now()
        self.running = True

        self.recognition_thread = threading.Thread(target=self.run_face_recognition_loop, daemon=True)
        self.recognition_thread.start()

        self.update_video()


    def create_buttons(self, parent):
        button_frame = tk.Frame(parent, bg="black")
        button_frame.pack(side=tk.BOTTOM, fill=tk.X)
    
        buttons = [
            ("Add Face", self.show_add_face_keyboard),
            ("Delete Face", self.show_delete_face_keyboard),
            ("Exit", self.exit_program)
        ]
    
        for text, command in buttons:
            btn = tk.Button(button_frame, text=text, command=command, font=('Arial', 12))
            btn.pack(side=tk.LEFT, expand=True, fill=tk.X)
    
    def show_add_face_keyboard(self):
        """Show keyboard for adding a new face"""
        VirtualKeyboard(self.master, self.register_face)
    
    def show_delete_face_keyboard(self):
        """Show keyboard for deleting a face"""
        VirtualKeyboard(self.master, self.delete_face)
    
    def register_face(self, name):
        """
        Register a new face
        
        :param name: Name to register
        """
        # Capture frame
        frame = self.camera_manager.capture_frame()
        
        # Convert to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)


        
        if not face_locations:
            messagebox.showerror("Error", "No face detected. Try again.")
            return
        
        # Register first detected face
        if self.face_recognizer.register_face(name, face_encodings[0]):
            # Assign locker
            locker = self.locker_manager.assign_locker(name)
            if locker:
                messagebox.showinfo("Success", 
                    f"Registered {name} - Locker #{locker['locker']}")
                self.face_recognizer.save_encodings()
            else:
                messagebox.showerror("Error", "Could not assign locker")
        else:
            messagebox.showerror("Error", "Face already registered")
    
    def delete_face(self, name):
        """
        Delete a registered face
        
        :param name: Name to delete
        """
        # TODO: Implement face deletion logic
        pass
    
    def exit_program(self):
        """Exit the application"""
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            self.running = False
            self.camera_manager.stop()
            self.locker_manager.cleanup()
            self.master.quit()

    def update_video(self):
        if not self.camera_manager or not self.camera_manager.picam2:
            self.status_var.set("❌ Camera not available.")
            self.video_label.configure(image="", text="Camera Feed Unavailable", font=('Arial', 24), fg="red")
            self.master.after(1000, self.update_video)  # Retry in 1s
            return
    
        # Capture frame
        frame = self.camera_manager.capture_frame()
        if frame is None:
            self.status_var.set("⚠️ Failed to capture frame.")
            self.video_label.configure(image="", text="No Frame", font=('Arial', 24), fg="orange")
            self.master.after(1000, self.update_video)
            return
    
        # Get frame and label dimensions
        frame_height, frame_width = frame.shape[:2]
        label_width = self.video_label.winfo_width()
        label_height = self.video_label.winfo_height()
    
        # Ensure the label has valid dimensions
        if label_width <= 0 or label_height <= 0:
            self.status_var.set("⚠️ Label dimensions are invalid.")
            self.master.after(1000, self.update_video)  # Retry in 1s
            return
    
        # Resize the frame to fill the label completely, without black bars
        frame_resized = cv2.resize(frame, (label_width, label_height), interpolation=cv2.INTER_LINEAR)
    
        # Flip the frame horizontally (to correct for mirrored display)
        frame_resized = cv2.flip(frame_resized, 1)
    
        # Calculate resizing scale factors
        scale_x = label_width / frame_width
        scale_y = label_height / frame_height
    
        # Overlay face recognition results on the resized frame
        with self.recognition_lock:
            recognized = list(self.recognized_faces)
    
        for name, (top, right, bottom, left) in recognized:
            # Scale the coordinates according to the resized frame
            scaled_top = int(top * scale_y)
            scaled_bottom = int(bottom * scale_y)
            scaled_left = int(left * scale_x)
            scaled_right = int(right * scale_x)
    
            # Flip horizontal positions to match the frame flip
            flipped_left = label_width - scaled_right
            flipped_right = label_width - scaled_left
    
            # Draw rectangles and put text for face recognition
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            cv2.rectangle(frame_resized, (flipped_left, scaled_top), (flipped_right, scaled_bottom), color, 2)
            cv2.putText(frame_resized, name, (flipped_left, scaled_top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
    
        # Convert frame to ImageTk format for display in the UI
        img = Image.fromarray(frame_resized)
        imgtk = ImageTk.PhotoImage(image=img)
    
        # Update the video label with the new frame
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)
    
        # Schedule the next update (~30 FPS)
        self.master.after(33, self.update_video)










    def run_face_recognition_loop(self):
        if not self.camera_manager or not self.camera_manager.picam2:
            print("[UI] Camera manager not initialized. Skipping recognition loop.")
            return

        while self.running:
            frame = self.camera_manager.capture_frame(resize_factor=0.25)
            rgb_small = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
            face_locations = face_recognition.face_locations(rgb_small)
            face_encodings = face_recognition.face_encodings(rgb_small, face_locations)
            
            recognized = []
    
            if face_encodings:
                for encoding, (top, right, bottom, left) in zip(face_encodings, face_locations):
                    name = self.face_recognizer.match_face(encoding)
                    recognized.append((name, (top * 4, right * 4, bottom * 4, left * 4)))
            with self.recognition_lock:
                self.recognized_faces = recognized

            print(f"[DEBUG] Recognized: {recognized}")




