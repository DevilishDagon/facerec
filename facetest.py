import face_recognition
import cv2
import os
import pickle
import numpy as np
import time
import RPi.GPIO as GPIO
from picamera2 import Picamera2
from libcamera import controls
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

# CONFIGURATION
ADMIN_NAME = "tim"  # Ensure lowercase for consistency
THRESHOLD = 0.45  # Adjust for better accuracy
IDLE_TIMEOUT = 60  # Reset system after 60 seconds of inactivity
TOTAL_LOCKERS = 100  # Max locker count
DELAY_BETWEEN_PROMPTS = 20  # Time between locker prompts

# Screen resolution
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 480

# File paths
KNOWN_FACES_DIR = "known_faces"
ENCODINGS_FILE = "faces.pkl"
LOCKERS_FILE = "lockers.pkl"

os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

# Initialize variables
known_encodings = []
known_names = []
lockers = {}
last_prompt_time = {}
last_activity_time = time.time()
current_action = None
show_virtual_keyboard = False
keyboard_input = ""
current_buttons = []

available_gpio_pins = [2,3,4]

# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Similar functions for loading/saving encodings and lockers (unchanged from previous script)
def load_encodings():
    global known_encodings, known_names  
    try:
        if os.path.exists(ENCODINGS_FILE):
            with open(ENCODINGS_FILE, "rb") as f:
                known_encodings, known_names = pickle.load(f)
                known_names = [name.lower() for name in known_names]
        else:
            known_encodings, known_names = [], []
    except Exception as e:
        print(f"Error loading encodings: {e}")
        known_encodings, known_names = [], []

def load_lockers():
    global lockers
    try:
        if os.path.exists(LOCKERS_FILE):
            with open(LOCKERS_FILE, "rb") as f:
                lockers = pickle.load(f)
                lockers = {name.lower(): num for name, num in lockers.items()}
        else:
            lockers = {}
    except Exception as e:
        print(f"Error loading lockers: {e}")
        lockers = {}

def save_lockers():
    try:
        with open(LOCKERS_FILE, "wb") as f:
            pickle.dump(lockers, f)
    except Exception as e:
        print(f"Error saving lockers: {e}")

def save_encodings():
    try:
        with open(ENCODINGS_FILE, "wb") as f:
            pickle.dump((known_encodings, known_names), f)
    except Exception as e:
        print(f"Error saving encodings: {e}")

# Initializing PiCamera
picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (SCREEN_WIDTH, SCREEN_HEIGHT)})
picam2.configure(config)
picam2.start()
picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})

# Load data
load_encodings()
load_lockers()

class VirtualKeyboard:
    def __init__(self, master):
        self.window = tk.Toplevel(master)
        self.window.title("Virtual Keyboard")
        self.window.geometry("600x400")
        
        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(self.window, textvariable=self.input_var, font=('Arial', 16))
        self.input_entry.pack(pady=20)
        
        # Create keyboard layout
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
        
        self.action = None
    
    def add_char(self, char):
        current = self.input_var.get()
        self.input_var.set(current + char)
    
    def backspace(self):
        current = self.input_var.get()
        self.input_var.set(current[:-1])
    
    def confirm(self):
        name = self.input_var.get().strip()
        if name:
            if self.action == "Add":
                register_face(name)
            elif self.action == "Delete":
                delete_face(name)
        self.window.destroy()
    
    def cancel(self):
        self.window.destroy()

