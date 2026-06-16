"""
Event Manager Module
Handles logging of failure events with multi-sensor trend extraction.
Extracts trends based on aggregated features (mean, max, std_dev, kurtosis) across all sensors.
Tracks slope changes BACKWARDS from failure point for acceleration, current, and audio.
Queries aggregated data from database tables (acceleration, current, audio).
"""

import os
import csv
import json
import datetime
import numpy as np
from scipy import stats as sp_stats
from typing import Dict, List, Tuple, Optional
from database import insert_event_data


def calculate_statistics(z_values):
    """Calculate comprehensive statistical parameters for acceleration data."""
    if not z_values or len(z_values) == 0:
        return {}

    def safe_float(val):
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return 0.0
        return f

    z_array = np.array(z_values)

    max_val = np.max(z_array)
    min_val = np.min(z_array)
    mean_val = np.mean(z_array)
    abs_mean = np.mean(np.abs(z_array))
    rms = np.sqrt(np.mean(z_array**2))
    variance = np.var(z_array)
    std_dev = np.std(z_array)
    peak = max(abs(max_val), abs(min_val))
    peak_to_peak = max_val - min_val

    crest_factor = peak / rms if rms != 0 else 0
    impulse_factor = peak / abs_mean if abs_mean != 0 else 0
    shape_factor = rms / abs_mean if abs_mean != 0 else 0
    sqrt_mean = np.mean(np.sqrt(np.abs(z_array)))
    clearance_factor = peak / (sqrt_mean**2) if sqrt_mean != 0 else 0

    skewness = sp_stats.skew(z_array)
    kurtosis_val = sp_stats.kurtosis(z_array)

    energy = np.sum(z_array**2)
    zero_crossings = np.sum(np.diff(np.signbit(z_array)))
    zero_crossing_rate = zero_crossings / len(z_array) if len(z_array) > 1 else 0

    percentile_90 = np.percentile(z_array, 90)
    percentile_95 = np.percentile(z_array, 95)
    percentile_99 = np.percentile(z_array, 99)

    return {
        'max': safe_float(max_val),
        'min': safe_float(min_val),
        'mean': safe_float(mean_val),
        'abs_mean': safe_float(abs_mean),
        'rms': safe_float(rms),
        'variance': safe_float(variance),
        'std_dev': safe_float(std_dev),
        'peak': safe_float(peak),
        'peak_to_peak': safe_float(peak_to_peak),
        'crest_factor': safe_float(crest_factor),
        'impulse_factor': safe_float(impulse_factor),
        'shape_factor': safe_float(shape_factor),
        'clearance_factor': safe_float(clearance_factor),
        'skewness': safe_float(skewness),
        'kurtosis': safe_float(kurtosis_val + 3.0),
        'excess_kurtosis': safe_float(kurtosis_val),
        'energy': safe_float(energy),
        'zero_crossing_rate': safe_float(zero_crossing_rate),
        'percentile_90': safe_float(percentile_90),
        'percentile_95': safe_float(percentile_95),
        'percentile_99': safe_float(percentile_99),
    }


