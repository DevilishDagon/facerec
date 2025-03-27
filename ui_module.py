# ui_module.py
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import time
import cv2

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
        """
        Initialize Locker Access UI
        
        :param master: Root tkinter window
        :param camera_manager: Camera management instance
        :param face_recognizer: Face recognition instance
        :param locker_manager: Locker management instance
        """
        self.master = master
        self.camera_manager = camera_manager
        self.face_recognizer = face_recognizer
        self.locker_manager = locker_manager
        
        master.title("Locker Access System")
        master.attributes('-fullscreen', True)
        master.geometry("800x480")
        
        # Video label
        self.video_label = tk.Label(master)
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        # Status message
        self.status_var = tk.StringVar()
        status_label = tk.Label(master, textvariable=self.status_var, 
                                font=('Arial', 12), 
                                wraplength=780)
        status_label.pack(side=tk.BOTTOM)
        
        # Buttons
        self.create_buttons()
        
        # Start video update
        self.update_video()
    
    def create_buttons(self):
        """Create control buttons"""
        button_frame = tk.Frame(self.master)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        buttons = [
            ("Add Face", self.show_add_face_keyboard),
            ("Delete Face", self.show_delete_face_keyboard),
            ("Exit", self.exit_program)
        ]
        
        for text, command in buttons:
            btn = tk.Button(button_frame, text=text, command=command)
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
        face_locations = self.face_recognizer.face_recognition.face_locations(rgb_frame)
        face_encodings = self.face_recognizer.face_recognition.face_encodings(rgb_frame, face_locations)
        
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
            self.camera_manager.stop()
            self.locker_manager.cleanup()
            self.master.quit()
    
    def update_video(self):
        """Update video frame"""
        start_time = time.time()
        
        # Capture frame
        frame = self.camera_manager.capture_frame(resize_factor=0.5)
        
        # Recognize faces
        names, face_locations = self.face_recognizer.recognize_face(frame)
        
        # Draw faces and attempt to open lockers
        for name, (top, right, bottom, left) in zip(names, face_locations):
            # Different colors based on recognition status
            if name == "Unknown":
                # Red frame for unknown faces
                rectangle_color = (0, 0, 255)  # Red in BGR
                text_color = (0, 0, 255)
            else:
                # Green frame for recognized faces
                rectangle_color = (0, 255, 0)  # Green in BGR
                text_color = (0, 255, 0)
            
            # Draw rectangle with chosen color
            cv2.rectangle(frame, (left, top), (right, bottom), rectangle_color, 2)
            
            # Draw name text with chosen color
            cv2.putText(frame, name, (left, top-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, text_color, 2)
            
            # Open locker for recognized users
            if name != "Unknown":
                success, message = self.locker_manager.open_locker(name)
                self.status_var.set(message)
        
        # Convert to PhotoImage
        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)
        
        # Calculate and adjust update interval
        processing_time = time.time() - start_time
        delay = max(1, int((1/30 - processing_time) * 1000))
        
        # Schedule next update
        self.master.after(delay, self.update_video)
