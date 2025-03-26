# face_recognition_module.py
import face_recognition
import numpy as np
import pickle
import os
import cv2
from config import ENCODINGS_FILE, THRESHOLD

class FaceRecognitionManager:
    def __init__(self, encodings_file=ENCODINGS_FILE):
        """
        Initialize face recognition system
        
        :param encodings_file: Path to saved face encodings
        """
        self.known_encodings = []
        self.known_names = []
        self.load_encodings(encodings_file)
    
    def load_encodings(self, encodings_file):
        """
        Load face encodings from file
        
        :param encodings_file: Path to saved encodings
        """
        try:
            if os.path.exists(encodings_file):
                with open(encodings_file, "rb") as f:
                    self.known_encodings, self.known_names = pickle.load(f)
                    # Ensure names are lowercase
                    self.known_names = [name.lower() for name in self.known_names]
            else:
                self.known_encodings, self.known_names = [], []
        except Exception as e:
            print(f"Error loading encodings: {e}")
            self.known_encodings, self.known_names = [], []
    
    def save_encodings(self, encodings_file=ENCODINGS_FILE):
        """
        Save current face encodings to file
        
        :param encodings_file: Path to save encodings
        """
        try:
            with open(encodings_file, "wb") as f:
                pickle.dump((self.known_encodings, self.known_names), f)
        except Exception as e:
            print(f"Error saving encodings: {e}")
    
    def recognize_face(self, frame):
        """
        Recognize faces in a given frame
        
        :param frame: Input frame to detect faces
        :return: List of recognized names
        """
        # Convert frame to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        
        recognized_names = []
        
        # Compare each face with known faces
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(
                self.known_encodings, 
                face_encoding, 
                tolerance=THRESHOLD
            )
            
            name = "Unknown"
            
            if True in matches:
                first_match_index = matches.index(True)
                name = self.known_names[first_match_index]
            
            recognized_names.append(name)
        
        return recognized_names, face_locations
    
    def register_face(self, name, face_encoding):
        """
        Register a new face
        
        :param name: Name of the person
        :param face_encoding: Face encoding to register
        """
        # Prevent duplicate registrations
        for existing_encoding in self.known_encodings:
            if np.linalg.norm(existing_encoding - face_encoding) < THRESHOLD:
                return False
        
        name = name.lower()
        self.known_encodings.append(face_encoding)
        self.known_names.append(name)
        return True
