from flask import Flask, jsonify, send_from_directory, abort, Response, request
from flask_socketio import SocketIO
from flask_cors import CORS
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import glob
import datetime
import re
import json
import csv
import numpy as np
from scipy import stats
from event_manager import EventManager

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])  # Vite default port
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:5173", "http://127.0.0.1:5173"])

# Configure the data directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'Data')
EVENTS_DIR = os.path.join(BASE_DIR, 'Events')
FNAME_RE = re.compile(r"^[^/\\]+\.csv$")  # simple guard against path traversal
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(EVENTS_DIR, exist_ok=True)

# Initialize Event Manager
event_manager = EventManager(EVENTS_DIR, DATA_DIR)

def load_config():
    cfg_path = os.path.join(BASE_DIR, 'config.json')
    default_cfg = {"interval_seconds": 300}
    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            if not isinstance(cfg.get('interval_seconds'), int):
                return default_cfg
            return cfg
    except (FileNotFoundError, json.JSONDecodeError):
        return default_cfg

CONFIG = load_config()

def calculate_statistics(z_values):
    """Calculate comprehensive statistical parameters for acceleration data."""
    if not z_values or len(z_values) == 0:
        return {}
    
    def safe_float(val):
        """Convert value to float, replacing NaN/Inf with 0."""
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return 0.0
        return f
    
    z_array = np.array(z_values)
    
    # Basic Amplitude Statistics
    max_val = np.max(z_array)
    min_val = np.min(z_array)
    mean_val = np.mean(z_array)
    abs_mean = np.mean(np.abs(z_array))
    rms = np.sqrt(np.mean(z_array**2))
    variance = np.var(z_array)
    std_dev = np.std(z_array)
    peak = max(abs(max_val), abs(min_val))
    peak_to_peak = max_val - min_val
    
    # Severity / Health Ratios
    crest_factor = peak / rms if rms != 0 else 0
    impulse_factor = peak / abs_mean if abs_mean != 0 else 0
    shape_factor = rms / abs_mean if abs_mean != 0 else 0
    clearance_factor = peak / (np.mean(np.sqrt(np.abs(z_array)))**2) if np.mean(np.sqrt(np.abs(z_array))) != 0 else 0
    
    # Distribution Shape Features
    skewness = stats.skew(z_array)
    kurtosis_val = stats.kurtosis(z_array)
    excess_kurtosis = kurtosis_val  # scipy.stats.kurtosis already returns excess kurtosis by default
    
    # Optional Extras
    energy = np.sum(z_array**2)
    
    # Zero-crossing rate
    zero_crossings = np.sum(np.diff(np.signbit(z_array)))
    zero_crossing_rate = zero_crossings / len(z_array) if len(z_array) > 1 else 0
    
    # Percentiles
    percentile_90 = np.percentile(z_array, 90)
    percentile_95 = np.percentile(z_array, 95)
    percentile_99 = np.percentile(z_array, 99)
    
    return {
        # Basic Amplitude Statistics
        'max': safe_float(max_val),
        'min': safe_float(min_val),
        'mean': safe_float(mean_val),
        'abs_mean': safe_float(abs_mean),
        'rms': safe_float(rms),
        'variance': safe_float(variance),
        'std_dev': safe_float(std_dev),
        'peak': safe_float(peak),
        'peak_to_peak': safe_float(peak_to_peak),
        
        # Severity / Health Ratios
        'crest_factor': safe_float(crest_factor),
        'impulse_factor': safe_float(impulse_factor),
        'shape_factor': safe_float(shape_factor),
        'clearance_factor': safe_float(clearance_factor),
        
        # Distribution Shape Features
        'skewness': safe_float(skewness),
        'kurtosis': safe_float(kurtosis_val),
        'excess_kurtosis': safe_float(excess_kurtosis),
        
        # Optional Extras
        'energy': safe_float(energy),
        'zero_crossing_rate': safe_float(zero_crossing_rate),
        'percentile_90': safe_float(percentile_90),
        'percentile_95': safe_float(percentile_95),
        'percentile_99': safe_float(percentile_99)
    }

class FileChangeHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.csv'):
            # Emit the new file event to connected clients
            file_info = get_file_info(event.src_path)
            socketio.emit('file_created', file_info)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.csv'):
            # Emit the file modified event to connected clients
            file_info = get_file_info(event.src_path)
            socketio.emit('file_modified', file_info)

def get_file_info(filepath):
    stats = os.stat(filepath)
    return {
        'name': os.path.basename(filepath),
        'size': stats.st_size,
        'modified': datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
        'path': filepath
    }

