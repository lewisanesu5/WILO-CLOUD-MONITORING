from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import glob
import csv
import numpy as np
from scipy import stats
import datetime as dt
import logging
from functools import wraps
import hashlib
import time
from dotenv import load_dotenv
from database import save_statistics, test_connection

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
CORS(app, origins=ALLOWED_ORIGINS)

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
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_LOG_DIR, exist_ok=True)

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
    """Get all sensor data for all three modes."""
    api_start = time.time()
    try:
        mode = request.args.get('mode', 'max').lower()
        
        if mode not in ['max', 'min', 'combined']:
            return jsonify({'status': 'error', 'message': f'Invalid mode: {mode}'}), 400
        
        sensor_data = load_all_sensor_data_with_modes()
        
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

if __name__ == '__main__':
    print(' * Starting Predictive Maintenance Backend...')
    from flask_socketio import SocketIO
    
    # Get port from environment variable or default to 5001
    port = int(os.environ.get('PORT', 5001))
    debug_mode = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    socketio = SocketIO(
        app,
        cors_allowed_origins=ALLOWED_ORIGINS,
        async_mode='threading'
    )
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=debug_mode,
        allow_unsafe_werkzeug=True
    )
