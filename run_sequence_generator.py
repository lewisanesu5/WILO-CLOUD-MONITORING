"""
WILO Cloud Monitoring - Sequential Fault Generator Runner
Runs each fault generator one-by-one (1-15 interval range) with automatic cycling
Perfect for plotting and fault detection within defined interval ranges

Usage:
  python run_sequence_generator.py                           # Interactive CLI
  python run_sequence_generator.py --fault "Motor Stall"     # Run specific fault
"""

import sys
import shutil
import logging
import time
import json
import os
import argparse
from pathlib import Path

# Add parent directory to path for imports
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
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fault_generators_sequence.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Status file for frontend communication
STATUS_FILE = os.path.join(os.path.dirname(__file__), '.sequential_runner_status.json')

def write_status(fault_name, fault_number, total_faults, cycles, status_message):
    """Write status update to JSON file for frontend polling."""
    try:
        status = {
            'active': True,
            'status': 'running',
            'current_fault': fault_name,
            'current_fault_number': fault_number,
            'total_faults': total_faults,
            'cycles': cycles,
            'last_log': status_message,
            'timestamp': time.time()
        }
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f)
    except Exception as e:
        logger.error(f"Error writing status file: {e}")

# Fault configurations
FAULT_SEQUENCE = [
    ('Motor Stall', MotorStallGenerator, 'SUDDEN'),
    ('Pump Cavitation', PumpCavitationGenerator, 'SUDDEN'),
    ('Pump Impeller Damage', PumpImpellerDamageGenerator, 'SUDDEN'),
    ('Pump Seal Leakage', PumpSealLeakageGenerator, 'SUDDEN'),
    ('Motor Bearing Failure', MotorBearingFailureGenerator, 'GRADUAL'),
    ('Motor Shaft Misalignment', MotorShaftMisalignmentGenerator, 'GRADUAL'),
    ('Motor Overheating', MotorOverheatingGenerator, 'GRADUAL'),
    ('Motor Winding Failure', MotorWindingFailureGenerator, 'GRADUAL'),
    ('Motor Vibration Anomaly', MotorVibrationAnomalyGenerator, 'GRADUAL'),
    ('Motor Electrical Fault', MotorElectricalFaultGenerator, 'GRADUAL'),
    ('Custom Event', CustomEventGenerator, 'CUSTOM'),
]

INTERVAL_RANGE = (1, 15)  # Plot intervals 1-15 for each fault
INTER_FAULT_DELAY = 5  # Seconds between fault completions


def display_welcome():
    """Display welcome message."""
    print("\n" + "=" * 100)
    print(" " * 20 + "WILO CLOUD MONITORING - SEQUENTIAL FAULT RUNNER")
    print("=" * 100)
    print("\n📊 OPERATION MODE: Sequential (One Fault After Another)")
    print("✓ Each fault will run within interval range 1-15")
    print("✓ Fault detection happens between intervals 5-16/15")
    print("✓ After each fault completes, the next fault will START FROM INTERVAL 1")
    print("✓ Plots will reset and display only current fault data (1-15 range)")
    print(f"✓ {len(FAULT_SEQUENCE)} faults configured for sequential testing")
    print("\nFault Sequence:")
    for i, (name, _, fault_type) in enumerate(FAULT_SEQUENCE, 1):
        print(f"  {i:2d}. {name:<35} ({fault_type})")
    print("\n" + "=" * 100)


def clear_fault_data(fault_name):
    """Clear all previous data for the fault - start completely fresh."""
    try:
        # Clear Data/<fault_name> directory
        data_dir = Path('Data') / fault_name
        if data_dir.exists():
            shutil.rmtree(data_dir)
            
        # Clear Events/<fault_name> directory
        events_dir = Path('Events') / fault_name
        if events_dir.exists():
            shutil.rmtree(events_dir)
        
        # Recreate empty directories
        data_dir.mkdir(parents=True, exist_ok=True)
        events_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"✓ Cleared all data for '{fault_name}' - starting fresh")
        
    except Exception as e:
        logger.warning(f"Warning during data cleanup for {fault_name}: {e}")


