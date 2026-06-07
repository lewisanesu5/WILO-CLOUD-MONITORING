from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import glob
import csv
import shutil
import json
import numpy as np
from scipy import stats
import datetime as dt
import logging
from functools import wraps
import hashlib
import time
import multiprocessing
import threading
from dotenv import load_dotenv
from database import save_statistics, test_connection, get_all_latest_statistics_by_mode
from event_manager import EventManager

load_dotenv()

app = Flask(__name__)

# CORS configuration - allow frontend and production domains
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # Add your production domain here:
    # "https://your-domain.com",
    # "https://your-domain.onrender.com"
]

# Configure CORS with explicit options
CORS(app, 
     origins=ALLOWED_ORIGINS,
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
     allow_headers=['Content-Type', 'Authorization'],
     supports_credentials=False,
     max_age=3600)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test database connection on startup
try:
    if test_connection():
        logger.info("Connected to Neon database successfully")
except Exception as e:
    logger.warning(f"Database connection not available: {e}")

# Configure directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'Data')
UPLOAD_LOG_DIR = os.path.join(BASE_DIR, 'UploadLogs')
EVENTS_DIR = os.path.join(BASE_DIR, 'Events')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_LOG_DIR, exist_ok=True)
os.makedirs(EVENTS_DIR, exist_ok=True)

event_manager = EventManager(EVENTS_DIR, DATA_DIR)

# ======================== REQUEST LOGGING FOR DEBUGGING ========================
@app.before_request
def log_request():
    """Log all incoming requests with headers for CORS debugging"""
    logger.info(f"{'='*60}")
    logger.info(f"REQUEST: {request.method} {request.path}")
    logger.info(f"Origin: {request.headers.get('Origin', 'N/A')}")
    logger.info(f"Content-Type: {request.headers.get('Content-Type', 'N/A')}")
    if request.method == 'OPTIONS':
        logger.info(f"PREFLIGHT REQUEST DETECTED")
        logger.info(f"Access-Control-Request-Method: {request.headers.get('Access-Control-Request-Method', 'N/A')}")
        logger.info(f"Access-Control-Request-Headers: {request.headers.get('Access-Control-Request-Headers', 'N/A')}")
    logger.info(f"{'='*60}")

@app.after_request
def log_response(response):
    """Log response headers for CORS debugging"""
    logger.info(f"RESPONSE: {response.status}")
    logger.info(f"Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin', 'NOT SET')}")
    logger.info(f"Access-Control-Allow-Methods: {response.headers.get('Access-Control-Allow-Methods', 'NOT SET')}")
    logger.info(f"Access-Control-Allow-Headers: {response.headers.get('Access-Control-Allow-Headers', 'NOT SET')}")
    return response

# ======================== SEQUENTIAL FAULT RUNNER STATE ========================
sequential_runner_state = {
    'active': False,
    'status': 'idle',
    'current_fault': '',
    'current_fault_number': 0,
    'total_faults': 11,
    'cycles': 1,
    'last_log': '',
    'process': None,
    'lock': threading.Lock()
}

# Sensor configuration
SENSORS = ['acceleration', 'current', 'audio']
SAMPLING_RATE = 700  # 1400 points per 2 seconds

