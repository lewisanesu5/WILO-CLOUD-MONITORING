import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
import logging
import time

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv('DATABASE_URL')

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
        stats_dict: Dictionary with keys: mean, max, min, std_dev, skewness, kurtosis
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
            (x_min, x_max, mean, standard_deviation, skewness, kurtosis,
             frequency1, frequency2, frequency3, frequency4, frequency5,
             amplitude1, amplitude2, amplitude3, amplitude4, amplitude5)
            VALUES (%s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s)
        """
        
        query_start = time.time()
        cur.execute(query, (
            stats_dict.get('min', 0),           # x_min
            stats_dict.get('max', 0),           # x_max
            stats_dict.get('mean', 0),          # mean
            stats_dict.get('std_dev', 0),       # standard_deviation
            stats_dict.get('skewness', 0),      # skewness
            stats_dict.get('kurtosis', 0),      # kurtosis
            freqs[0], freqs[1], freqs[2], freqs[3], freqs[4],  # frequency1-5
            amps[0], amps[1], amps[2], amps[3], amps[4]        # amplitude1-5
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
