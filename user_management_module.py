# user_management_module.py
import os
import pickle
import tkinter as tk
from tkinter import ttk
import traceback
from PIL import Image, ImageTk
import time
from config import ENCODINGS_FILE, LOCKERS_FILE

class UserManagementUI:
    def __init__(self, master, face_recognizer, locker_manager, return_callback):
        """
        Initialize user management UI to view and manage users
        
        :param master: Root window
        :param face_recognizer: FaceRecognitionManager instance
        :param locker_manager: LockerManager instance
        :param return_callback: Function to call when returning to main screen
        """
        self.master = master
        self.face_recognizer = face_recognizer
        self.locker_manager = locker_manager
        self.return_callback = return_callback
        
        # Create main frame
        self.frame = tk.Frame(master, bg="black")
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(self.frame, text="User Management", 
                               font=("Arial", 24, "bold"), bg="black", fg="white")
        title_label.pack(pady=10)
        
        # Create table frame
        table_frame = tk.Frame(self.frame, bg="black")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Create treeview for user list with custom styling
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", 
                         background="black", 
                         foreground="white",
                         fieldbackground="black",
                         font=("Arial", 12))
        style.configure("Treeview.Heading", 
                         font=("Arial", 14, "bold"),
                         background="gray20",
                         foreground="white")
        
        # Create scrollbar
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create treeview
        self.treeview = ttk.Treeview(table_frame, 
                                    columns=("Name", "Locker #", "Status"),
                                    show="headings",
                                    yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.treeview.yview)
        
        # Configure column headings
        self.treeview.heading("Name", text="Name")
        self.treeview.heading("Locker #", text="Locker #")
        self.treeview.heading("Status", text="Status")
        
        # Configure column widths
        self.treeview.column("Name", width=250)
        self.treeview.column("Locker #", width=150, anchor=tk.CENTER)
        self.treeview.column("Status", width=150, anchor=tk.CENTER)
        
        self.treeview.pack(fill=tk.BOTH, expand=True)
        
        # Button frame
        button_frame = tk.Frame(self.frame, bg="black")
        button_frame.pack(fill=tk.X, pady=20)
        
        # Return button
        return_button = tk.Button(button_frame, text="Return to Main Screen", 
                                 font=("Arial", 14), bg="blue", fg="white",
                                 command=self.return_to_main)
        return_button.pack(pady=10)
        
        # Populate data
        self.refresh_users()
    
    def refresh_users(self):
        """Refresh the user list"""
        # Clear existing items
        for item in self.treeview.get_children():
            self.treeview.delete(item)
        
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
            
            self.treeview.insert("", tk.END, values=(name.title(), locker_num, status))
    
    def return_to_main(self):
        """Return to main screen"""
        self.frame.destroy()
        if self.return_callback:
            self.return_callback()

print(values=(name.title(), locker_num, status))
