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

    all_usernames = set(name.lower() for name in known_names)
    all_locker_users = set(lockers.keys())

    # Display users with known faces
    for name in sorted(all_usernames):
        locker_info = lockers.get(name)
        locker_num = str(locker_info.get("locker")) if locker_info else "Not Assigned"
        status = "Available" if locker_info else "No Locker"
        print(f"Name: {name.title():<20} | Locker #: {locker_num:<10} | Status: {status}")

    # Display orphaned lockers (users who no longer have a face entry)
    orphans = all_locker_users - all_usernames
    if orphans:
        print("\n--- Orphaned Locker Assignments (No Face Found) ---")
        for name in sorted(orphans):
            locker_info = lockers[name]
            locker_num = str(locker_info.get("locker", "???"))
            print(f"Name: {name.title():<20} | Locker #: {locker_num:<10} | Status: Orphaned")

def remove_orphaned_lockers():
    face_data = load_data(ENCODINGS_FILE)
    known_names = set(name.lower() for name in face_data.get("names", []))

    lockers = load_data(LOCKERS_FILE)
    updated_lockers = {name: data for name, data in lockers.items() if name in known_names}

    with open(LOCKERS_FILE, "wb") as f:
        pickle.dump(updated_lockers, f)

    print("Orphaned lockers removed.")


if __name__ == "__main__":
    display_users()
