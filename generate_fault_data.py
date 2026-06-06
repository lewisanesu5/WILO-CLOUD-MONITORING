"""
Generate realistic fault-specific sensor data for each fault type.
Creates 6 CSV files per fault: max_acceleration, min_acceleration, max_current, min_current, max_audio, min_audio
"""

import os
import csv
import numpy as np
from datetime import datetime

# Configuration
FREQUENCY = 700  # Hz
DURATION = 2  # seconds
SAMPLES = FREQUENCY * DURATION  # 1400 readings
SAMPLE_INTERVAL = 1000 / FREQUENCY  # milliseconds between samples

# Define fault types
FAULT_TYPES = [
    'Motor Bearing Failure',
    'Motor Overheating',
    'Motor Winding Failure',
    'Motor Shaft Misalignment',
    'Motor Vibration Anomaly',
    'Motor Stall',
    'Motor Electrical Fault',
    'Pump Seal Leakage',
    'Pump Cavitation',
    'Pump Impeller Damage',
    'Custom Event'
]

class FaultDataGenerator:
    """Generate realistic fault-specific sensor data patterns."""
    
    def __init__(self, fault_type):
        self.fault_type = fault_type
        np.random.seed(hash(fault_type) % 2**32)  # Consistent randomness per fault
        
    def generate_timestamps(self):
        """Generate millisecond timestamps."""
        return [i * SAMPLE_INTERVAL for i in range(SAMPLES)]
    
    # ==================== ACCELERATION DATA ====================
    def generate_acceleration_baseline(self):
        """Normal baseline acceleration (low, steady)."""
        # Small noise around 0.5 m/s²
        baseline = 0.5
        noise = np.random.normal(0, 0.05, SAMPLES)
        return baseline + noise
    
    def generate_acceleration_fault(self):
        """Fault-specific acceleration patterns."""
        t = np.linspace(0, 2, SAMPLES)
        
        if self.fault_type == 'Motor Bearing Failure':
            # Progressive increase with friction-induced spikes
            base = 1.0 + 3.0 * (t / 2)  # Linear increase from 1 to 4
            spikes = np.random.poisson(3, SAMPLES) * np.random.normal(0.5, 0.1, SAMPLES)
            return base + spikes
        
        elif self.fault_type == 'Motor Overheating':
            # Steady high vibration due to thermal expansion/stress
            base = 2.5 + 0.5 * np.sin(2 * np.pi * 5 * t)
            noise = np.random.normal(0, 0.3, SAMPLES)
            return base + noise
        
        elif self.fault_type == 'Motor Winding Failure':
            # Irregular spikes from electrical arcing
            base = 1.5
            spikes = np.random.binomial(1, 0.15, SAMPLES) * np.random.normal(4, 0.5, SAMPLES)
            return base + spikes
        
        elif self.fault_type == 'Motor Shaft Misalignment':
            # Periodic vibration at shaft rotation frequency
            base = 2.0 * (1 + 0.8 * np.sin(2 * np.pi * 12 * t))  # 12Hz shaft rotation
            noise = np.random.normal(0, 0.2, SAMPLES)
            return base + noise
        
        elif self.fault_type == 'Motor Vibration Anomaly':
            # High frequency chaotic vibrations
            base = 3.5 + 1.5 * np.sin(2 * np.pi * 25 * t)
            high_freq = 0.5 * np.sin(2 * np.pi * 180 * t)
            noise = np.random.normal(0, 0.4, SAMPLES)
            return base + high_freq + noise
        
        elif self.fault_type == 'Motor Stall':
            # Initial spike then sustained high vibration
            surge = 4.0 * np.exp(-2 * t) if t[0] < 0.5 else 0
            sustained = 2.0 + 0.3 * np.random.normal(0, 1, SAMPLES)
            spikes = np.zeros(SAMPLES)
            for i in range(SAMPLES):
                if np.random.random() < 0.1:
                    spikes[i] = np.random.normal(3, 0.5)
            return 1.0 + surge + sustained + spikes
        
        elif self.fault_type == 'Motor Electrical Fault':
            # Electrical noise creates high-frequency vibrations
            base = 1.8
            electrical = 2.0 * np.sin(2 * np.pi * 60 * t) * np.sin(2 * np.pi * 150 * t)
            noise = np.random.normal(0, 0.3, SAMPLES)
            return base + electrical + noise
        
        elif self.fault_type == 'Pump Seal Leakage':
            # Slight increase in vibration from internal leakage
            base = 1.2 + 0.8 * (t / 2)
            cavitation = 0.3 * np.random.normal(0, 1, SAMPLES)
            return base + cavitation
        
        elif self.fault_type == 'Pump Cavitation':
            # Rapid irregular vibrations from bubble collapse
            base = 2.0
            cavitation_spikes = np.random.poisson(5, SAMPLES) * 0.4
            return base + cavitation_spikes + np.random.normal(0, 0.2, SAMPLES)
        
        elif self.fault_type == 'Pump Impeller Damage':
            # Periodic imbalance vibrations
            base = 2.2 * (1 + 0.7 * np.sin(2 * np.pi * 8 * t))
            noise = np.random.normal(0, 0.3, SAMPLES)
            return base + noise
        
        else:  # Custom Event
            # Generic elevated values
            base = 2.0 + 0.5 * np.sin(2 * np.pi * 10 * t)
            noise = np.random.normal(0, 0.3, SAMPLES)
            return base + noise
    
    # ==================== CURRENT DATA ====================
    def generate_current_baseline(self):
        """Normal baseline current (steady, lower)."""
        # Typical steady-state current
        baseline = 15.0  # Amperes
        noise = np.random.normal(0, 0.5, SAMPLES)
        return baseline + noise
    
    def generate_current_fault(self):
        """Fault-specific current patterns."""
        t = np.linspace(0, 2, SAMPLES)
        
        if self.fault_type == 'Motor Bearing Failure':
            # Steady increase as friction increases load
            base = 15.0 + 10.0 * (t / 2)
            noise = np.random.normal(0, 0.3, SAMPLES)
            return base + noise
        
        elif self.fault_type == 'Motor Overheating':
            # Sustained elevated current
            base = 25.0 + 2.0 * np.sin(2 * np.pi * 2 * t)
            noise = np.random.normal(0, 0.5, SAMPLES)
            return base + noise
        
        elif self.fault_type == 'Motor Winding Failure':
            # Irregular current spikes from arcing
            base = 20.0
            spikes = np.random.binomial(1, 0.2, SAMPLES) * np.random.normal(15, 2, SAMPLES)
            return base + spikes
        
        elif self.fault_type == 'Motor Shaft Misalignment':
            # Periodic current variation
            base = 18.0 * (1 + 0.3 * np.sin(2 * np.pi * 12 * t))
            noise = np.random.normal(0, 0.5, SAMPLES)
            return base + noise
        
        elif self.fault_type == 'Motor Vibration Anomaly':
            # Moderate increase with noise
            base = 20.0
            noise = np.random.normal(0, 1.0, SAMPLES)
            return base + noise
        
        elif self.fault_type == 'Motor Stall':
            # Dramatic current spike (locked rotor)
            spike_time = 0.5
            stall_current = np.where(t < spike_time, 40.0, 25.0)
            noise = np.random.normal(0, 0.5, SAMPLES)
            return stall_current + noise
        
        elif self.fault_type == 'Motor Electrical Fault':
            # Irregular current spikes and dips
            base = 18.0
            faults = np.random.binomial(1, 0.1, SAMPLES) * np.random.normal(15, 3, SAMPLES)
            return base + faults
        
        elif self.fault_type == 'Pump Seal Leakage':
            # Slight current increase
            base = 16.0 + 3.0 * (t / 2)
            noise = np.random.normal(0, 0.3, SAMPLES)
            return base + noise
        
        elif self.fault_type == 'Pump Cavitation':
            # Irregular current from cavitation activity
            base = 18.0
            cavitation = np.random.poisson(2, SAMPLES) * 2.0
            return base + cavitation
        
        elif self.fault_type == 'Pump Impeller Damage':
            # Periodic current variation
            base = 17.0 * (1 + 0.4 * np.sin(2 * np.pi * 8 * t))
            noise = np.random.normal(0, 0.5, SAMPLES)
            return base + noise
        
        else:  # Custom Event
            # Generic elevated current
            base = 20.0
            noise = np.random.normal(0, 0.5, SAMPLES)
            return base + noise
    
    # ==================== AUDIO/NOISE DATA ====================
    def generate_audio_baseline(self):
        """Normal baseline audio (low noise)."""
        # Low ambient noise
        baseline = 50.0  # dB
        noise = np.random.normal(0, 2.0, SAMPLES)
        return np.maximum(baseline + noise, 40)
    
    def generate_audio_fault(self):
        """Fault-specific audio patterns."""
        t = np.linspace(0, 2, SAMPLES)
        
        if self.fault_type == 'Motor Bearing Failure':
            # Grinding noise that increases with friction
            base = 70.0 + 10.0 * (t / 2)  # Progressive increase
            grinding = 5.0 * np.sin(2 * np.pi * 100 * t)  # Friction frequency
            noise = np.random.normal(0, 2.0, SAMPLES)
            return base + grinding + noise
        
        elif self.fault_type == 'Motor Overheating':
            # Thermal noise and slight hum increase
            base = 60.0 + 5.0 * np.sin(2 * np.pi * 60 * t)  # 60Hz hum
            noise = np.random.normal(0, 3.0, SAMPLES)
            return base + noise
        
        elif self.fault_type == 'Motor Winding Failure':
            # Arcing noise (crackling)
            base = 65.0
            arcing = np.random.poisson(4, SAMPLES) * np.random.normal(5, 1, SAMPLES)
            return base + arcing
        
        elif self.fault_type == 'Motor Shaft Misalignment':
            # Rubbing noise
            base = 62.0 * (1 + 0.3 * np.sin(2 * np.pi * 12 * t))
            noise = np.random.normal(0, 2.0, SAMPLES)
            return base + noise
        
        elif self.fault_type == 'Motor Vibration Anomaly':
            # High-pitched vibration noise
            base = 70.0
            high_freq = 10.0 * np.sin(2 * np.pi * 200 * t)
            noise = np.random.normal(0, 3.0, SAMPLES)
            return base + high_freq + noise
        
        elif self.fault_type == 'Motor Stall':
            # Loud hum with noise bursts
            hum = 15.0 * np.sin(2 * np.pi * 60 * t)
            bursts = np.random.poisson(2, SAMPLES) * 8.0
            return 75.0 + hum + bursts
        
        elif self.fault_type == 'Motor Electrical Fault':
            # Buzzing and crackling
            base = 68.0
            buzzing = 5.0 * np.sin(2 * np.pi * 120 * t)  # 120Hz buzzing
            crackling = np.random.binomial(1, 0.2, SAMPLES) * np.random.normal(8, 1, SAMPLES)
            return base + buzzing + crackling
        
        elif self.fault_type == 'Pump Seal Leakage':
            # Leakage noise (whistling/hissing)
            base = 58.0 + 3.0 * (t / 2)
            hissing = 3.0 * np.random.normal(0, 1, SAMPLES)
            return base + hissing
        
        elif self.fault_type == 'Pump Cavitation':
            # Very distinctive cavitation noise (rapid crackling)
            base = 75.0  # Cavitation is loud
            cavitation_spikes = np.random.poisson(10, SAMPLES) * np.random.normal(2, 0.5, SAMPLES)
            return base + cavitation_spikes
        
        elif self.fault_type == 'Pump Impeller Damage':
            # Irregular thumping/knocking
            base = 63.0 * (1 + 0.4 * np.sin(2 * np.pi * 8 * t))
            knocking = np.random.binomial(1, 0.15, SAMPLES) * np.random.normal(6, 1, SAMPLES)
            return base + knocking
        
        else:  # Custom Event
            # Generic elevated noise
            base = 65.0
            noise = np.random.normal(0, 3.0, SAMPLES)
            return base + noise
    
    def save_csv(self, filename, timestamps, values):
        """Save data to CSV file."""
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'value'])
            for ts, val in zip(timestamps, values):
                writer.writerow([f'{ts:.2f}', f'{max(0, val):.4f}'])
    
    def generate_all_files(self, fault_dir):
        """Generate all 6 CSV files for this fault type."""
        timestamps = self.generate_timestamps()
        
        files_created = []
        
        # Acceleration files
        acc_baseline = self.generate_acceleration_baseline()
        acc_fault = self.generate_acceleration_fault()
        
        acc_min_path = os.path.join(fault_dir, 'min_acceleration.csv')
        acc_max_path = os.path.join(fault_dir, 'max_acceleration.csv')
        
        self.save_csv(acc_min_path, timestamps, acc_baseline)
        self.save_csv(acc_max_path, timestamps, acc_fault)
        files_created.append('min_acceleration.csv')
        files_created.append('max_acceleration.csv')
        
        # Current files
        cur_baseline = self.generate_current_baseline()
        cur_fault = self.generate_current_fault()
        
        cur_min_path = os.path.join(fault_dir, 'min_current.csv')
        cur_max_path = os.path.join(fault_dir, 'max_current.csv')
        
        self.save_csv(cur_min_path, timestamps, cur_baseline)
        self.save_csv(cur_max_path, timestamps, cur_fault)
        files_created.append('min_current.csv')
        files_created.append('max_current.csv')
        
        # Audio files
        aud_baseline = self.generate_audio_baseline()
        aud_fault = self.generate_audio_fault()
        
        aud_min_path = os.path.join(fault_dir, 'min_audio.csv')
        aud_max_path = os.path.join(fault_dir, 'max_audio.csv')
        
        self.save_csv(aud_min_path, timestamps, aud_baseline)
        self.save_csv(aud_max_path, timestamps, aud_fault)
        files_created.append('min_audio.csv')
        files_created.append('max_audio.csv')
        
        return files_created

