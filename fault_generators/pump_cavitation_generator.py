"""
Pump Cavitation Generator - SUDDEN FAULT
Characteristics:
- Normal baseline: steady operation
- Sudden spike: Rapid irregular vibrations from bubble collapse
- Distinct audio cavitation noise (popcorn-like)
- Pressure fluctuations
- Once triggered, goes to system failure
"""

import numpy as np
import random
from .base_generator import BaseGenerator


class PumpCavitationGenerator(BaseGenerator):
    """Generate Pump Cavitation fault data - sudden pressure/vibration spike."""
    
    def __init__(self):
        super().__init__('Pump Cavitation')
        self.spike_interval = random.randint(10, 15)
        self.logger.info(f"Cavitation will trigger at interval: {self.spike_interval}")
    
    def generate_acceleration_data(self):
        """Generate acceleration: normal or cavitation spikes."""
        timestamps = np.linspace(0, 2, 1400)
        
        if self.system_failure_state:
            # Post-cavitation: sustained high vibration with erosion
            base = 4.0
            cavitation_spikes = np.random.poisson(8, 1400) * 0.7
            noise = np.random.normal(0, 0.5, 1400)
            return base + cavitation_spikes + noise
        
        if self.interval_count == self.spike_interval and not self.failure_triggered:
            # SPIKE: Rapid cavitation bubbles collapsing
            self.failure_triggered = True
            self.system_failure_state = True
            self.logger.warning(f"💥 CAVITATION SPIKE at interval {self.interval_count}!")
            
            cavitation_spikes = np.random.poisson(15, 1400) * 0.8
            sustained = 2.5 + np.random.normal(0, 0.4, 1400)
            return sustained + cavitation_spikes
        
        # Normal baseline with slight pump ripple
        baseline = 1.5
        pump_ripple = 0.3 * np.sin(2 * np.pi * 8 * timestamps)  # 8Hz pump frequency
        noise = baseline * 0.05 * np.random.normal(0, 1, 1400)
        return baseline + pump_ripple + noise
    
    def generate_current_data(self):
        """Generate current: normal or spike with cavitation load."""
        timestamps = np.linspace(0, 2, 1400)
        
        if self.system_failure_state:
            # Post-cavitation: elevated current from inefficiency
            base = 45.0
            noise = np.random.normal(0, 2, 1400)
            irregular_spikes = np.random.binomial(1, 0.2, 1400) * 15
            return np.clip(base + noise + irregular_spikes, 30, 90)
        
        if self.interval_count == self.spike_interval and not self.failure_triggered:
            # SPIKE: Current surge from cavitation resistance
            spike = 75.0 + np.random.normal(0, 8, 1400)
            return np.clip(spike, 60, 120)
        
        # Normal baseline
        baseline = 22.0
        noise = baseline * 0.05 * np.random.normal(0, 1, 1400)
        return baseline + noise
    
    def generate_audio_data(self):
        """Generate audio: normal or cavitation roar (popcorn-like noise)."""
        timestamps = np.linspace(0, 2, 1400)
        
        if self.system_failure_state:
            # Post-cavitation: roaring cavitation noise
            base = 98.0
            popcorn_noise = np.random.normal(0, 5, 1400)
            high_freq = 8.0 * np.random.normal(0, 1, 1400)
            return base + popcorn_noise + high_freq
        
        if self.interval_count == self.spike_interval and not self.failure_triggered:
            # SPIKE: Sudden cavitation roar
            roar = 105.0 + 12 * np.sin(2 * np.pi * 120 * timestamps)
            popcorn = np.random.poisson(10, 1400) * 3
            return roar + popcorn
        
        # Normal baseline: smooth pump sound
        baseline = 87.0
        noise = baseline * 0.05 * np.random.normal(0, 1, 1400)
        return baseline + noise


if __name__ == '__main__':
    generator = PumpCavitationGenerator()
    generator.run_indefinitely()
