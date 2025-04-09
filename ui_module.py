# ui_module.py - Modified with threading fix for face registration
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import time
import cv2
import threading
import face_recognition
import numpy as np
import traceback
from datetime import datetime

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
        self.master = master
        self.camera_manager = camera_manager
        self.face_recognizer = face_recognizer
        self.locker_manager = locker_manager

        # Configure the root window
        master.title("Locker Access System")
        master.attributes('-fullscreen', True)
        master.geometry("800x480")
        master.configure(bg="black")
        
        # Constants for button area
        self.BUTTON_HEIGHT = 60
        
        # Use grid instead of pack for better layout control
        master.grid_rowconfigure(0, weight=1)  # Video area expands
        master.grid_rowconfigure(1, weight=0)  # Button area fixed height
        master.grid_columnconfigure(0, weight=1)
        
        # Create video frame (takes up everything except button area)
        self.video_frame = tk.Frame(master, bg="black")
        self.video_frame.grid(row=0, column=0, sticky="nsew")
        
        # Create the video label with an initial welcome message
        self.video_label = tk.Label(self.video_frame, bg="black", 
                                    text="Starting camera...", fg="white",
                                    font=('Arial', 24))
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        # Create button area with fixed height
        self.button_area = tk.Frame(master, bg="black", height=self.BUTTON_HEIGHT)
        self.button_area.grid(row=1, column=0, sticky="ew")
        self.button_area.grid_propagate(False)  # Prevent this frame from resizing
        
        # Create buttons directly in button area
        self.create_buttons(self.button_area)
        
        # Initialize recognition variables
        self.recognized_faces = []
        self.recognition_lock = threading.Lock()
        self.last_recognition_time = datetime.now()
        self.running = True
        self.ui_initialized = False
        self.registration_active = False
        
        # Status var for internal messages
        self.status_var = tk.StringVar()
        
        # Pre-render a placeholder image for the UI
        self.placeholder_frame = self.create_placeholder_frame(800, 380)
        
        # Check camera initialization
        try:
            if not self.camera_manager or not self.camera_manager.picam2:
                print("[UI] Camera initialization failed")
        except Exception as e:
            print(f"[UI] Camera error: {str(e)}")
        
        # Update UI immediately
        master.update_idletasks()
        
        # Start the recognition thread
        self.recognition_thread = threading.Thread(target=self.run_face_recognition_loop, daemon=True)
        self.recognition_thread.start()
        
        # Start the video update
        self.update_video()

    def create_placeholder_frame(self, width, height):
        """Create a placeholder frame with welcome text"""
        try:
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            # Add welcome text
            cv2.putText(frame, "Locker Access System", (width//2-150, height//2-30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            cv2.putText(frame, "Starting camera...", (width//2-120, height//2+30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
            return frame
        except Exception as e:
            print(f"[UI] Error creating placeholder frame: {str(e)}")
            # Return a simple black frame as fallback
            return np.zeros((height, width, 3), dtype=np.uint8)

    def create_buttons(self, parent):
        # Create button frame at the bottom of button area
        button_frame = tk.Frame(parent, bg="black")
        button_frame.pack(fill=tk.BOTH, expand=True)  # Fill the entire button area

        # Define buttons
        buttons = [
            ("Add Face", self.show_add_face_keyboard),
            ("Delete Face", self.show_delete_face_keyboard),
            ("Exit", self.exit_program)
        ]

        # Create each button
        for text, command in buttons:
            btn = tk.Button(button_frame, text=text, command=command, 
                           font=('Arial', 14), height=1)
            btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

    def show_add_face_keyboard(self):
        """Show keyboard for adding a new face"""
        try:
            VirtualKeyboard(self.master, self.register_face)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open keyboard: {str(e)}")
            print(f"[UI] Keyboard error: {str(e)}")
            traceback.print_exc()

    def show_delete_face_keyboard(self):
        """Show keyboard for deleting a face"""
        try:
            VirtualKeyboard(self.master, self.delete_face)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open keyboard: {str(e)}")
            print(f"[UI] Keyboard error: {str(e)}")
            traceback.print_exc()

    def register_face(self, name):
        """
        Register a new face
        
        :param name: Name to register
        """
        # Prevent multiple registration attempts at once
        if self.registration_active:
            messagebox.showerror("Error", "Registration already in progress")
            return
            
        self.registration_active = True
        
        # Show a processing message
        self.show_processing_message("Processing registration...")
        
        # Create a thread for the registration process
        registration_thread = threading.Thread(
            target=self._register_face_worker,
            args=(name,),
            daemon=True
        )
        registration_thread.start()
    
    def _register_face_worker(self, name):
        """Worker thread for face registration"""
        try:
            # Pause recognition thread temporarily
            original_running_state = self.running
            self.running = False
            time.sleep(0.5)  # Give recognition thread time to stop
            
            # Capture frame with full resolution
            frame = self.camera_manager.capture_frame()
            if frame is None:
                self.master.after(0, lambda: messagebox.showerror("Error", "Failed to capture image. Please try again."))
                return

            # Convert to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Detect faces
            face_locations = face_recognition.face_locations(rgb_frame)
            
            if not face_locations:
                self.master.after(0, lambda: messagebox.showerror("Error", "No face detected. Try again."))
                return
                
            # Find largest face (closest to camera)
            largest_area = 0
            largest_idx = 0
            
            for i, (top, right, bottom, left) in enumerate(face_locations):
                area = (bottom - top) * (right - left)
                if area > largest_area:
                    largest_area = area
                    largest_idx = i
            
            best_location = face_locations[largest_idx]
            
            # Generate face encoding
            face_encodings = face_recognition.face_encodings(rgb_frame, [best_location])
            
            if not face_encodings:
                self.master.after(0, lambda: messagebox.showerror("Error", "Could not encode face. Try again with better lighting."))
                return

            # Register first detected face
            name = name.strip().lower()
            if not name:
                self.master.after(0, lambda: messagebox.showerror("Error", "Invalid name"))
                return
                
            if self.face_recognizer.register_face(name, face_encodings[0]):
                # Assign locker
                locker = self.locker_manager.assign_locker(name)
                if locker:
                    self.master.after(0, lambda: messagebox.showinfo("Success",
                                     f"Registered {name} - Locker #{locker['locker']}"))
                else:
                    self.master.after(0, lambda: messagebox.showerror("Error", "Could not assign locker"))
            else:
                self.master.after(0, lambda: messagebox.showerror("Error", "Face already registered or registration failed"))
                
        except Exception as e:
            self.master.after(0, lambda: messagebox.showerror("Error", f"Registration failed: {str(e)}"))
            print(f"[UI] Registration error: {str(e)}")
            traceback.print_exc()
            
        finally:
            # Always resume recognition thread with original state
            self.running = original_running_state
            self.registration_active = False
            # Clear the processing message
            self.clear_processing_message()
    
    def show_processing_message(self, message):
        """Show a processing message on the UI"""
        # Use after() to ensure thread safety with tkinter
        self.master.after(0, lambda: self._show_processing_message_ui(message))
    
    def _show_processing_message_ui(self, message):
        """Actually update the UI with processing message (must be called from main thread)"""
        # Create processing label if it doesn't exist
        if not hasattr(self, 'processing_label'):
            self.processing_label = tk.Label(
                self.video_frame,
                text=message,
                font=('Arial', 18),
                bg='black',
                fg='white',
                bd=2,
                relief=tk.RAISED
            )
            # Position at center bottom of video frame
            self.processing_label.place(
                relx=0.5, rely=0.9,
                anchor=tk.CENTER
            )
        else:
            # Update existing label
            self.processing_label.config(text=message)
            self.processing_label.place(
                relx=0.5, rely=0.9,
                anchor=tk.CENTER
            )
    
    def clear_processing_message(self):
        """Remove the processing message from UI"""
        # Use after() to ensure thread safety with tkinter
        self.master.after(0, lambda: self._clear_processing_message_ui())
    
    def _clear_processing_message_ui(self):
        """Actually clear the processing message (must be called from main thread)"""
        if hasattr(self, 'processing_label'):
            self.processing_label.place_forget()

    def delete_face(self, name):
        """
        Delete a registered face
        
        :param name: Name to delete
        """
        try:
            name = name.lower().strip()
            if not name:
                messagebox.showerror("Error", "Invalid name")
                return
                
            if name in self.face_recognizer.known_names:
                index = self.face_recognizer.known_names.index(name)
                self.face_recognizer.known_names.pop(index)
                self.face_recognizer.known_encodings.pop(index)
                self.face_recognizer.save_encodings()
                
                # Also remove locker assignment if it exists
                if name in self.locker_manager.lockers:
                    del self.locker_manager.lockers[name]
                    self.locker_manager.save_lockers()
                    
                messagebox.showinfo("Success", f"Deleted {name}")
            else:
                messagebox.showerror("Error", f"Name '{name}' not found")
        except Exception as e:
            messagebox.showerror("Error", f"Deletion failed: {str(e)}")
            print(f"[UI] Deletion error: {str(e)}")
            traceback.print_exc()

    def exit_program(self):
        """Exit the application"""
        try:
            if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
                self.running = False
                if self.camera_manager:
                    self.camera_manager.stop()
                if self.locker_manager:
                    self.locker_manager.cleanup()
                # Force cleanup
                self.master.after(100, self.master.destroy)
        except Exception as e:
            print(f"[UI] Error during shutdown: {str(e)}")
            traceback.print_exc()
            self.master.destroy()

    def update_video(self):
        """Update the video display with the current camera frame"""
        if not self.running:
            return
            
        try:
            if not self.camera_manager or not self.camera_manager.picam2:
                # Show placeholder if camera not available
                img = Image.fromarray(self.placeholder_frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
                print("[UI] Camera not available")
                self.master.after(1000, self.update_video)  # Retry in 1s
                return

            # Capture frame
            frame = self.camera_manager.capture_frame()
            if frame is None:
                # Show placeholder if frame capture failed
                img = Image.fromarray(self.placeholder_frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
                print("[UI] Failed to capture frame")
                self.master.after(1000, self.update_video)
                return

            # Get frame and label dimensions
            frame_height, frame_width = frame.shape[:2]
            label_width = self.video_label.winfo_width()
            label_height = self.video_label.winfo_height()

            # If UI isn't fully initialized yet (dimensions not set)
            if label_width <= 1 or label_height <= 1:
                # Use the current window dimensions to estimate video area
                win_width = self.master.winfo_width()
                win_height = self.master.winfo_height() - self.BUTTON_HEIGHT
                
                # Placeholder with dimensions that match the window
                placeholder = self.create_placeholder_frame(win_width, win_height)
                img = Image.fromarray(placeholder)
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
                
                # Try again soon
                self.master.after(100, self.update_video)
                return
                
            # UI is initialized
            if not self.ui_initialized:
                self.ui_initialized = True
                print("[UI] System ready")

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
            img = Image.fromarray(cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB))
            imgtk = ImageTk.PhotoImage(image=img)

            # Update the video label with the new frame
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

            # Schedule the next update (~30 FPS)
            self.master.after(33, self.update_video)
            
        except Exception as e:
            print(f"[UI] Error in update_video: {str(e)}")
            traceback.print_exc()
            
            # Show a placeholder image to avoid complete black screen
            try:
                img = Image.fromarray(self.placeholder_frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
            except:
                # If even that fails, set a text message
                self.video_label.configure(image='', text="System Error")
                
            # Try again in 1 second
            self.master.after(1000, self.update_video)

    def run_face_recognition_loop(self):
        """Background thread for face recognition processing"""
        print("[UI] Starting face recognition thread")
        
        # Keep track of recent recognitions and when they were processed
        recent_recognitions = {}
        # Minimum time between opening the same locker (seconds)
        min_reopen_time = 10
        
        while self.running:
            try:
                if not self.camera_manager or not self.camera_manager.picam2:
                    print("[UI] Camera manager not initialized. Waiting...")
                    time.sleep(1)
                    continue
    
                frame = self.camera_manager.capture_frame(resize_factor=0.25)
                if frame is None:
                    time.sleep(0.1)
                    continue
                    
                rgb_small = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
                face_locations = face_recognition.face_locations(rgb_small)
                face_encodings = face_recognition.face_encodings(rgb_small, face_locations)
                
                recognized = []
        
                if face_encodings:
                    for encoding, (top, right, bottom, left) in zip(face_encodings, face_locations):
                        name = self.face_recognizer.match_face(encoding)
                        # Apply scale factor to compensate for resized frame
                        recognized.append((name, (top * 4, right * 4, bottom * 4, left * 4)))
                        
                        # Check for locker action if recognized
                        if name != "Unknown":
                            current_time = datetime.now()
                            
                            # Check if we've seen this person recently
                            if name in recent_recognitions:
                                last_action_time = recent_recognitions[name]
                                time_diff = (current_time - last_action_time).total_seconds()
                                
                                # Only open locker if sufficient time has passed since last opening
                                if time_diff > min_reopen_time:
                                    success, message = self.locker_manager.open_locker(name)
                                    if success:
                                        print(f"[UI] Welcome {name}! {message}")
                                        # Update last action time
                                        recent_recognitions[name] = current_time
                                    else:
                                        print(f"[UI] {message}")
                            else:
                                # First time seeing this person, open their locker
                                success, message = self.locker_manager.open_locker(name)
                                if success:
                                    print(f"[UI] Welcome {name}! {message}")
                                    # Store when we opened their locker
                                    recent_recognitions[name] = current_time
                                else:
                                    print(f"[UI] {message}")
                            
                            self.last_recognition_time = current_time
                            
                with self.recognition_lock:
                    self.recognized_faces = recognized
                    
            except Exception as e:
                print(f"[UI] Error in face recognition loop: {str(e)}")
                traceback.print_exc()
                time.sleep(1)  # Wait a bit before trying again
                
            # Short sleep to prevent CPU overuse
            time.sleep(0.1)
        
        print("[UI] Face recognition thread stopped")