# Upload security configuration
UPLOAD_API_KEYS = {
    'sensor-001': 'sk_prod_7f3b8e2a9c1d4f6e5a2b9c8d7e1f3a5b',
    'sensor-002': 'sk_prod_2c5d8f1a4e7b9a3d6f2e5c8b1a4d7f3e'
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_CSV_ROWS = 10000  # Reasonable for 2-second samples
UPLOAD_FREQUENCY_MINUTES = 110  # Min 110 mins between uploads (2hr target +10min buffer)
UPLOAD_BATCH_SIZE = 2  # Expected 2 files per upload (max and min)

def load_csv_data(filename):
    """Load CSV data and return timestamps, values, and file modified timestamp (ISO).

    Returns: (timestamps_ms_list, values_list, file_modified_iso or None)
    """
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return [], [], None
    
    timestamps = []
    values = []
    file_modified_iso = None
    try:
        # Record file modified time
        try:
            mtime = os.path.getmtime(filepath)
            file_modified_iso = dt.datetime.fromtimestamp(mtime).isoformat()
        except Exception:
            file_modified_iso = None

        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Handle timestamp
                    timestamp_str = row.get('timestamp', '')
                    if isinstance(timestamp_str, str) and 'T' in timestamp_str:  # ISO format
                        dt_obj = dt.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        timestamp = dt_obj.timestamp() * 1000
                    else:
                        # If timestamp is numeric string, try float (assumed seconds or milliseconds)
                        ts_val = float(timestamp_str)
                        # Heuristic: if ts looks like seconds (10 digits), convert to ms
                        if ts_val < 1e11:
                            timestamp = ts_val * 1000
                        else:
                            timestamp = ts_val
                    
                    # Handle value
                    value = float(row.get('value', 0))
                    timestamps.append(timestamp)
                    values.append(value)
                except (ValueError, KeyError):
                    continue
    except Exception as e:
        logger.error(f"Error loading {filename}: {e}")
    
    return timestamps, values, file_modified_iso

def merge_max_min_files(max_timestamps, max_values, min_timestamps, min_values):
    """
    Merge max and min files by sorting all values by timestamp.
    Returns sorted combined timestamps and values.
    """
    if not max_values or not min_values:
        return [], []
    
    # Create list of (timestamp, value) tuples
    combined = []
    for ts, val in zip(max_timestamps, max_values):
        combined.append((ts, val))
    for ts, val in zip(min_timestamps, min_values):
        combined.append((ts, val))
    
    # Sort by timestamp
    combined.sort(key=lambda x: x[0])
    
    # Separate back into timestamps and values
    merged_timestamps = [item[0] for item in combined]
    merged_values = [item[1] for item in combined]
    
    return merged_timestamps, merged_values

def calculate_statistics(values):
    """Calculate statistical parameters for sensor data."""
    if not values or len(values) == 0:
        return {}
    
    def safe_float(val):
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return 0.0
        return f
    
    z_array = np.array(values)
    
    stats_dict = {
        'mean': safe_float(np.mean(z_array)),
        'max': safe_float(np.max(z_array)),
        'min': safe_float(np.min(z_array)),
        'std_dev': safe_float(np.std(z_array)),
        'range': safe_float(np.max(z_array) - np.min(z_array)),
        'skewness': safe_float(stats.skew(z_array)),
        'kurtosis': safe_float(stats.kurtosis(z_array))
    }
    
    return stats_dict

def calculate_fft_analysis(values):
    """
    Calculate FFT and extract top 5 frequencies and amplitudes.
    Returns frequencies in Hz and their corresponding amplitudes.
    """
    if not values or len(values) < 2:
        return [], []
    
    z_array = np.array(values)
    
    # Perform FFT
    fft_result = np.fft.fft(z_array)
    frequencies = np.fft.fftfreq(len(z_array), d=1.0/SAMPLING_RATE)
    amplitudes = np.abs(fft_result)
    
    # Get only positive frequencies
    positive_freq_idx = frequencies > 0
    positive_freqs = frequencies[positive_freq_idx]
    positive_amps = amplitudes[positive_freq_idx]
    
    if len(positive_amps) == 0:
        return [], []
    
    # Get top 5
    top_indices = np.argsort(positive_amps)[-5:][::-1]
    
    top_frequencies = [float(positive_freqs[i]) for i in top_indices if i < len(positive_freqs)]
    top_amplitudes = [float(positive_amps[i]) for i in top_indices if i < len(positive_amps)]
    
    # Pad with zeros if less than 5
    while len(top_frequencies) < 5:
        top_frequencies.append(0.0)
        top_amplitudes.append(0.0)
    
    return top_frequencies[:5], top_amplitudes[:5]

def calculate_fft_full_spectrum(values):
    """
    Calculate full FFT spectrum for line graph visualization.
    Returns frequencies in Hz and their corresponding amplitudes.
    """
    if not values or len(values) < 2:
        return [], []
    
    z_array = np.array(values)
    
    # Perform FFT
    fft_result = np.fft.fft(z_array)
    frequencies = np.fft.fftfreq(len(z_array), d=1.0/SAMPLING_RATE)
    amplitudes = np.abs(fft_result)
    
    # Get only positive frequencies
    positive_freq_idx = frequencies > 0
    positive_freqs = frequencies[positive_freq_idx]
    positive_amps = amplitudes[positive_freq_idx]
    
    if len(positive_amps) == 0:
        return [], []
    
    # Downsample to 500 points max for cleaner visualization
    if len(positive_freqs) > 500:
        step = len(positive_freqs) // 500
        positive_freqs = positive_freqs[::step]
        positive_amps = positive_amps[::step]
    
    return [float(f) for f in positive_freqs], [float(a) for a in positive_amps]

def get_sensor_health_status(stats_dict):
    """Determine health status based on statistics."""
    if not stats_dict:
        return 'unknown'
    
    # Health thresholds
    kurtosis_critical = 5.0
    std_dev_warning = 2.0
    
    kurtosis = stats_dict.get('kurtosis', 0)
    std_dev = stats_dict.get('std_dev', 0)
    
    if kurtosis > kurtosis_critical:
        return 'critical'
    elif kurtosis > kurtosis_critical * 0.6 or std_dev > std_dev_warning:
        return 'warning'
    else:
        return 'normal'

def extract_stats_from_db_row(row):
    """Extract stats dict from database row."""
    if not row:
        return {}
    row_dict = dict(row) if hasattr(row, '__getitem__') else row
    return {
        'min': row_dict.get('x_min', 0),
        'max': row_dict.get('x_max', 0),
        'mean': row_dict.get('mean', 0),
        'range': row_dict.get('range', 0),
        'std_dev': row_dict.get('standard_deviation', 0),
        'skewness': row_dict.get('skewness', 0),
        'kurtosis': row_dict.get('kurtosis', 0)
    }

def extract_fft_from_db_row(row):
    """Extract FFT frequencies and amplitudes from database row."""
    if not row:
        return [], []
    row_dict = dict(row) if hasattr(row, '__getitem__') else row
    frequencies = [
        row_dict.get('frequency1', 0),
        row_dict.get('frequency2', 0),
        row_dict.get('frequency3', 0),
        row_dict.get('frequency4', 0),
        row_dict.get('frequency5', 0)
    ]
    amplitudes = [
        row_dict.get('amplitude1', 0),
        row_dict.get('amplitude2', 0),
        row_dict.get('amplitude3', 0),
        row_dict.get('amplitude4', 0),
        row_dict.get('amplitude5', 0)
    ]
    return frequencies, amplitudes

def get_latest_statistics_for_mode(sensor_name, mode):
    """Get latest statistics from database for a specific sensor and mode."""
    from database import get_latest_statistics
    try:
        return get_latest_statistics(sensor_name)
    except Exception as e:
        logger.warning(f"Could not get stats from DB for {sensor_name}: {e}")
        return None

def get_sensor_data_with_raw_data(mode='max'):
    """
    Get sensor data combining:
    - Raw CSV data (timestamps, values) for time-series charts
    - Calculated statistics from database
    
    This hybrid approach:
    - Keeps CSV loading for visualization
    - Gets pre-calculated stats from DB (efficient)
    """
    sensor_data = {}
    
    for sensor in SENSORS:
        sensor_data[sensor] = {}
        
        # Load raw data from CSV files for time-series display
        max_timestamps, max_values, max_file_ts = load_csv_data(f"max_{sensor}.csv")
        min_timestamps, min_values, min_file_ts = load_csv_data(f"min_{sensor}.csv")
        
        # Get stats from database instead of calculating
        try:
            max_stats_row = get_latest_statistics_for_mode(sensor, 'max')
            min_stats_row = get_latest_statistics_for_mode(sensor, 'min')
            combined_stats_row = get_latest_statistics_for_mode(sensor, 'combined')
        except Exception as e:
            logger.error(f"Could not fetch stats from DB for {sensor}: {e}")
            max_stats_row = None
            min_stats_row = None
            combined_stats_row = None
        
        # --- MAX MODE ---
        if max_values:
            max_stats = extract_stats_from_db_row(max_stats_row) if max_stats_row else calculate_statistics(max_values)
            max_frequencies, max_amplitudes = extract_fft_from_db_row(max_stats_row) if max_stats_row else calculate_fft_analysis(max_values)
            max_health = get_sensor_health_status(max_stats)
            
            sensor_data[sensor]['max'] = {
                'stats': max_stats,
                'frequencies': max_frequencies,
                'amplitudes': max_amplitudes,
                'health': max_health,
                'data_points': len(max_values),
                'raw_timestamps': max_timestamps,
                'raw_values': max_values,
                'file_timestamp': max_file_ts
            }
        else:
            sensor_data[sensor]['max'] = {
                'stats': {}, 'frequencies': [], 'amplitudes': [],
                'health': 'unknown', 'data_points': 0,
                'raw_timestamps': [], 'raw_values': []
            }
        
        # --- MIN MODE ---
        if min_values:
            min_stats = extract_stats_from_db_row(min_stats_row) if min_stats_row else calculate_statistics(min_values)
            min_frequencies, min_amplitudes = extract_fft_from_db_row(min_stats_row) if min_stats_row else calculate_fft_analysis(min_values)
            min_health = get_sensor_health_status(min_stats)
            
            sensor_data[sensor]['min'] = {
                'stats': min_stats,
                'frequencies': min_frequencies,
                'amplitudes': min_amplitudes,
                'health': min_health,
                'data_points': len(min_values),
                'raw_timestamps': min_timestamps,
                'raw_values': min_values,
                'file_timestamp': min_file_ts
            }
        else:
            sensor_data[sensor]['min'] = {
                'stats': {}, 'frequencies': [], 'amplitudes': [],
                'health': 'unknown', 'data_points': 0,
                'raw_timestamps': [], 'raw_values': []
            }
        
        # --- COMBINED MODE ---
        if max_values and min_values:
            merged_timestamps, merged_values = merge_max_min_files(max_timestamps, max_values, min_timestamps, min_values)
            combined_stats = extract_stats_from_db_row(combined_stats_row) if combined_stats_row else calculate_statistics(merged_values)
            combined_frequencies, combined_amplitudes = extract_fft_from_db_row(combined_stats_row) if combined_stats_row else calculate_fft_analysis(merged_values)
            combined_health = get_sensor_health_status(combined_stats)
            
            combined_file_ts = None
            try:
                if max_file_ts and min_file_ts:
                    dt_max = dt.datetime.fromisoformat(max_file_ts)
                    dt_min = dt.datetime.fromisoformat(min_file_ts)
                    combined_file_ts = dt_max.isoformat() if dt_max >= dt_min else dt_min.isoformat()
                else:
                    combined_file_ts = max_file_ts or min_file_ts
            except Exception:
                combined_file_ts = max_file_ts or min_file_ts

            sensor_data[sensor]['combined'] = {
                'stats': combined_stats,
                'frequencies': combined_frequencies,
                'amplitudes': combined_amplitudes,
                'health': combined_health,
                'data_points': len(merged_values),
                'raw_timestamps': merged_timestamps,
                'raw_values': merged_values,
                'file_timestamp': combined_file_ts
            }
        else:
            sensor_data[sensor]['combined'] = {
                'stats': {}, 'frequencies': [], 'amplitudes': [],
                'health': 'unknown', 'data_points': 0,
                'raw_timestamps': [], 'raw_values': []
            }
    
    return sensor_data

def load_all_sensor_data_with_modes():
    """
    Load data from all 6 CSV files and calculate statistics/FFT for all three modes.
    Returns: {sensor: {mode: {stats, frequencies, amplitudes, health, data_points}}}
    Also saves statistics to Neon database.
    """
    load_start = time.time()
    save_times = {'max': 0, 'min': 0, 'combined': 0}
    sensor_data = {}
    
    for sensor in SENSORS:
        sensor_data[sensor] = {}
        
        # Load max and min files (now also returns file modified timestamp)
        max_timestamps, max_values, max_file_ts = load_csv_data(f"max_{sensor}.csv")
        min_timestamps, min_values, min_file_ts = load_csv_data(f"min_{sensor}.csv")
        
        # --- MAX MODE ---
        if max_values:
            max_stats = calculate_statistics(max_values)
            max_frequencies, max_amplitudes = calculate_fft_analysis(max_values)
            max_full_freqs, max_full_amps = calculate_fft_full_spectrum(max_values)
            max_health = get_sensor_health_status(max_stats)
            
            sensor_data[sensor]['max'] = {
                'stats': max_stats,
                'frequencies': max_frequencies,
                'amplitudes': max_amplitudes,
                'full_spectrum_freqs': max_full_freqs,
                'full_spectrum_amps': max_full_amps,
                'health': max_health,
                'data_points': len(max_values),
                'raw_timestamps': max_timestamps,
                'raw_values': max_values,
                'file_timestamp': max_file_ts
            }
            
            # Save MAX statistics to database
            try:
                save_start = time.time()
                save_statistics(sensor, 'max', max_stats, max_frequencies, max_amplitudes)
                save_times['max'] += time.time() - save_start
            except Exception as e:
                logger.error(f"Failed to save {sensor} (max) statistics to database: {e}")
        else:
            sensor_data[sensor]['max'] = {
                'stats': {}, 'frequencies': [], 'amplitudes': [],
                'full_spectrum_freqs': [], 'full_spectrum_amps': [],
                'health': 'unknown', 'data_points': 0
            }
        
        # --- MIN MODE ---
        if min_values:
            min_stats = calculate_statistics(min_values)
            min_frequencies, min_amplitudes = calculate_fft_analysis(min_values)
            min_full_freqs, min_full_amps = calculate_fft_full_spectrum(min_values)
            min_health = get_sensor_health_status(min_stats)
            
            sensor_data[sensor]['min'] = {
                'stats': min_stats,
                'frequencies': min_frequencies,
                'amplitudes': min_amplitudes,
                'full_spectrum_freqs': min_full_freqs,
                'full_spectrum_amps': min_full_amps,
                'health': min_health,
                'data_points': len(min_values),
                'raw_timestamps': min_timestamps,
                'raw_values': min_values,
                'file_timestamp': min_file_ts
            }
            
            # Save MIN statistics to database
            try:
                save_start = time.time()
                save_statistics(sensor, 'min', min_stats, min_frequencies, min_amplitudes)
                save_times['min'] += time.time() - save_start
            except Exception as e:
                logger.error(f"Failed to save {sensor} (min) statistics to database: {e}")
        else:
            sensor_data[sensor]['min'] = {
                'stats': {}, 'frequencies': [], 'amplitudes': [],
                'full_spectrum_freqs': [], 'full_spectrum_amps': [],
                'health': 'unknown', 'data_points': 0
            }
        
        # --- COMBINED MODE ---
        if max_values and min_values:
            merged_timestamps, merged_values = merge_max_min_files(
                max_timestamps, max_values, min_timestamps, min_values
            )
            
            combined_stats = calculate_statistics(merged_values)
            combined_frequencies, combined_amplitudes = calculate_fft_analysis(merged_values)
            combined_full_freqs, combined_full_amps = calculate_fft_full_spectrum(merged_values)
            combined_health = get_sensor_health_status(combined_stats)
            
            # Determine latest file timestamp between max and min files
            combined_file_ts = None
            try:
                if max_file_ts and min_file_ts:
                    dt_max = dt.datetime.fromisoformat(max_file_ts)
                    dt_min = dt.datetime.fromisoformat(min_file_ts)
                    combined_file_ts = dt_max.isoformat() if dt_max >= dt_min else dt_min.isoformat()
                else:
                    combined_file_ts = max_file_ts or min_file_ts
            except Exception:
                combined_file_ts = max_file_ts or min_file_ts

            sensor_data[sensor]['combined'] = {
                'stats': combined_stats,
                'frequencies': combined_frequencies,
                'amplitudes': combined_amplitudes,
                'full_spectrum_freqs': combined_full_freqs,
                'full_spectrum_amps': combined_full_amps,
                'health': combined_health,
                'data_points': len(merged_values),
                'raw_timestamps': merged_timestamps,
                'raw_values': merged_values,
                'file_timestamp': combined_file_ts
            }
            
            # Save COMBINED statistics to database
            try:
                save_start = time.time()
                save_statistics(sensor, 'combined', combined_stats, combined_frequencies, combined_amplitudes)
                save_times['combined'] += time.time() - save_start
            except Exception as e:
                logger.error(f"Failed to save {sensor} (combined) statistics to database: {e}")
        else:
            sensor_data[sensor]['combined'] = {
                'stats': {}, 'frequencies': [], 'amplitudes': [],
                'full_spectrum_freqs': [], 'full_spectrum_amps': [],
                'health': 'unknown', 'data_points': 0
            }
    
    total_load_time = time.time() - load_start
    logger.info(
        f"📊 Data load complete: "
        f"total={total_load_time*1000:.1f}ms, "
        f"max_saves={save_times['max']*1000:.1f}ms, "
        f"min_saves={save_times['min']*1000:.1f}ms, "
        f"combined_saves={save_times['combined']*1000:.1f}ms | "
        f"3 sensors × 3 modes = 9 database rows"
    )
    
    return sensor_data

@app.route('/api/sensor-data')
def get_sensor_data():
    """
    Get sensor data from database + raw CSV files.
    - Stats: Fetched from Render PostgreSQL
    - Raw data: Loaded from Data/ directory on Render
    """
    api_start = time.time()
    try:
        mode = request.args.get('mode', 'max').lower()
        
        if mode not in ['max', 'min', 'combined']:
            return jsonify({'status': 'error', 'message': f'Invalid mode: {mode}'}), 400
        
        # Get sensor data with both raw CSV data and database statistics
        sensor_data = get_sensor_data_with_raw_data(mode)
        
        # Filter data for requested mode
        filtered_data = {}
        for sensor_name, modes in sensor_data.items():
            if mode in modes:
                filtered_data[sensor_name] = modes[mode]
        
        api_time = time.time() - api_start
        logger.info(f"🚀 /api/sensor-data ({mode}) response time: {api_time*1000:.1f}ms")
        
        return jsonify({
            'status': 'success',
            'mode': mode,
            'data': filtered_data,
            'timestamp': dt.datetime.now().isoformat(),
            'response_time_ms': round(api_time * 1000, 2)
        })
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/sensor/<sensor_name>')
def get_sensor_detail(sensor_name):
    """Get detailed data for a specific sensor in all modes."""
    api_start = time.time()
    if sensor_name not in SENSORS:
        return jsonify({'error': 'Invalid sensor'}), 400
    
    try:
        sensor_data = load_all_sensor_data_with_modes()
        data = sensor_data.get(sensor_name, {})
        
        api_time = time.time() - api_start
        logger.info(f"🚀 /api/sensor/{sensor_name} response time: {api_time*1000:.1f}ms")
        
        return jsonify({
            'sensor': sensor_name,
            'max': data.get('max', {}),
            'min': data.get('min', {}),
            'combined': data.get('combined', {}),
            'response_time_ms': round(api_time * 1000, 2)
        })
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/files')
def get_files():
    """List all CSV files in Data directory."""
    files = []
    try:
        for filepath in glob.glob(os.path.join(DATA_DIR, '*.csv')):
            stat = os.stat(filepath)
            files.append({
                'name': os.path.basename(filepath),
                'size': stat.st_size,
                'modified': dt.datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """
    Secure endpoint for remote servers to upload sensor CSV files.
    
    Expected:
    - API Key in header: X-API-Key
    - 2 files: max_<sensor>.csv and min_<sensor>.csv
    
    Returns validation report and upload timestamp.
    """
    try:
        # 1. AUTHENTICATION
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            logger.warning('Upload attempt without API key')
            return jsonify({'status': 'error', 'message': 'Missing API key'}), 401
        
        if api_key not in UPLOAD_API_KEYS.values():
            logger.warning(f'Upload attempt with invalid API key: {api_key[:10]}...')
            return jsonify({'status': 'error', 'message': 'Invalid API key'}), 403
        
        sensor_id = [k for k, v in UPLOAD_API_KEYS.items() if v == api_key][0]
        
        # 2. FILE VALIDATION
        if 'files' not in request.files:
            logger.warning(f'Upload attempt from {sensor_id} with no files')
            return jsonify({'error': 'No files provided'}), 400
        
        uploaded_files = request.files.getlist('files')
        if len(uploaded_files) != UPLOAD_BATCH_SIZE:
            logger.warning(f'Upload from {sensor_id}: Expected {UPLOAD_BATCH_SIZE} files, got {len(uploaded_files)}')
            return jsonify({
                'error': f'Expected {UPLOAD_BATCH_SIZE} files, got {len(uploaded_files)}'
            }), 400
        
        saved_files = []
        validation_report = []
        upload_timestamp = dt.datetime.now().isoformat()
        
        for file in uploaded_files:
            if not file or not file.filename.endswith('.csv'):
                return jsonify({'error': f'Invalid file format: {file.filename}'}), 400
            
            # Validate filename format
            if not validate_filename(file.filename):
                return jsonify({'error': f'Invalid filename format: {file.filename}'}), 400
            
            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > MAX_FILE_SIZE:
                return jsonify({'error': f'File too large: {file.filename}'}), 413
            
            # Validate CSV content
            validation_result = validate_csv_file(file)
            if not validation_result['valid']:
                logger.warning(f'Invalid CSV from {sensor_id}: {file.filename} - {validation_result["error"]}')
                return jsonify({
                    'error': f'Invalid CSV format: {validation_result["error"]}'
                }), 400
            
            # Save file
            try:
                filepath = os.path.join(DATA_DIR, file.filename)
                file.seek(0)
                file.save(filepath)
                saved_files.append(file.filename)
                
                validation_report.append({
                    'file': file.filename,
                    'rows': validation_result['row_count'],
                    'size_kb': round(file_size / 1024, 2),
                    'status': 'success'
                })
                
                logger.info(f'Successfully saved {file.filename} from {sensor_id} ({validation_result["row_count"]} rows)')
            except Exception as e:
                logger.error(f'Failed to save {file.filename}: {str(e)}')
                return jsonify({'error': f'Failed to save file: {str(e)}'}), 500
        
        # 3. LOG UPLOAD EVENT
        log_upload_event(sensor_id, saved_files, upload_timestamp)
        
        # 4. CALCULATE AND SAVE STATISTICS TO DATABASE
        try:
            db_write_start = time.time()
            sensor_data = load_all_sensor_data_with_modes()
            db_write_time = time.time() - db_write_start
            logger.info(f"✓ Statistics calculated and saved to database in {db_write_time*1000:.1f}ms after upload from {sensor_id}")
        except Exception as e:
            logger.error(f"Warning: Could not save statistics to database after upload: {e}")
            # Don't fail the upload response - just log the error
        
        return jsonify({
            'status': 'success',
            'message': f'Uploaded {len(saved_files)} file(s)',
            'sensor_id': sensor_id,
            'files': saved_files,
            'timestamp': upload_timestamp,
            'validation_report': validation_report,
            'next_expected_upload': (dt.datetime.now() + dt.timedelta(minutes=120)).isoformat()
        }), 201
        
    except Exception as e:
        logger.error(f'Upload endpoint error: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

def validate_filename(filename):
    """Validate CSV filename follows expected pattern: max_<sensor>.csv or min_<sensor>.csv"""
    valid_patterns = [f'{ftype}_{sensor}.csv' for ftype in ['max', 'min'] for sensor in SENSORS]
    return filename in valid_patterns

def validate_csv_file(file):
    """Validate CSV file format and content."""
    try:
        file.seek(0)
        content = file.read().decode('utf-8')
        
        if not content.strip():
            return {'valid': False, 'error': 'Empty file'}
        
        lines = content.strip().split('\n')
        if len(lines) < 2:
            return {'valid': False, 'error': 'No data rows'}
        
        # Check header
        header = lines[0].split(',')
        if 'timestamp' not in header or 'value' not in header:
            return {'valid': False, 'error': 'Missing required columns: timestamp, value'}
        
        # Check data rows
        row_count = 0
        for line in lines[1:]:
            if line.strip():
                parts = line.split(',')
                if len(parts) < 2:
                    return {'valid': False, 'error': f'Invalid data row: {line[:50]}...'}
                row_count += 1
        
        if row_count == 0:
            return {'valid': False, 'error': 'No valid data rows'}
        
        if row_count > MAX_CSV_ROWS:
            return {'valid': False, 'error': f'Too many rows: {row_count} (max: {MAX_CSV_ROWS})'}
        
        file.seek(0)
        return {'valid': True, 'row_count': row_count}
        
    except Exception as e:
        return {'valid': False, 'error': str(e)}

def log_upload_event(sensor_id, files, timestamp):
    """Log upload event to tracking file."""
    try:
        log_file = os.path.join(UPLOAD_LOG_DIR, 'upload_history.log')
        with open(log_file, 'a') as f:
            log_entry = {
                'timestamp': timestamp,
                'sensor_id': sensor_id,
                'files': files,
                'file_count': len(files)
            }
            f.write(f"{log_entry}\n")
    except Exception as e:
        logger.error(f'Failed to log upload event: {str(e)}')

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'ok'}), 200

@app.route('/api/upload/status')
def upload_status():
    """Get upload history and monitoring dashboard."""
    try:
        log_file = os.path.join(UPLOAD_LOG_DIR, 'upload_history.log')
        upload_history = []
        
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                for line in f.readlines()[-50:]:  # Last 50 uploads
                    try:
                        upload_history.append(eval(line.strip()))
                    except:
                        pass
        
        # Calculate upload frequency stats
        sensor_stats = {}
        for entry in upload_history:
            sensor_id = entry.get('sensor_id')
            if sensor_id not in sensor_stats:
                sensor_stats[sensor_id] = {'count': 0, 'last_upload': None}
            sensor_stats[sensor_id]['count'] += 1
            sensor_stats[sensor_id]['last_upload'] = entry.get('timestamp')
        
        return jsonify({
            'status': 'success',
            'total_uploads': len(upload_history),
            'sensor_stats': sensor_stats,
            'recent_uploads': upload_history[-10:] if upload_history else []
        })
    except Exception as e:
        logger.error(f'Error getting upload status: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/file-stats')
def file_stats():
    """Return statistics and raw data for a specific CSV filename in the Data directory.

    Query param: filename=<basename.csv>
    """
    filename = request.args.get('filename')
    if not filename:
        return jsonify({'error': 'filename parameter required'}), 400

    # Prevent directory traversal
    if os.path.basename(filename) != filename:
        return jsonify({'error': 'invalid filename'}), 400

    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'file not found'}), 404

    try:
        timestamps, values, file_ts = load_csv_data(filename)
        stats_dict = calculate_statistics(values)
        freqs, amps = calculate_fft_analysis(values)
        full_freqs, full_amps = calculate_fft_full_spectrum(values)

        return jsonify({
            'status': 'success',
            'filename': filename,
            'file_timestamp': file_ts,
            'row_count': len(values),
            'stats': stats_dict,
            'frequencies': freqs,
            'amplitudes': amps,
            'full_spectrum_freqs': full_freqs,
            'full_spectrum_amps': full_amps,
            'raw_timestamps': timestamps,
            'raw_values': values
        })
    except Exception as e:
        logger.error(f'Error computing file stats for {filename}: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/simulate-event', methods=['POST'])