def run_fault_in_sequence(fault_name, generator_class, fault_type, fault_number, total_faults):
    """Run a single fault generator in sequential mode."""
    try:
        logger.info("=" * 100)
        logger.info(f"[FAULT {fault_number}/{total_faults}] Starting: {fault_name.upper()}")
        logger.info(f"Type: {fault_type}")
        logger.info(f"Interval Range: {INTERVAL_RANGE[0]}-{INTERVAL_RANGE[1]}")
        logger.info("Status: Plotting intervals and monitoring for fault detection...")
        logger.info("=" * 100)

        # Write status to file
        write_status(fault_name, fault_number, total_faults, 1, f'Starting {fault_name}...')
        
        # Clear previous data
        clear_fault_data(fault_name)

        # Create generator instance (this resets interval_count to 0)
        generator = generator_class()

        # Show trigger interval
        if hasattr(generator, 'spike_interval'):
            logger.info(f"   🎯 SUDDEN: Spike will trigger at interval {generator.spike_interval}")
            write_status(fault_name, fault_number, total_faults, 1, f'Sudden fault - trigger at interval {generator.spike_interval}')
        elif hasattr(generator, 'critical_interval'):
            logger.info(f"   🎯 GRADUAL: Critical failure at interval {generator.critical_interval}")
            write_status(fault_name, fault_number, total_faults, 1, f'Gradual fault - critical at interval {generator.critical_interval}')
        
        logger.info(f"   📈 Monitoring starts NOW - Interval 1/15")
        logger.info(f"   ⏱️  Each interval takes ~30 seconds")
        logger.info(f"   🔄 REAL-TIME MODE: One data point every 30 seconds")
        
        # STARTUP SYNC: Wait 2 seconds for frontend to start polling (30sec intervals)
        logger.info(f"   ⏳ Synchronizing with frontend polling (2 second startup delay)...")
        time.sleep(2)
        
        # Run generator - will stop when system_failure_state is True
        # The run_indefinitely() method already has time.sleep(30) between intervals
        generator.run_indefinitely()

        logger.info(f"✓ Fault '{fault_name}' completed at interval {generator.interval_count}")
        write_status(fault_name, fault_number, total_faults, 1, f'✓ {fault_name} completed at interval {generator.interval_count}')
        logger.info("=" * 100)
        
    except KeyboardInterrupt:
        logger.info(f"\n⏸️  Stopped by user at fault: {fault_name}")
        raise
    except Exception as e:
        logger.error(f"Error in {fault_name} generator: {e}", exc_info=True)
        write_status(fault_name, fault_number, total_faults, 1, f'Error in {fault_name}: {str(e)}')
        raise


def run_sequential_cycle(repeat_cycles=1):
    """Run the complete fault sequence one or more times."""
    total_cycles = repeat_cycles
    
    for cycle in range(1, repeat_cycles + 1):
        logger.info(f"\n{'#' * 100}")
        logger.info(f"# CYCLE {cycle}/{total_cycles} - Starting fault sequence")
        logger.info(f"{'#' * 100}\n")
        
        for fault_num, (fault_name, generator_class, fault_type) in enumerate(FAULT_SEQUENCE, 1):
            try:
                run_fault_in_sequence(fault_name, generator_class, fault_type, fault_num, len(FAULT_SEQUENCE))
                
                # Delay between faults
                if fault_num < len(FAULT_SEQUENCE):  # Don't delay after last fault
                    logger.info(f"\n⏳ Waiting {INTER_FAULT_DELAY} seconds before next fault...")
                    time.sleep(INTER_FAULT_DELAY)
                    
            except KeyboardInterrupt:
                logger.info("Sequence interrupted by user")
                return False
            except Exception as e:
                logger.error(f"Critical error in fault {fault_num}: {e}")
                return False
        
        logger.info(f"\n✓ Cycle {cycle} complete!")
        
        if cycle < repeat_cycles:
            logger.info(f"Waiting before cycle {cycle + 1}...")
            time.sleep(INTER_FAULT_DELAY * 2)
    
    return True


