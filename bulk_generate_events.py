#!/usr/bin/env python3
"""
Bulk Event Generator Runner
Runs each of the 11 fault generators 50 times in a fast sequential loop
to generate ML training data and events in the database.
"""

import sys
import os
import time
import logging
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import generator classes
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

# Temporarily disable standard logs to prevent stdout flooding
logging.getLogger().setLevel(logging.WARNING)

# Quiet down other chatty loggers
for logger_name in ['Generator-Motor Stall', 'Generator-Pump Cavitation', 
                    'Generator-Pump Impeller Damage', 'Generator-Pump Seal Leakage',
                    'Generator-Motor Bearing Failure', 'Generator-Motor Shaft Misalignment',
                    'Generator-Motor Overheating', 'Generator-Motor Winding Failure',
                    'Generator-Motor Vibration Anomaly', 'Generator-Motor Electrical Fault',
                    'Generator-Custom Event', 'database', 'event_manager']:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# Patch base generator's interval to 0 so it generates data at maximum speed
import fault_generators.base_generator as bg
bg.GENERATION_INTERVAL = 0

FAULT_GENERATORS = [
    ('Motor Stall', MotorStallGenerator),
    ('Pump Cavitation', PumpCavitationGenerator),
    ('Pump Impeller Damage', PumpImpellerDamageGenerator),
    ('Pump Seal Leakage', PumpSealLeakageGenerator),
    ('Motor Bearing Failure', MotorBearingFailureGenerator),
    ('Motor Shaft Misalignment', MotorShaftMisalignmentGenerator),
    ('Motor Overheating', MotorOverheatingGenerator),
    ('Motor Winding Failure', MotorWindingFailureGenerator),
    ('Motor Vibration Anomaly', MotorVibrationAnomalyGenerator),
    ('Motor Electrical Fault', MotorElectricalFaultGenerator),
    ('Custom Event', CustomEventGenerator),
]

def main():
    # Enable global database connection reuse to speed up bulk execution
    os.environ['REUSE_CONNECTION'] = 'true'

    print("=" * 80)
    print("                 WILO CLOUD MONITORING - BULK EVENT GENERATOR")
    print("=" * 80)
    print("  This script will run each of the 11 fault generators 50 times.")
    print("  - Disabling sleep interval (fast mode: 0s delay)")
    print("  - Disabling verbose stdout logs for speed and readability")
    print("  - Reusing database connection (high-speed pooling)")
    print("  - Each run automatically creates a corresponding database event")
    print("=" * 80)
    
    total_runs = len(FAULT_GENERATORS) * 50
    run_counter = 0
    start_time = time.time()
    
    try:
        for fault_name, generator_class in FAULT_GENERATORS:
            print(f"\n🚀 Starting sequence for fault: {fault_name}")
            
            for iteration in range(1, 51):
                run_counter += 1
                iter_start = time.time()
                
                # Instantiate and run the generator
                generator = generator_class()
                generator.run_indefinitely()
                
                elapsed = time.time() - iter_start
                pct = (run_counter / total_runs) * 100
                print(f"  [{run_counter:03d}/{total_runs:03d}] {fault_name:<30} | Run {iteration:02d}/50 complete ({elapsed:.2f}s) | Progress: {pct:.1f}%")
                sys.stdout.flush()
                
    except KeyboardInterrupt:
        print("\n\n⚠️ Execution stopped by user.")
    except Exception as e:
        print(f"\n❌ Error during bulk run: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up global database connection if active
        try:
            import database
            if database._GLOBAL_CONN is not None:
                if hasattr(database._GLOBAL_CONN, 'real_close'):
                    database._GLOBAL_CONN.real_close()
                else:
                    database._GLOBAL_CONN.close()
                print("\n✓ Closed shared database connection.")
        except Exception as e:
            print(f"\n⚠️ Warning during connection cleanup: {e}")
        
    total_elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(" BULK GENERATION SUMMARY")
    print("=" * 80)
    print(f"  Completed runs: {run_counter}/{total_runs}")
    print(f"  Total time:     {total_elapsed/60:.2f} minutes")
    print(f"  Average speed:  {total_elapsed/max(1, run_counter):.2f} seconds per run")
    print("=" * 80)

if __name__ == '__main__':
    main()