class EventManager:
    def __init__(self, events_dir: str, data_dir: str):
        """
        Initialize the Event Manager.
        
        Args:
            events_dir: Directory to store event CSVs (only on local, not on Render)
            data_dir: Directory containing max_reading CSV files
        """
        self.events_dir = events_dir
        self.data_dir = data_dir
    
    def _load_all_data_points(self) -> List[Tuple[float, float]]:
        """
        Load all data points from max_reading CSV files.
        
        Returns:
            List of (timestamp_ms, z_value, filename) tuples sorted by timestamp
        """
        import glob
        
        all_points = []
        max_reading_files = glob.glob(os.path.join(self.data_dir, 'max_reading*.csv'))
        
        for file_path in max_reading_files:
            filename = os.path.basename(file_path)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        try:
                            # Handle different timestamp formats
                            timestamp_str = row['timestamp']
                            if 'T' in timestamp_str:  # ISO format
                                dt_obj = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                timestamp_ms = dt_obj.timestamp() * 1000
                            else:
                                timestamp_ms = float(timestamp_str)
                            
                            # Handle different value column names
                            if 'z' in row:
                                z_value = float(row['z'])
                            elif 'value' in row:
                                z_value = float(row['value'])
                            else:
                                continue
                            
                            all_points.append((timestamp_ms, z_value, filename))
                        except (ValueError, KeyError):
                            continue
            except Exception as e:
                print(f"Error loading data from {file_path}: {e}")
                continue
        
        # Sort by timestamp
        all_points.sort(key=lambda x: x[0])
        return all_points
    
    # -- Fault classification for intelligent deviation detection ----------------
    # SUDDEN: flat baseline until one catastrophic interval; deviation IS the failure.
    # GRADUAL: progressive degradation; 3-sigma scan finds the onset reliably.
    FAULT_TYPES = {
        'Motor Stall':            'SUDDEN',
        'Pump Cavitation':        'SUDDEN',
        'Pump Impeller Damage':   'SUDDEN',
        'Pump Seal Leakage':      'SUDDEN',
        'Motor Bearing Failure':  'GRADUAL',
        'Motor Shaft Misalignment': 'GRADUAL',
        'Motor Overheating':      'GRADUAL',
        'Motor Winding Failure':  'GRADUAL',
        'Motor Vibration Anomaly': 'GRADUAL',
        'Motor Electrical Fault': 'GRADUAL',
        'Custom Event':           'GRADUAL',
    }

    def _load_all_sensor_data(self, start_time_iso: Optional[str] = None) -> Dict[str, List[Dict]]:
        """
        Load aggregated feature data for ALL sensors from database tables.
        If start_time_iso is provided, fetches only records created since then (representing the current generator run).
        Otherwise, defaults to fetching the last 30 MAX-mode rows per sensor.

        Returns:
            Dict mapping sensor names to lists of feature data:
            {
                'acceleration': [
                    {'timestamp': created_at, 'mean': val, 'max': val, 'min': val,
                     'std_dev': val, 'variance': val, 'skewness': val, 'kurtosis': val,
                     'frequency1-5': [...], 'amplitude1-5': [...]},
                    ...
                ],
                'current': [...],
                'audio': [...]
            }
        """
        from database import get_connection
        import logging

        logger = logging.getLogger(__name__)

        sensor_data = {'acceleration': [], 'current': [], 'audio': []}
        table_names = {
            'acceleration': 'acceleration',
            'current': 'current',
            'audio': 'audio'
        }

        LIMIT = 30
        if start_time_iso:
            logger.info(f"🔍 Querying database for records created since start_time={start_time_iso}")
        else:
            logger.info(f"🔍 Querying database for last {LIMIT} MAX rows per sensor")

        try:
            conn = get_connection()
            cur = conn.cursor()

            for sensor_type, table_name in table_names.items():
                try:
                    if start_time_iso:
                        query = f"""
                            SELECT
                                x_min, x_max, mean, standard_deviation, range,
                                skewness, kurtosis,
                                frequency1, frequency2, frequency3, frequency4, frequency5,
                                amplitude1, amplitude2, amplitude3, amplitude4, amplitude5,
                                created_at, file_type
                            FROM {table_name}
                            WHERE file_type = 'max' AND created_at >= %s
                            ORDER BY created_at ASC
                        """
                        logger.debug(f"Executing filtered query since {start_time_iso} for {sensor_type}")
                        cur.execute(query, (start_time_iso,))
                    else:
                        query = f"""
                            SELECT * FROM (
                                SELECT
                                    x_min, x_max, mean, standard_deviation, range,
                                    skewness, kurtosis,
                                    frequency1, frequency2, frequency3, frequency4, frequency5,
                                    amplitude1, amplitude2, amplitude3, amplitude4, amplitude5,
                                    created_at, file_type
                                FROM {table_name}
                                WHERE file_type = 'max'
                                ORDER BY created_at DESC
                                LIMIT %s
                            ) sub
                            ORDER BY created_at ASC
                        """
                        logger.debug(f"Executing fallback query for {sensor_type}")
                        cur.execute(query, (LIMIT,))
                    rows = cur.fetchall()
                    
                    logger.info(f"✓ Query returned {len(rows)} {sensor_type} records from database")
                    
                    if not rows:
                        logger.warning(f"⚠️ No data found for {sensor_type} in last 24 hours")
                    
                    for row in rows:
                        try:
                            created_at = row[17]  # created_at column
                            if created_at:
                                timestamp_ms = created_at.timestamp() * 1000
                            else:
                                timestamp_ms = 0
                                logger.warning(f"Null timestamp found for {sensor_type}")
                                
                            std_dev_val = row[3] if row[3] is not None else 0.0
                            feature_data = {
                                'timestamp': timestamp_ms,
                                'min': row[0],           # x_min
                                'max': row[1],           # x_max
                                'mean': row[2],          # mean
                                'std_dev': std_dev_val,  # standard_deviation
                                'range': row[4],         # range
                                'variance': std_dev_val ** 2,  # variance calculated from std_dev
                                'skewness': row[5],      # skewness
                                'kurtosis': row[6],      # kurtosis
                                'frequency1': row[7],
                                'frequency2': row[8],
                                'frequency3': row[9],
                                'frequency4': row[10],
                                'frequency5': row[11],
                                'amplitude1': row[12],
                                'amplitude2': row[13],
                                'amplitude3': row[14],
                                'amplitude4': row[15],
                                'amplitude5': row[16],
                            }
                            sensor_data[sensor_type].append(feature_data)
                        except Exception as row_error:
                            logger.error(f"Error processing row for {sensor_type}: {row_error}")
                            continue
                    
                    logger.info(f"✓ Loaded {len(sensor_data[sensor_type])} {sensor_type} records (mapped to feature dict)")
                    
                except Exception as e:
                    logger.error(f"❌ Error loading {sensor_type} data from database: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    sensor_data[sensor_type] = []
                    continue
            
            conn.close()
            logger.info(f"📊 Total loaded - acceleration: {len(sensor_data['acceleration'])}, current: {len(sensor_data['current'])}, audio: {len(sensor_data['audio'])}")
            
        except Exception as e:
            logger.error(f"❌ Database connection error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        
        return sensor_data
    
    def _find_nearest_data_point(self, failure_time_ms: float, data_points: List[Tuple[float, float]]) -> Optional[int]:
        """
        Find index of data point at or just before the failure time.
        
        Args:
            failure_time_ms: Failure timestamp in milliseconds
            data_points: List of (timestamp, value) tuples
            
        Returns:
            Index of nearest data point at or before failure, or None if no data available
        """
        if not data_points:
            return None
        
        # Find the last point that is at or before the failure time
        nearest_idx = None
        
        for idx, point in enumerate(data_points):
            timestamp = point[0]
            if timestamp <= failure_time_ms:
                nearest_idx = idx
            else:
                break  # Stop when we find a point after failure
        
        return nearest_idx
    
    # _calculate_feature_slopes removed - slope computation is done inline
    # inside _extract_multi_sensor_trends with correct forward/backward differences.
    #
    # _find_stable_baseline_idx removed - was a stub returning last index;
    # deviation onset is now detected dynamically in _extract_multi_sensor_trends.
    
    # Minimum number of chronological MAX-mode upload cycles required to attempt
    # any trend extraction.  With fewer points there is no baseline to compare
    # against, deviation detection is impossible, and all slopes are 0.
    MIN_TREND_POINTS = 5

    def _extract_multi_sensor_trends(self, sensor_data: Dict, failure_time_ms: Optional[float] = None, fault_name: Optional[str] = None) -> Dict[str, List[Dict]]:
        """
        Extract trend data for all sensors.

        For SUDDEN faults (Motor Stall, Pump Cavitation, …) the deviation IS the failure
        event — there is no gradual ramp.  We skip the 3-sigma scan and set the deviation
        start to the failure interval directly, capturing 3 baseline points before it.

        For GRADUAL faults (Bearing Failure, Overheating, …) we run the 3-sigma
        statistical scan to find when the trend first leaves the normal baseline.

        Raises ValueError if any sensor has fewer than MIN_TREND_POINTS data points.

        Args:
            sensor_data:      {sensor_name: [feature_dict, ...]}
            failure_time_ms:  epoch-ms timestamp of the failure event (optional)
            fault_name:       fault name string used to classify SUDDEN vs GRADUAL
        """
        ALL_FEATURES = ['mean', 'max', 'min', 'std_dev', 'variance', 'skewness', 'kurtosis']

        import logging as _logging
        _log = _logging.getLogger(__name__)

        # Classify the fault
        fault_category = self.FAULT_TYPES.get(fault_name or '', 'GRADUAL')
        _log.info(f"🎯 Fault classification: '{fault_name}' → {fault_category}")

        # -- Minimum data guard --------------------------------------------------
        insufficient = {
            s: len(sensor_data.get(s, []))
            for s in ['acceleration', 'current', 'audio']
            if len(sensor_data.get(s, [])) < self.MIN_TREND_POINTS
        }
        if insufficient:
            detail = ", ".join(
                f"{s}: {n} row(s)" for s, n in insufficient.items()
            )
            raise ValueError(
                f"Insufficient data for trend extraction ({detail}). "
                f"Need at least {self.MIN_TREND_POINTS} chronological MAX-mode upload "
                f"cycles per sensor (currently only 1 snapshot row exists - no baseline "
                f"comparison or deviation detection is possible)."
            )
        # ------------------------------------------------------------------------

        # Assume all sensors have same timestamps; use acceleration as reference
        accel_data = sensor_data.get('acceleration', [])
        if not accel_data:
            raise ValueError("No acceleration data available")

        # Find failure index based on failure_time_ms if provided
        if failure_time_ms is not None:
            # find index of nearest point at or before failure_time_ms
            failure_idx = self._find_nearest_data_point(failure_time_ms, [(p['timestamp'], 0.0) for p in accel_data])
            if failure_idx is None:
                failure_idx = len(accel_data) - 1
        else:
            failure_idx = len(accel_data) - 1
            
        failure_time = accel_data[failure_idx]['timestamp']
        
        # Calculate normal baseline stats (mean & standard deviation) for each sensor and feature
        # using a robust baseline size (20% of data up to failure_idx, min 5, max 30)
        baseline_size = max(5, min(30, int((failure_idx + 1) * 0.2)))
        baseline_size = min(baseline_size, failure_idx + 1)
        
        baselines = {}
        for sensor_type in ['acceleration', 'current', 'audio']:
            if sensor_type not in sensor_data or not sensor_data[sensor_type]:
                continue
            sensor_points = sensor_data[sensor_type]
            baselines[sensor_type] = {}
            for feature in ALL_FEATURES:
                vals = [p.get(feature, 0.0) for p in sensor_points[:baseline_size] if p.get(feature) is not None]
                if vals:
                    mean_val = np.mean(vals)
                    std_val = np.std(vals)
                else:
                    mean_val = 0.0
                    std_val = 0.0
                baselines[sensor_type][feature] = (mean_val, std_val)

        import logging as _logger_mod
        _logger = _logger_mod.getLogger(__name__)

        if fault_category == 'SUDDEN':
            # -----------------------------------------------------------------
            # SUDDEN faults: flat baseline → instant spike at failure point.
            # The 3-sigma scan would never find a pre-failure deviation because
            # there is none.  We set deviation_idx = failure_idx so we capture
            # exactly 3 normal baseline points + the failure point.
            # -----------------------------------------------------------------
            deviation_idx = failure_idx
            _logger.info(
                f"⚡ SUDDEN fault — using failure_idx={failure_idx} as deviation start. "
                f"Will extract 3 baseline + 1 failure = 4 rows per sensor."
            )
        else:
            # -----------------------------------------------------------------
            # GRADUAL faults: scan forward from baseline_size looking for the
            # first point where any feature crosses 3-sigma from baseline.
            # -----------------------------------------------------------------
            deviation_idx = None
            for i in range(baseline_size, failure_idx + 1):
                for sensor_type in ['acceleration', 'current', 'audio']:
                    if sensor_type not in sensor_data or i >= len(sensor_data[sensor_type]):
                        continue
                    point = sensor_data[sensor_type][i]
                    for feature in ALL_FEATURES:
                        val = point.get(feature)
                        if val is None:
                            continue
                        b_mean, b_std = baselines[sensor_type].get(feature, (0.0, 0.0))
                        # Adaptive threshold: 3σ, at least 5% of mean, floor 1e-5
                        threshold = max(3.0 * b_std, 0.05 * abs(b_mean))
                        if threshold < 1e-5:
                            threshold = 1e-5
                        if abs(val - b_mean) > threshold:
                            deviation_idx = i
                            break
                    if deviation_idx is not None:
                        break
                if deviation_idx is not None:
                    break

        # Set start_idx: exactly 3 normal points before the deviation point
        if deviation_idx is not None:
            start_idx = max(0, deviation_idx - 3)
            _logger.info(
                f"🎯 Deviation at index {deviation_idx} "
                f"({datetime.datetime.fromtimestamp(accel_data[deviation_idx]['timestamp']/1000).isoformat()}). "
                f"start_idx={start_idx} (3 baseline points before deviation)."
            )
        else:
            # Fallback: capture last 6 points
            start_idx = max(0, failure_idx - 5)
            _logger.info(f"⚠️ No deviation detected. Fallback start_idx={start_idx}.")

        # Extract trends for each sensor from start_idx to failure_idx.
        # Uses acceleration as the master time reference to align current and audio parameters.
        trends = {}
        for sensor_type in ['acceleration', 'current', 'audio']:
            if sensor_type not in sensor_data or not sensor_data[sensor_type]:
                continue
            
            all_raw_points = sensor_data[sensor_type]
            
            # Map intervals to the closest matching timestamp of the acceleration reference point
            sensor_points = []
            for accel_idx in range(start_idx, failure_idx + 1):
                ref_time = accel_data[accel_idx]['timestamp']
                # Select the record whose timestamp is closest to the acceleration timestamp
                best_point = min(all_raw_points, key=lambda p: abs(p['timestamp'] - ref_time))
                sensor_points.append(best_point)
            
            trend_data = []
            for idx in range(len(sensor_points)):
                point = sensor_points[idx]
                point_data = {
                    'timestamp': point['timestamp'],
                    'time_delta': (point['timestamp'] - failure_time) / 1000,
                    'mean': point.get('mean', 0),
                    'max': point.get('max', 0),
                    'min': point.get('min', 0),
                    'std_dev': point.get('std_dev', 0),
                    'kurtosis': point.get('kurtosis', 0),
                    'variance': point.get('variance', 0),
                    'skewness': point.get('skewness', 0),
                    'frequency1': point.get('frequency1', 0),
                    'frequency2': point.get('frequency2', 0),
                    'frequency3': point.get('frequency3', 0),
                    'frequency4': point.get('frequency4', 0),
                    'frequency5': point.get('frequency5', 0),
                    'amplitude1': point.get('amplitude1', 0),
                    'amplitude2': point.get('amplitude2', 0),
                    'amplitude3': point.get('amplitude3', 0),
                    'amplitude4': point.get('amplitude4', 0),
                    'amplitude5': point.get('amplitude5', 0),
                }
                
                # Calculate slopes based on sequential points in matched list
                if idx < len(sensor_points) - 1:
                    next_point = sensor_points[idx + 1]
                    time_diff = next_point['timestamp'] - point['timestamp']
                    
                    if time_diff > 0:
                        point_data['mean_slope'] = (next_point['mean'] - point['mean']) / (time_diff / 1000)
                        point_data['max_slope'] = (next_point['max'] - point['max']) / (time_diff / 1000)
                        point_data['min_slope'] = (next_point['min'] - point['min']) / (time_diff / 1000)
                        point_data['std_dev_slope'] = (next_point['std_dev'] - point['std_dev']) / (time_diff / 1000)
                        point_data['variance_slope'] = (next_point['variance'] - point['variance']) / (time_diff / 1000)
                        point_data['skewness_slope'] = (next_point['skewness'] - point['skewness']) / (time_diff / 1000)
                        point_data['kurtosis_slope'] = (next_point['kurtosis'] - point['kurtosis']) / (time_diff / 1000)
                    else:
                        for feature in ALL_FEATURES:
                            point_data[f'{feature}_slope'] = 0.0
                elif idx > 0:
                    prev_point = sensor_points[idx - 1]
                    time_diff = point['timestamp'] - prev_point['timestamp']
                    
                    if time_diff > 0:
                        point_data['mean_slope'] = (point['mean'] - prev_point['mean']) / (time_diff / 1000)
                        point_data['max_slope'] = (point['max'] - prev_point['max']) / (time_diff / 1000)
                        point_data['min_slope'] = (point['min'] - prev_point['min']) / (time_diff / 1000)
                        point_data['std_dev_slope'] = (point['std_dev'] - prev_point['std_dev']) / (time_diff / 1000)
                        point_data['variance_slope'] = (point['variance'] - prev_point['variance']) / (time_diff / 1000)
                        point_data['skewness_slope'] = (point['skewness'] - prev_point['skewness']) / (time_diff / 1000)
                        point_data['kurtosis_slope'] = (point['kurtosis'] - prev_point['kurtosis']) / (time_diff / 1000)
                    else:
                        for feature in ALL_FEATURES:
                            point_data[f'{feature}_slope'] = 0.0
                else:
                    for feature in ALL_FEATURES:
                        point_data[f'{feature}_slope'] = 0.0
                
                trend_data.append(point_data)
            
            trends[sensor_type] = trend_data
        
        return trends
    
    def create_event(self, event_name: str, failure_time_iso: str, description: str = "", start_time_iso: Optional[str] = None) -> Dict:
        """
        Create a new event with multi-sensor trend tracking BACKWARDS from failure.
        Extracts trends based on aggregated features for acceleration, current, and audio.
        
        Args:
            event_name: Name of the event (e.g., "Bearing Failure")
            failure_time_iso: ISO format timestamp of failure (e.g., "2025-11-27T12:24:00")
            description: Optional description of the event
            start_time_iso: Optional generator run start time (prevents historical data contamination)
            
        Returns:
            Dict with event details and file paths
        """
        # Parse failure time
        try:
            failure_dt = datetime.datetime.fromisoformat(failure_time_iso)
            failure_time_ms = failure_dt.timestamp() * 1000
        except ValueError as e:
            raise ValueError(f"Invalid failure time format: {e}")
        
        # Load sensor data (with aggregated features for all sensors)
        sensor_data = self._load_all_sensor_data(start_time_iso=start_time_iso)
        
        if not sensor_data.get('acceleration'):
            raise ValueError("No acceleration data available in database tables (acceleration, current, audio). Check: 1) Database connection, 2) Tables are populated, 3) Data exists from last 24 hours")
        
        # Extract multi-sensor trends
        multi_sensor_trends = self._extract_multi_sensor_trends(sensor_data, failure_time_ms, fault_name=event_name)
        
        print(f"\n📊 Trend Extraction Results:")
        for sensor_type, trends in multi_sensor_trends.items():
            print(f"  {sensor_type}: {len(trends)} data points extracted")

        # ==================== INSERT TO NEON DATABASE ====================
        try:
            db_result = insert_event_data(event_name, multi_sensor_trends)
            fault_id = db_result['fault_id']
            total_rows_inserted = db_result['total_rows_inserted']
            rows_per_sensor = db_result['rows_per_sensor']
            
            print(f"\n✓ Event saved to Neon database!")
            print(f"  Fault ID: {fault_id}")
            print(f"  Total Rows Inserted: {total_rows_inserted}")
            for sensor_type, count in rows_per_sensor.items():
                print(f"    - {sensor_type}: {count} rows")
            
        except Exception as e:
            print(f"❌ Error saving to database: {e}")
            raise

        # ==================== SAVE METADATA JSON FOR REFERENCE (LOCAL ONLY) ====================
        event_name_safe = event_name.replace(' ', '_').replace('/', '-')
        failure_date_str = failure_dt.strftime('%Y%m%d_%H%M%S')
        event_id = f"{event_name_safe}_{failure_date_str}"
        
        json_filename = f"{event_id}.json"
        json_path = os.path.join(self.events_dir, json_filename)
        
        # Calculate metadata
        accel_trends = multi_sensor_trends.get('acceleration', [])
        time_before_failure = abs(accel_trends[0]['time_delta']) if accel_trends else 0
        
        # Compute stats for each sensor
        sensor_stats = {}
        for sensor_type, trends in multi_sensor_trends.items():
            values = [t['mean'] for t in trends]
            slopes = [t['mean_slope'] for t in trends[:-1]]
            sensor_stats[sensor_type] = {
                'data_points': len(trends),
                'max_value': max(values) if values else 0,
                'min_value': min(values) if values else 0,
                'avg_value': sum(values) / len(values) if values else 0,
                'max_slope': max(slopes) if slopes else 0,
                'min_slope': min(slopes) if slopes else 0,
                'avg_slope': sum(slopes) / len(slopes) if slopes else 0
            }

        metadata = {
            'event_id': event_id,
            'event_name': event_name,
            'description': description,
            'failure_time_iso': failure_time_iso,
            'failure_timestamp_ms': failure_time_ms,
            'actual_data_time_iso': datetime.datetime.fromtimestamp(failure_time_ms / 1000).isoformat(),
            'time_before_failure_seconds': time_before_failure,
            'total_data_points_all_sensors': total_rows_inserted,
            'fault_id_in_database': fault_id,
            'rows_per_sensor': rows_per_sensor,
            'sensor_statistics': sensor_stats,
            'created_at': datetime.datetime.now().isoformat()
        }
        
        # Try to write metadata JSON (optional, for local development reference only)
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
        except (PermissionError, OSError):
            # On Render or if no write permissions, skip - data is in database anyway
            print(f"   ℹ️ Metadata JSON not saved to file (database has all data)")
        
        return {
            'success': True,
            'event_id': event_id,
            'fault_id': fault_id,
            'total_rows_inserted': total_rows_inserted,
            'rows_per_sensor': rows_per_sensor,
            'metadata': metadata,
            'multi_sensor_trends': multi_sensor_trends
        }
    
    def list_events(self) -> List[Dict]:
        """
        List all logged events with their metadata.
        Returns empty list if directory doesn't exist (e.g., on Render).
        
        Returns:
            List of event metadata dicts (or empty list if directory doesn't exist)
        """
        events = []
        
        # Handle case where events directory doesn't exist (e.g., on Render)
        if not os.path.exists(self.events_dir):
            return events
        
        try:
            filenames = os.listdir(self.events_dir)
        except OSError as e:
            print(f"⚠️ Could not list events directory: {e}")
            return events
        
        for filename in filenames:
            if filename.endswith('.json'):
                json_path = os.path.join(self.events_dir, filename)
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        events.append(metadata)
                except Exception as e:
                    print(f"Error reading event metadata {filename}: {e}")
                    continue
        
        # Sort by creation time (newest first)
        events.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return events
    
    def get_event(self, event_id: str) -> Optional[Dict]:
        """
        Get detailed data for a specific event.

        Reads the metadata JSON (written locally at event creation time) and
        queries trend rows from the fault-specific database table using the
        fault_id stored in that metadata.  CSV files are no longer used.

        Args:
            event_id: Event identifier (e.g. "Motor_Stall_20260613_125401")

        Returns:
            Dict with 'metadata' and 'trend_data' (list of per-sensor rows),
            or None if the metadata JSON is not found.
        """
        from database import get_connection, FAILURE_TABLE_MAPPING

        json_path = os.path.join(self.events_dir, f"{event_id}.json")
        if not os.path.exists(json_path):
            return None

        with open(json_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        fault_id   = metadata.get('fault_id_in_database')
        event_name = metadata.get('event_name')
        table_name = FAILURE_TABLE_MAPPING.get(event_name) if event_name else None

        if fault_id is None or table_name is None:
            # Metadata exists but we cannot map to a table - return metadata only
            return {'metadata': metadata, 'trend_data': []}

        try:
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute(
                f"""
                SELECT sensor_type, timestamp,
                       mean, x_max, x_min, standard_deviation,
                       range, variance, skewness, kurtosis,
                       frequency1, frequency2, frequency3, frequency4, frequency5,
                       amplitude1, amplitude2, amplitude3, amplitude4, amplitude5
                FROM {table_name}
                WHERE fault_id = %s
                ORDER BY sensor_type, timestamp
                """,
                (fault_id,)
            )
            rows = cur.fetchall()
            conn.close()

            def _f(v):
                """Safe float conversion."""
                try:
                    return float(v) if v is not None else 0.0
                except (TypeError, ValueError):
                    return 0.0

            trend_data = []
            for row in rows:
                ts_raw = row[1]
                ts_ms  = (ts_raw.timestamp() * 1000
                          if hasattr(ts_raw, 'timestamp') else _f(ts_raw))
                trend_data.append({
                    'sensor_type': row[0],
                    'timestamp':   ts_ms,
                    'mean':        _f(row[2]),
                    'max':         _f(row[3]),
                    'min':         _f(row[4]),
                    'std_dev':     _f(row[5]),
                    'range':       _f(row[6]),
                    'variance':    _f(row[7]),
                    'skewness':    _f(row[8]),
                    'kurtosis':    _f(row[9]),
                    'frequency1':  _f(row[10]),
                    'frequency2':  _f(row[11]),
                    'frequency3':  _f(row[12]),
                    'frequency4':  _f(row[13]),
                    'frequency5':  _f(row[14]),
                    'amplitude1':  _f(row[15]),
                    'amplitude2':  _f(row[16]),
                    'amplitude3':  _f(row[17]),
                    'amplitude4':  _f(row[18]),
                    'amplitude5':  _f(row[19]),
                })

            return {'metadata': metadata, 'trend_data': trend_data}

        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                "get_event DB query failed for fault_id=%s table=%s: %s",
                fault_id, table_name, e
            )
            return {'metadata': metadata, 'trend_data': [], 'error': str(e)}
    
    def get_unique_event_names(self) -> List[str]:
        """
        Get list of unique event names for dropdown.
        
        Returns:
            List of unique event names
        """
        events = self.list_events()
        unique_names = list(set([event['event_name'] for event in events]))
        unique_names.sort()
        return unique_names