def simulate_event():
    """
    Simulate a fault event by copying fault-specific sensor data files.
    Copies max_*.csv files from Data/[fault_type]/ to Data/
    This triggers the normal processing pipeline.
    """
    try:
        data = request.get_json(silent=True) or {}
        fault_type = data.get('fault_type')
        event_time = data.get('event_time')
        
        if not fault_type:
            return jsonify({'error': 'fault_type is required'}), 400
        
        # Use current time if not provided
        if not event_time:
            event_time = dt.datetime.now().isoformat()
        
        # Build fault directory path
        fault_dir = os.path.join(DATA_DIR, fault_type)
        
        # Debug logging
        logger.info(f'Attempting to simulate: {fault_type}')
        logger.info(f'DATA_DIR: {DATA_DIR}')
        logger.info(f'fault_dir: {fault_dir}')
        logger.info(f'fault_dir exists: {os.path.exists(fault_dir)}')
        
        # Validate fault folder exists
        if not os.path.exists(fault_dir):
            logger.error(f'Fault directory not found: {fault_dir}')
            # List available directories for debugging
            available = []
            try:
                available = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]
            except Exception as list_err:
                logger.error(f'Cannot list Data directory: {list_err}')
            
            return jsonify({
                'error': f'Fault type "{fault_type}" not found',
                'available_faults': available,
                'data_dir': DATA_DIR,
                'checked_path': fault_dir
            }), 404
        
        logger.info(f'Simulating event: {fault_type} at {event_time}')
        
        # Copy max_*.csv and min_*.csv files from fault folder to Data/
        copied_files = []
        param_types = ['acceleration', 'current', 'audio']
        
        for param in param_types:
            # Copy MAX (fault) files
            source_file = os.path.join(fault_dir, f'max_{param}.csv')
            if os.path.exists(source_file):
                dest_filename = f'max_{param}.csv'
                dest_file = os.path.join(DATA_DIR, dest_filename)
                shutil.copy2(source_file, dest_file)
                copied_files.append(dest_filename)
                logger.info(f'Copied: {source_file} → {dest_file}')
            
            # Copy MIN (baseline) files
            source_file_min = os.path.join(fault_dir, f'min_{param}.csv')
            if os.path.exists(source_file_min):
                dest_filename_min = f'min_{param}.csv'
                dest_file_min = os.path.join(DATA_DIR, dest_filename_min)
                shutil.copy2(source_file_min, dest_file_min)
                copied_files.append(dest_filename_min)
                logger.info(f'Copied: {source_file_min} → {dest_file_min}')
        
        if not copied_files:
            return jsonify({'error': 'No sensor files found in fault directory'}), 404
        
        # Load and process the copied files to populate database
        try:
            load_all_sensor_data_with_modes()
            logger.info(f'Database populated with simulated event data')
        except Exception as e:
            logger.warning(f'Database population warning: {e}')
            # Don't fail the request, files are still copied
        
        # Fetch the simulated data
        sensor_data = get_sensor_data_with_raw_data('max')
        
        return jsonify({
            'success': True,
            'message': f'Event "{fault_type}" simulated successfully',
            'event_time': event_time,
            'fault_type': fault_type,
            'files_copied': copied_files,
            'sensor_data': sensor_data
        }), 200
        
    except Exception as e:
        logger.error(f'Error simulating event: {e}', exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/create-event', methods=['POST'])
def create_event():
    """Create a new failure event with backward slope tracking."""
    try:
        data = request.get_json(silent=True) or {}
        event_name = data.get('event_name')
        failure_time_iso = data.get('failure_time_iso')
        description = data.get('description', '')

        if not event_name or not failure_time_iso:
            return jsonify({'error': 'event_name and failure_time_iso are required'}), 400

        result = event_manager.create_event(event_name, failure_time_iso, description)
        return jsonify(result), 201
    except Exception as e:
        logger.error(f'Error creating event: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/available-faults', methods=['GET'])
def get_available_faults():
    """Get list of available fault types that can be simulated."""
    try:
        faults = []
        for item in os.listdir(DATA_DIR):
            item_path = os.path.join(DATA_DIR, item)
            # Only include directories that are not sensor-related files
            if os.path.isdir(item_path) and not item.startswith('.'):
                # Check if it has the max_*.csv files
                has_max_files = any(
                    os.path.exists(os.path.join(item_path, f'max_{param}.csv'))
                    for param in ['acceleration', 'current', 'audio']
                )
                if has_max_files:
                    faults.append(item)
        
        faults.sort()
        return jsonify({
            'faults': faults,
            'count': len(faults)
        }), 200
    except Exception as e:
        logger.error(f'Error getting available faults: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/events')
def list_events():
    """Return all saved failure events."""
    try:
        events = event_manager.list_events()
        return jsonify({'events': events, 'count': len(events)})
    except Exception as e:
        logger.error(f'Error listing events: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/event/<event_id>')
def get_event(event_id):
    """Return one saved failure event."""
    try:
        event_data = event_manager.get_event(event_id)
        if not event_data:
            return jsonify({'error': 'Event not found'}), 404
        return jsonify(event_data)
    except Exception as e:
        logger.error(f'Error getting event {event_id}: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/event-names')
def get_event_names():
    """Return unique event names for the frontend dropdown."""
    try:
        event_names = event_manager.get_unique_event_names()
        return jsonify({'event_names': event_names, 'count': len(event_names)})
    except Exception as e:
        logger.error(f'Error getting event names: {e}')
        return jsonify({'error': str(e)}), 500


# ==================== PHASE 1: NEW FAULT MONITORING ENDPOINTS ====================

@app.route('/api/fault-state/<fault_name>', methods=['GET'])
def get_fault_state(fault_name):
    """
    Get current state of a fault event from generated stats file.
    Returns interval count, system_failure_state, and current statistics.
    Returns 200 OK with initial data if generating but no data yet (waiting for first interval).
    """
    try:
        events_dir = os.path.join(EVENTS_DIR, fault_name)
        stats_file = os.path.join(events_dir, 'stats.json')
        
        if not os.path.exists(stats_file):
            # Fault generation might be starting, return initial/waiting state
            import time
            return jsonify({
                'fault_name': fault_name,
                'interval_count': 0,
                'system_failure_state': False,
                'failure_interval': None,
                'is_generating': True,  # Still waiting for first data
                'current_stats': {},
                'start_time': None,
                'current_time': time.time(),
                'message': 'Waiting for first interval...'
            }), 200
        
        with open(stats_file, 'r') as f:
            stats_data = json.load(f)
        
        current_stats = {}
        if stats_data.get('intervals'):
            current_stats = stats_data['intervals'][-1]  # Get latest interval
        
        return jsonify({
            'fault_name': fault_name,
            'interval_count': stats_data.get('interval_count', 0),
            'system_failure_state': stats_data.get('system_failure_state', False),
            'failure_interval': stats_data.get('failure_interval'),
            'is_generating': not stats_data.get('system_failure_state', True),
            'current_stats': current_stats,
            'start_time': stats_data.get('start_time'),
            'current_time': stats_data.get('current_time')
        }), 200
    except Exception as e:
        logger.error(f'Error getting fault state for {fault_name}: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/fault-trend/<fault_name>', methods=['GET'])
def get_fault_trend(fault_name):
    """
    Get historical trend data (all intervals) for a fault event.
    Returns array of intervals with statistics for trend plotting.
    Returns 200 OK with empty intervals if generating but no data yet.
    """
    try:
        events_dir = os.path.join(EVENTS_DIR, fault_name)
        stats_file = os.path.join(events_dir, 'stats.json')
        
        if not os.path.exists(stats_file):
            # Fault generation might be starting, return empty but valid response
            import time
            return jsonify({
                'fault_name': fault_name,
                'intervals': [],
                'failure_interval': None,
                'system_failure_state': False,
                'start_time': None,
                'current_time': time.time(),
                'message': 'Waiting for data...'
            }), 200
        
        with open(stats_file, 'r') as f:
            stats_data = json.load(f)
        
        # Extract key statistics per interval for trend graphing
        intervals = []
        for interval_data in stats_data.get('intervals', []):
            interval_num = interval_data.get('interval')
            accel_stats = interval_data.get('acceleration', {})
            current_stats = interval_data.get('current', {})
            audio_stats = interval_data.get('audio', {})
            
            intervals.append({
                'interval': interval_num,
                'timestamp': interval_data.get('timestamp'),
                'system_failure_state': interval_data.get('system_failure_state', False),
                # Acceleration metrics
                'accel_rms': accel_stats.get('rms', 0),
                'accel_max': accel_stats.get('max', 0),
                'accel_kurtosis': accel_stats.get('kurtosis', 0),
                'accel_std_dev': accel_stats.get('std_dev', 0),
                # Current metrics
                'current_mean': current_stats.get('mean', 0),
                'current_max': current_stats.get('max', 0),
                # Audio metrics
                'audio_mean': audio_stats.get('mean', 0),
                'audio_max': audio_stats.get('max', 0)
            })
        
        return jsonify({
            'fault_name': fault_name,
            'start_time': stats_data.get('start_time'),
            'current_time': stats_data.get('current_time'),
            'intervals': intervals,
            'failure_interval': stats_data.get('failure_interval'),
            'system_failure_state': stats_data.get('system_failure_state', False),
            'fault_type': 'SUDDEN' if (stats_data.get('failure_interval') or 99) < 10 else 'GRADUAL'
        }), 200
    except Exception as e:
        logger.error(f'Error getting fault trend for {fault_name}: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/fault-current/<fault_name>', methods=['GET'])
def get_fault_current(fault_name):
    """
    Get current interval's time series data (raw timestamps/values).
    Returns raw data for time series chart plotting.
    """
    try:
        sensor_type = request.args.get('sensor', 'acceleration')
        if sensor_type not in SENSORS:
            sensor_type = 'acceleration'
        
        data_dir = os.path.join(DATA_DIR, fault_name)
        if not os.path.exists(data_dir):
            return jsonify({
                'fault_name': fault_name,
                'sensor_type': sensor_type,
                'message': 'No data directory found'
            }), 404
        
        # Load max file (represents current fault state)
        timestamps, values, file_ts = load_csv_data(f'{fault_name}/max_{sensor_type}.csv')
        
        if not timestamps or not values:
            return jsonify({
                'fault_name': fault_name,
                'sensor_type': sensor_type,
                'timestamps': [],
                'values': []
            }), 200
        
        # Normalize timestamps to 0-2000ms window
        if timestamps:
            start_ts = min(timestamps)
            relative_timestamps = [ts - start_ts for ts in timestamps]
        else:
            relative_timestamps = timestamps
        
        return jsonify({
            'fault_name': fault_name,
            'sensor_type': sensor_type,
            'timestamps': relative_timestamps,
            'values': values,
            'file_timestamp': file_ts,
            'data_points': len(values)
        }), 200
    except Exception as e:
        logger.error(f'Error getting fault current data for {fault_name}: {e}')
        return jsonify({'error': str(e)}), 500


# ======================== SEQUENTIAL FAULT RUNNER ENDPOINTS ========================

@app.route('/api/start-sequential-faults', methods=['POST'])
def start_sequential_faults():
    """
    Start a single fault generator.
    Runs the selected fault with fresh data and interval reset.
    """
    try:
        data = request.get_json() or {}
        fault_name = data.get('fault_name', 'Motor Stall')

        with sequential_runner_state['lock']:
            # Check if process is actually still running
            if sequential_runner_state['active']:
                process = sequential_runner_state['process']
                # If process exists, check if it's still alive
                if process and process.poll() is not None:
                    # Process has finished, reset the state
                    logger.info(f"Previous process finished, resetting state")
                    sequential_runner_state['active'] = False
                    sequential_runner_state['process'] = None
                    sequential_runner_state['status'] = 'idle'
                else:
                    # Process still running
                    return jsonify({'error': 'Fault runner already active'}), 409

            # Import here to avoid circular imports
            import subprocess
            import sys

            # Start the fault runner in a subprocess with fault name as argument
            cmd = [
                sys.executable,
                'run_sequence_generator.py',
                '--fault',
                fault_name
            ]

            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    text=True,
                    cwd=BASE_DIR
                )

                sequential_runner_state['active'] = True
                sequential_runner_state['status'] = 'running'
                sequential_runner_state['process'] = process
                sequential_runner_state['current_fault'] = fault_name
                sequential_runner_state['current_fault_number'] = 1
                sequential_runner_state['total_faults'] = 1
                sequential_runner_state['last_log'] = f'✓ Running {fault_name}...'

                logger.info(f"Fault generator started for: {fault_name}")
                
                # Start background thread to monitor subprocess completion
                def monitor_subprocess():
                    """Monitor subprocess and reset active flag when done."""
                    try:
                        process.wait()  # Wait for process to complete
                        with sequential_runner_state['lock']:
                            sequential_runner_state['active'] = False
                            sequential_runner_state['status'] = 'completed'
                            sequential_runner_state['process'] = None
                        logger.info(f"Fault generator completed for: {fault_name}")
                    except Exception as e:
                        logger.error(f"Error monitoring subprocess: {e}")
                        with sequential_runner_state['lock']:
                            sequential_runner_state['active'] = False
                            sequential_runner_state['process'] = None
                
                monitor_thread = threading.Thread(target=monitor_subprocess, daemon=True)
                monitor_thread.start()

                return jsonify({
                    'status': 'started',
                    'message': f'Fault generator started for {fault_name}',
                    'fault_name': fault_name,
                    'pid': process.pid
                }), 200

            except Exception as e:
                logger.error(f"Failed to start fault generator: {e}")
                sequential_runner_state['active'] = False
                sequential_runner_state['process'] = None
                return jsonify({'error': f'Failed to start process: {str(e)}'}), 500

    except Exception as e:
        logger.error(f'Error starting fault generator: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/stop-sequential-faults', methods=['POST'])
