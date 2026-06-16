#!/usr/bin/env python
"""
Fault Generator Launcher
Entry point for running fault generators as subprocess
"""
import sys
from fault_generators import (
    MotorStallGenerator,
    MotorBearingFailureGenerator,
    MotorOverheatingGenerator,
    MotorWindingFailureGenerator,
    MotorVibrationAnomalyGenerator,
    MotorElectricalFaultGenerator,
    MotorShaftMisalignmentGenerator,
    PumpCavitationGenerator,
    PumpImpellerDamageGenerator,
    PumpSealLeakageGenerator,
    CustomEventGenerator
)

# Mapping of fault names to generator classes
FAULT_GENERATOR_MAP = {
    'Motor Stall': MotorStallGenerator,
    'Motor Bearing Failure': MotorBearingFailureGenerator,
    'Motor Overheating': MotorOverheatingGenerator,
    'Motor Winding Failure': MotorWindingFailureGenerator,
    'Motor Vibration Anomaly': MotorVibrationAnomalyGenerator,
    'Motor Electrical Fault': MotorElectricalFaultGenerator,
    'Motor Shaft Misalignment': MotorShaftMisalignmentGenerator,
    'Pump Cavitation': PumpCavitationGenerator,
    'Pump Impeller Damage': PumpImpellerDamageGenerator,
    'Pump Seal Leakage': PumpSealLeakageGenerator,
    'Custom Event': CustomEventGenerator,
}

def main():
    if len(sys.argv) < 2:
        print("Usage: python fault_generator_launcher.py <fault_name>")
        print("Available faults:")
        for fault_name in sorted(FAULT_GENERATOR_MAP.keys()):
            print(f"  - {fault_name}")
        sys.exit(1)
    
    fault_name = sys.argv[1]
    
    if fault_name not in FAULT_GENERATOR_MAP:
        print(f"Error: Unknown fault '{fault_name}'")
        print("Available faults:")
        for name in sorted(FAULT_GENERATOR_MAP.keys()):
            print(f"  - {name}")
        sys.exit(1)
    
    # Get the generator class
    GeneratorClass = FAULT_GENERATOR_MAP[fault_name]
    
    # Instantiate and run
    generator = GeneratorClass()
    print(f"Started {fault_name} generator")
    sys.stdout.flush()
    
    try:
        generator.run_indefinitely()
    except KeyboardInterrupt:
        print(f"\n{fault_name} generator interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"Error in {fault_name} generator: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
