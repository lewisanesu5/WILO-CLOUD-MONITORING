"""
Setup script to create fault/event type directories in the Data directory.
Runs once to initialize the folder structure for each fault type.
"""

import os

# Define all fault types from the frontend EVENT_TYPES
FAULT_TYPES = [
    # Motor Failures
    'Motor Bearing Failure',
    'Motor Overheating',
    'Motor Winding Failure',
    'Motor Shaft Misalignment',
    'Motor Vibration Anomaly',
    'Motor Stall',
    'Motor Electrical Fault',
    # Pump Failures
    'Pump Seal Leakage',
    'Pump Cavitation',
    'Pump Impeller Damage',
    # Other
    'Custom Event'
]

def create_fault_directories():
    """Create fault type directories in the Data directory."""
    data_dir = 'Data'
    
    # Create main Data directory if it doesn't exist
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"✓ Created main directory: {data_dir}")
    
    # Create subdirectory for each fault type
    for fault in FAULT_TYPES:
        # Replace spaces with underscores for folder names (or keep spaces - user preference)
        folder_name = fault  # Keep spaces as-is
        folder_path = os.path.join(data_dir, folder_name)
        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"✓ Created fault directory: {folder_path}")
        else:
            print(f"  Fault directory already exists: {folder_path}")
    
    print(f"\n✅ Setup complete! Created {len(FAULT_TYPES)} fault type directories in {data_dir}/")

if __name__ == '__main__':
    create_fault_directories()
