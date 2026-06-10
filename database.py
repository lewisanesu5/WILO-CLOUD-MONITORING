import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
import logging
import time
from datetime import datetime

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv('DATABASE_URL')

# ==================== FAILURE TABLE MAPPING ====================
FAILURE_TABLE_MAPPING = {
    'Motor Bearing Failure': 'motor_bearing_failure',
    'Motor Electrical Fault': 'motor_electrical_fault',
    'Motor Overheating': 'motor_overheating',
    'Motor Shaft Misalignment': 'motor_shaft_misalignment',
    'Motor Stall': 'motor_stall',
    'Motor Vibration Anomaly': 'motor_vibration_anomaly',
    'Motor Winding Failure': 'motor_winding_failure',
    'Pump Cavitation': 'pump_cavitation',
    'Pump Impeller Damage': 'pump_impeller_damage',
    'Pump Seal Leakage': 'pump_seal_leakage',
    'Custom Event': 'custom_fault'
}

def get_connection():
    """Get database connection with timeout"""
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection error (operational): {e}")
        raise
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

def save_statistics(sensor_name, mode, stats_dict, frequencies, amplitudes):
    """
    Save calculated statistics and FFT data to Neon database.
    
    Args:
        sensor_name: 'acceleration', 'current', or 'audio'
        mode: 'max', 'min', or 'combined'
        stats_dict: Dictionary with keys: mean, max, min, std_dev, range, skewness, kurtosis
        frequencies: List of top 5 frequencies
        amplitudes: List of top 5 amplitudes
    """
    start_time = time.time()
    conn = None
    try:
        conn = get_connection()
        connection_time = time.time() - start_time
        
        cur = conn.cursor()
        
        # Map sensor_name to table name
        table_name = sensor_name.lower()
        
        # Validate table name to prevent SQL injection
        valid_tables = ['acceleration', 'current', 'audio']
        if table_name not in valid_tables:
            raise ValueError(f"Invalid sensor name: {sensor_name}")
        
        # Ensure we have exactly 5 frequencies and amplitudes (pad with 0 if needed)
        freqs = (frequencies + [0] * 5)[:5]
        amps = (amplitudes + [0] * 5)[:5]
        
        query = f"""
            INSERT INTO {table_name} 
            (x_min, x_max, mean, range, standard_deviation, skewness, kurtosis,
             frequency1, frequency2, frequency3, frequency4, frequency5,
             amplitude1, amplitude2, amplitude3, amplitude4, amplitude5, file_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s)
        """
        
        query_start = time.time()
        cur.execute(query, (
            stats_dict.get('min', 0),           # x_min
            stats_dict.get('max', 0),           # x_max
            stats_dict.get('mean', 0),          # mean
            stats_dict.get('range', 0),         # range ✅ NOW INCLUDED
            stats_dict.get('std_dev', 0),       # standard_deviation
            stats_dict.get('skewness', 0),      # skewness
            stats_dict.get('kurtosis', 0),      # kurtosis
            freqs[0], freqs[1], freqs[2], freqs[3], freqs[4],  # frequency1-5
            amps[0], amps[1], amps[2], amps[3], amps[4],       # amplitude1-5
            mode                                 # file_type signature (max, min, or combined)
        ))
        query_time = time.time() - query_start
        
        commit_start = time.time()
        conn.commit()
        commit_time = time.time() - commit_start
        
        total_time = time.time() - start_time
        logger.info(
            f"✓ {sensor_name} ({mode}): "
            f"connection={connection_time*1000:.1f}ms, "
            f"query={query_time*1000:.1f}ms, "
            f"commit={commit_time*1000:.1f}ms, "
            f"total={total_time*1000:.1f}ms"
        )
        return True
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error saving {mode} statistics for {sensor_name}: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_latest_statistics(sensor_name):
    """Retrieve latest statistics from database"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        table_name = sensor_name.lower()
        
        # Validate table name
        valid_tables = ['acceleration', 'current', 'audio']
        if table_name not in valid_tables:
            raise ValueError(f"Invalid sensor name: {sensor_name}")
        
        query = f"""
            SELECT * FROM {table_name}
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        cur.execute(query)
        result = cur.fetchone()
        
        return dict(result) if result else None
        
    except Exception as e:
        logger.error(f"Error retrieving statistics for {sensor_name}: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_latest_statistics_by_mode(mode='max'):
    """
    Fetch the latest statistics from all sensors in the database.
    
    Returns a dict formatted for the frontend API response:
    {
        "sensor_name": {
            "stats": {mean, max, min, std_dev, skewness, kurtosis},
            "frequencies": [f1, f2, f3, f4, f5],
            "amplitudes": [a1, a2, a3, a4, a5],
            "raw_values": [],
            "raw_timestamps": []
        }
    }
    
    Args:
        mode: 'max', 'min', or 'combined' (currently ignored since DB stores latest only)
    
    Returns:
        Dict with sensor data or empty dict if DB unavailable
    """
    result = {}
    sensor_names = ['acceleration', 'current', 'audio']
    
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        for sensor_name in sensor_names:
            try:
                query = f"""
                    SELECT 
                        x_min, x_max, mean, range, standard_deviation, skewness, kurtosis,
                        frequency1, frequency2, frequency3, frequency4, frequency5,
                        amplitude1, amplitude2, amplitude3, amplitude4, amplitude5
                    FROM {sensor_name}
                    ORDER BY created_at DESC
                    LIMIT 1
                """
                
                cur.execute(query)
                row = cur.fetchone()
                
                if row:
                    row_dict = dict(row)
                    result[sensor_name] = {
                        'stats': {
                            'min': row_dict.get('x_min', 0),
                            'max': row_dict.get('x_max', 0),
                            'mean': row_dict.get('mean', 0),
                            'range': row_dict.get('range', 0),
                            'std_dev': row_dict.get('standard_deviation', 0),
                            'skewness': row_dict.get('skewness', 0),
                            'kurtosis': row_dict.get('kurtosis', 0)
                        },
                        'frequencies': [
                            row_dict.get('frequency1', 0),
                            row_dict.get('frequency2', 0),
                            row_dict.get('frequency3', 0),
                            row_dict.get('frequency4', 0),
                            row_dict.get('frequency5', 0)
                        ],
                        'amplitudes': [
                            row_dict.get('amplitude1', 0),
                            row_dict.get('amplitude2', 0),
                            row_dict.get('amplitude3', 0),
                            row_dict.get('amplitude4', 0),
                            row_dict.get('amplitude5', 0)
                        ],
                        'raw_values': [],  # Not available from DB-only approach
                        'raw_timestamps': []  # Not available from DB-only approach
                    }
                else:
                    logger.warning(f"No statistics found in database for {sensor_name}")
                    result[sensor_name] = {
                        'stats': {},
                        'frequencies': [],
                        'amplitudes': [],
                        'raw_values': [],
                        'raw_timestamps': []
                    }
            except Exception as e:
                logger.error(f"Error fetching stats for {sensor_name}: {e}")
                result[sensor_name] = {
                    'stats': {},
                    'frequencies': [],
                    'amplitudes': [],
                    'raw_values': [],
                    'raw_timestamps': []
                }
        
        logger.info(f"✓ Fetched latest statistics from DB for all sensors")
        return result
        
    except Exception as e:
        logger.error(f"Database connection error in get_all_latest_statistics_by_mode: {e}")
        # Graceful fallback: return empty structure so frontend doesn't break
        return {
            'acceleration': {'stats': {}, 'frequencies': [], 'amplitudes': [], 'raw_values': [], 'raw_timestamps': []},
            'current': {'stats': {}, 'frequencies': [], 'amplitudes': [], 'raw_values': [], 'raw_timestamps': []},
            'audio': {'stats': {}, 'frequencies': [], 'amplitudes': [], 'raw_values': [], 'raw_timestamps': []}
        }
    finally:
        if conn:
            conn.close()

def test_connection():
    """Test database connection"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        logger.info("Database connection successful!")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False
    finally:
        if conn:
            conn.close()

# ==================== EVENT DATA INSERTION FUNCTIONS ====================

def create_event_table_if_not_exists(table_name):
    """
    Create a failure-specific event table if it doesn't already exist.
    Called before inserting data to ensure table is ready.
    
    Args:
        table_name: Name of the table (e.g., "pump_seal_leakage")
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Create table if it doesn't exist
        create_query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {table_name}_id SERIAL PRIMARY KEY,
                fault_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                x_min FLOAT,
                x_max FLOAT,
                mean FLOAT,
                standard_deviation FLOAT,
                range FLOAT,
                variance FLOAT,
                skewness FLOAT,
                kurtosis FLOAT,
                frequency1 FLOAT,
                frequency2 FLOAT,
                frequency3 FLOAT,
                frequency4 FLOAT,
                frequency5 FLOAT,
                amplitude1 FLOAT,
                amplitude2 FLOAT,
                amplitude3 FLOAT,
                amplitude4 FLOAT,
                amplitude5 FLOAT
            );
        """
        
        cur.execute(create_query)
        
        # Create indices
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_fault_id ON {table_name}(fault_id);")
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_timestamp ON {table_name}(timestamp);")
        
        conn.commit()
        logger.info(f"✓ Event table '{table_name}' ensured to exist")
        
    except Exception as e:
        logger.error(f"Error creating event table '{table_name}': {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def get_next_fault_id(failure_type):
    """
    Get the next fault_id for a given failure type.
    Fault ID increments per event for each failure type independently.
    
    Args:
        failure_type: Name of the failure (e.g., "Motor Stall")
        
    Returns:
        Next fault_id (integer starting from 1)
    """
    conn = None
    try:
        table_name = FAILURE_TABLE_MAPPING.get(failure_type)
        if not table_name:
            raise ValueError(f"Unknown failure type: {failure_type}")
        
        # Ensure table exists before querying
        create_event_table_if_not_exists(table_name)
        
        conn = get_connection()
        cur = conn.cursor()
        
        # Get max fault_id from table
        query = f"SELECT MAX(fault_id) FROM {table_name}"
        cur.execute(query)
        result = cur.fetchone()
        
        max_fault_id = result[0] if result[0] else 0
        next_id = max_fault_id + 1
        
        logger.info(f"✓ Next fault_id for {failure_type}: {next_id}")
        return next_id
        
    except Exception as e:
        logger.error(f"Error getting next fault_id for {failure_type}: {e}")
        raise
    finally:
        if conn:
            conn.close()


def insert_event_data_to_database(failure_type, slope_data, event_statistics):
    """
    Insert event data into the appropriate failure-specific table in Neon.
    
    Args:
        failure_type: Name of the failure (e.g., "Motor Stall")
        slope_data: List of dicts with keys: timestamp, value, slope, time_delta
        event_statistics: Dict with keys: min, max, mean, std_dev, range, variance, 
                         skewness, kurtosis, frequency1-5, amplitude1-5
        
    Returns:
        Dict with fault_id, rows_inserted, and table name
    """
    conn = None
    rows_inserted = 0
    fault_id = None
    
    try:
        # Get table name and validate
        table_name = FAILURE_TABLE_MAPPING.get(failure_type)
        if not table_name:
            raise ValueError(f"Unknown failure type: {failure_type}")
        
        # Get next fault_id
        fault_id = get_next_fault_id(failure_type)
        
        conn = get_connection()
        cur = conn.cursor()
        
        # Prepare insert query
        query = f"""
            INSERT INTO {table_name}
            (fault_id, timestamp, x_min, x_max, mean, standard_deviation, range, variance,
             skewness, kurtosis, frequency1, frequency2, frequency3, frequency4, frequency5,
             amplitude1, amplitude2, amplitude3, amplitude4, amplitude5)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Insert each data point
        for point in slope_data:
            try:
                # Convert timestamp (milliseconds) to datetime
                timestamp_dt = datetime.fromtimestamp(point['timestamp'] / 1000)
                
                cur.execute(query, (
                    fault_id,                                           # fault_id
                    timestamp_dt,                                       # timestamp
                    event_statistics.get('min', 0),                    # x_min
                    event_statistics.get('max', 0),                    # x_max
                    event_statistics.get('mean', 0),                   # mean
                    event_statistics.get('std_dev', 0),                # standard_deviation
                    event_statistics.get('range', 0),                  # range
                    event_statistics.get('variance', 0),               # variance
                    event_statistics.get('skewness', 0),               # skewness
                    event_statistics.get('kurtosis', 0),               # kurtosis
                    event_statistics.get('frequency1', 0),             # frequency1
                    event_statistics.get('frequency2', 0),             # frequency2
                    event_statistics.get('frequency3', 0),             # frequency3
                    event_statistics.get('frequency4', 0),             # frequency4
                    event_statistics.get('frequency5', 0),             # frequency5
                    event_statistics.get('amplitude1', 0),             # amplitude1
                    event_statistics.get('amplitude2', 0),             # amplitude2
                    event_statistics.get('amplitude3', 0),             # amplitude3
                    event_statistics.get('amplitude4', 0),             # amplitude4
                    event_statistics.get('amplitude5', 0)              # amplitude5
                ))
                rows_inserted += 1
                
            except Exception as e:
                logger.error(f"Error inserting row for {failure_type}: {e}")
                raise
        
        # Commit all inserts
        conn.commit()
        
        logger.info(
            f"✓ Event saved to database: "
            f"Table={table_name}, fault_id={fault_id}, rows={rows_inserted}"
        )
        
        return {
            'success': True,
            'fault_id': fault_id,
            'rows_inserted': rows_inserted,
            'table_name': table_name
        }
        
    except Exception as e:
        logger.error(f"Error inserting event data for {failure_type}: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def insert_event_from_historical_data(failure_type, extracted_data):
    """
    Insert event data from historical extraction into the appropriate failure table in Neon.
    Used when creating events from existing historical database records.
    
    Args:
        failure_type: Name of the failure (e.g., "Motor Stall")
        extracted_data: List of dicts with historical stat columns
        
    Returns:
        Dict with fault_id, rows_inserted, and table name
    """
    conn = None
    rows_inserted = 0
    fault_id = None
    
    try:
        # Get table name and validate
        table_name = FAILURE_TABLE_MAPPING.get(failure_type)
        if not table_name:
            raise ValueError(f"Unknown failure type: {failure_type}")
        
        # Get next fault_id for this failure type
        fault_id = get_next_fault_id(failure_type)
        
        conn = get_connection()
        cur = conn.cursor()
        
        # Prepare insert query
        query = f"""
            INSERT INTO {table_name}
            (fault_id, timestamp, x_min, x_max, mean, standard_deviation, range, variance,
             skewness, kurtosis, frequency1, frequency2, frequency3, frequency4, frequency5,
             amplitude1, amplitude2, amplitude3, amplitude4, amplitude5)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # Insert each historical data point with the new fault_id
        for data_point in extracted_data:
            try:
                # Parse timestamp if it's a string
                timestamp_val = data_point.get('timestamp', datetime.now())
                if isinstance(timestamp_val, str):
                    try:
                        timestamp_val = datetime.fromisoformat(timestamp_val)
                    except:
                        timestamp_val = datetime.now()
                
                cur.execute(query, (
                    fault_id,                                           # fault_id
                    timestamp_val,                                      # timestamp
                    data_point.get('min', 0),                          # x_min
                    data_point.get('max', 0),                          # x_max
                    data_point.get('mean', 0),                         # mean
                    data_point.get('std_dev', 0),                      # standard_deviation
                    data_point.get('range', 0),                        # range
                    data_point.get('variance', 0),                     # variance
                    data_point.get('skewness', 0),                     # skewness
                    data_point.get('kurtosis', 0),                     # kurtosis
                    data_point.get('frequency1', 0),                   # frequency1
                    data_point.get('frequency2', 0),                   # frequency2
                    data_point.get('frequency3', 0),                   # frequency3
                    data_point.get('frequency4', 0),                   # frequency4
                    data_point.get('frequency5', 0),                   # frequency5
                    data_point.get('amplitude1', 0),                   # amplitude1
                    data_point.get('amplitude2', 0),                   # amplitude2
                    data_point.get('amplitude3', 0),                   # amplitude3
                    data_point.get('amplitude4', 0),                   # amplitude4
                    data_point.get('amplitude5', 0)                    # amplitude5
                ))
                rows_inserted += 1
                
            except Exception as e:
                logger.error(f"Error inserting historical data point for {failure_type}: {e}")
                raise
        
        # Commit all inserts
        conn.commit()
        
        logger.info(
            f"✓ Event saved to database from historical data: "
            f"Table={table_name}, fault_id={fault_id}, rows={rows_inserted}"
        )
        
        return {
            'success': True,
            'fault_id': fault_id,
            'rows_inserted': rows_inserted,
            'table_name': table_name
        }
        
    except Exception as e:
        logger.error(f"Error inserting historical event data for {failure_type}: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
