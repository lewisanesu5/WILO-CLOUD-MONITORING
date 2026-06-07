"""
Motor Stall Generator - SUDDEN FAULT
Characteristics:
- Normal baseline current ~15-20A, acceleration ~0.5 m/s²
- Sudden spike: Current jumps to 40-100A (locked rotor)
- Acceleration spikes 300%+ with sustained high vibration
- Audio shriek
- Once triggered, goes to system failure state
"""

import numpy as np
import random
from .base_generator import BaseGenerator


class MotorStallGenerator(BaseGenerator):
    """Generate Motor Stall fault data - sudden catastrophic failure."""
    
    def __init__(self):
        super().__init__('Motor Stall')
        # Random interval between 10-15 inclusive when spike occurs
        self.spike_interval = random.randint(10, 15)
        self.logger.info(f"Spike will occur at interval: {self.spike_interval}")
    
    def generate_acceleration_data(self):
        """Generate acceleration data: normal baseline or sudden spike."""
        timestamps = np.linspace(0, 2, 1400)
        
        if self.system_failure_state:
            # System failure: sustained high vibration or lockup
            base = 3.5
            noise = np.random.normal(0, 0.4, 1400)
            random_spikes = np.random.poisson(2, 1400) * 0.8
            return base + noise + random_spikes
        
        if self.interval_count == self.spike_interval and not self.failure_triggered:
            # SPIKE MOMENT: Sudden surge then sustained high
            self.failure_triggered = True
            self.system_failure_state = True
            self.logger.warning(f"⚡ STALL SPIKE TRIGGERED at interval {self.interval_count}!")
            
            surge = 4.0 * np.exp(-3 * timestamps)  # Initial spike decay
            sustained = 2.5 + np.random.normal(0, 0.3, 1400)
            random_spikes = np.random.poisson(3, 1400) * 0.6
            return surge + sustained + random_spikes
        
        # Normal baseline ± 5% noise
        baseline = 0.5
        noise_amount = baseline * 0.05 * np.random.normal(0, 1, 1400)
        return baseline + noise_amount
    
    def generate_current_data(self):
        """Generate current data: normal baseline or spike to locked rotor current."""
        timestamps = np.linspace(0, 2, 1400)
        
        if self.system_failure_state:
            # System failure: sustained high current
            base = 60.0  # Sustained fault current
            noise = np.random.normal(0, 1.5, 1400)
            return np.clip(base + noise, 40, 120)
        
        if self.interval_count == self.spike_interval and not self.failure_triggered:
            # SPIKE: Locked rotor current (3-6x normal)
            spike_current = 85.0 + np.random.normal(0, 5, 1400)
            return np.clip(spike_current, 70, 150)
        
        # Normal baseline ± 5% noise
        baseline = 18.0
        noise_amount = baseline * 0.05 * np.random.normal(0, 1, 1400)
        return baseline + noise_amount
    
    def generate_audio_data(self):
        """Generate audio data: normal baseline or shriek."""
        timestamps = np.linspace(0, 2, 1400)
        
        if self.system_failure_state:
            # System failure: high-pitched grinding
            base = 95.0  # dB - loud grinding
            noise = np.random.normal(0, 3, 1400)
            high_freq = 5.0 * np.sin(2 * np.pi * 150 * timestamps)
            return base + noise + high_freq
        
        if self.interval_count == self.spike_interval and not self.failure_triggered:
            # SPIKE: Sudden shriek
            shriek = 105.0 + 10 * np.sin(2 * np.pi * 200 * timestamps)
            noise = np.random.normal(0, 2, 1400)
            return shriek + noise
        
        # Normal baseline ± 5% noise
        baseline = 88.0  # dB
        noise_amount = baseline * 0.05 * np.random.normal(0, 1, 1400)
        return baseline + noise_amount


if __name__ == '__main__':
    generator = MotorStallGenerator()
    generator.run_indefinitely()