def get_user_selection():
    """Get user selection for run mode."""
    print("\n" + "=" * 100)
    print("CHOOSE RUN MODE:")
    print("=" * 100)
    print("1. Single Cycle (Run all 11 faults once, then stop)")
    print("2. Continuous Cycles (Run all 11 faults repeatedly)")
    print("3. Run Specific Fault Only (Choose one fault)")
    print("4. Exit")
    print("=" * 100)
    
    while True:
        choice = input("\nSelect mode (1-4): ").strip()
        
        if choice == '1':
            return ('cycle', 1)
        elif choice == '2':
            cycles = input("How many cycles? (default: 2): ").strip()
            try:
                cycles = int(cycles) if cycles else 2
                return ('cycle', cycles)
            except ValueError:
                print("Invalid input, using default 2 cycles")
                return ('cycle', 2)
        elif choice == '3':
            return ('single', None)
        elif choice == '4':
            return ('exit', None)
        else:
            print("Invalid choice, please select 1-4")


def display_fault_menu():
    """Display fault menu for single fault selection."""
    print("\n" + "=" * 80)
    print("SELECT A FAULT TO RUN:")
    print("=" * 80)
    for i, (name, _, fault_type) in enumerate(FAULT_SEQUENCE, 1):
        print(f"{i:2d}. {name:<35} ({fault_type})")
    print("=" * 80)


def main():
    """Main entry point - supports both CLI and programmatic invocation."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='WILO Fault Generator Runner')
    parser.add_argument('--fault', type=str, help='Specific fault to run (e.g., "Motor Stall")')
    args = parser.parse_args()
    
    try:
        # If a specific fault is requested (from API), run it directly
        if args.fault:
            # Find the fault in the sequence
            for fault_name, generator_class, fault_type in FAULT_SEQUENCE:
                if fault_name.lower() == args.fault.lower():
                    logger.info("=" * 100)
                    logger.info(f"API MODE: Running single fault: {fault_name}")
                    logger.info("=" * 100)
                    run_fault_in_sequence(fault_name, generator_class, fault_type, 1, 1)
                    write_status(fault_name, 1, 1, 1, f'✓ {fault_name} completed')
                    return
            
            # If fault not found
            logger.error(f"Fault not found: {args.fault}")
            logger.error(f"Available faults: {', '.join([name for name, _, _ in FAULT_SEQUENCE])}")
            sys.exit(1)
        
        # Otherwise, interactive CLI mode
        display_welcome()
        
        mode, param = get_user_selection()
        
        if mode == 'exit':
            logger.info("Exiting...")
            return
        
        elif mode == 'single':
            # Single fault mode
            while True:
                display_fault_menu()
                choice = input("\nSelect fault (1-11) or 'q' to quit: ").strip()
                
                if choice.lower() == 'q':
                    return
                
                try:
                    fault_idx = int(choice) - 1
                    if 0 <= fault_idx < len(FAULT_SEQUENCE):
                        fault_name, generator_class, fault_type = FAULT_SEQUENCE[fault_idx]
                        run_fault_in_sequence(fault_name, generator_class, fault_type, 1, 1)
                        break
                    else:
                        print(f"Invalid selection '{choice}', please choose 1-{len(FAULT_SEQUENCE)}")
                except ValueError:
                    print(f"Invalid input '{choice}'")
        
        else:  # mode == 'cycle'
            success = run_sequential_cycle(repeat_cycles=param)
            if success:
                logger.info("\n" + "=" * 100)
                logger.info("✓ ALL FAULT SEQUENCES COMPLETED SUCCESSFULLY!")
                logger.info("=" * 100)
    
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 100)
        logger.info("Sequential fault runner stopped by user")
        logger.info("=" * 100)
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
