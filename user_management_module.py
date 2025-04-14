import face_recognition_module

# Get face data
names = face_recognition_module
        
# Add each user to the treeview
for name in (names):
	locker_num = "Not Assigned"
	status = "No Locker"
	            
	# Check if user has a locker assigned
	if name in self.locker_manager.lockers:
		locker_info = self.locker_manager.lockers[name]
		locker_num = str(locker_info['locker']) if 'locker' in locker_info else "Error"
		status = "Available"
            
print(values=(name.title(), locker_num, status))
