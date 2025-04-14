import os
import pickle
import tkinter as tk
from tkinter import ttk
import traceback
from PIL import Image, ImageTk
import time
from config import ENCODINGS_FILE, LOCKERS_FILE

# Get face data
names = self.face_recognizer.known_names
        
# Add each user to the treeview
for name in sorted(names):
	locker_num = "Not Assigned"
	status = "No Locker"
	            
	# Check if user has a locker assigned
	if name in self.locker_manager.lockers:
		locker_info = self.locker_manager.lockers[name]
		locker_num = str(locker_info['locker']) if 'locker' in locker_info else "Error"
		status = "Available"
            
print(values=(name.title(), locker_num, status))
