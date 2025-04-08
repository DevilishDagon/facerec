# config.py
import os

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

# Ensure known faces directory exists
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

# Available GPIO pins
AVAILABLE_GPIO_PINS = [3, 4]