def generate_all_fault_data():
    """Generate sensor data for all fault types."""
    data_dir = 'Data'
    
    print("=" * 70)
    print("GENERATING FAULT-SPECIFIC SENSOR DATA")
    print("=" * 70)
    print(f"Configuration:")
    print(f"  Frequency: {FREQUENCY} Hz")
    print(f"  Duration: {DURATION} seconds")
    print(f"  Samples per file: {SAMPLES}")
    print(f"  Sample interval: {SAMPLE_INTERVAL:.2f} ms")
    print("=" * 70)
    
    total_files = 0
    
    for fault_type in FAULT_TYPES:
        fault_dir = os.path.join(data_dir, fault_type)
        
        if not os.path.exists(fault_dir):
            print(f"⚠️  Skipping {fault_type} - directory not found")
            continue
        
        print(f"\n📊 Generating data for: {fault_type}")
        
        generator = FaultDataGenerator(fault_type)
        files = generator.generate_all_files(fault_dir)
        
        for file in files:
            print(f"   ✓ {file}")
        
        total_files += len(files)
    
    print("\n" + "=" * 70)
    print(f"✅ Complete! Generated {total_files} CSV files")
    print(f"   ({total_files // 6} fault types × 6 files each)")
    print("=" * 70)

if __name__ == '__main__':
    generate_all_fault_data()
