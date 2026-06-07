"""
WILO Cloud Monitoring - Single Fault Generator Runner
Select and run a single fault generator for monitoring
Each fault will trigger failure between intervals 5-15 (random)
"""

import sys
import shutil
import logging
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
        logging.FileHandler('fault_generators.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Map of fault names to generator classes
FAULTS = {
    '1': ('Motor Stall', MotorStallGenerator, 'SUDDEN'),
    '2': ('Pump Cavitation', PumpCavitationGenerator, 'SUDDEN'),
    '3': ('Pump Impeller Damage', PumpImpellerDamageGenerator, 'SUDDEN'),
    '4': ('Pump Seal Leakage', PumpSealLeakageGenerator, 'SUDDEN'),
    '5': ('Motor Bearing Failure', MotorBearingFailureGenerator, 'GRADUAL'),
    '6': ('Motor Shaft Misalignment', MotorShaftMisalignmentGenerator, 'GRADUAL'),
    '7': ('Motor Overheating', MotorOverheatingGenerator, 'GRADUAL'),
    '8': ('Motor Winding Failure', MotorWindingFailureGenerator, 'GRADUAL'),
    '9': ('Motor Vibration Anomaly', MotorVibrationAnomalyGenerator, 'GRADUAL'),
    '10': ('Motor Electrical Fault', MotorElectricalFaultGenerator, 'GRADUAL'),
    '11': ('Custom Event', CustomEventGenerator, 'CUSTOM'),
}


def display_menu():
    """Display available fault options."""
    print("\n" + "=" * 80)
    print("WILO CLOUD MONITORING - SELECT A FAULT TO MONITOR")
    print("=" * 80)
    print("\nSUDDEN FAULTS (trigger unpredictably between intervals 5-15):")
    print("  1. Motor Stall - Sudden catastrophic failure with current spike")
    print("  2. Pump Cavitation - Sudden pressure/vibration spike")
    print("  3. Pump Impeller Damage - Sudden structural failure")
    print("  4. Pump Seal Leakage - Sudden seal rupture")
    
    print("\nGRADUAL FAULTS (progressive degradation, critical at interval 5-15):")
    print("  5. Motor Bearing Failure - Linear vibration growth")
    print("  6. Motor Shaft Misalignment - 2x frequency amplitude growth")
    print("  7. Motor Overheating - Thermal degradation")
    print("  8. Motor Winding Failure - Insulation breakdown")
    print("  9. Motor Vibration Anomaly - Chaotic high-frequency energy")
    print("  10. Motor Electrical Fault - Insulation/phase issues")
    
    print("\nCUSTOM:")
    print("  11. Custom Event - Ready for manual triggers")
    print("\n" + "=" * 80)


def get_fault_selection():
    """Get user selection from menu."""
    while True:
        display_menu()
        choice = input("\nSelect a fault (1-11) or 'q' to quit: ").strip()
        
        if choice.lower() == 'q':
            logger.info("Exiting...")
            sys.exit(0)
        
        if choice in FAULTS:
            return choice
        
        print(f"\n❌ Invalid selection '{choice}'. Please choose 1-11.")


def clear_fault_data(fault_name):
    """Clear previous run data for the selected fault."""
    try:
        # Clear Data/<fault_name> directory completely
        data_dir = Path('Data') / fault_name
        if data_dir.exists():
            shutil.rmtree(data_dir)
            logger.info(f"Cleared data directory: {data_dir}")
        
        # Clear entire Events/<fault_name> directory to start completely fresh
        events_dir = Path('Events') / fault_name
        if events_dir.exists():
            shutil.rmtree(events_dir)
            logger.info(f"Cleared events directory: {events_dir}")
        
        # Recreate empty Events directory structure
        events_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created fresh events directory: {events_dir}")
        
        logger.info(f"✓ Reset data for {fault_name} - starting fresh from interval 1")
        
    except Exception as e:
        logger.warning(f"Warning while clearing data: {e}")


def run_fault_generator(fault_name, generator_class, fault_type):
    """Run a single fault generator."""
    try:
        logger.info("=" * 80)
        logger.info(f"RUNNING FAULT GENERATOR: {fault_name.upper()}")
        logger.info(f"Type: {fault_type}")
        logger.info("Fault will trigger at random interval between 5-15 (inclusive)")
        logger.info("Data will be updated every 30 seconds")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 80)
        
        # Instantiate and run the generator
        generator = generator_class()
        
        # Show trigger interval
        if hasattr(generator, 'spike_interval'):
            logger.info(f"✓ SUDDEN fault will trigger at interval: {generator.spike_interval}")
        elif hasattr(generator, 'critical_interval'):
            logger.info(f"✓ GRADUAL fault will reach critical at interval: {generator.critical_interval}")
        
        # Run indefinitely
        generator.run_indefinitely()
        
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 80)
        logger.info(f"Stopped {fault_name} generator")
        logger.info("=" * 80)
    except Exception as e:
        logger.error(f"Error in {fault_name} generator: {e}", exc_info=True)
        raise


def main():
    """Main entry point."""
    try:
        # Get user selection
        choice = get_fault_selection()
        fault_name, generator_class, fault_type = FAULTS[choice]
        
        # Clear old data before starting fresh
        clear_fault_data(fault_name)
        
        # Run the selected generator
        run_fault_generator(fault_name, generator_class, fault_type)
        
    except KeyboardInterrupt:
        print("\n\nGenerator stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
