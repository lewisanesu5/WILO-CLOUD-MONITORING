"""
Remote Sensor Client Upload Script
For uploading CSV files from remote servers to the Predictive Maintenance system
Runs on 2-hour schedule with retry logic
"""

import requests
import os
import time
import logging
from datetime import datetime, timedelta
import schedule
import json

# Configuration
SERVER_URL = 'https://wilo-cloud-monitoring.onrender.com'  # Change to your server
API_KEY = 'sk_prod_7f3b8e2a9c1d4f6e5a2b9c8d7e1f3a5b'  # Use your assigned API key
SENSOR_ID = 'sensor-001'
LOCAL_DATA_DIR = './sensor_data'  # Where max/min files are generated locally
UPLOAD_INTERVAL_HOURS = 2

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('upload_client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RemoteUploadClient:
    def __init__(self, server_url, api_key, sensor_id):
        self.server_url = server_url
        self.api_key = api_key
        self.sensor_id = sensor_id
        self.session = requests.Session()
        self.last_successful_upload = None
        
    def upload_sensor_batch(self, sensor_name):
        """
        Upload max and min CSV files for a sensor.
        
        Args:
            sensor_name: 'acceleration', 'current', or 'audio'
        """
        try:
            max_file = f"{LOCAL_DATA_DIR}/max_{sensor_name}.csv"
            min_file = f"{LOCAL_DATA_DIR}/min_{sensor_name}.csv"
            
            # Verify files exist
            if not os.path.exists(max_file) or not os.path.exists(min_file):
                logger.error(f'Files not found for {sensor_name}')
                return False
            
            # Prepare upload
            files = [
                ('files', ('max_' + sensor_name + '.csv', open(max_file, 'rb'), 'text/csv')),
                ('files', ('min_' + sensor_name + '.csv', open(min_file, 'rb'), 'text/csv'))
            ]
            
            headers = {
                'X-API-Key': self.api_key
            }
            
            # Upload with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f'Uploading {sensor_name} batch (attempt {attempt + 1}/{max_retries})')
                    
                    response = self.session.post(
                        f'{self.server_url}/api/upload',
                        files=files,
                        headers=headers,
                        timeout=30
                    )
                    
                    if response.status_code == 201:
                        result = response.json()
                        logger.info(f'✓ Upload successful: {result}')
                        self.last_successful_upload = datetime.now()
                        return True
                    
                    elif response.status_code == 401:
                        logger.error('Authentication failed: Invalid API key')
                        return False
                    
                    elif response.status_code == 403:
                        logger.error('Authorization failed: Access denied')
                        return False
                    
                    else:
                        logger.warning(f'Upload failed (status {response.status_code}): {response.text}')
                        if attempt < max_retries - 1:
                            wait_time = 5 * (2 ** attempt)  # Exponential backoff: 5, 10, 20 seconds
                            logger.info(f'Retrying in {wait_time} seconds...')
                            time.sleep(wait_time)
                
                except requests.exceptions.Timeout:
                    logger.error(f'Timeout on attempt {attempt + 1}')
                    if attempt < max_retries - 1:
                        time.sleep(5)
                except requests.exceptions.ConnectionError as e:
                    logger.error(f'Connection error: {e}')
                    if attempt < max_retries - 1:
                        time.sleep(10)
            
            logger.error(f'Upload failed after {max_retries} attempts')
            return False
            
        except Exception as e:
            logger.error(f'Upload error: {str(e)}')
            return False
    
    def upload_all_sensors(self):
        """Upload all sensor data (acceleration, current, audio)."""
        logger.info('=' * 50)
        logger.info(f'Starting upload batch at {datetime.now()}')
        logger.info('=' * 50)
        
        sensors = ['acceleration', 'current', 'audio']
        results = {}
        
        for sensor in sensors:
            results[sensor] = self.upload_sensor_batch(sensor)
        
        success_count = sum(1 for v in results.values() if v)
        logger.info(f'Upload batch complete: {success_count}/{len(sensors)} sensors successful')
        logger.info('=' * 50)
        
        return all(results.values())
    
    def check_server_health(self):
        """Verify server connectivity."""
        try:
            response = self.session.get(f'{self.server_url}/health', timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_upload_status(self):
        """Get upload history from server."""
        try:
            response = self.session.get(f'{self.server_url}/api/upload/status', timeout=5)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None

def run_scheduler():
    """Main scheduler loop."""
    client = RemoteUploadClient(SERVER_URL, API_KEY, SENSOR_ID)
    
    # Check server health on startup
    logger.info(f'Connecting to server: {SERVER_URL}')
    if not client.check_server_health():
        logger.error('Server is not reachable! Check SERVER_URL and connectivity.')
    else:
        logger.info('✓ Server is reachable')
    
    # Schedule upload every 2 hours
    schedule.every(UPLOAD_INTERVAL_HOURS).hours.do(client.upload_all_sensors)
    
    # Schedule status check every 30 minutes
    schedule.every(30).minutes.do(lambda: log_status(client))
    
    logger.info(f'Scheduler started. Upload interval: {UPLOAD_INTERVAL_HOURS} hours')
    logger.info('Waiting for first scheduled upload...')
    
    # Run scheduler
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def log_status(client):
    """Log current upload status."""
    status = client.get_upload_status()
    if status:
        logger.info(f'Status: {json.dumps(status, indent=2)}')

if __name__ == '__main__':
    # Run immediate upload for testing (comment out for production)
    # client = RemoteUploadClient(SERVER_URL, API_KEY, SENSOR_ID)
    # client.upload_all_sensors()
    
    # Run scheduler
    run_scheduler()