# Removed template route - now API-only for React frontend

@app.route('/files')
def get_files():
    files = []
    for filepath in glob.glob(os.path.join(DATA_DIR, '*.csv')):
        files.append(get_file_info(filepath))
    return jsonify(files)

def _resolve_csv_path(name: str) -> str:
    """Validate and resolve CSV path within DATA_DIR."""
    if not FNAME_RE.match(name or ""):
        abort(400, description="Invalid file name")
    fpath = os.path.join(DATA_DIR, name)
    if not os.path.isfile(fpath):
        abort(404, description="File not found")
    return fpath

@app.route('/download/<path:name>')
def download_file(name):
    # Validate and serve as attachment
    _resolve_csv_path(name)
    return send_from_directory(DATA_DIR, name, as_attachment=True, mimetype='text/csv', download_name=name)

@app.route('/view/<path:name>')
def view_file(name):
    # Stream a small preview inline (first ~200 KB) as text for quick viewing
    fpath = _resolve_csv_path(name)
    try:
        chunks = []
        read_bytes = 0
        limit = 200 * 1024  # 200 KB preview
        with open(fpath, 'rb') as f:
            while read_bytes < limit:
                chunk = f.read(min(16 * 1024, limit - read_bytes))
                if not chunk:
                    break
                chunks.append(chunk)
                read_bytes += len(chunk)
        content = b''.join(chunks)
        # Ensure text rendering in browser
        return Response(content, mimetype='text/plain; charset=utf-8', headers={
            'Cache-Control': 'no-store'
        })
    except OSError:
        abort(500, description="Error reading file")

def load_20_day_data():
    """Load and aggregate data from multiple max_reading files over the last 20 days."""
    import datetime as dt
    
    # Find all max_reading files
    max_reading_files = glob.glob(os.path.join(DATA_DIR, 'max_reading*.csv'))
    
    if not max_reading_files:
        return [], [], "No max_reading files found"
    
    # Sort files by modification time (newest first)
    max_reading_files.sort(key=os.path.getmtime, reverse=True)
    
    # Calculate 20 days ago
    twenty_days_ago = dt.datetime.now() - dt.timedelta(days=20)
    
    timestamps = []
    z_values = []
    files_processed = 0
    
    # Process files from the last 20 days
    for file_path in max_reading_files:
        # Check if file is within 20 days
        file_mtime = dt.datetime.fromtimestamp(os.path.getmtime(file_path))
        if file_mtime < twenty_days_ago:
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    try:
                        # Handle different timestamp formats
                        timestamp_str = row['timestamp']
                        if 'T' in timestamp_str:  # ISO format
                            dt_obj = dt.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            timestamp = dt_obj.timestamp() * 1000
                        else:
                            timestamp = float(timestamp_str)
                        
                        # Handle different value column names
                        if 'z' in row:
                            z_value = float(row['z'])
                        elif 'value' in row:
                            z_value = float(row['value'])
                        else:
                            continue
                            
                        timestamps.append(timestamp)
                        z_values.append(z_value)
                        
                    except (ValueError, KeyError):
                        continue
                
                files_processed += 1
                    
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
            continue
    
    # Sort by timestamp (oldest first for proper time series)
    if timestamps and z_values:
        combined = list(zip(timestamps, z_values))
        combined.sort(key=lambda x: x[0])
        timestamps, z_values = zip(*combined)
        timestamps, z_values = list(timestamps), list(z_values)
    
    # Limit to last 500 points for performance
    if len(timestamps) > 500:
        timestamps = timestamps[-500:]
        z_values = z_values[-500:]
    
    return timestamps, z_values, f"Processed {files_processed} files with {len(timestamps)} data points"

