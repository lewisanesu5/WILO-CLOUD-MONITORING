"""
Motor Winding Failure Generator - GRADUAL FAULT
Characteristics:
- Insulation degradation over extended period (years in reality)
- Gradually increasing partial discharge activity
- Electrical spikes and arcing increase
- RMS and kurtosis slowly increase
- Compressed to 15 intervals for testing
"""

import numpy as np
import random
from .base_generator import BaseGenerator


class MotorWindingFailureGenerator(BaseGenerator):
    """Generate Motor Winding Failure - extremely gradual insulation breakdown."""
    
    def __init__(self):
        super().__init__('Motor Winding Failure')
        self.critical_interval = random.randint(10, 15)
        self.logger.info("Winding insulation degradation (compressed from years to 15 intervals)")
    
    def get_insulation_degradation(self):
        """Return insulation health (1.0 = new, 0.0 = failed)."""
        return max(1.0 - (self.interval_count / self.critical_interval), 0.0)
    
    def get_arc_probability(self):
        """Probability of electrical arc event per sample."""
        severity = 1.0 - self.get_insulation_degradation()
        return 0.001 + (0.05 * severity)  # 0.1% → 5% per interval
    
    def generate_acceleration_data(self):
        """Generate acceleration with electrical noise signature."""
        timestamps = np.linspace(0, 2, 1400)
        severity = 1.0 - self.get_insulation_degradation()
        
        if self.system_failure_state:
            # System failure: violent electrical discharge
            base = 3.8
            arcs = np.random.poisson(12, 1400) * 1.2
            electrical_noise = np.random.normal(0, 1.0, 1400)
            return base + arcs + electrical_noise
        
        # Electrical noise increases with insulation degradation
        baseline = 0.8 + (1.5 * severity)
        arc_spikes = np.random.binomial(1, self.get_arc_probability(), 1400) * np.random.normal(3, 0.5, 1400)
        electrical_signal = 1.0 * severity * np.sin(2 * np.pi * 150 * timestamps)  # 150Hz carrier
        noise = np.random.normal(0, 0.1 + 0.3 * severity, 1400)
        
        data = baseline + arc_spikes + electrical_signal + noise
        
        if self.interval_count > self.critical_interval and not self.system_failure_state:
            self.system_failure_state = True
            self.logger.warning(f"⚡ WINDING FAILURE at interval {self.interval_count}!")
        
        return data
    
    def generate_current_data(self):
        """Generate current with increasing arcing current spikes."""
        timestamps = np.linspace(0, 2, 1400)
        severity = 1.0 - self.get_insulation_degradation()
        
        if self.system_failure_state:
            # System failure: sustained high current from phase-to-ground short
            base = 70.0
            noise = np.random.normal(0, 3, 1400)
            return np.clip(base + noise, 50, 120)
        
        # Arc events cause current spikes
        baseline = 17.0 + (12.0 * severity)
        arc_current_spikes = np.random.binomial(1, self.get_arc_probability() * 5, 1400) * np.random.normal(20, 3, 1400)
        noise = np.random.normal(0, 0.3, 1400)
        return np.clip(baseline + arc_current_spikes + noise, 5, 100)
    
    def generate_audio_data(self):
        """Generate audio with electrical discharge crackling."""
        timestamps = np.linspace(0, 2, 1400)
        severity = 1.0 - self.get_insulation_degradation()
        
        if self.system_failure_state:
            # System failure: loud electrical arcing and burning
            base = 102.0
            arcing = 20.0 * np.sin(2 * np.pi * 200 * timestamps)
            crackling = np.random.poisson(15, 1400) * 4
            noise = np.random.normal(0, 4, 1400)
            return base + arcing + crackling + noise
        
        # Partial discharge crackling increases with degradation
        base = 87.0 + (6.0 * severity)
        crackle_events = np.random.poisson(int(1 + 10 * severity), 1400) * 2
        electrical_noise = 5.0 * severity * np.sin(2 * np.pi * 200 * timestamps)
        noise = np.random.normal(0, 1 + 2 * severity, 1400)
        return base + crackle_events + electrical_noise + noise


if __name__ == '__main__':
    generator = MotorWindingFailureGenerator()
    generator.run_indefinitely()
