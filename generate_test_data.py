"""
Generate dummy sensor data for Predictive Maintenance System
Creates 6 CSV files: max/min for acceleration, current, and audio
"""
import csv
import datetime as dt
import numpy as np
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), 'Data')
os.makedirs(DATA_DIR, exist_ok=True)

def generate_sensor_data(sensor_type, file_type, num_points=1400):
    """Generate synthetic sensor data simulating a failure scenario."""
    
    # Base configuration per sensor
    configs = {
        'acceleration': {'baseline': 2.5, 'peak': 9.8, 'noise': 0.3},
        'current': {'baseline': 5.0, 'peak': 15.0, 'noise': 0.5},
        'audio': {'baseline': 1.5, 'peak': 8.0, 'noise': 0.2}
    }
    
    config = configs.get(sensor_type, configs['acceleration'])
    
    # Timestamps: spanning 2 seconds with 1400 points
    start_time = dt.datetime.now() - dt.timedelta(hours=2)
    timestamps = [
        start_time + dt.timedelta(seconds=i * (2.0 / num_points))
        for i in range(num_points)
    ]
    
    # Generate values simulating equipment behavior
    values = []
    for i in range(num_points):
        progress = i / num_points  # 0 to 1
        
        # Phase 1: Normal baseline (0-0.6)
        if progress < 0.6:
            base_value = config['baseline']
            noise = np.random.normal(0, config['noise'])
        
        # Phase 2: Degradation starts (0.6-0.85)
        elif progress < 0.85:
            degradation = (progress - 0.6) / 0.25  # 0 to 1
            base_value = config['baseline'] + (config['peak'] - config['baseline']) * degradation ** 2
            noise = np.random.normal(0, config['noise'] * (1 + degradation))
        
        # Phase 3: Critical phase (0.85-1.0)
        else:
            base_value = config['peak'] - (progress - 0.85) / 0.15 * 2  # Slight recovery
            noise = np.random.normal(0, config['noise'] * 2)
        
        value = max(0, base_value + noise)
        
        # Apply min/max filtering
        if file_type == 'max':
            value = base_value + abs(noise)  # Keep higher values
        else:  # min
            value = base_value - abs(noise)  # Keep lower values
        
        values.append(max(0, value))
    
    return timestamps, values

def save_csv_file(sensor_type, file_type, timestamps, values):
    """Save data to CSV file."""
    filename = f"{file_type}_{sensor_type}.csv"
    filepath = os.path.join(DATA_DIR, filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['timestamp', 'value'])
        writer.writeheader()
        
        for ts, val in zip(timestamps, values):
            writer.writerow({
                'timestamp': ts.isoformat(),
                'value': f"{val:.6f}"
            })
    
    print(f"✓ Created {filename} ({len(values)} points)")

def main():
    print("🔧 Generating dummy data for Predictive Maintenance System\n")
    
    sensors = ['acceleration', 'current', 'audio']
    file_types = ['max', 'min']
    
    total_files = 0
    for sensor in sensors:
        for file_type in file_types:
            timestamps, values = generate_sensor_data(sensor, file_type)
            save_csv_file(sensor, file_type, timestamps, values)
            total_files += 1
    
    print(f"\n✨ Successfully created {total_files} CSV files in {DATA_DIR}")
    print("\nFile structure:")
    print("  - max_acceleration.csv / min_acceleration.csv")
    print("  - max_current.csv / min_current.csv")
    print("  - max_audio.csv / min_audio.csv")

if __name__ == '__main__':
    main()
