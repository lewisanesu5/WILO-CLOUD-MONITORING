"""
Master Fault Generator Runner
Launches all 11 fault generators in parallel for system-wide testing
Each generator runs indefinitely with 30-second intervals
"""

import multiprocessing
import logging
import time
import sys
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

GENERATORS = [
    ('SUDDEN', MotorStallGenerator),
    ('SUDDEN', PumpCavitationGenerator),
    ('SUDDEN', PumpImpellerDamageGenerator),
    ('SUDDEN', PumpSealLeakageGenerator),
    ('GRADUAL', MotorBearingFailureGenerator),
    ('GRADUAL', MotorShaftMisalignmentGenerator),
    ('GRADUAL', MotorOverheatingGenerator),
    ('GRADUAL', MotorWindingFailureGenerator),
    ('GRADUAL', MotorVibrationAnomalyGenerator),
    ('GRADUAL', MotorElectricalFaultGenerator),
    ('CUSTOM', CustomEventGenerator),
]


def run_generator(fault_type, generator_class):
    """Run a single generator in a separate process."""
    try:
        logger.info(f"Starting {fault_type} generator: {generator_class.__name__}")
        generator = generator_class()
        generator.run_indefinitely()
    except Exception as e:
        logger.error(f"Error in {generator_class.__name__}: {e}", exc_info=True)


def main():
    """Launch all generators in parallel."""
    logger.info("=" * 80)
    logger.info("WILO CLOUD MONITORING - FAULT GENERATOR MASTER")
    logger.info("=" * 80)
    logger.info(f"Launching {len(GENERATORS)} fault generators...")
    logger.info("Each runs indefinitely with 30-second intervals")
    logger.info("Sudden faults: Random spike within 15 intervals")
    logger.info("Gradual faults: Linear degradation over 15 intervals")
    logger.info("=" * 80)
    
    processes = []
    
    for fault_type, generator_class in GENERATORS:
        process = multiprocessing.Process(
            target=run_generator,
            args=(fault_type, generator_class),
            daemon=True
        )
        process.start()
        processes.append(process)
        logger.info(f"✓ Started: {generator_class.__name__}")
        time.sleep(0.5)  # Stagger start times slightly
    
    logger.info(f"\nAll {len(processes)} generators running. Press Ctrl+C to stop.")
    logger.info("=" * 80)
    
    try:
        # Keep main process alive
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 80)
        logger.info("Stopping all generators...")
        for process in processes:
            process.terminate()
        for process in processes:
            process.join(timeout=2)
        logger.info("All generators stopped")
        logger.info("=" * 80)


if __name__ == '__main__':
    main()
