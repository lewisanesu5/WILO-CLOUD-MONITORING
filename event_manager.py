"""
Event Manager Module
Handles logging of failure events with slope tracking BACKWARDS from failure point.
Tracks slope changes that LED TO the failure.
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
    
    def _calculate_slopes_backwards(self, data_points: List[Tuple[float, float]], failure_idx: int) -> List[Dict]:
        """
        Calculate slopes BACKWARDS from the failure point to previous data.
        This shows what LED TO the failure.
        
        Args:
            data_points: List of (timestamp, value) tuples
            failure_idx: Index of failure point
            
        Returns:
            List of dicts with timestamp, value, slope, and time_delta (going backwards)
        """
        NEGLIGIBLE_SLOPE_THRESHOLD = 0.001  # Adjust based on data characteristics
        MAX_LOOKBACK_POINTS = 100  # Maximum number of points to track backwards
        
        slope_data = []
        failure_time = data_points[failure_idx][0]
        
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
            
            # Check if we've reached negligible slope (stable baseline before failure)
            if i < failure_idx and abs(slope) < NEGLIGIBLE_SLOPE_THRESHOLD:
                # Check previous few points to confirm stability
                all_negligible = True
                for j in range(i - 1, max(-1, i - 5), -1):
                    if j < 0:
                        break
                    curr_timestamp = data_points[j][0]
                    curr_value = data_points[j][1]
                    next_timestamp = data_points[j + 1][0]
                    next_value = data_points[j + 1][1]
                    time_diff = next_timestamp - curr_timestamp
                    
                    if time_diff > 0:
                        check_slope = (next_value - curr_value) / (time_diff / 1000)
                        if abs(check_slope) >= NEGLIGIBLE_SLOPE_THRESHOLD:
                            all_negligible = False
                            break
                
                if all_negligible:
                    # Add a few more stable points for context
                    for j in range(i - 1, max(-1, i - 5), -1):
                        if j < 0:
                            break
                        timestamp = data_points[j][0]
                        value = data_points[j][1]
                        next_timestamp = data_points[j + 1][0]
                        next_value = data_points[j + 1][1]
                        time_diff = next_timestamp - timestamp
                        
                        if time_diff > 0:
                            slope = (next_value - value) / (time_diff / 1000)
                        else:
                            slope = 0.0
                        
                        time_delta = (timestamp - failure_time) / 1000
                        slope_data.append({
                            'timestamp': timestamp,
                            'value': value,
                            'slope': slope,
                            'time_delta': time_delta
                        })
                    break
        
        # Reverse the list so it's chronological (oldest to newest, ending at failure)
        slope_data.reverse()
        
        return slope_data
    
    def create_event(self, event_name: str, failure_time_iso: str, description: str = "") -> Dict:
        """
        Create a new event with slope tracking BACKWARDS from failure to baseline.
        
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
        
        # Load all data points
        data_points = self._load_all_data_points()
        
        if not data_points:
            raise ValueError("No data available in Data directory")
        
        # Find data point at or before failure time
        failure_idx = self._find_nearest_data_point(failure_time_ms, data_points)
        
        if failure_idx is None:
            raise ValueError("Could not find data point at or before failure time")
        
        # Get failure value and source filename
        failure_timestamp = data_points[failure_idx][0]
        failure_value = data_points[failure_idx][1]
        source_filename = data_points[failure_idx][2]
        
        # Calculate slopes BACKWARDS from failure to baseline
        slope_data = self._calculate_slopes_backwards(data_points, failure_idx)
        
        # Compute statistics over the entire event data window
        event_values = [p['value'] for p in slope_data]
        event_statistics = calculate_statistics(event_values)

        # ==================== INSERT TO NEON DATABASE ====================
        try:
            db_result = insert_event_data(event_name, slope_data, event_statistics, sensor_type='acceleration')
            fault_id = db_result['fault_id']
            rows_inserted = db_result['rows_inserted']
            
            print(f"\n✓ Event saved to Neon database!")
            print(f"  Table: {db_result['table_name']}")
            print(f"  Fault ID: {fault_id}")
            print(f"  Rows Inserted: {rows_inserted}")
            
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
        time_before_failure = abs(slope_data[0]['time_delta']) if slope_data else 0
        slopes = [p['slope'] for p in slope_data[:-1]]  # Skip last point (failure, slope=0)

        metadata = {
            'event_id': event_id,
            'event_name': event_name,
            'description': description,
            'failure_time_iso': failure_time_iso,
            'failure_timestamp_ms': failure_timestamp,
            'failure_value': failure_value,
            'source_filename': source_filename,
            'actual_data_time_iso': datetime.datetime.fromtimestamp(failure_timestamp / 1000).isoformat(),
            'time_before_failure_seconds': time_before_failure,
            'total_data_points': len(slope_data),
            'fault_id_in_database': fault_id,
            'rows_in_database': rows_inserted,
            'slope_statistics': {
                'max_slope': max(slopes) if slopes else 0,
                'min_slope': min(slopes) if slopes else 0,
                'avg_slope': sum(slopes) / len(slopes) if slopes else 0
            },
            'statistics': event_statistics,
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
            'rows_inserted': rows_inserted,
            'database_table': db_result['table_name'],
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
