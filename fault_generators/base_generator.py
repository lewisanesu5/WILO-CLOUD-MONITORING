"""
Base Generator Class for Fault-Specific Data Generation
Provides common functionality for all fault generators
"""

import os
import csv
import sys
import json
import numpy as np
from datetime import datetime
from scipy import stats as sp_stats
import time
import logging
from pathlib import Path

# Make the project root importable (database, fft_analysis, event_manager live there)
_BASE_DIR = Path(__file__).resolve().parent.parent
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

# Safe import of database helpers — not available in all environments
try:
    from database import save_statistics, save_raw_datapoints
    from fft_analysis import calculate_fft_analysis
    _DB_AVAILABLE = True
except ImportError:
    _DB_AVAILABLE = False

# Configuration
FREQUENCY = 700  # Hz
DURATION = 2  # seconds (sampling window)
SAMPLES = FREQUENCY * DURATION  # 1400 readings per file
SAMPLE_INTERVAL = 1000 / FREQUENCY  # ~1.43 milliseconds between samples
GENERATION_INTERVAL = 10  # seconds between file generations (for testing)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s'
)


class BaseGenerator:
    """Base class for fault-specific generators."""
    
    def __init__(self, fault_name):
        """
        Initialize generator for a specific fault type.
        
        Args:
            fault_name: Name of the fault (e.g., "Motor Stall")
        """
        self.fault_name = fault_name
        self.logger = logging.getLogger(f"Generator-{fault_name}")
        
        # Setup data directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(base_dir, 'Data', fault_name)
        self.events_dir = os.path.join(base_dir, 'Events', fault_name)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.events_dir, exist_ok=True)
        
        # Stats file path
        self.stats_file = os.path.join(self.events_dir, 'stats.json')
        self.metadata_file = os.path.join(self.events_dir, 'metadata.json')
        
        # Fault state tracking
        self.interval_count = 0
        self.failure_triggered = False
        self.failure_interval = None
        self.system_failure_state = False
        self.start_time = datetime.utcnow().isoformat()
        self.intervals_data = []
        
        # Seed random with time-based entropy so each run produces unique data for ML training
        np.random.seed(int(time.time() * 1000) % 2**32)
        
        # Initialize metadata file
        self._init_metadata()
        
        self.logger.info(f"Initialized generator for: {fault_name}")
        self.logger.info(f"Data directory: {self.data_dir}")
        self.logger.info(f"Events directory: {self.events_dir}")
    
    def _init_metadata(self):
        """Initialize event metadata file."""
        try:
            metadata = {
                "fault_name": self.fault_name,
                "start_time": self.start_time,
                "end_time": None,
                "failure_interval": None,
                "system_failure_state": False,
                "intervals": []
            }
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error initializing metadata: {e}")
    
    def log_interval_progress(self, interval_max=15):
        """Log current interval progress with visual indicator."""
        progress_bar = "█" * self.interval_count + "░" * (interval_max - self.interval_count)
        state = "🔥 FAILURE" if self.system_failure_state else "✓ NORMAL"
        self.logger.info(
            f"[{progress_bar}] Interval {self.interval_count}/{interval_max} | {state}"
        )
    
    def _calculate_stats(self, data):
        """Calculate statistical features from raw data."""
        # Handle numpy arrays safely - can't use 'not' on arrays
        if isinstance(data, np.ndarray):
            if data.size == 0:
                return {}
        elif not data or len(data) == 0:
            return {}
        
        try:
            arr = np.array(data, dtype=np.float64)
            # Remove NaN and Inf values
            mask = np.isfinite(arr)
            arr = arr[mask]
            
            if len(arr) == 0:
                return {}
            
            # Force all results to Python native types immediately
            stats_dict = {
                "mean": float(np.mean(arr)),
                "median": float(np.median(arr)),
                "std_dev": float(np.std(arr)),
                "variance": float(np.var(arr)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "range": float(np.max(arr)) - float(np.min(arr)),
                "rms": float(np.sqrt(np.mean(arr**2))),
                "peak": float(np.max(np.abs(arr))),
                "skewness": float(sp_stats.skew(arr).item() if hasattr(sp_stats.skew(arr), 'item') else sp_stats.skew(arr)),
                "kurtosis": float(sp_stats.kurtosis(arr).item() if hasattr(sp_stats.kurtosis(arr), 'item') else sp_stats.kurtosis(arr)),
            }
            return stats_dict
        except Exception as e:
            self.logger.error(f"Error calculating stats: {e}", exc_info=True)
            return {}
    
    def _numpy_to_python(self, obj):
        """Convert numpy types to Python native types for JSON serialization."""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, dict):
            return {k: self._numpy_to_python(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._numpy_to_python(item) for item in obj]
        return obj

    def _save_interval_stats(self, accel_data, current_data, audio_data):
        """Save statistics for current interval to files."""
        try:
            accel_stats = self._calculate_stats(accel_data)
            current_stats = self._calculate_stats(current_data)
            audio_stats = self._calculate_stats(audio_data)
            
            interval_stats = {
                "interval": int(self.interval_count),
                "timestamp": datetime.now().isoformat(),
                "system_failure_state": bool(self.system_failure_state),
                "acceleration": accel_stats,
                "current": current_stats,
                "audio": audio_stats,
            }
            
            self.intervals_data.append(interval_stats)
            
            # Write stats.json with numpy-safe serialization
            stats_output = {
                "fault_name": self.fault_name,
                "start_time": self.start_time,
                "current_time": datetime.now().isoformat(),
                "interval_count": int(self.interval_count),
                "system_failure_state": bool(self.system_failure_state),
                "failure_interval": self._numpy_to_python(self.failure_interval) if self.failure_interval is not None else None,
                "intervals": [self._numpy_to_python(i) for i in self.intervals_data]
            }
            
            # Convert all numpy types to Python natives
            stats_output = self._numpy_to_python(stats_output)
            
            # Validate before writing - check for problematic types
            try:
                test_json = json.dumps(stats_output)  # Test serialization
                with open(self.stats_file, 'w') as f:
                    json.dump(stats_output, f, indent=2)
                # Log successful write with interval count
                self.logger.info(f"📝 Saved interval {self.interval_count} to stats.json ({len(self.intervals_data)} intervals total)")
            except Exception as json_error:
                self.logger.error(f"JSON serialization failed: {json_error}")
                # Try to identify problematic field
                for key, value in stats_output.items():
                    try:
                        json.dumps({key: value})
                    except:
                        self.logger.error(f"Problematic field '{key}' with type {type(value)}: {value}")
                raise
                
        except Exception as e:
            self.logger.error(f"Error saving interval stats: {e}", exc_info=True)
    
    def generate_timestamps(self):
        """Generate millisecond timestamps for 2-second window at 700Hz."""
        return [i * SAMPLE_INTERVAL for i in range(SAMPLES)]
    
    def write_csv_file(self, filename, timestamps, values):
        """Write timestamps and values to CSV file."""
        filepath = os.path.join(self.data_dir, filename)
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'value'])
                for ts, val in zip(timestamps, values):
                    # Ensure value is a float
                    val = float(val)
                    if not (np.isnan(val) or np.isinf(val)):
                        writer.writerow([ts, val])
            self.logger.debug(f"Created: {filename}")
        except Exception as e:
            self.logger.error(f"Error writing {filename}: {e}")
    
    def generate_acceleration_data(self):
        """Override in subclass for acceleration patterns."""
        raise NotImplementedError("Subclass must implement generate_acceleration_data()")
    
    def generate_current_data(self):
        """Override in subclass for current patterns."""
        raise NotImplementedError("Subclass must implement generate_current_data()")
    
    def generate_audio_data(self):
        """Override in subclass for audio patterns."""
        raise NotImplementedError("Subclass must implement generate_audio_data()")
    
    def generate_interval(self):
        """
        Generate one complete interval of data (6 CSV files).
        Calls subclass-specific fault logic.
        Returns: True to continue, False to stop (on failure)
        """
        timestamps = self.generate_timestamps()
        self.interval_count += 1
        self.logger.info(f"🔄 Generating interval {self.interval_count}...")
        
        # Generate data based on fault state
        accel_data = self.generate_acceleration_data()
        current_data = self.generate_current_data()
        audio_data = self.generate_audio_data()
        
        # Set failure_interval if system failure detected (BEFORE saving stats)
        if self.system_failure_state and self.failure_interval is None:
            self.failure_interval = self.interval_count
        
        # Save statistics
        self._save_interval_stats(accel_data, current_data, audio_data)
        
        # Write all 6 files
        self.write_csv_file('max_acceleration.csv', timestamps, accel_data)
        self.write_csv_file('min_acceleration.csv', timestamps, accel_data)
        self.write_csv_file('max_current.csv', timestamps, current_data)
        self.write_csv_file('min_current.csv', timestamps, current_data)
        self.write_csv_file('max_audio.csv', timestamps, audio_data)
        self.write_csv_file('min_audio.csv', timestamps, audio_data)
        
        state_str = 'SYSTEM_FAILURE' if self.system_failure_state else 'NORMAL'
        self.logger.info(
            f"Interval {self.interval_count}: Generated 6 files | "
            f"State: {state_str}"
        )

        # -- Save statistics and raw datapoints to Neon database in real-time --
        self._save_interval_to_db(accel_data, current_data, audio_data)

        # Stop generation if system failed
        if self.system_failure_state:
            self.logger.warning(f"🔥 SYSTEM FAILURE at interval {self.failure_interval}")
            return False  # Signal to stop infinite loop

        return True  # Continue generating
    
    def _save_interval_to_db(self, accel_data, current_data, audio_data):
        """
        Save the current interval's raw data and statistics to Neon database.
        Called after every interval so EventManager always has fresh rows.
        Silently skipped if the database helpers are not importable.
        """
        if not _DB_AVAILABLE:
            self.logger.debug("[DB-SAVE] database helpers not available, skipping Neon save.")
            return

        sensors = {
            'acceleration': accel_data,
            'current':      current_data,
            'audio':        audio_data,
        }

        for sensor_name, raw_data in sensors.items():
            try:
                arr = np.asarray(raw_data, dtype=np.float64)
                arr = arr[np.isfinite(arr)]  # strip NaN / Inf
                if arr.size == 0:
                    self.logger.warning(f"[DB-SAVE] {sensor_name}: all values non-finite, skipping")
                    continue

                stats_dict = {
                    'mean':     float(np.mean(arr)),
                    'max':      float(np.max(arr)),
                    'min':      float(np.min(arr)),
                    'std_dev':  float(np.std(arr)),
                    'range':    float(np.max(arr) - np.min(arr)),
                    'skewness': float(sp_stats.skew(arr)),
                    'kurtosis': float(sp_stats.kurtosis(arr)),
                }

                # FFT on raw array — use the 1400-point waveform
                freqs, amps = calculate_fft_analysis(arr.tolist())

                save_statistics(sensor_name, 'max', stats_dict, freqs, amps)

                # Raw datapoints: timestamps in milliseconds (relative to epoch=0 for now)
                raw_timestamps = [int(i * SAMPLE_INTERVAL) for i in range(len(arr))]
                save_raw_datapoints(
                    sensor_name, 'max',
                    timestamp_ms=time.time() * 1000,
                    datapoints=arr.tolist(),
                    datapoint_timestamps=raw_timestamps,
                )

                self.logger.info(f"[DB-SAVE] ✓ {sensor_name} interval {self.interval_count} saved to Neon")

            except Exception as exc:
                self.logger.error(f"[DB-SAVE] Failed to save {sensor_name} to Neon: {exc}", exc_info=True)

    def trigger_auto_event(self):
        """
        Auto-create a fault event in the database after the generator completes.
        Uses EventManager to detect the deviation window and insert rows into
        the appropriate fault table — same logic as the manual 'Create Event' button.
        """
        if not _DB_AVAILABLE:
            self.logger.warning("[AUTO-EVENT] database helpers not importable, skipping auto-event.")
            return

        try:
            from event_manager import EventManager
        except ImportError as e:
            self.logger.error(f"[AUTO-EVENT] Cannot import EventManager: {e}")
            return

        try:
            failure_time = datetime.now().isoformat()
            self.logger.info(f"[AUTO-EVENT] Triggering automatic event creation for '{self.fault_name}' at {failure_time}")

            em = EventManager(
                events_dir=self.events_dir,
                data_dir=self.data_dir,
            )
            result = em.create_event(
                event_name=self.fault_name,
                failure_time_iso=failure_time,
                description="auto-triggered after generator completed",
                start_time_iso=self.start_time,
            )

            if result.get('success'):
                self.logger.info(
                    f"[AUTO-EVENT] ✓ Event created successfully! "
                    f"fault_id={result.get('fault_id')}  "
                    f"rows_inserted={result.get('total_rows_inserted')}"
                )
            else:
                self.logger.warning(f"[AUTO-EVENT] Event creation returned failure: {result}")

        except Exception as exc:
            self.logger.error(f"[AUTO-EVENT] Exception during auto-event: {exc}", exc_info=True)

    def run_indefinitely(self):
        """Run generator indefinitely with 30-second intervals."""
        try:
            self.logger.info(f"Starting infinite generation loop for {self.fault_name}")
            self.logger.info(f"📊 Plot Interval Range: 1-15")
            self.logger.info(f"⚠️  Fault Detection Range: 5-15")
            self.logger.info(f"⏱️  Interval Duration: ~10 seconds")
            
            while True:
                should_continue = self.generate_interval()
                self.logger.debug(f"After interval {self.interval_count}: should_continue={should_continue}, failure_state={self.system_failure_state}")
                
                # Log progress
                self.log_interval_progress(interval_max=15)
                
                if not should_continue:
                    self.logger.info(f"✓ Event ended: {self.fault_name}")
                    self.logger.info(f"🔥 Final state: SYSTEM FAILURE at interval {self.failure_interval}")
                    break
                    
                time.sleep(GENERATION_INTERVAL)

            # ----------------------------------------------------------------
            # Fault run complete: auto-create the event in the database.
            # This fires ONLY when the loop terminated because the generator
            # reached system_failure_state (not on KeyboardInterrupt).
            # ----------------------------------------------------------------
            if self.system_failure_state and _DB_AVAILABLE:
                self.trigger_auto_event()

        except KeyboardInterrupt:
            self.logger.info(f"Generator stopped by user")
        except Exception as e:
            self.logger.error(f"Critical error in generation loop: {e}")
            raise
