"""
Motor Electrical Fault Generator - GRADUAL/HYBRID FAULT
Characteristics:
- Insulation breakdown developing gradually
- Random electrical spikes increase in frequency
- Could be line-to-ground faults or phase imbalance
- Similar to winding failure but with more immediate mechanical effects
- After 15 intervals: catastrophic failure
"""

import numpy as np
import random
from .base_generator import BaseGenerator


class MotorElectricalFaultGenerator(BaseGenerator):
    """Generate Motor Electrical Fault - insulation/phase issues."""
    
    def __init__(self):
        super().__init__('Motor Electrical Fault')
        self.critical_interval = random.randint(10, 15)
        self.logger.info("Electrical fault development: spikes increase with severity")
    
    def get_electrical_severity(self):
        """Return electrical fault severity (0.0 to 1.0)."""
        return min(self.interval_count / self.critical_interval, 1.0)
    
    def get_spike_probability(self):
        """Probability of electrical event per sample."""
        severity = self.get_electrical_severity()
        return 0.005 + (0.08 * severity)  # 0.5% → 8.5% per interval
    
    def generate_acceleration_data(self):
        """Generate vibration with electrical noise modulation."""
        timestamps = np.linspace(0, 2, 1400)
        severity = self.get_electrical_severity()
        
        if self.system_failure_state:
            # System failure: violent electrical shorts causing mechanical shock
            base = 4.5
            electrical_spikes = np.random.poisson(15, 1400) * 1.5
            noise = np.random.normal(0, 1.0, 1400)
            return base + electrical_spikes + noise
        
        # Modulated carrier (120Hz electrical) with growing noise
        carrier = 1.5 * severity * np.sin(2 * np.pi * 120 * timestamps)
        baseline = 0.7 + (1.2 * severity)
        electrical_noise = np.random.normal(0, 0.15 + 0.4 * severity, 1400)
        spike_events = np.random.binomial(1, self.get_spike_probability(), 1400) * np.random.normal(2.5, 0.5, 1400)
        
        data = baseline + carrier + electrical_noise + spike_events
        
        if self.interval_count > self.critical_interval and not self.system_failure_state:
            self.system_failure_state = True
            self.logger.warning(f"⚡ ELECTRICAL FAULT at interval {self.interval_count}!")
        
        return data
    
    def generate_current_data(self):
        """Generate current with increasing electrical fault signature."""
        timestamps = np.linspace(0, 2, 1400)
        severity = self.get_electrical_severity()
        
        if self.system_failure_state:
            # System failure: sustained high fault current
            base = 75.0
            fault_spikes = np.random.poisson(8, 1400) * 20
            noise = np.random.normal(0, 4, 1400)
            return np.clip(base + fault_spikes + noise, 40, 150)
        
        # Phase imbalance / fault current increases
        baseline = 16.0 + (14.0 * severity)
        phase_ripple = 3.0 * severity * np.sin(2 * np.pi * 50 * timestamps)  # Line frequency modulation
        fault_spikes = np.random.binomial(1, self.get_spike_probability() * 3, 1400) * np.random.normal(15, 3, 1400)
        noise = np.random.normal(0, 0.5, 1400)
        
        return np.clip(baseline + phase_ripple + fault_spikes + noise, 5, 100)
    
    def generate_audio_data(self):
        """Generate audio: electrical hum with crackling increasing."""
        timestamps = np.linspace(0, 2, 1400)
        severity = self.get_electrical_severity()
        
        if self.system_failure_state:
            # System failure: loud electrical arc and burn sounds
            base = 104.0
            arcing = 25.0 * np.sin(2 * np.pi * 120 * timestamps)
            crackling = np.random.poisson(20, 1400) * 3
            noise = np.random.normal(0, 5, 1400)
            return base + arcing + crackling + noise
        
        # 120Hz hum (2x line frequency for 50Hz system) with crackling
        base = 88.0 + (7.0 * severity)
        hum = 8.0 * severity * np.sin(2 * np.pi * 120 * timestamps)
        crackling = np.random.poisson(int(2 + 12 * severity), 1400) * (1 + severity)
        noise = np.random.normal(0, 1.5 + 2.5 * severity, 1400)
        return base + hum + crackling + noise


if __name__ == '__main__':
    generator = MotorElectricalFaultGenerator()
    generator.run_indefinitely()
