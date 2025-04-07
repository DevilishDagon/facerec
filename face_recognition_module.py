# face_recognition_module.py
import face_recognition
import numpy as np
import pickle
import os
import cv2
from config import ENCODINGS_FILE, THRESHOLD

class FaceRecognitionManager:
    def __init__(self, encodings_file=ENCODINGS_FILE):
        self.known_encodings = []
        self.known_names = []
        self.load_encodings(encodings_file)

    def match_face(self, face_encoding):
        matches = face_recognition.compare_faces(self.known_encodings, face_encoding, tolerance=THRESHOLD)
        name = "Unknown"
        if True in matches:
            first_match_index = matches.index(True)
            name = self.known_names[first_match_index]
        return name

    def load_encodings(self, encodings_file):
        try:
            if os.path.exists(encodings_file):
                with open(encodings_file, "rb") as f:
                    self.known_encodings, self.known_names = pickle.load(f)
                    self.known_names = [name.lower() for name in self.known_names]
            else:
                self.known_encodings, self.known_names = [], []
        except Exception as e:
            print(f"Error loading encodings: {e}")
            self.known_encodings, self.known_names = [], []

    def save_encodings(self, encodings_file=ENCODINGS_FILE):
        try:
            with open(encodings_file, "wb") as f:
                pickle.dump((self.known_encodings, self.known_names), f)
        except Exception as e:
            print(f"Error saving encodings: {e}")

    def register_face(self, name, face_encoding):
        for existing_encoding in self.known_encodings:
            if np.linalg.norm(existing_encoding - face_encoding) < THRESHOLD:
                return False
        name = name.lower()
        self.known_encodings.append(face_encoding)
        self.known_names.append(name)
        self.save_encodings()
        return True
