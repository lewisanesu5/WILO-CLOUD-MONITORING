from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import glob
import csv
import numpy as np
from scipy import stats, fft
import datetime as dt

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

# Configure directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'Data')
os.makedirs(DATA_DIR, exist_ok=True)

# Sensor configuration
SENSORS = ['acceleration', 'current', 'audio']

def load_csv_data(filename):
    """Load CSV data and return timestamps and values."""
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return [], []
    
    timestamps = []
    values = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Handle timestamp
                    timestamp_str = row.get('timestamp', '')
                    if 'T' in timestamp_str:  # ISO format
                        dt_obj = dt.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        timestamp = dt_obj.timestamp() * 1000
                    else:
                        timestamp = float(timestamp_str)
                    
                    # Handle value
                    value = float(row.get('value', 0))
                    timestamps.append(timestamp)
                    values.append(value)
                except (ValueError, KeyError):
                    continue
    except Exception as e:
        print(f"Error loading {filename}: {e}")
    
    return timestamps, values

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
    """Calculate FFT and extract top 5 frequencies and amplitudes."""
    if not values or len(values) < 2:
        return [], []
    
    z_array = np.array(values)
    
    # Perform FFT
    fft_result = np.fft.fft(z_array)
    frequencies = np.fft.fftfreq(len(z_array), d=1.0)
    amplitudes = np.abs(fft_result)
    
    # Get only positive frequencies
    positive_freq_idx = frequencies > 0
    positive_freqs = frequencies[positive_freq_idx]
    positive_amps = amplitudes[positive_freq_idx]
    
    # Get top 5
    top_indices = np.argsort(positive_amps)[-5:][::-1]
    
    top_frequencies = [float(positive_freqs[i]) for i in top_indices if i < len(positive_freqs)]
    top_amplitudes = [float(positive_amps[i]) for i in top_indices if i < len(positive_amps)]
    
    # Pad with zeros if less than 5
    while len(top_frequencies) < 5:
        top_frequencies.append(0.0)
        top_amplitudes.append(0.0)
    
    return top_frequencies[:5], top_amplitudes[:5]

def get_sensor_health_status(stats_dict):
    """Determine health status based on statistics."""
    if not stats_dict:
        return 'unknown'
    
    # Health thresholds (adjustable)
    kurtosis_critical = 5.0  # High kurtosis indicates anomalies
    std_dev_warning = 2.0
    
    kurtosis = stats_dict.get('kurtosis', 0)
    std_dev = stats_dict.get('std_dev', 0)
    
    if kurtosis > kurtosis_critical:
        return 'critical'
    elif kurtosis > kurtosis_critical * 0.6 or std_dev > std_dev_warning:
        return 'warning'
    else:
        return 'normal'

def load_all_sensor_data():
    """Load data from all 6 CSV files and calculate statistics."""
    sensor_data = {}
    
    for sensor in SENSORS:
        sensor_data[sensor] = {
            'stats': {},
            'frequencies': [],
            'amplitudes': [],
            'health': 'unknown',
            'files': {}
        }
        
        # Load max and min files
        for file_type in ['max', 'min']:
            filename = f"{file_type}_{sensor}.csv"
            timestamps, values = load_csv_data(filename)
            
            if values:
                # Calculate statistics
                stats_dict = calculate_statistics(values)
                
                # Calculate FFT analysis
                frequencies, amplitudes = calculate_fft_analysis(values)
                
                # Store data
                sensor_data[sensor]['files'][file_type] = {
                    'count': len(values),
                    'timestamps': timestamps,
                    'values': values
                }
                
                # Merge statistics (take max file as primary)
                if file_type == 'max':
                    sensor_data[sensor]['stats'] = stats_dict
                    sensor_data[sensor]['frequencies'] = frequencies
                    sensor_data[sensor]['amplitudes'] = amplitudes
                    sensor_data[sensor]['health'] = get_sensor_health_status(stats_dict)
    
    return sensor_data

@app.route('/api/sensor-data')
def get_sensor_data():
    """Get all sensor statistics, frequencies, and amplitudes."""
    try:
        sensor_data = load_all_sensor_data()
        
        # Filter by time if provided
        time_start = request.args.get('time_start')
        time_end = request.args.get('time_end')
        
        filtered_data = {}
        for sensor_name, data in sensor_data.items():
            filtered_data[sensor_name] = {
                'stats': data['stats'],
                'frequencies': data['frequencies'],
                'amplitudes': data['amplitudes'],
                'health': data['health'],
                'data_points': sum(f['count'] for f in data['files'].values())
            }
        
        return jsonify({
            'status': 'success',
            'data': filtered_data,
            'timestamp': dt.datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/sensor/<sensor_name>')
def get_sensor_detail(sensor_name):
    """Get detailed data for a specific sensor."""
    if sensor_name not in SENSORS:
        return jsonify({'error': 'Invalid sensor'}), 400
    
    try:
        sensor_data = load_all_sensor_data()
        data = sensor_data.get(sensor_name, {})
        
        return jsonify({
            'sensor': sensor_name,
            'stats': data['stats'],
            'frequencies': data['frequencies'],
            'amplitudes': data['amplitudes'],
            'health': data['health'],
            'files': {k: {'count': v['count']} for k, v in data['files'].items()}
        })
    except Exception as e:
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
    """Receive and store CSV files from remote sensor."""
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        uploaded_files = request.files.getlist('files')
        saved_files = []
        
        for file in uploaded_files:
            if file and file.filename.endswith('.csv'):
                # Save file to Data directory
                filepath = os.path.join(DATA_DIR, file.filename)
                file.save(filepath)
                saved_files.append(file.filename)
        
        if not saved_files:
            return jsonify({'error': 'No valid CSV files uploaded'}), 400
        
        return jsonify({
            'status': 'success',
            'message': f'Uploaded {len(saved_files)} file(s)',
            'files': saved_files
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    print(' * Starting Predictive Maintenance Backend...')
    from flask_socketio import SocketIO
    socketio = SocketIO(app)
    socketio.run(app, host='0.0.0.0', port=5001, debug=False, allow_unsafe_werkzeug=True)
