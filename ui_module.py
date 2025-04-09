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
import gc
import random

class LockerAccessUI:
    # Keep existing __init__ and other methods but replace these problematic methods
    
    def register_face(self, name):
        """
        Register a new face
        
        :param name: Name to register
        """
        # Prevent multiple registration attempts at once
        if self.registration_active:
            messagebox.showerror("Error", "Registration already in progress")
            return
            
        # Validate input before proceeding
        name = name.strip().lower()
        if not name:
            messagebox.showerror("Error", "Invalid name")
            return
        
        # Set flag to prevent multiple registrations
        self.registration_active = True
        
        # Pause the recognition thread
        self.pause_recognition()
        
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
            # Ensure recognition is paused
            self.pause_recognition()
            time.sleep(0.5)  # Give recognition thread time to pause
            
            # Explicitly clear any previous frames
            # This helps prevent memory issues
            gc.collect()
            
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

            # Register the face
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
            # Make sure to clean up and release resources
            del frame
            del rgb_frame
            gc.collect()
            
            # Schedule cleanup to run on the main thread
            self.master.after(0, self._finish_registration)
    
    def _finish_registration(self):
        """Clean up after registration (runs on main thread)"""
        # Clear processing message
        self.clear_processing_message()
        
        # Reset recognized faces to prevent stale data
        with self.recognition_lock:
            self.recognized_faces = []
        
        # Resume recognition
        self.resume_recognition()
        
        # Reset registration flag
        self.registration_active = False
        
        # Force an update of the video display
        self.master.after(10, self.update_video)
    
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

            # Capture frame with timeout protection
            try:
                frame = self.camera_manager.capture_frame()
                if frame is None:
                    raise ValueError("Failed to capture frame")
            except Exception as e:
                print(f"[UI] Frame capture error: {str(e)}")
                img = Image.fromarray(self.placeholder_frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
                self.master.after(500, self.update_video)
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

            # Copy the frame for processing to avoid reference issues
            frame_copy = frame.copy()

            # Resize the frame to fill the label completely, without black bars
            frame_resized = cv2.resize(frame_copy, (label_width, label_height), interpolation=cv2.INTER_LINEAR)

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

            # Clean up to prevent memory issues
            del frame
            del frame_copy
            del frame_resized
            
            # Schedule the next update (~20 FPS, slightly reduced to help with resource usage)
            self.master.after(50, self.update_video)
            
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
        
        # Add throttling to prevent CPU overuse
        last_process_time = time.time()
        process_interval = 0.3  # Process frames at most every 300ms
        
        while self.running:
            try:
                # Check if recognition is paused
                if self.recognition_paused.is_set():
                    time.sleep(0.1)  # Sleep briefly and check again
                    continue
                    
                # Throttle processing
                current_time = time.time()
                if current_time - last_process_time < process_interval:
                    time.sleep(0.05)  # Short sleep to yield CPU
                    continue
                    
                last_process_time = current_time
                    
                if not self.camera_manager or not self.camera_manager.picam2:
                    print("[UI] Camera manager not initialized. Waiting...")
                    time.sleep(1)
                    continue
    
                # Use a smaller resize factor to improve performance
                frame = self.camera_manager.capture_frame(resize_factor=0.2)
                if frame is None:
                    time.sleep(0.1)
                    continue
                    
                # Use a copy to prevent reference issues
                frame_copy = frame.copy()
                rgb_small = cv2.cvtColor(frame_copy, cv2.COLOR_BGR2RGB)
        
                face_locations = face_recognition.face_locations(rgb_small)
                
                # Skip encoding if no faces detected
                if not face_locations:
                    # Clear recognized faces when no faces are detected
                    with self.recognition_lock:
                        if self.recognized_faces:
                            self.recognized_faces = []
                    time.sleep(0.1)
                    continue
                
                face_encodings = face_recognition.face_encodings(rgb_small, face_locations)
                
                recognized = []
        
                if face_encodings:
                    for encoding, (top, right, bottom, left) in zip(face_encodings, face_locations):
                        name = self.face_recognizer.match_face(encoding)
                        # Apply scale factor to compensate for resized frame (5x instead of 4x due to 0.2 factor)
                        recognized.append((name, (top * 5, right * 5, bottom * 5, left * 5)))
                        
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
                    
                # Clean up to avoid memory issues
                del frame
                del frame_copy
                del rgb_small
                    
            except Exception as e:
                print(f"[UI] Error in face recognition loop: {str(e)}")
                traceback.print_exc()
                time.sleep(1)  # Wait a bit before trying again
                
            # Force garbage collection occasionally
            if random.random() < 0.05:  # ~5% chance each iteration
                gc.collect()
                
        print("[UI] Face recognition thread stopped")
