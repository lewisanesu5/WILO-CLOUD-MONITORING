"""
Motor Vibration Anomaly Generator - GRADUAL FAULT
Characteristics:
- Gradual increase in random high-frequency vibrations
- Could be imbalance, looseness, or friction developing
- Energy and std_dev increase linearly
- RMS gradually increases
- After 15 intervals: reaches CRITICAL
"""

import numpy as np
import random
from .base_generator import BaseGenerator


class MotorVibrationAnomalyGenerator(BaseGenerator):
    """Generate Motor Vibration Anomaly - gradual looseness/imbalance."""
    
    def __init__(self):
        super().__init__('Motor Vibration Anomaly')
        self.critical_interval = random.randint(10, 15)
        self.baseline_rms = 0.6
        self.critical_rms = 2.5
        self.logger.info("Anomalous vibration growth: chaotic high-frequency energy")
    
    def get_anomaly_severity(self):
        """Return severity (0.0 to 1.0)."""
        return min(self.interval_count / self.critical_interval, 1.0)
    
    def generate_acceleration_data(self):
        """Generate chaotic high-frequency vibrations."""
        timestamps = np.linspace(0, 2, 1400)
        severity = self.get_anomaly_severity()
        
        if self.system_failure_state:
            # System failure: violent chaotic motion
            base = 5.0
            chaos_freq1 = 2.5 * np.sin(2 * np.pi * 180 * timestamps)
            chaos_freq2 = 1.8 * np.sin(2 * np.pi * 250 * timestamps)
            noise = np.random.normal(0, 1.2, 1400)
            return base + chaos_freq1 + chaos_freq2 + noise
        
        # Multiple frequency components increase with severity
        base = 0.8 + (1.8 * severity)
        freq1 = 1.0 * severity * np.sin(2 * np.pi * 150 * timestamps)
        freq2 = 0.8 * severity * np.sin(2 * np.pi * 220 * timestamps)
        random_spikes = np.random.normal(0, 0.3 + 0.7 * severity, 1400)
        
        data = base + freq1 + freq2 + random_spikes
        
        if self.interval_count > self.critical_interval and not self.system_failure_state:
            self.system_failure_state = True
            self.logger.warning(f"📈 VIBRATION ANOMALY FAILURE at interval {self.interval_count}!")
        
        return data
    
    def generate_current_data(self):
        """Generate current with increasing random variations."""
        timestamps = np.linspace(0, 2, 1400)
        severity = self.get_anomaly_severity()
        
        if self.system_failure_state:
            # System failure: severe current spikes from friction/binding
            base = 56.0
            chaos = 15.0 * np.random.normal(0, 1, 1400)
            return np.clip(base + chaos, 30, 100)
        
        # Anomaly increases current draw
        baseline = 18.0 + (18.0 * severity)  # 18A → 36A
        random_variation = 8.0 * severity * np.random.normal(0, 1, 1400)
        noise = np.random.normal(0, 0.5, 1400)
        return np.clip(baseline + random_variation + noise, 5, 80)
    
    def generate_audio_data(self):
        """Generate audio: high-frequency noise increasing."""
        timestamps = np.linspace(0, 2, 1400)
        severity = self.get_anomaly_severity()
        
        if self.system_failure_state:
            # System failure: loud broadband noise
            base = 103.0
            hf_noise = np.random.normal(0, 8, 1400)
            freq1 = 15.0 * np.sin(2 * np.pi * 300 * timestamps)
            freq2 = 12.0 * np.sin(2 * np.pi * 400 * timestamps)
            return base + hf_noise + freq1 + freq2
        
        # High-frequency noise gradually increases
        base = 87.0 + (8.0 * severity)
        hf_noise = np.random.normal(0, 2 + 4 * severity, 1400)
        high_freq = 10.0 * severity * np.sin(2 * np.pi * 250 * timestamps)
        return base + hf_noise + high_freq


if __name__ == '__main__':
    generator = MotorVibrationAnomalyGenerator()
    generator.run_indefinitely()
