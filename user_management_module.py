import pickle
import traceback
from config import ENCODINGS_FILE, LOCKERS_FILE

def load_data(file_path):
    """Safely load a pickled file"""
    try:
        with open(file_path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        traceback.print_exc()
        return {}

def display_users():
    print("=== User Management (CLI) ===\n")

    # Load face recognition data
    face_data = load_data(ENCODINGS_FILE)
    known_names = face_data.get("names", []) if isinstance(face_data, dict) else []

    # Load locker assignments
    lockers = load_data(LOCKERS_FILE)

    if not known_names:
        print("No users found.")
        return

    for name in sorted(known_names):
        locker_num = "Not Assigned"
        status = "No Locker"

        if name in lockers:
            locker_info = lockers[name]
            locker_num = str(locker_info.get("locker", "Error"))
            status = "Available"

        print(f"Name: {name.title():<20} | Locker #: {locker_num:<10} | Status: {status}")

if __name__ == "__main__":
    display_users()
