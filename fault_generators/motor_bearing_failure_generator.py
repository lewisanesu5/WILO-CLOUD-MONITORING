"""
Motor Bearing Failure Generator - GRADUAL FAULT
Characteristics:
- Progressive kurtosis and RMS increase over weeks/months
- Friction increases as bearing degrades
- Linear increase in vibration (spikes become more frequent)
- Current gradually increases
- After 15 intervals: reaches CRITICAL and goes to system failure
"""

import numpy as np
import random
from .base_generator import BaseGenerator


class MotorBearingFailureGenerator(BaseGenerator):
    """Generate Motor Bearing Failure - gradual degradation."""
    
    def __init__(self):
        super().__init__('Motor Bearing Failure')
        self.critical_interval = random.randint(10, 15)
        # Normal RMS ~0.5, Target critical RMS ~2.0 over 15 intervals
        self.baseline_rms = 0.5
        self.critical_rms = 2.0
        self.rms_per_interval = (self.critical_rms - self.baseline_rms) / self.critical_interval
        self.logger.info(f"Linear progression: RMS +{self.rms_per_interval:.3f} per interval")
        self.logger.info(f"Critical failure at interval {self.critical_interval}")
    
    def get_current_rms(self):
        """Calculate RMS for current interval (linear progression)."""
        return self.baseline_rms + (self.rms_per_interval * self.interval_count)
    
    def get_current_acceleration_baseline(self):
        """Get baseline acceleration for this interval."""
        progress = min(self.interval_count / self.critical_interval, 1.0)
        return 0.5 + (2.5 * progress)  # 0.5 → 3.0 m/s² over 15 intervals
    
    def get_current_current_baseline(self):
        """Get baseline current for this interval."""
        progress = min(self.interval_count / self.critical_interval, 1.0)
        return 15.0 + (20.0 * progress)  # 15A → 35A over 15 intervals
    
    def generate_acceleration_data(self):
        """Generate acceleration with progressive bearing wear friction."""
        timestamps = np.linspace(0, 2, 1400)
        
        if self.system_failure_state:
            # System failure: extreme vibration from catastrophic bearing seizure
            base = 4.5
            spikes = np.random.poisson(10, 1400) * 1.0
            noise = np.random.normal(0, 0.8, 1400)
            return base + spikes + noise
        
        # Progressive degradation: linear increase in friction spikes
        progress = self.interval_count / self.critical_interval
        base = self.get_current_acceleration_baseline()
        
        # As bearing degrades, friction spikes increase
        spike_frequency = int(3 + 10 * progress)  # 3 → 13 spikes over 15 intervals
        spikes = np.random.poisson(spike_frequency, 1400) * (0.2 + 0.5 * progress)
        
        noise = np.random.normal(0, 0.05 + 0.2 * progress, 1400)
        
        data = base + spikes + noise
        
        # Trigger system failure at interval 15+
        if self.interval_count > self.critical_interval and not self.system_failure_state:
            self.system_failure_state = True
            self.logger.warning(f"🔥 BEARING FAILURE at interval {self.interval_count}!")
        
        return data
    
    def generate_current_data(self):
        """Generate current with linear increase from friction load."""
        timestamps = np.linspace(0, 2, 1400)
        
        if self.system_failure_state:
            # System failure: sustained maximum current from locked bearing
            base = 65.0
            noise = np.random.normal(0, 2, 1400)
            return np.clip(base + noise, 50, 100)
        
        # Linear progression: friction increases current draw
        base = self.get_current_current_baseline()
        noise = base * 0.05 * np.random.normal(0, 1, 1400)
        return base + noise
    
    def generate_audio_data(self):
        """Generate audio: gradually increasing grinding/squealing."""
        timestamps = np.linspace(0, 2, 1400)
        
        if self.system_failure_state:
            # System failure: loud grinding
            base = 100.0
            grinding = 20.0 * np.sin(2 * np.pi * 100 * timestamps)
            noise = np.random.normal(0, 4, 1400)
            return base + grinding + noise
        
        # Progressive: baseline + increasing friction sounds
        progress = self.interval_count / self.critical_interval
        base = 88.0 + (8 * progress)  # 88 → 96 dB
        friction_sound = 5.0 * progress * np.sin(2 * np.pi * 80 * timestamps)
        noise = np.random.normal(0, 1 + 2 * progress, 1400)
        return base + friction_sound + noise


if __name__ == '__main__':
    generator = MotorBearingFailureGenerator()
    generator.run_indefinitely()
