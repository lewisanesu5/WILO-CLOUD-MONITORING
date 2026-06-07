"""
Motor Overheating Generator - GRADUAL FAULT
Characteristics:
- Sustained elevated temperature and vibration
- Thermal expansion increases clearances → more vibration
- Current increases from higher resistance
- Linear degradation over hours/days
- After 15 intervals: reaches critical temperature → system failure
"""

import numpy as np
import random
from .base_generator import BaseGenerator


class MotorOverheatingGenerator(BaseGenerator):
    """Generate Motor Overheating - gradual thermal degradation."""
    
    def __init__(self):
        super().__init__('Motor Overheating')
        self.critical_interval = random.randint(10, 15)
        self.baseline_vibration = 0.6
        self.critical_vibration = 2.2
        self.logger.info("Thermal degradation: linear increase in vibration and current")
    
    def get_thermal_severity(self):
        """Return thermal severity (0.0 to 1.0)."""
        return min(self.interval_count / self.critical_interval, 1.0)
    
    def generate_acceleration_data(self):
        """Generate vibration with thermal expansion effects."""
        timestamps = np.linspace(0, 2, 1400)
        severity = self.get_thermal_severity()
        
        if self.system_failure_state:
            # System failure: winding insulation breakdown causing vibration spikes
            base = 4.2
            thermal_spikes = np.random.poisson(8, 1400) * 0.8
            noise = np.random.normal(0, 0.6, 1400)
            return base + thermal_spikes + noise
        
        # Thermal expansion increases static imbalance and clearance
        base = self.baseline_vibration + (self.critical_vibration * severity)
        thermal_ripple = 0.8 * severity * np.sin(2 * np.pi * 5 * timestamps)  # Slow ripple from thermal cycling
        noise = np.random.normal(0, 0.1 + 0.2 * severity, 1400)
        
        data = base + thermal_ripple + noise
        
        if self.interval_count > self.critical_interval and not self.system_failure_state:
            self.system_failure_state = True
            self.logger.warning(f"🔥 OVERHEATING FAILURE at interval {self.interval_count}!")
        
        return data
    
    def generate_current_data(self):
        """Generate current: increasing from higher winding resistance at temperature."""
        timestamps = np.linspace(0, 2, 1400)
        severity = self.get_thermal_severity()
        
        if self.system_failure_state:
            # System failure: severely elevated current from insulation breakdown
            base = 62.0
            noise = np.random.normal(0, 2, 1400)
            return np.clip(base + noise, 45, 95)
        
        # Resistance increases ~0.4% per °C, leading to more current
        # Linear progression: 18A → 38A
        baseline = 18.0 + (20.0 * severity)
        thermal_variation = 2.0 * severity * np.sin(2 * np.pi * 1 * timestamps)  # Slow thermal cycling
        noise = np.random.normal(0, 0.5, 1400)
        return baseline + thermal_variation + noise
    
    def generate_audio_data(self):
        """Generate audio: thermal stress sounds increasing."""
        timestamps = np.linspace(0, 2, 1400)
        severity = self.get_thermal_severity()
        
        if self.system_failure_state:
            # System failure: loud buzzing from winding shorts
            base = 101.0
            thermal_buzz = 25.0 * np.sin(2 * np.pi * 120 * timestamps)
            sputter = np.random.poisson(6, 1400) * 3
            noise = np.random.normal(0, 3, 1400)
            return base + thermal_buzz + sputter + noise
        
        # Thermal stress: hum increases with temperature
        base = 88.0 + (8.0 * severity)  # 88 → 96 dB
        thermal_hum = 8.0 * severity * np.sin(2 * np.pi * 120 * timestamps)  # 120Hz thermal hum
        noise = np.random.normal(0, 1.5 + 1.5 * severity, 1400)
        return base + thermal_hum + noise


if __name__ == '__main__':
    generator = MotorOverheatingGenerator()
    generator.run_indefinitely()
