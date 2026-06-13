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
        'kurtosis': safe_float(kurtosis_val),
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
    
    def _load_all_sensor_data(self) -> Dict[str, List[Dict]]:
        """
        Load aggregated feature data for ALL sensors from database tables.
        Queries acceleration, current, and audio tables for last 24 hours.
        
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
        from datetime import datetime, timedelta
        import logging
        
        logger = logging.getLogger(__name__)
        
        sensor_data = {'acceleration': [], 'current': [], 'audio': []}
        table_names = {
            'acceleration': 'acceleration',
            'current': 'current',
            'audio': 'audio'
        }
        
        logger.info(f"🔍 Querying database for all available data (no time filter)")
        
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            for sensor_type, table_name in table_names.items():
                try:
                    # Query ALL MAX file_type data, ordered by created_at ASC (chronological)
                    query = f"""
                        SELECT 
                            x_min, x_max, mean, standard_deviation, range,
                            skewness, kurtosis,
                            frequency1, frequency2, frequency3, frequency4, frequency5,
                            amplitude1, amplitude2, amplitude3, amplitude4, amplitude5,
                            created_at, file_type
                        FROM {table_name}
                        WHERE file_type = 'max'
                        ORDER BY created_at ASC
                    """
                    
                    logger.debug(f"Executing query for {sensor_type}: {query}")
                    cur.execute(query)
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
    
    def _calculate_feature_slopes(self, sensor_data: List[Dict], failure_idx: int) -> Dict:
        """
        Calculate slopes for all features (mean, max, std_dev, kurtosis) for a sensor.
        
        Args:
            sensor_data: List of dicts with features for one sensor
            failure_idx: Index of failure point
            
        Returns:
            Dict with slope data for each feature
        """
        features = ['mean', 'max', 'std_dev', 'kurtosis']
        slopes = {feature: [] for feature in features}
        failure_time = sensor_data[failure_idx]['timestamp']
        
        # Calculate backwards from failure
        for i in range(failure_idx, max(-1, failure_idx - 100), -1):
            for feature in features:
                if i == failure_idx:
                    slope = 0.0
                else:
                    time_diff = sensor_data[i + 1]['timestamp'] - sensor_data[i]['timestamp']
                    value_diff = sensor_data[i + 1][feature] - sensor_data[i][feature]
                    
                    if time_diff > 0:
                        slope = value_diff / (time_diff / 1000)
                    else:
                        slope = 0.0
                
                slopes[feature].append({
                    'timestamp': sensor_data[i]['timestamp'],
                    'slope': slope,
                    'value': sensor_data[i][feature],
                    'time_delta': (sensor_data[i]['timestamp'] - failure_time) / 1000
                })
        
        # Reverse to chronological order
        for feature in slopes:
            slopes[feature].reverse()
        
        return slopes
    
    def _find_stable_baseline_idx(self, sensor_data: Dict) -> int:
        """
        Find index where all sensors show stable baseline (3 consecutive stable points).
        Uses multi-sensor approach: ALL sensors must be stable.
        
        Args:
            sensor_data: Dict with sensor data for all three sensors
            
        Returns:
            Index of failure point (assuming last point is failure)
        """
        return len(sensor_data.get('acceleration', [])) - 1
    
    def _extract_multi_sensor_trends(self, sensor_data: Dict) -> Dict[str, List[Dict]]:
        """
        Extract trend data for all sensors.
        Dynamically detects when a statistical feature first starts to deviate from its normal baseline.
        Extracts exactly 3 normal baseline points followed by the deviation ramp leading to failure.
        """
        ALL_FEATURES = ['mean', 'max', 'min', 'std_dev', 'variance', 'skewness', 'kurtosis']
        
        # Assume all sensors have same timestamps; use acceleration as reference
        accel_data = sensor_data.get('acceleration', [])
        if not accel_data:
            raise ValueError("No acceleration data available")
        
        failure_idx = len(accel_data) - 1
        failure_time = accel_data[failure_idx]['timestamp']
        
        # Calculate normal baseline stats (mean & standard deviation) for each sensor and feature
        # using the first 5 records of the dataset.
        baseline_size = min(5, len(accel_data))
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

        # Detect the first index 'd' where any statistical feature starts behaving abnormally.
        deviation_idx = None
        for i in range(baseline_size, len(accel_data)):
            for sensor_type in ['acceleration', 'current', 'audio']:
                if sensor_type not in sensor_data or i >= len(sensor_data[sensor_type]):
                    continue
                point = sensor_data[sensor_type][i]
                for feature in ALL_FEATURES:
                    val = point.get(feature)
                    if val is None:
                        continue
                    b_mean, b_std = baselines[sensor_type].get(feature, (0.0, 0.0))
                    
                    # Establish an adaptive threshold (min 0.05 or 5% of baseline value to avoid noise triggering)
                    threshold = max(3.0 * b_std, 0.05 * abs(b_mean), 0.05)
                    
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
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"🎯 Deviation detected at index {deviation_idx} ({datetime.datetime.fromtimestamp(accel_data[deviation_idx]['timestamp']/1000).isoformat()}). Setting start_idx to {start_idx} (3 normal points before).")
        else:
            # Fallback if no deviation detected: capture last 10 points
            start_idx = max(0, failure_idx - 10)
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"⚠️ No deviation detected. Defaulting start_idx to {start_idx}.")

        # Extract trends for each sensor from start_idx to failure_idx
        trends = {}
        for sensor_type in ['acceleration', 'current', 'audio']:
            if sensor_type not in sensor_data:
                continue
            
            sensor_points = sensor_data[sensor_type]
            trend_data = []
            
            for i in range(start_idx, min(failure_idx + 1, len(sensor_points))):
                point_data = {
                    'timestamp': sensor_points[i]['timestamp'],
                    'time_delta': (sensor_points[i]['timestamp'] - failure_time) / 1000,
                    'mean': sensor_points[i].get('mean', 0),
                    'max': sensor_points[i].get('max', 0),
                    'min': sensor_points[i].get('min', 0),
                    'std_dev': sensor_points[i].get('std_dev', 0),
                    'kurtosis': sensor_points[i].get('kurtosis', 0),
                    'variance': sensor_points[i].get('variance', 0),
                    'skewness': sensor_points[i].get('skewness', 0),
                    'frequency1': sensor_points[i].get('frequency1', 0),
                    'frequency2': sensor_points[i].get('frequency2', 0),
                    'frequency3': sensor_points[i].get('frequency3', 0),
                    'frequency4': sensor_points[i].get('frequency4', 0),
                    'frequency5': sensor_points[i].get('frequency5', 0),
                    'amplitude1': sensor_points[i].get('amplitude1', 0),
                    'amplitude2': sensor_points[i].get('amplitude2', 0),
                    'amplitude3': sensor_points[i].get('amplitude3', 0),
                    'amplitude4': sensor_points[i].get('amplitude4', 0),
                    'amplitude5': sensor_points[i].get('amplitude5', 0),
                }
                
                # Calculate slopes for ALL features at this point
                if i < len(sensor_points) - 1:
                    next_point = sensor_points[i + 1]
                    time_diff = next_point['timestamp'] - sensor_points[i]['timestamp']
                    
                    if time_diff > 0:
                        point_data['mean_slope'] = (next_point['mean'] - sensor_points[i]['mean']) / (time_diff / 1000)
                        point_data['max_slope'] = (next_point['max'] - sensor_points[i]['max']) / (time_diff / 1000)
                        point_data['min_slope'] = (next_point['min'] - sensor_points[i]['min']) / (time_diff / 1000)
                        point_data['std_dev_slope'] = (next_point['std_dev'] - sensor_points[i]['std_dev']) / (time_diff / 1000)
                        point_data['variance_slope'] = (next_point['variance'] - sensor_points[i]['variance']) / (time_diff / 1000)
                        point_data['skewness_slope'] = (next_point['skewness'] - sensor_points[i]['skewness']) / (time_diff / 1000)
                        point_data['kurtosis_slope'] = (next_point['kurtosis'] - sensor_points[i]['kurtosis']) / (time_diff / 1000)
                    else:
                        # No time diff
                        for feature in ALL_FEATURES:
                            point_data[f'{feature}_slope'] = 0.0
                else:
                    # Last point (failure) - slopes are zero
                    for feature in ALL_FEATURES:
                        point_data[f'{feature}_slope'] = 0.0
                
                trend_data.append(point_data)
            
            trends[sensor_type] = trend_data
        
        return trends

        """
        Calculate slopes BACKWARDS from the failure point to previous data.
        This shows what LED TO the failure, including the stable baseline period.
        Extracts: all deviation points + 3 stable baseline points.
        
        Args:
            data_points: List of (timestamp, value) tuples
            failure_idx: Index of failure point
            
        Returns:
            List of dicts with timestamp, value, slope, and time_delta (going backwards)
        """
        NEGLIGIBLE_SLOPE_THRESHOLD = 0.001  # Threshold for detecting "stable" slopes
        MAX_LOOKBACK_POINTS = 100  # Maximum number of points to track backwards
        STABLE_POINTS_TO_CAPTURE = 3  # Number of consecutive stable points to include in baseline
        
        slope_data = []
        failure_time = data_points[failure_idx][0]
        stable_slope_count = 0  # Track consecutive stable slopes
        
        # Start from failure and go backwards
        for i in range(failure_idx, max(-1, failure_idx - MAX_LOOKBACK_POINTS), -1):
            timestamp = data_points[i][0]
            value = data_points[i][1]
            
            # Calculate slope (comparing current point to next point in time)
            if i == failure_idx:
                slope = 0.0  # Failure point has no slope (reference point)
            else:
                next_timestamp = data_points[i + 1][0]
                next_value = data_points[i + 1][1]
                time_diff = next_timestamp - timestamp
                value_diff = next_value - value
                
                # Avoid division by zero
                if time_diff > 0:
                    slope = value_diff / (time_diff / 1000)  # Slope per second
                else:
                    slope = 0.0
            
            # Time delta is negative (going backwards in time)
            time_delta = (timestamp - failure_time) / 1000  # Convert to seconds (will be negative)
            
            slope_data.append({
                'timestamp': timestamp,
                'value': value,
                'slope': slope,
                'time_delta': time_delta
            })
            
            # Track consecutive stable slopes (baseline detection)
            if i < failure_idx and abs(slope) < NEGLIGIBLE_SLOPE_THRESHOLD:
                stable_slope_count += 1
            else:
                stable_slope_count = 0  # Reset if deviation detected again
            
            # Stop once we've captured 3 consecutive stable points (stable baseline reached)
            if stable_slope_count >= STABLE_POINTS_TO_CAPTURE:
                break
        
        # Reverse the list so it's chronological (oldest to newest, ending at failure)
        slope_data.reverse()
        
        return slope_data
    
    def create_event(self, event_name: str, failure_time_iso: str, description: str = "") -> Dict:
        """
        Create a new event with multi-sensor trend tracking BACKWARDS from failure.
        Extracts trends based on aggregated features for acceleration, current, and audio.
        
        Args:
            event_name: Name of the event (e.g., "Bearing Failure")
            failure_time_iso: ISO format timestamp of failure (e.g., "2025-11-27T12:24:00")
            description: Optional description of the event
            
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
        sensor_data = self._load_all_sensor_data()
        
        if not sensor_data.get('acceleration'):
            raise ValueError("No acceleration data available in database tables (acceleration, current, audio). Check: 1) Database connection, 2) Tables are populated, 3) Data exists from last 24 hours")
        
        # Extract multi-sensor trends
        multi_sensor_trends = self._extract_multi_sensor_trends(sensor_data)
        
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
            'metadata': metadata
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
        
        Args:
            event_id: Event identifier
            
        Returns:
            Dict with metadata and CSV data, or None if not found
        """
        json_path = os.path.join(self.events_dir, f"{event_id}.json")
        csv_path = os.path.join(self.events_dir, f"{event_id}.csv")
        
        if not os.path.exists(json_path) or not os.path.exists(csv_path):
            return None
        
        # Load metadata
        with open(json_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Load CSV data
        slope_data = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                slope_data.append({
                    'timestamp': float(row['timestamp']),
                    'timestamp_iso': row['timestamp_iso'],
                    'value': float(row['value']),
                    'slope': float(row['slope']),
                    'time_delta_seconds': float(row['time_delta_seconds'])
                })
        
        return {
            'metadata': metadata,
            'slope_data': slope_data
        }
    
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