class LockerAccessApp:
    def __init__(self, master):
        self.master = master
        master.title("Locker Access System")
        master.geometry(f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}")
        
        # Video feed
        self.video_label = tk.Label(master)
        self.video_label.pack()
        
        # Buttons frame
        button_frame = tk.Frame(master)
        button_frame.pack(side=tk.BOTTOM)
        
        # Add Face Button
        add_button = tk.Button(button_frame, text="Add Face", 
                               command=self.show_add_face_keyboard)
        add_button.pack(side=tk.LEFT)
        
        # Delete Face Button
        delete_button = tk.Button(button_frame, text="Delete Face", 
                                  command=self.show_delete_face_keyboard)
        delete_button.pack(side=tk.LEFT)
        
        # Exit Button
        exit_button = tk.Button(button_frame, text="Exit", 
                                command=self.exit_program)
        exit_button.pack(side=tk.LEFT)
        
        # Status message
        self.status_var = tk.StringVar()
        status_label = tk.Label(master, textvariable=self.status_var)
        status_label.pack()
        
        # Start video feed
        self.update_video()
    
    def show_add_face_keyboard(self):
        keyboard = VirtualKeyboard(self.master)
        keyboard.action = "Add"
    
    def show_delete_face_keyboard(self):
        keyboard = VirtualKeyboard(self.master)
        keyboard.action = "Delete"
    
    def exit_program(self):
        picam2.stop()
        GPIO.cleanup()
        self.master.quit()
    
    def update_video(self):
        # Capture frame from PiCamera
        frame = picam2.capture_array()
        
        # Convert to RGB for face recognition
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        
        # Process each detected face
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            # Compare face with known faces
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=THRESHOLD)
            name = "Unknown"
            
            if True in matches:
                first_match_index = matches.index(True)
                name = known_names[first_match_index]
                
                # Open locker for recognized user
                if name != "Unknown":
                    self.open_locker(name)
            
            # Draw rectangle around face
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(frame, name, (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36,255,12), 2)
        
        # Convert frame to PhotoImage
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)
        
        # Schedule next update
        self.master.after(50, self.update_video)
    
    def open_locker(self, name):
        if name not in lockers:
            self.status_var.set(f"No locker assigned for {name}")
            return
        
        locker_info = lockers[name]
        gpio_pin = locker_info['gpio']
        
        try:
            # Unlock the locker
            GPIO.output(gpio_pin, GPIO.HIGH)
            self.status_var.set(f"Locker {locker_info['locker']} opened")
            
            # Schedule locker closure
            self.master.after(5000, lambda: self.close_locker(gpio_pin, locker_info['locker']))
        
        except Exception as e:
            self.status_var.set(f"Error opening locker: {e}")
    
    def close_locker(self, gpio_pin, locker_number):
        try:
            GPIO.output(gpio_pin, GPIO.LOW)
            self.status_var.set(f"Locker {locker_number} closed")
        except Exception as e:
            self.status_var.set(f"Error closing locker: {e}")

def register_face(name):
    global known_encodings, known_names, lockers
    
    try:
        # Capture frame
        frame = picam2.capture_array()
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_frame)
        
        if not face_locations:
            messagebox.showerror("Error", "No face detected. Try again.")
            return

        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        if not face_encodings:
            messagebox.showerror("Error", "Failed to encode face. Try again.")
            return

        # Check for existing face
        for existing_encoding in known_encodings:
            if np.linalg.norm(existing_encoding - face_encodings[0]) < THRESHOLD:
                messagebox.showerror("Error", "Face already registered.")
                return

        name = name.lower()

        # Prevent duplicate name registration
        if name in lockers:
            messagebox.showerror("Error", f"Name '{name}' is already assigned to a locker")
            return

        # Assign locker and GPIO pin
        def get_next_available_locker():
            used_lockers = {data["locker"] for data in lockers.values()}
            used_pins = {data["gpio"] for data in lockers.values()}

            for i in range(1, TOTAL_LOCKERS + 1):
                for pin in available_gpio_pins:
                    if i not in used_lockers and pin not in used_pins:
                        return i, pin

            return None, None

        locker_number, gpio_pin = get_next_available_locker()
        if locker_number is None:
            messagebox.showerror("Error", "No available lockers or GPIO pins.")
            return

        # Save face encoding and name
        known_encodings.append(face_encodings[0])
        known_names.append(name)
        lockers[name] = {"locker": locker_number, "gpio": gpio_pin}

        # Set up GPIO pin
        GPIO.setup(gpio_pin, GPIO.OUT)
        GPIO.output(gpio_pin, GPIO.LOW)

        # Save data
        save_encodings()
        save_lockers()

        messagebox.showinfo("Success", f"Registered {name} - Locker #{locker_number}")

    except Exception as e:
        messagebox.showerror("Error", f"Registration failed: {str(e)}")

def delete_face(name):
    global known_encodings, known_names, lockers
    
    # Prevent deleting admin
    if name.lower() == ADMIN_NAME.lower():
        messagebox.showerror("Error", "Cannot delete admin account")
        return
    
    try:
        # Find and remove the face
        for i, known_name in enumerate(known_names):
            if known_name.lower() == name.lower():
                del known_names[i]
                del known_encodings[i]
                
                # Remove from lockers
                if name.lower() in lockers:
                    del lockers[name.lower()]
                
                # Save updated data
                save_encodings()
                save_lockers()
                
                messagebox.showinfo("Success", f"Deleted user: {name}")
                return
        
        messagebox.showerror("Error", "Name not found in system")
    
    except Exception as e:
        messagebox.showerror("Error", f"Deletion failed: {str(e)}")

def main():
    # Initialize GPIO pins for all lockers
    for locker_data in lockers.values():
        gpio_pin = locker_data['gpio']
        GPIO.setup(gpio_pin, GPIO.OUT)
        GPIO.output(gpio_pin, GPIO.LOW)  # Default all lockers to closed
    
    # Create main window
    root = tk.Tk()
    app = LockerAccessApp(root)
    root.mainloop()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Program terminated by user")
    finally:
        picam2.stop()
        GPIO.cleanup()
