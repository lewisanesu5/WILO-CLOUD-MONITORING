"""
Individual Fault Generator Runner
Run a single fault generator for testing/debugging
Usage: python run_single_generator.py <fault_name>
Example: python run_single_generator.py "Motor Stall"
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fault_generators.motor_stall_generator import MotorStallGenerator
from fault_generators.pump_cavitation_generator import PumpCavitationGenerator
from fault_generators.pump_impeller_damage_generator import PumpImpellerDamageGenerator
from fault_generators.pump_seal_leakage_generator import PumpSealLeakageGenerator
from fault_generators.motor_bearing_failure_generator import MotorBearingFailureGenerator
from fault_generators.motor_shaft_misalignment_generator import MotorShaftMisalignmentGenerator
from fault_generators.motor_overheating_generator import MotorOverheatingGenerator
from fault_generators.motor_winding_failure_generator import MotorWindingFailureGenerator
from fault_generators.motor_vibration_anomaly_generator import MotorVibrationAnomalyGenerator
from fault_generators.motor_electrical_fault_generator import MotorElectricalFaultGenerator
from fault_generators.custom_event_generator import CustomEventGenerator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s'
)

GENERATOR_MAP = {
    'Motor Stall': MotorStallGenerator,
    'Pump Cavitation': PumpCavitationGenerator,
    'Pump Impeller Damage': PumpImpellerDamageGenerator,
    'Pump Seal Leakage': PumpSealLeakageGenerator,
    'Motor Bearing Failure': MotorBearingFailureGenerator,
    'Motor Shaft Misalignment': MotorShaftMisalignmentGenerator,
    'Motor Overheating': MotorOverheatingGenerator,
    'Motor Winding Failure': MotorWindingFailureGenerator,
    'Motor Vibration Anomaly': MotorVibrationAnomalyGenerator,
    'Motor Electrical Fault': MotorElectricalFaultGenerator,
    'Custom Event': CustomEventGenerator,
}


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_single_generator.py <fault_name>")
        print("\nAvailable faults:")
        for fault_name in GENERATOR_MAP.keys():
            print(f"  - {fault_name}")
        sys.exit(1)
    
    fault_name = ' '.join(sys.argv[1:])
    
    if fault_name not in GENERATOR_MAP:
        print(f"Error: Fault '{fault_name}' not found")
        print("\nAvailable faults:")
        for name in GENERATOR_MAP.keys():
            print(f"  - {name}")
        sys.exit(1)
    
    generator_class = GENERATOR_MAP[fault_name]
    print(f"\n{'=' * 60}")
    print(f"Running: {fault_name}")
    print(f"{'=' * 60}\n")
    
    generator = generator_class()
    try:
        generator.run_indefinitely()
    except KeyboardInterrupt:
        print(f"\n\nStopped: {fault_name}")


if __name__ == '__main__':
    main()