def stop_sequential_faults():
    """
    Stop the sequential fault runner process.
    """
    try:
        with sequential_runner_state['lock']:
            process = sequential_runner_state['process']
            
            if not process or not sequential_runner_state['active']:
                return jsonify({'error': 'No active sequential runner'}), 404

            try:
                # Send Ctrl+C to the process
                process.terminate()
                process.wait(timeout=5)
                
                sequential_runner_state['active'] = False
                sequential_runner_state['status'] = 'stopped'
                sequential_runner_state['last_log'] = '⏹️ Stopped by user'

                logger.info("Sequential fault runner stopped")

                return jsonify({
                    'status': 'stopped',
                    'message': 'Sequential fault runner stopped successfully'
                }), 200

            except subprocess.TimeoutExpired:
                # Force kill if terminate doesn't work
                process.kill()
                sequential_runner_state['active'] = False
                sequential_runner_state['status'] = 'killed'
                
                return jsonify({
                    'status': 'killed',
                    'message': 'Sequential fault runner force terminated'
                }), 200

    except Exception as e:
        logger.error(f'Error stopping sequential faults: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/sequential-faults-status', methods=['GET'])
def get_sequential_faults_status():
    """
    Get the current status of the sequential fault runner.
    Used by frontend for polling and progress updates.
    """
    try:
        status_file = os.path.join(BASE_DIR, '.sequential_runner_status.json')
        
        # Try to read status from file (written by run_sequence_generator.py)
        if os.path.exists(status_file):
            try:
                with open(status_file, 'r') as f:
                    return jsonify(json.load(f)), 200
            except:
                pass

        # Return default state if file doesn't exist or can't be read
        with sequential_runner_state['lock']:
            status_dict = {
                'active': sequential_runner_state['active'],
                'status': sequential_runner_state['status'],
                'current_fault': sequential_runner_state['current_fault'],
                'current_fault_number': sequential_runner_state['current_fault_number'],
                'total_faults': sequential_runner_state['total_faults'],
                'cycles': sequential_runner_state['cycles'],
                'last_log': sequential_runner_state['last_log']
            }

            # Check if process is still running
            if sequential_runner_state['process'] and sequential_runner_state['active']:
                poll_result = sequential_runner_state['process'].poll()
                if poll_result is not None:  # Process has terminated
                    sequential_runner_state['active'] = False
                    sequential_runner_state['status'] = 'completed'
                    status_dict['status'] = 'completed'
                    logger.info("Sequential fault runner process completed")

            return jsonify(status_dict), 200

    except Exception as e:
        logger.error(f'Error getting sequential faults status: {e}')
        return jsonify({'error': str(e)}), 500


# ======================== HELPER FUNCTION FOR SEQUENTIAL RUNNER ========================

def update_sequential_runner_status(fault_name, fault_number, log_message):
    """
    Update the sequential runner state (called from run_sequence_generator.py)
    """
    with sequential_runner_state['lock']:
        sequential_runner_state['current_fault'] = fault_name
        sequential_runner_state['current_fault_number'] = fault_number
        sequential_runner_state['last_log'] = log_message
        logger.info(f"Sequential runner: {fault_name} ({fault_number}/11) - {log_message}")


if __name__ == '__main__':
    print(' * Starting Predictive Maintenance Backend...')
    
    # Get port from environment variable or default to 5001
    port = int(os.environ.get('PORT', 5001))
    debug_mode = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    # Use Flask's built-in run method (simpler, better CORS support for HTTP)
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode,
        use_reloader=False
    )
