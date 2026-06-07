"""
Motor Shaft Misalignment Generator - GRADUAL FAULT
Characteristics:
- Periodic vibration at shaft rotation frequency (2x line frequency)
- Misalignment increases over weeks/months
- 2x frequency energy grows progressively
- Linear increase in kurtosis and RMS
- After 15 intervals: reaches CRITICAL
"""

import numpy as np
import random
from .base_generator import BaseGenerator


class MotorShaftMisalignmentGenerator(BaseGenerator):
    """Generate Motor Shaft Misalignment - gradual angular/parallel shift."""
    
    def __init__(self):
        super().__init__('Motor Shaft Misalignment')
        self.critical_interval = random.randint(10, 15)
        self.baseline_rms = 0.4
        self.critical_rms = 1.8
        self.rms_per_interval = (self.critical_rms - self.baseline_rms) / self.critical_interval
        self.logger.info(f"2x frequency amplitude growth: +{self.rms_per_interval:.3f} per interval")
    
    def get_misalignment_severity(self):
        """Return severity factor (0.0 to 1.0)."""
        return min(self.interval_count / self.critical_interval, 1.0)
    
    def generate_acceleration_data(self):
        """Generate periodic vibration at 2x shaft frequency."""
        timestamps = np.linspace(0, 2, 1400)
        severity = self.get_misalignment_severity()
        
        if self.system_failure_state:
            # System failure: chaotic vibration from complete misalignment
            base = 4.0
            chaos = 3.0 * np.sin(2 * np.pi * 25 * timestamps)
            noise = np.random.normal(0, 0.7, 1400)
            return base + chaos + noise
        
        # 2x line frequency = 2 * 50 Hz = 100 Hz shaft component
        # Motor speed ~730 RPM = 12.17 Hz, so 2x = 24.3 Hz fundamental
        shaft_freq = 24.3  # Hz for 8-pole motor at 50Hz
        two_x_amplitude = 0.3 + (1.5 * severity)  # Grows with misalignment
        
        two_x_component = two_x_amplitude * np.sin(2 * np.pi * shaft_freq * timestamps)
        baseline = 0.5 + (0.4 * severity)
        noise = np.random.normal(0, 0.05 + 0.1 * severity, 1400)
        
        data = baseline + two_x_component + noise
        
        if self.interval_count > self.critical_interval and not self.system_failure_state:
            self.system_failure_state = True
            self.logger.warning(f"🔄 MISALIGNMENT FAILURE at interval {self.interval_count}!")
        
        return data
    
    def generate_current_data(self):
        """Generate current with progressive misalignment load."""
        timestamps = np.linspace(0, 2, 1400)
        severity = self.get_misalignment_severity()
        
        if self.system_failure_state:
            # System failure: high current from mechanical friction
            base = 58.0
            noise = np.random.normal(0, 2, 1400)
            return np.clip(base + noise, 45, 90)
        
        # Misalignment increases mechanical load
        baseline = 16.0 + (15.0 * severity)  # 16A → 31A
        periodic = 3.0 * severity * np.sin(2 * np.pi * 24.3 * timestamps)
        noise = np.random.normal(0, 0.5, 1400)
        return baseline + periodic + noise
    
    def generate_audio_data(self):
        """Generate audio with 2x frequency tone growing louder."""
        timestamps = np.linspace(0, 2, 1400)
        severity = self.get_misalignment_severity()
        
        if self.system_failure_state:
            # System failure: loud thumping and grinding
            base = 99.0
            low_freq_thump = 10.0 * np.sin(2 * np.pi * 24 * timestamps)
            high_freq = 8.0 * np.sin(2 * np.pi * 150 * timestamps)
            noise = np.random.normal(0, 3, 1400)
            return base + low_freq_thump + high_freq + noise
        
        # 2x frequency tone grows with severity
        base = 87.0 + (5.0 * severity)
        two_x_tone = 12.0 * severity * np.sin(2 * np.pi * 48.6 * timestamps)  # 2x * 2
        noise = np.random.normal(0, 1 + 1.5 * severity, 1400)
        return base + two_x_tone + noise


if __name__ == '__main__':
    generator = MotorShaftMisalignmentGenerator()
    generator.run_indefinitely()
