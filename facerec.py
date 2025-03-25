import face_recognition
import cv2
import os
import pickle
import numpy as np
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import time
try:
    import RPi.GPIO as GPIO
except ImportError:
    # If not on Raspberry Pi, mock GPIO for testing
    class MockGPIO:
        BCM = "BCM"
        OUT = "OUT"
        
        def setmode(self, mode): pass
        def setup(self, pin, mode): pass
        def output(self, pin, state): print(f"GPIO {pin} {'HIGH' if state else 'LOW'}")
        def cleanup(self): pass

    GPIO = MockGPIO()

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
locker_prompt = None
current_buttons = []

available_gpio_pins = [2,3,4]


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

# Load data
load_encodings()
load_lockers()

# Initialize video capture
video_capture = cv2.VideoCapture(0)
video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, SCREEN_WIDTH)
video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, SCREEN_HEIGHT)
video_capture.set(cv2.CAP_PROP_FPS, 60)
video_capture.set(cv2.CAP_PROP_BUFFERSIZE, 0)  # Minimize buffering for realtime

# Classes to handle overlay UI elements
class OverlayButton:
    def __init__(self, x, y, width, height, text, action, color=(0, 120, 255), text_color=(255, 255, 255)):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.action = action
        self.color = color
        self.text_color = text_color
        self.hover = False
        
    def draw(self, frame):
        # Draw button background
        cv2.rectangle(frame, (self.x, self.y), (self.x + self.width, self.y + self.height), 
                     self.color, -1)
        cv2.rectangle(frame, (self.x, self.y), (self.x + self.width, self.y + self.height), 
                     (0, 0, 0), 2)
        
        # Center text
        text_size = cv2.getTextSize(self.text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
        text_x = self.x + (self.width - text_size[0]) // 2
        text_y = self.y + (self.height + text_size[1]) // 2
        
        cv2.putText(frame, self.text, (text_x, text_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.text_color, 2)
                   
    def contains_point(self, x, y):
        return (self.x <= x <= self.x + self.width and 
                self.y <= y <= self.y + self.height)

class VirtualKeyboard:
    def __init__(self, frame_width, frame_height):
        self.width = 600
        self.height = 300  # Increased height to prevent overlap
        self.x = (frame_width - self.width) // 2
        self.y = (frame_height - self.height) // 2 - 20  # Move up slightly
        self.keys = []
        self.input_text = ""
        self.active = False
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.action = None
        self.init_keys()
        
    def init_keys(self):
        self.keys = []
        # Create alphanumeric keys
        layouts = [
            "1234567890",
            "QWERTYUIOP",
            "ASDFGHJKL",
            "ZXCVBNM"
        ]
        
        key_width = 40
        key_height = 40
        key_margin = 3
        
        # Initialize regular keys
        for row_idx, row in enumerate(layouts):
            for col_idx, key in enumerate(row):
                x = self.x + col_idx * (key_width + key_margin) + (row_idx * 12)
                y = self.y + row_idx * (key_height + key_margin) + 100  # Increased from 50 to 100
                
                self.keys.append(OverlayButton(
                    x, y, key_width, key_height, key,
                    lambda k=key.lower(): self.add_char(k)
                ))
                
        # Add special keys
        # Space
        space_x = self.x + 80
        space_y = self.y + 4 * (key_height + key_margin) + 100  # Adjusted based on new layout
        self.keys.append(OverlayButton(
            space_x, space_y, 260, key_height, "SPACE",
            lambda: self.add_char(" "),
            color=(100, 100, 100)
        ))
        
        # Backspace
        bksp_x = self.x + 350
        bksp_y = self.y + 4 * (key_height + key_margin) + 100  # Adjusted
        self.keys.append(OverlayButton(
            bksp_x, bksp_y, 80, key_height, "DEL",
            self.backspace,
            color=(200, 100, 100)
        ))
        
        # Enter
        enter_x = self.x + 440
        enter_y = self.y + 4 * (key_height + key_margin) + 100  # Adjusted
        self.keys.append(OverlayButton(
            enter_x, enter_y, 80, key_height, "ENTER",
            self.confirm,
            color=(100, 200, 100)
        ))
        
        # Cancel
        cancel_x = self.x + self.width - 60
        cancel_y = self.y + 10
        self.keys.append(OverlayButton(
            cancel_x, cancel_y, 50, 30, "✕",
            self.cancel,
            color=(200, 50, 50)
        ))
    
    def draw(self, frame):
        if not self.active:
            return
            
        # Draw keyboard background
        cv2.rectangle(frame, (self.x, self.y), 
                     (self.x + self.width, self.y + self.height), 
                     (30, 30, 30), -1)
        cv2.rectangle(frame, (self.x, self.y), 
                     (self.x + self.width, self.y + self.height), 
                     (100, 100, 100), 2)
                     
        # Draw title - moved up to prevent overlap
        title = f"{self.action} Face"
        cv2.putText(frame, title, (self.x + 20, self.y + 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Draw input field - moved down
        input_box_x = self.x + 20
        input_box_y = self.y + 70  # Increased from 40 to provide more space
        input_box_width = self.width - 100
        input_box_height = 30
        
        cv2.rectangle(frame, (input_box_x, input_box_y), 
                     (input_box_x + input_box_width, input_box_y + input_box_height), 
                     (10, 10, 10), -1)
        cv2.rectangle(frame, (input_box_x, input_box_y), 
                     (input_box_x + input_box_width, input_box_y + input_box_height), 
                     (150, 150, 150), 1)
                     
        # Draw input text with cursor
        input_with_cursor = self.input_text + "|"
        cv2.putText(frame, input_with_cursor, (input_box_x + 10, input_box_y + 22), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # Draw keys
        for key in self.keys:
            key.draw(frame)
    
    def add_char(self, char):
        self.input_text += char
        
    def backspace(self):
        if self.input_text:
            self.input_text = self.input_text[:-1]
            
    def confirm(self):
        if self.input_text.strip():
            if self.action == "Add":
                register_face(self.input_text.strip())
            elif self.action == "Delete":
                delete_face(self.input_text.strip())
            elif self.action == "Delete Target":
                process_delete_target(self.input_text.strip())
            self.cancel()
            
    def cancel(self):
        self.active = False
        self.input_text = ""
        
    def activate(self, action):
        self.active = True
        self.action = action
        self.input_text = ""
        
    def handle_click(self, x, y):
        if not self.active:
            return False
            
        for key in self.keys:
            if key.contains_point(x, y):
                key.action()
                return True
                
        return True  # Consume click even if not on a key

class LockerPrompt:
    def __init__(self, frame_width, frame_height):
        self.width = 300
        self.height = 150
        self.x = (frame_width - self.width) // 2
        self.y = (frame_height - self.height) // 2
        self.active = False
        self.name = ""
        self.locker_num = 0
        self.yes_button = None
        self.no_button = None
        self.frame_width = frame_width
        self.frame_height = frame_height
        
    def activate(self, name, locker_num):
        self.active = True
        self.name = name
        self.locker_num = locker_num
        
        # Create buttons
        btn_width = 100
        btn_height = 40
        margin = 15
        
        y_pos = self.y + self.height - btn_height - margin
        
        self.yes_button = OverlayButton(
            self.x + margin, y_pos, btn_width, btn_height,
            "YES", lambda: self.confirm(True),
            color=(100, 200, 100)
        )
        
        self.no_button = OverlayButton(
            self.x + self.width - btn_width - margin, y_pos, btn_width, btn_height,
            "NO", lambda: self.confirm(False),
            color=(200, 100, 100)
        )
        
    def draw(self, frame):
        if not self.active:
            return
            
        # Draw background
        cv2.rectangle(frame, (self.x, self.y), 
                     (self.x + self.width, self.y + self.height), 
                     (40, 40, 40), -1)
        cv2.rectangle(frame, (self.x, self.y), 
                     (self.x + self.width, self.y + self.height), 
                     (150, 150, 150), 2)
                     
        # Draw title
        cv2.putText(frame, f"Hello, {self.name}", (self.x + 20, self.y + 35), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                   
        # Draw message
        cv2.putText(frame, f"Open Locker {self.locker_num}?", (self.x + 20, self.y + 65), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                   
        # Draw buttons
        self.yes_button.draw(frame)
        self.no_button.draw(frame)
        
    def confirm(self, response):
        if response:
            # Show success message
            global locker_success_message, locker_success_time
            locker_success_message = f"Locker {self.locker_num} unlocked"
            locker_success_time = time.time()
        self.active = False
        
    def handle_click(self, x, y):
        if not self.active:
            return False
            
        if self.yes_button.contains_point(x, y):
            self.yes_button.action()
            return True
            
        if self.no_button.contains_point(x, y):
            self.no_button.action()
            return True
            
        return True  # Consume click even if not on a button

def get_next_available_locker():
    used_lockers = {data["locker"] for data in lockers.values()}  # Track used locker numbers
    used_pins = {data["gpio"] for data in lockers.values()}  # Track used GPIO pins

    for i in range(1, TOTAL_LOCKERS + 1):  # Loop through lockers
        if i not in used_lockers:  # Find an unused locker number
            for pin in available_gpio_pins:  # Find an unused GPIO pin
                if pin not in used_pins:
                    return i, pin  # Return both locker number and GPIO pin

    return None, None  # Return None if no lockers or GPIO pins are available

def show_keyboard(action):
    global virtual_keyboard, last_activity_time
    last_activity_time = time.time()
    virtual_keyboard.activate(action)

def register_face(name):
    global known_encodings, known_names, lockers, last_activity_time
    last_activity_time = time.time()

    try:
        ret, frame = video_capture.read()
        if not ret:
            show_message("Failed to capture image")
            return

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)

        if not face_locations:
            show_message("No face detected. Try again.")
            return

        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        if not face_encodings:
            show_message("Failed to encode face. Try again.")
            return

        # Check if the face already exists using the threshold
        for existing_encoding in known_encodings:
            if np.linalg.norm(existing_encoding - face_encodings[0]) < THRESHOLD:
                show_message("Face already registered.")
                return

        name = name.lower()

        # Prevent duplicate name registration
        if name in lockers:
            show_message(f"Name '{name}' is already assigned to Locker {lockers[name]['locker']}")
            return

        # Assign locker and GPIO pin automatically
        locker_number, gpio_pin = get_next_available_locker()
        if locker_number is None or gpio_pin is None:
            show_message("No available lockers or GPIO pins.")
            return

        # Save face encoding and name
        known_encodings.append(face_encodings[0])
        known_names.append(name)
        lockers[name] = {"locker": locker_number, "gpio": gpio_pin}

        # Set up the GPIO pin
        GPIO.setup(gpio_pin, GPIO.OUT)
        GPIO.output(gpio_pin, GPIO.LOW)  # Default to LOW

        save_encodings()
        save_lockers()

        # Show success message
        global register_success_message, register_success_time
        register_success_message = f"Registered {name} - Locker #{locker_number}, GPIO {gpio_pin}"
        register_success_time = time.time()

    except Exception as e:
        show_message(f"Registration failed: {str(e)}")

def delete_face(name):
    global last_activity_time
    last_activity_time = time.time()
    
    # First check if the person requesting deletion is the admin
    if name.lower() != ADMIN_NAME.lower():
        show_message("Only admin can delete faces")
        return
        
    # If we get here, the admin is authenticated
    # Now show a keyboard to ask which user to delete
    virtual_keyboard.activate("Delete Target")

def process_delete_target(target_name):
    global known_names, known_encodings, lockers
    
    target_name = target_name.lower()
    
    # Don't allow deleting the admin
    if target_name == ADMIN_NAME.lower():
        show_message("Cannot delete admin account")
        return
    
    # Find the name in the list (case-insensitive)
    found = False
    for i, name in enumerate(known_names):
        if name.lower() == target_name:
            known_names.pop(i)
            known_encodings.pop(i)
            found = True
            break
    
    # Remove from lockers dictionary if present
    if target_name in lockers:
        del lockers[target_name]
    
    if found:
        save_encodings()
        save_lockers()
        
        # Show success message
        global register_success_message, register_success_time
        register_success_message = f"Admin deleted user: {target_name}"
        register_success_time = time.time()
    else:
        show_message("Name not found in system")

def show_message(message, duration=3):
    global status_message, status_message_time
    status_message = message
    status_message_time = time.time()

def open_locker(name):
    global last_prompt_time, last_activity_time, locker_prompt
    last_activity_time = time.time()
    
    # Check if enough time has passed since last prompt for this user
    if name in last_prompt_time and time.time() - last_prompt_time[name] < DELAY_BETWEEN_PROMPTS:
        return
    
    last_prompt_time[name] = time.time()
    if name not in lockers:
        show_message(f"No locker assigned for {name}")
        return
    
    locker_prompt.activate(name, lockers[name])

def check_idle_timeout():
    global last_activity_time, virtual_keyboard, locker_prompt
    
    if time.time() - last_activity_time > IDLE_TIMEOUT:
        # Reset the system state to idle mode
        virtual_keyboard.active = False
        locker_prompt.active = False
        last_activity_time = time.time()

def mouse_callback(event, x, y, flags, param):
    global virtual_keyboard, locker_prompt, last_activity_time
    last_activity_time = time.time()
    
    if event == cv2.EVENT_LBUTTONDOWN:
        # Check if keyboard is active
        if virtual_keyboard.active and virtual_keyboard.handle_click(x, y):
            return
            
        # Check if locker prompt is active
        if locker_prompt.active and locker_prompt.handle_click(x, y):
            return
            
        # Check bottom buttons
        for button in current_buttons:
            if button.contains_point(x, y):
                button.action()
                return

def exit_program():
    video_capture.release()
    cv2.destroyAllWindows()
    exit()

# Create main window
cv2.namedWindow("Locker Access System", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Locker Access System", SCREEN_WIDTH, SCREEN_HEIGHT)
cv2.setMouseCallback("Locker Access System", mouse_callback)

# Initialize overlay UI components
frame_width = SCREEN_WIDTH
frame_height = SCREEN_HEIGHT
virtual_keyboard = VirtualKeyboard(frame_width, frame_height)
locker_prompt = LockerPrompt(frame_width, frame_height)

# Message display variables
status_message = ""
status_message_time = 0
register_success_message = ""
register_success_time = 0
locker_success_message = ""
locker_success_time = 0
delete_target_mode = False

# Main loop
while True:
    def simulate_manual_recognition():
        """ Asks the user to enter a name manually instead of using face recognition. """
        name = input("Enter a recognized name (or type 'exit' to quit): ").strip().lower()
        return name if name else None  # Return None if input is empty
    name = simulate_manual_recognition()  # Ask for a manual name
    
    if name == "exit":
        print("Exiting test mode.")
        break

    if name in lockers:
        print(f"Simulated Recognition: {name}")
        print(f"Locker {lockers[name]['locker']} assigned - GPIO {lockers[name]['gpio']} HIGH")
        
        # Simulate unlocking the locker
        GPIO.output(lockers[name]["gpio"], GPIO.HIGH)
        time.sleep(5)  # Keep it unlocked for 5 seconds
        GPIO.output(lockers[name]["gpio"], GPIO.LOW)

        print(f"Locker {lockers[name]['locker']} closed - GPIO {lockers[name]['gpio']} LOW")
    
    else:
        print(f"Unknown name: {name} (No locker assigned)")
        
    # Flip for mirror effect
    frame = cv2.flip(frame, 1)
    
    # Create a separate frame for face detection to avoid slowdown
    if time.time() % 0.1 < 0.1:  # Run face detection at ~5fps for better performance
        process_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb_frame = cv2.cvtColor(process_frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_frame, model="hog")
        if face_locations:
            last_activity_time = time.time()
            
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        
        # Process each face
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            name = "Unknown"
            
            if known_encodings:
                distances = face_recognition.face_distance(known_encodings, face_encoding)
                best_match_index = np.argmin(distances)
                if distances[best_match_index] < THRESHOLD:
                    name = known_names[best_match_index]
            
            # Scale back to original size
            top, right, bottom, left = [int(x * 2) for x in [top, right, bottom, left]]
            
            # Draw box and name
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            
            # Create label with background for better readability
            label_y = top - 10 if top - 10 > 10 else top + 10
            cv2.putText(frame, name, (left, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Trigger locker prompt if recognized
            if name != "Unknown" and name in lockers and not locker_prompt.active and not virtual_keyboard.active:
                open_locker(name)
    
    # Check for idle timeout
    check_idle_timeout()
    
    # Create control buttons at the bottom
    button_height = 50
    button_width = 150
    button_margin = 20
    button_y = frame_height - button_height - 15
    
    # Clear the previous buttons
    current_buttons = []
    
    # Add face button
    add_button = OverlayButton(
        button_margin, button_y, button_width, button_height,
        "Add Face", lambda: show_keyboard("Add"),
        color=(0, 150, 0)
    )
    current_buttons.append(add_button)
    
    # Delete face button
    delete_button = OverlayButton(
        button_margin*2 + button_width, button_y, button_width, button_height,
        "Delete Face", lambda: show_keyboard("Delete"),
        color=(150, 0, 0)
    )
    current_buttons.append(delete_button)
    
    # Exit button
    exit_button = OverlayButton(
        button_margin*3 + button_width*2, button_y, button_width, button_height,
        "Exit", lambda: exit_program(),
        color=(100, 100, 100)
    )
    current_buttons.append(exit_button)
    
    # Draw the control buttons
    for button in current_buttons:
        button.draw(frame)
    
    # Draw virtual keyboard if active
    virtual_keyboard.draw(frame)
    
    # Draw locker prompt if active
    locker_prompt.draw(frame)
    
    # Show status messages
    message_time = 3  # seconds to show messages
    font_size = 0.6
    
    # Status message
    if time.time() - status_message_time < message_time and status_message:
        msg_width = len(status_message) * 9  # Approximate width calculation
        cv2.rectangle(frame, (0, 0), (msg_width, 30), (0, 0, 0), -1)
        cv2.putText(frame, status_message, (10, 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, font_size, (255, 255, 255), 1)
    
    # Registration success message
    if time.time() - register_success_time < message_time and register_success_message:
        y_pos = 60
        msg_width = len(register_success_message) * 9
        cv2.rectangle(frame, (0, y_pos-20), (msg_width, y_pos+10), (0, 100, 0), -1)
        cv2.putText(frame, register_success_message, (10, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, font_size, (255, 255, 255), 1)
    
    # Locker success message
    if time.time() - locker_success_time < message_time and locker_success_message:
        y_pos = 100
        msg_width = len(locker_success_message) * 9
        cv2.rectangle(frame, (0, y_pos-20), (msg_width, y_pos+10), (0, 0, 100), -1)
        cv2.putText(frame, locker_success_message, (10, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, font_size, (255, 255, 255), 1)
    
    # # Display the frame
    # cv2.imshow("Locker Access System", frame)
    
    # # Check for exit key
    # key = cv2.waitKey(1) & 0xFF
    # if key == 27:  # ESC key
    #     break

    # Headless Mode - No Display Output
    time.sleep(1)  # Simulate processing time
    print(f"Simulated Recognition: {name}")

# Cleanup
video_capture.release()
cv2.destroyAllWindows()