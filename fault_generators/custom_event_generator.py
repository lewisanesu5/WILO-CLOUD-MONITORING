"""
Custom Event Generator
For user-defined events, manual triggers, or testing specific scenarios
Default behavior: Normal operation with optional manual spike injection
"""

import numpy as np
from .base_generator import BaseGenerator


class CustomEventGenerator(BaseGenerator):
    """Generate Custom Event data - flexible for user testing."""
    
    def __init__(self):
        super().__init__('Custom Event')
        self.logger.info("Custom Event generator ready for manual triggers")
    
    def generate_acceleration_data(self):
        """Generate acceleration: normal or user-defined pattern."""
        timestamps = np.linspace(0, 2, 1400)
        
        if self.system_failure_state:
            # Custom failure state: elevated readings
            base = 3.2
            noise = np.random.normal(0, 0.5, 1400)
            spikes = np.random.poisson(4, 1400) * 0.5
            return base + noise + spikes
        
        # Default: normal baseline with slight variations
        baseline = 0.7
        noise = baseline * 0.08 * np.random.normal(0, 1, 1400)
        return baseline + noise
    
    def generate_current_data(self):
        """Generate current: normal or custom pattern."""
        timestamps = np.linspace(0, 2, 1400)
        
        if self.system_failure_state:
            # Custom failure: elevated current
            base = 50.0
            noise = np.random.normal(0, 1.5, 1400)
            return np.clip(base + noise, 35, 85)
        
        # Normal baseline
        baseline = 20.0
        noise = baseline * 0.05 * np.random.normal(0, 1, 1400)
        return baseline + noise
    
    def generate_audio_data(self):
        """Generate audio: normal or custom pattern."""
        timestamps = np.linspace(0, 2, 1400)
        
        if self.system_failure_state:
            # Custom failure: elevated audio
            base = 95.0
            noise = np.random.normal(0, 3, 1400)
            return base + noise
        
        # Normal baseline
        baseline = 85.0
        noise = baseline * 0.05 * np.random.normal(0, 1, 1400)
        return baseline + noise


if __name__ == '__main__':
    generator = CustomEventGenerator()
    generator.run_indefinitely()
