"""
Pump Seal Leakage Generator - SUDDEN FAULT
Characteristics:
- Normal: Stable operation
- Failure point: Seal rupture → sudden pressure drop + vibration surge
- Mechanical failure with immediate consequences
- Sustained high vibration post-failure
"""

import numpy as np
import random
from .base_generator import BaseGenerator


class PumpSealLeakageGenerator(BaseGenerator):
    """Generate Pump Seal Leakage - sudden mechanical seal failure."""
    
    def __init__(self):
        super().__init__('Pump Seal Leakage')
        self.spike_interval = random.randint(10, 15)
        self.logger.info(f"Seal leakage will occur at interval: {self.spike_interval}")
    
    def generate_acceleration_data(self):
        """Generate acceleration: stable or post-seal-rupture."""
        timestamps = np.linspace(0, 2, 1400)
        
        if self.system_failure_state:
            # Post-rupture: high cavitation vibration from fluid loss
            base = 3.2
            cavitation_spikes = np.random.poisson(6, 1400) * 0.6
            noise = np.random.normal(0, 0.4, 1400)
            return base + cavitation_spikes + noise
        
        if self.interval_count == self.spike_interval and not self.failure_triggered:
            # SPIKE: Seal rupture + pressure loss
            self.failure_triggered = True
            self.system_failure_state = True
            self.logger.warning(f"🔧 SEAL LEAKAGE at interval {self.interval_count}!")
            
            rupture_surge = 2.8 * np.exp(-3 * timestamps)
            sustained_cavitation = 2.0 + np.random.normal(0, 0.3, 1400)
            spikes = np.random.poisson(8, 1400) * 0.4
            return rupture_surge + sustained_cavitation + spikes
        
        # Normal: very stable operation
        baseline = 0.9
        noise = baseline * 0.05 * np.random.normal(0, 1, 1400)
        return baseline + noise
    
    def generate_current_data(self):
        """Generate current: normal or post-seal-failure."""
        timestamps = np.linspace(0, 2, 1400)
        
        if self.system_failure_state:
            # Post-rupture: Current increases from cavitation work
            base = 42.0
            cavitation_load = 6.0 * np.sin(2 * np.pi * 5 * timestamps)
            noise = np.random.normal(0, 1.5, 1400)
            return np.clip(base + cavitation_load + noise, 30, 75)
        
        if self.interval_count == self.spike_interval and not self.failure_triggered:
            # SPIKE: Pressure drop surge
            surge = 68.0 + np.random.normal(0, 5, 1400)
            return np.clip(surge, 50, 100)
        
        # Normal: steady baseline
        baseline = 19.0
        noise = baseline * 0.05 * np.random.normal(0, 1, 1400)
        return baseline + noise
    
    def generate_audio_data(self):
        """Generate audio: quiet operation or seal rupture cavitation roar."""
        timestamps = np.linspace(0, 2, 1400)
        
        if self.system_failure_state:
            # Post-rupture: cavitation roar from fluid vaporization
            base = 94.0
            cavitation = 10.0 * np.sin(2 * np.pi * 100 * timestamps)
            sputter = np.random.poisson(5, 1400) * 2
            noise = np.random.normal(0, 2, 1400)
            return base + cavitation + sputter + noise
        
        if self.interval_count == self.spike_interval and not self.failure_triggered:
            # SPIKE: Rupture sound + immediate cavitation
            rupture_noise = 101.0 + 8 * np.sin(2 * np.pi * 180 * timestamps)
            cavitation_sputter = np.random.poisson(10, 1400)
            return rupture_noise + cavitation_sputter
        
        # Normal: quiet operation
        baseline = 84.0
        noise = baseline * 0.05 * np.random.normal(0, 1, 1400)
        return baseline + noise


if __name__ == '__main__':
    generator = PumpSealLeakageGenerator()
    generator.run_indefinitely()
