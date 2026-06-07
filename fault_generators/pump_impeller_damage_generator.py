"""
Pump Impeller Damage Generator - SUDDEN FAULT
Characteristics:
- Normal: Balanced impeller, smooth vibration
- Sudden damage: Unbalanced rotating parts, bearing pulse frequency (BPF) spike
- Immediate surge in acceleration and current
- Grinding audio signature
"""

import numpy as np
import random
from .base_generator import BaseGenerator


class PumpImpellerDamageGenerator(BaseGenerator):
    """Generate Pump Impeller Damage - sudden mechanical imbalance."""
    
    def __init__(self):
        super().__init__('Pump Impeller Damage')
        self.spike_interval = random.randint(10, 15)
        self.logger.info(f"Impeller damage will occur at interval: {self.spike_interval}")
    
    def generate_acceleration_data(self):
        """Generate acceleration: balanced or damaged impeller patterns."""
        timestamps = np.linspace(0, 2, 1400)
        
        if self.system_failure_state:
            # Post-damage: sustained imbalance and bearing wear
            base = 3.8
            imbalance = 1.2 * np.sin(2 * np.pi * 9 * timestamps)  # BPF
            noise = np.random.normal(0, 0.5, 1400)
            grinding = np.random.poisson(4, 1400) * 0.6
            return base + imbalance + noise + grinding
        
        if self.interval_count == self.spike_interval and not self.failure_triggered:
            # SPIKE: Sudden imbalance
            self.failure_triggered = True
            self.system_failure_state = True
            self.logger.warning(f"⚙️ IMPELLER DAMAGE at interval {self.interval_count}!")
            
            imbalance_surge = 2.5 * np.sin(2 * np.pi * 9 * timestamps)
            impact = 3.0 * np.exp(-4 * timestamps)
            noise = np.random.normal(0, 0.3, 1400)
            return imbalance_surge + impact + noise
        
        # Normal: smooth with slight pump frequency ripple
        baseline = 1.2
        pump_ripple = 0.2 * np.sin(2 * np.pi * 8 * timestamps)
        noise = baseline * 0.05 * np.random.normal(0, 1, 1400)
        return baseline + pump_ripple + noise
    
    def generate_current_data(self):
        """Generate current: normal or damaged impeller draw."""
        timestamps = np.linspace(0, 2, 1400)
        
        if self.system_failure_state:
            # Post-damage: increased current from friction
            base = 48.0
            imbalance = 8.0 * np.sin(2 * np.pi * 9 * timestamps)
            noise = np.random.normal(0, 1.5, 1400)
            return np.clip(base + imbalance + noise, 35, 85)
        
        if self.interval_count == self.spike_interval and not self.failure_triggered:
            # SPIKE: Sudden load surge
            surge = 72.0 + np.random.normal(0, 6, 1400)
            return np.clip(surge, 55, 110)
        
        # Normal baseline
        baseline = 20.0
        noise = baseline * 0.05 * np.random.normal(0, 1, 1400)
        return baseline + noise
    
    def generate_audio_data(self):
        """Generate audio: smooth pump or grinding damage signature."""
        timestamps = np.linspace(0, 2, 1400)
        
        if self.system_failure_state:
            # Post-damage: grinding and whining
            base = 96.0
            grinding = 15.0 * np.sin(2 * np.pi * 120 * timestamps)
            whine = 8.0 * np.sin(2 * np.pi * 240 * timestamps)
            noise = np.random.normal(0, 3, 1400)
            return base + grinding + whine + noise
        
        if self.interval_count == self.spike_interval and not self.failure_triggered:
            # SPIKE: Sudden grinding noise
            crunch = 102.0 + 15 * np.sin(2 * np.pi * 150 * timestamps)
            impact_noise = np.random.poisson(8, 1400) * 2
            return crunch + impact_noise
        
        # Normal: smooth pump hum
        baseline = 86.0
        noise = baseline * 0.05 * np.random.normal(0, 1, 1400)
        return baseline + noise


if __name__ == '__main__':
    generator = PumpImpellerDamageGenerator()
    generator.run_indefinitely()
