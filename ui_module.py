# ui_module.py
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import time
import cv2
import threading
import face_recognition
import face_recognition_module
from datetime import datetime
import numpy as np

class VirtualKeyboard:
    def __init__(self, master, callback):
        self.window = tk.Toplevel(master)
        self.window.title("Virtual Keyboard")
        self.window.geometry("600x400")
        
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
        
        self.BUTTON_HEIGHT = 60
        
        master.grid_rowconfigure(0, weight=1)
        master.grid_rowconfigure(1, weight=0)
        master.grid_columnconfigure(0, weight=1)
        
        self.video_frame = tk.Frame(master, bg="black")
        self.video_frame.grid(row=0, column=0, sticky="nsew")
        
        self.video_label = tk.Label(self.video_frame, bg="black", 
                                    text="Starting camera...", fg="white",
                                    font=('Arial', 24))
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        self.button_area = tk.Frame(master, bg="black", height=self.BUTTON_HEIGHT)
        self.button_area.grid(row=1, column=0, sticky="ew")
        self.button_area.grid_propagate(False)
        
        self.create_buttons(self.button_area)
        
        self.recognized_faces = []
        self.recognition_lock = threading.Lock()
        self.last_recognition_time = datetime.now()
        self.running = True
        self.ui_initialized = False
        
        self.status_var = tk.StringVar()
        
        self.placeholder_frame = self.create_placeholder_frame(800, 380)
        
        self.recognition_thread = threading.Thread(target=self.run_face_recognition_loop, daemon=True)
        self.recognition_thread.start()
        
        self.update_video()

    def create_buttons(self, parent):
        button_frame = tk.Frame(parent, bg="black")
        button_frame.pack(fill=tk.BOTH, expand=True)

        buttons = [
            ("Add Face", self.show_add_face_keyboard),
            ("Delete Face", self.show_delete_face_keyboard),
            ("Exit", self.exit_program)
        ]

        for text, command in buttons:
            btn = tk.Button(button_frame, text=text, command=command, font=('Arial', 14), height=1)
            btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

    def show_add_face_keyboard(self):
        try:
            VirtualKeyboard(self.master, self.register_face)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open keyboard: {str(e)}")
            print(f"[UI] Keyboard error: {str(e)}")

    def register_face(self, name):
        try:
            frame = self.camera_manager.capture_frame()
            if frame is None:
                messagebox.showerror("Error", "Failed to capture image. Please try again.")
                return

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

            if not face_locations:
                messagebox.showerror("Error", "No face detected. Try again.")
                return

            if self.face_recognizer.register_face(name, face_encodings[0]):
                locker = self.locker_manager.assign_locker(name)
                if locker:
                    messagebox.showinfo("Success", f"Registered {name} - Locker #{locker['locker']}")
                    self.face_recognizer.save_encodings()
                else:
                    messagebox.showerror("Error", "Could not assign locker")
            else:
                messagebox.showerror("Error", "Face already registered")
        except Exception as e:
            messagebox.showerror("Error", f"Registration failed: {str(e)}")
            print(f"[UI] Registration error: {str(e)}")

    def update_video(self):
        if not self.running:
            return
        try:
            frame = self.camera_manager.capture_frame()
            if frame is None:
                img = Image.fromarray(self.placeholder_frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
                print("[UI] Failed to capture frame")
                self.master.after(1000, self.update_video)
                return

            frame_resized = cv2.resize(frame, (self.video_label.winfo_width(), self.video_label.winfo_height()), interpolation=cv2.INTER_LINEAR)
            frame_resized = cv2.flip(frame_resized, 1)

            scale_x = self.video_label.winfo_width() / frame.shape[1]
            scale_y = self.video_label.winfo_height() / frame.shape[0]

            with self.recognition_lock:
                recognized = list(self.recognized_faces)

            for name, (top, right, bottom, left) in recognized:
                scaled_top = int(top * scale_y)
                scaled_bottom = int(bottom * scale_y)
                scaled_left = int(left * scale_x)
                scaled_right = int(right * scale_x)

                flipped_left = self.video_label.winfo_width() - scaled_right
                flipped_right = self.video_label.winfo_width() - scaled_left

                color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                cv2.rectangle(frame_resized, (flipped_left, scaled_top), (flipped_right, scaled_bottom), color, 2)
                cv2.putText(frame_resized, name, (flipped_left, scaled_top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

            img = Image.fromarray(frame_resized)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

            self.master.after(33, self.update_video)
        except Exception as e:
            print(f"[UI] Error in update_video: {str(e)}")
            self.master.after(1000, self.update_video)

    def run_face_recognition_loop(self):
        while self.running:
            try:
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

            except Exception as e:
                print(f"[UI] Error in face recognition loop: {str(e)}")
                time.sleep(1)

            time.sleep(0.1)
