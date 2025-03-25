import face_recognition
import cv2
import os
import pickle
import numpy as np
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import time
from picamera2 import Picamera2
os.environ["DISPLAY"] = ":0"

try:
    import RPi.GPIO as GPIO
except ImportError:
    class MockGPIO:
        BCM = "BCM"
        OUT = "OUT"
        def setmode(self, mode): pass
        def setup(self, pin, mode): pass
        def output(self, pin, state): print(f"GPIO {pin} {'HIGH' if state else 'LOW'}")
        def cleanup(self): pass
    GPIO = MockGPIO()

# CONFIGURATION
ADMIN_NAME = "tim"
THRESHOLD = 0.45
IDLE_TIMEOUT = 60
TOTAL_LOCKERS = 100
DELAY_BETWEEN_PROMPTS = 20
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 480

KNOWN_FACES_DIR = "known_faces"
ENCODINGS_FILE = "faces.pkl"
LOCKERS_FILE = "lockers.pkl"

os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

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

available_gpio_pins = [2, 3, 4]

# Initialize Pi Camera
picam2 = Picamera2()
picam2.preview_configuration.main.size = (SCREEN_WIDTH, SCREEN_HEIGHT)
picam2.preview_configuration.main.format = "RGB888"
picam2.configure("preview")
picam2.start()

def capture_frame():
    return picam2.capture_array()

def save_encodings():
    try:
        with open(ENCODINGS_FILE, "wb") as f:
            pickle.dump((known_encodings, known_names), f)
    except Exception as e:
        print(f"Error saving encodings: {e}")

def save_lockers():
    try:
        with open(LOCKERS_FILE, "wb") as f:
            pickle.dump(lockers, f)
    except Exception as e:
        print(f"Error saving lockers: {e}")

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

def get_next_available_locker():
    used_lockers = {data["locker"] for data in lockers.values()}
    used_pins = {data["gpio"] for data in lockers.values()}
    for i in range(1, TOTAL_LOCKERS + 1):
        if i not in used_lockers:
            for pin in available_gpio_pins:
                if pin not in used_pins:
                    return i, pin
    return None, None

def register_face(name):
    global known_encodings, known_names, lockers, last_activity_time
    last_activity_time = time.time()
    try:
        frame = capture_frame()
        if frame is None:
            print("Failed to capture image")
            return
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        if not face_locations:
            print("No face detected. Try again.")
            return
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        if not face_encodings:
            print("Failed to encode face. Try again.")
            return
        for existing_encoding in known_encodings:
            if np.linalg.norm(existing_encoding - face_encodings[0]) < THRESHOLD:
                print("Face already registered.")
                return
        name = name.lower()
        if name in lockers:
            print(f"Name '{name}' is already assigned to Locker {lockers[name]['locker']}")
            return
        locker_number, gpio_pin = get_next_available_locker()
        if locker_number is None or gpio_pin is None:
            print("No available lockers or GPIO pins.")
            return
        known_encodings.append(face_encodings[0])
        known_names.append(name)
        lockers[name] = {"locker": locker_number, "gpio": gpio_pin}
        GPIO.setup(gpio_pin, GPIO.OUT)
        GPIO.output(gpio_pin, GPIO.LOW)
        save_encodings()
        save_lockers()
        print(f"Registered {name} - Locker #{locker_number}, GPIO {gpio_pin}")
    except Exception as e:
        print(f"Registration failed: {str(e)}")

def exit_program():
    picam2.stop()
    cv2.destroyAllWindows()
    exit()

# Minimal test loop (replace this with your full loop/UI logic)
if __name__ == "__main__":
    load_encodings()
    load_lockers()
    try:
        while True:
            name = input("Enter name to register or 'exit': ").strip().lower()
            if name == "exit":
                break
            register_face(name)
    finally:
        exit_program()
