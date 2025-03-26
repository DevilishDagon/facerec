# locker_control_module.py
import RPi.GPIO as GPIO
import pickle
import os
from config import LOCKERS_FILE, TOTAL_LOCKERS, AVAILABLE_GPIO_PINS

class LockerManager:
    def __init__(self, lockers_file=LOCKERS_FILE):
        """
        Initialize locker management system
        
        :param lockers_file: Path to saved locker assignments
        """
        # Set GPIO mode
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        self.lockers = {}
        self.load_lockers(lockers_file)
        self._initialize_gpio_pins()
    
    def load_lockers(self, lockers_file):
        """
        Load locker assignments from file
        
        :param lockers_file: Path to saved locker data
        """
        try:
            if os.path.exists(lockers_file):
                with open(lockers_file, "rb") as f:
                    self.lockers = pickle.load(f)
                    # Ensure names are lowercase
                    self.lockers = {name.lower(): data for name, data in self.lockers.items()}
            else:
                self.lockers = {}
        except Exception as e:
            print(f"Error loading lockers: {e}")
            self.lockers = {}
    
    def save_lockers(self, lockers_file=LOCKERS_FILE):
        """
        Save current locker assignments
        
        :param lockers_file: Path to save locker data
        """
        try:
            with open(lockers_file, "wb") as f:
                pickle.dump(self.lockers, f)
        except Exception as e:
            print(f"Error saving lockers: {e}")
    
    def _initialize_gpio_pins(self):
        """
        Initialize GPIO pins for all assigned lockers
        """
        for locker_data in self.lockers.values():
            gpio_pin = locker_data['gpio']
            GPIO.setup(gpio_pin, GPIO.OUT)
            GPIO.output(gpio_pin, GPIO.LOW)  # Default all lockers to closed
    
    def assign_locker(self, name):
        """
        Assign a new locker to a user
        
        :param name: Name of the user
        :return: Locker assignment details or None
        """
        name = name.lower()
        
        # Check if name already has a locker
        if name in self.lockers:
            return None
        
        # Find next available locker
        used_lockers = {data["locker"] for data in self.lockers.values()}
        used_pins = {data["gpio"] for data in self.lockers.values()}

        for i in range(1, TOTAL_LOCKERS + 1):
            for pin in AVAILABLE_GPIO_PINS:
                if i not in used_lockers and pin not in used_pins:
                    # Assign locker
                    locker_details = {"locker": i, "gpio": pin}
                    self.lockers[name] = locker_details
                    
                    # Setup GPIO pin
                    GPIO.setup(pin, GPIO.OUT)
                    GPIO.output(pin, GPIO.LOW)
                    
                    # Save updated lockers
                    self.save_lockers()
                    
                    return locker_details
        
        return None
    
    def open_locker(self, name):
        """
        Open locker for a specific user
        
        :param name: Name of the user
        :return: Success status and message
        """
        name = name.lower()
        
        if name not in self.lockers:
            return False, f"No locker assigned for {name}"
        
        locker_info = self.lockers[name]
        gpio_pin = locker_info['gpio']
        
        try:
            # Unlock the locker
            GPIO.output(gpio_pin, GPIO.HIGH)
            return True, f"Locker {locker_info['locker']} opened"
        
        except Exception as e:
            return False, f"Error opening locker: {e}"
    
    def close_locker(self, name):
        """
        Close locker for a specific user
        
        :param name: Name of the user
        :return: Success status and message
        """
        name = name.lower()
        
        if name not in self.lockers:
            return False, f"No locker assigned for {name}"
        
        locker_info = self.lockers[name]
        gpio_pin = locker_info['gpio']
        
        try:
            # Lock the locker
            GPIO.output(gpio_pin, GPIO.LOW)
            return True, f"Locker {locker_info['locker']} closed"
        
        except Exception as e:
            return False, f"Error closing locker: {e}"
    
    def cleanup(self):
        """
        Cleanup GPIO pins
        """
        GPIO.cleanup()
