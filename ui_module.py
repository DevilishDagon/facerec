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

        # Top: Video Frame
        self.video_label = tk.Label(master, bg="black")
        self.video_label.place(x=0, y=0, width=800, height=360)  # Top 75%

        # Bottom: Control Frame
        control_frame = tk.Frame(master, bg="black")
        control_frame.place(x=0, y=360, width=800, height=120)  # Bottom 25%

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
            self.master.after(1000, self.update_video)
            return
    
        # Try to capture a frame
        try:
            frame = self.camera_manager.capture_frame()
            if frame is None:
                self.status_var.set("⚠️ Failed to capture frame.")
                self.video_label.configure(image="", text="No Frame", font=('Arial', 24), fg="orange")
                self.master.after(1000, self.update_video)
                return
        except Exception as e:
            self.status_var.set(f"⚠️ Error: {str(e)}")
            self.master.after(1000, self.update_video)
            return
        
        # Flip before recognition so coordinates match
        frame = cv2.flip(frame, 1)
        
        # Get dimensions for flipping
        frame_width = frame.shape[1]
        frame_height = frame.shape[0]
    
        # Flip recognition coordinates to match flipped image
        with self.recognition_lock:
            recognized = list(self.recognized_faces)
    
        for name, (top, right, bottom, left) in recognized:
            # Flip horizontal positions
            flipped_left = frame_width - right
            flipped_right = frame_width - left
    
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            cv2.rectangle(frame, (flipped_left, top), (flipped_right, bottom), color, 2)
            cv2.putText(frame, name, (flipped_left, top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
    
            if name != "Unknown":
                success, message = self.locker_manager.open_locker(name)
                self.status_var.set(message)
    
        # Get the dimensions of the video label
        label_width = self.video_label.winfo_width()
        label_height = self.video_label.winfo_height()
    
        if label_width > 0 and label_height > 0:
            # Maintain the aspect ratio while resizing, scale frame to fit completely
            aspect_ratio = frame_width / frame_height
            label_aspect_ratio = label_width / label_height
    
            if aspect_ratio > label_aspect_ratio:
                # Wider than label, fill width and adjust height
                new_width = label_width
                new_height = int(label_width / aspect_ratio)
            else:
                # Taller than label, fill height and adjust width
                new_height = label_height
                new_width = int(label_height * aspect_ratio)
    
            # Resize frame to fit the label
            frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
    
            # Center the image in the label area
            top_left_x = (label_width - new_width) // 2
            top_left_y = (label_height - new_height) // 2
    
            # Place the frame in the center of the label
            frame_with_padding = cv2.copyMakeBorder(frame, top_left_y, label_height - new_height - top_left_y, top_left_x, label_width - new_width - top_left_x, cv2.BORDER_CONSTANT, value=(0, 0, 0))
    
            # Convert frame and show in label
            img = Image.fromarray(frame_with_padding)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
    
        # Schedule next update (~30 FPS)
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




