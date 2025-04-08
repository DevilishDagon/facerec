# face_recognition_module.py
import face_recognition
import numpy as np
import pickle
import os
import cv2
import traceback
from config import ENCODINGS_FILE, THRESHOLD, KNOWN_FACES_DIR

class FaceRecognitionManager:
    def __init__(self, encodings_file=ENCODINGS_FILE):
        self.known_encodings = []
        self.known_names = []
        self.encodings_file = encodings_file
        self.load_encodings(encodings_file)
        
    def match_face(self, face_encoding):
        """
        Match a face encoding against known encodings
        
        :param face_encoding: Face encoding to match
        :return: Name of the matched person or "Unknown"
        """
        if not self.known_encodings:
            return "Unknown"
            
        try:
            matches = face_recognition.compare_faces(self.known_encodings, face_encoding, tolerance=THRESHOLD)
            name = "Unknown"
            if True in matches:
                first_match_index = matches.index(True)
                name = self.known_names[first_match_index]
            return name
        except Exception as e:
            print(f"Error matching face: {e}")
            traceback.print_exc()
            return "Unknown"
    
    def load_encodings(self, encodings_file):
        """
        Load face encodings from file
        
        :param encodings_file: Path to encodings file
        """
        try:
            if os.path.exists(encodings_file):
                with open(encodings_file, "rb") as f:
                    data = pickle.load(f)
                    # Handle both tuple format and dict format for backward compatibility
                    if isinstance(data, tuple) and len(data) == 2:
                        self.known_encodings, self.known_names = data
                    elif isinstance(data, dict):
                        self.known_encodings = data.get('encodings', [])
                        self.known_names = data.get('names', [])
                    else:
                        print("Warning: Unknown format in encodings file")
                        self.known_encodings, self.known_names = [], []
                        
                    # Ensure names are lowercase
                    self.known_names = [name.lower() for name in self.known_names]
                    
                print(f"Loaded {len(self.known_names)} face(s): {', '.join(self.known_names)}")
            else:
                self.known_encodings, self.known_names = [], []
                print("No encodings file found. Starting with empty database.")
        except Exception as e:
            print(f"Error loading encodings: {e}")
            traceback.print_exc()
            self.known_encodings, self.known_names = [], []
    
    def save_encodings(self, encodings_file=None):
        """
        Save face encodings to file with backup
        
        :param encodings_file: Path to save encodings
        """
        if encodings_file is None:
            encodings_file = self.encodings_file
            
        try:
            # First create a backup of the existing file if it exists
            if os.path.exists(encodings_file):
                backup_file = encodings_file + '.bak'
                try:
                    with open(encodings_file, 'rb') as src, open(backup_file, 'wb') as dst:
                        dst.write(src.read())
                except Exception as e:
                    print(f"Error creating backup: {e}")
            
            # Now save the current data
            data = {
                'encodings': self.known_encodings,
                'names': self.known_names
            }
            
            # Use a temporary file for atomic write
            temp_file = encodings_file + '.tmp'
            with open(temp_file, "wb") as f:
                pickle.dump(data, f)
                
            # Rename the temp file to the actual file
            if os.path.exists(temp_file):
                if os.path.exists(encodings_file):
                    os.remove(encodings_file)
                os.rename(temp_file, encodings_file)
                
            print(f"Successfully saved {len(self.known_names)} encodings")
            return True
        except Exception as e:
            print(f"Error saving encodings: {e}")
            traceback.print_exc()
            return False
    
    def register_face(self, name, face_encoding):
        """
        Register a new face
        
        :param name: Name of the person
        :param face_encoding: Face encoding to register
        :return: Success status
        """
        try:
            name = name.lower().strip()
            if not name:
                print("Error: Empty name provided")
                return False
                
            # Check if this face is already registered
            for existing_encoding in self.known_encodings:
                if np.linalg.norm(existing_encoding - face_encoding) < THRESHOLD:
                    print(f"Face similar to existing entry found")
                    return False
            
            # Check if name already exists
            if name in self.known_names:
                # Update the existing entry instead of adding a duplicate
                index = self.known_names.index(name)
                self.known_encodings[index] = face_encoding
                print(f"Updated existing entry for {name}")
            else:
                # Add new entry
                self.known_encodings.append(face_encoding)
                self.known_names.append(name)
                print(f"Added new entry for {name}")
            
            # Save to file
            success = self.save_encodings()
            return success
        except Exception as e:
            print(f"Error registering face: {e}")
            traceback.print_exc()
            return False
