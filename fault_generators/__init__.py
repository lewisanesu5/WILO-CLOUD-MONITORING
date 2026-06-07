"""
Fault Generators Package
Provides fault-specific data generation for predictive maintenance testing
"""

from .base_generator import BaseGenerator
from .motor_stall_generator import MotorStallGenerator
from .pump_cavitation_generator import PumpCavitationGenerator
from .pump_impeller_damage_generator import PumpImpellerDamageGenerator
from .pump_seal_leakage_generator import PumpSealLeakageGenerator
from .motor_bearing_failure_generator import MotorBearingFailureGenerator
from .motor_shaft_misalignment_generator import MotorShaftMisalignmentGenerator
from .motor_overheating_generator import MotorOverheatingGenerator
from .motor_winding_failure_generator import MotorWindingFailureGenerator
from .motor_vibration_anomaly_generator import MotorVibrationAnomalyGenerator
from .motor_electrical_fault_generator import MotorElectricalFaultGenerator
from .custom_event_generator import CustomEventGenerator

__version__ = "1.0.0"
__all__ = [
    'BaseGenerator',
    'MotorStallGenerator',
    'PumpCavitationGenerator',
    'PumpImpellerDamageGenerator',
    'PumpSealLeakageGenerator',
    'MotorBearingFailureGenerator',
    'MotorShaftMisalignmentGenerator',
    'MotorOverheatingGenerator',
    'MotorWindingFailureGenerator',
    'MotorVibrationAnomalyGenerator',
    'MotorElectricalFaultGenerator',
    'CustomEventGenerator',
]