@app.route('/chart-data')
def get_chart_data():
    """Get aggregated max_reading CSV data for the chart over 20 days."""
    # Threshold constants
    MAX_THRESHOLD = 0.6
    MIN_THRESHOLD = -0.1
    
    try:
        # Load 20-day aggregated data
        timestamps, z_values, status_msg = load_20_day_data()
        
        if not timestamps:
            return jsonify({'error': 'No data available for the last 20 days'}), 404
        
        # Check for threshold violations in the aggregated data
        max_violations = []
        min_violations = []
        
        for timestamp, z_value in zip(timestamps, z_values):
            if z_value >= MAX_THRESHOLD:
                max_violations.append({'timestamp': timestamp, 'value': z_value})
            if z_value <= MIN_THRESHOLD:
                min_violations.append({'timestamp': timestamp, 'value': z_value})
        
        # Limit to last 500 points for performance
        if len(timestamps) > 500:
            timestamps = timestamps[-500:]
            z_values = z_values[-500:]
        
        # Calculate statistical parameters
        stats_data = calculate_statistics(z_values)
        
        return jsonify({
            'filename': '20-day aggregated data',
            'timestamps': timestamps,
            'z_values': z_values,
            'count': len(timestamps),
            'max_threshold': MAX_THRESHOLD,
            'min_threshold': MIN_THRESHOLD,
            'max_violations': max_violations,
            'min_violations': min_violations,
            'max_violations_count': len(max_violations),
            'min_violations_count': len(min_violations),
            'statistics': stats_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/parameter-data/<parameter>')
def get_parameter_data(parameter):
    """Get time-series data for a specific statistical parameter."""
    try:
        # Get optional date range and timestamp parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        # Load 20-day aggregated data
        timestamps, z_values, status_msg = load_20_day_data()
        
        if not timestamps:
            return jsonify({'error': 'No data available for the last 20 days'}), 404
        
        # Filter by date range if provided
        if start_date or end_date:
            import datetime as dt
            filtered_timestamps = []
            filtered_z_values = []
            
            for i, timestamp in enumerate(timestamps):
                # Convert timestamp (milliseconds) to datetime
                dt_obj = dt.datetime.fromtimestamp(timestamp / 1000)
                
                # Check if within range
                if start_date:
                    start_dt = dt.datetime.fromisoformat(start_date)
                    if dt_obj < start_dt:
                        continue
                
                if end_date:
                    end_dt = dt.datetime.fromisoformat(end_date)
                    # Set to end of day
                    end_dt = end_dt.replace(hour=23, minute=59, second=59)
                    if dt_obj > end_dt:
                        continue
                
                filtered_timestamps.append(timestamp)
                filtered_z_values.append(z_values[i])
            
            timestamps = filtered_timestamps
            z_values = filtered_z_values
            
            if not timestamps:
                return jsonify({'error': 'No data available for the selected date range'}), 404
        
        # Filter by timestamp (full datetime) if provided
        if start_time or end_time:
            import datetime as dt
            filtered_timestamps = []
            filtered_z_values = []
            
            for i, timestamp in enumerate(timestamps):
                # Convert timestamp (milliseconds) to datetime
                dt_obj = dt.datetime.fromtimestamp(timestamp / 1000)
                
                # Check if within timestamp range (full datetime comparison)
                if start_time:
                    start_time_dt = dt.datetime.fromisoformat(start_time)
                    if dt_obj < start_time_dt:
                        continue
                
                if end_time:
                    end_time_dt = dt.datetime.fromisoformat(end_time)
                    if dt_obj > end_time_dt:
                        continue
                
                filtered_timestamps.append(timestamp)
                filtered_z_values.append(z_values[i])
            
            timestamps = filtered_timestamps
            z_values = filtered_z_values
            
            if not timestamps:
                return jsonify({'error': 'No data available for the selected time range'}), 404
        
        # Filter by time-of-day only (across all dates) if provided
        time_start = request.args.get('time_start')
        time_end = request.args.get('time_end')
        
        if time_start or time_end:
            import datetime as dt
            filtered_timestamps = []
            filtered_z_values = []
            
            for i, timestamp in enumerate(timestamps):
                # Convert timestamp (milliseconds) to datetime
                dt_obj = dt.datetime.fromtimestamp(timestamp / 1000)
                dt_time = dt_obj.time()
                
                # Check if within time-of-day range
                if time_start:
                    start_t = dt.datetime.strptime(time_start, '%H:%M').time()
                    if dt_time < start_t:
                        continue
                
                if time_end:
                    end_t = dt.datetime.strptime(time_end, '%H:%M').time()
                    if dt_time > end_t:
                        continue
                
                filtered_timestamps.append(timestamp)
                filtered_z_values.append(z_values[i])
            
            timestamps = filtered_timestamps
            z_values = filtered_z_values
            
            if not timestamps:
                return jsonify({'error': 'No data available for the selected time range'}), 404
        
        # Calculate statistical parameters
        stats_data = calculate_statistics(z_values)
        
        # Get the requested parameter values
        if parameter == 'raw_z':
            parameter_values = z_values
            parameter_label = 'Z-Axis Value'
        elif parameter in stats_data:
            # For statistical parameters, calculate rolling statistics over a window
            # This shows how the parameter evolves over the 20-day period
            window_size = min(7, len(z_values))  # 7-day rolling window or available data
            parameter_values = []
            
            for i in range(len(z_values)):
                # Calculate rolling window
                start_idx = max(0, i - window_size + 1)
                window_data = z_values[start_idx:i+1]
                
                # Calculate statistic for this window
                if len(window_data) > 0:
                    window_stats = calculate_statistics(window_data)
                    if parameter in window_stats:
                        parameter_values.append(window_stats[parameter])
                    else:
                        parameter_values.append(0)
                else:
                    parameter_values.append(0)
            
            parameter_label = parameter.replace('_', ' ').title()
            
            # Improve label formatting
            label_map = {
                'max': 'Maximum',
                'min': 'Minimum', 
                'mean': 'Mean',
                'abs_mean': 'Absolute Mean',
                'rms': 'RMS (Root Mean Square)',
                'variance': 'Variance',
                'std_dev': 'Standard Deviation',
                'peak': 'Peak',
                'peak_to_peak': 'Peak-to-Peak',
                'crest_factor': 'Crest Factor',
                'impulse_factor': 'Impulse Factor',
                'shape_factor': 'Shape Factor',
                'clearance_factor': 'Clearance Factor',
                'skewness': 'Skewness',
                'kurtosis': 'Kurtosis',
                'excess_kurtosis': 'Excess Kurtosis',
                'energy': 'Energy',
                'zero_crossing_rate': 'Zero-Crossing Rate',
                'percentile_90': '90th Percentile',
                'percentile_95': '95th Percentile',
                'percentile_99': '99th Percentile'
            }
            parameter_label = label_map.get(parameter, parameter_label)
        else:
            return jsonify({'error': f'Unknown parameter: {parameter}'}), 400
        
        return jsonify({
            'filename': '20-day aggregated data',
            'timestamps': timestamps,
            'parameter_values': parameter_values,
            'parameter_name': parameter,
            'parameter_label': parameter_label,
            'count': len(timestamps),
            'statistics': stats_data,
            'status': status_msg
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/create-event', methods=['POST'])
def create_event():
    """Create a new failure event with slope tracking."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        event_name = data.get('event_name')
        failure_time_iso = data.get('failure_time_iso')
        description = data.get('description', '')
        
        if not event_name or not failure_time_iso:
            return jsonify({'error': 'event_name and failure_time_iso are required'}), 400
        
        result = event_manager.create_event(event_name, failure_time_iso, description)
        return jsonify(result), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/events')
def list_events():
    """List all logged events with metadata."""
    try:
        events = event_manager.list_events()
        return jsonify({
            'events': events,
            'count': len(events)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/event/<event_id>')
def get_event(event_id):
    """Get detailed data for a specific event."""
    try:
        event_data = event_manager.get_event(event_id)
        
        if event_data is None:
            return jsonify({'error': 'Event not found'}), 404
        
        return jsonify(event_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/event-names')
def get_event_names():
    """Get list of unique event names for dropdown."""
    try:
        event_names = event_manager.get_unique_event_names()
        return jsonify({
            'event_names': event_names,
            'count': len(event_names)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download-event/<event_id>')
def download_event(event_id):
    """Download the generated CSV file for a specific event."""
    try:
        filename = f"{event_id}.csv"
        file_path = os.path.join(EVENTS_DIR, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Event file not found'}), 404
            
        return send_from_directory(EVENTS_DIR, filename, as_attachment=True, mimetype='text/csv')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download-source/<event_id>')
def download_source(event_id):
    """Download the archived source CSV file for a specific event."""
    try:
        # First we need to find the filename from metadata
        json_path = os.path.join(EVENTS_DIR, f"{event_id}.json")
        if not os.path.exists(json_path):
            return jsonify({'error': 'Event metadata not found'}), 404
            
        with open(json_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            
        archived_filename = metadata.get('archived_source_filename')
        if not archived_filename:
            return jsonify({'error': 'Source file info not found in metadata'}), 404
            
        file_path = os.path.join(EVENTS_DIR, archived_filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'Archived source file not found'}), 404
            
        return send_from_directory(EVENTS_DIR, archived_filename, as_attachment=True, mimetype='text/csv')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Set up the file system observer (disabled during debug to prevent watchdog restart loops)
    observer = None
    try:
        # Run the Flask app on all network interfaces
        print(' * Starting Flask application...')
        socketio.run(app, host='0.0.0.0', port=5001, debug=False, allow_unsafe_werkzeug=True)
    finally:
        if observer:
            observer.stop()
            observer.join()