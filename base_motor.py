"""
base_motor.py
=============
Shared base module for all fault simulation scripts.

Motor: Havells MHPE355LB8 - 200kW / 270HP, 8-Pole, IE3
       415V 3-Phase 50Hz, Rated Current ~375A, ~735 RPM
"""

import os
import math
import random
import time
import shutil
import logging
import json
import requests
import urllib3
from datetime import datetime, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------
# SERVER / CLIENT CONFIG
# ---------------------------------------------
SERVER_URL   = os.getenv('SERVER_URL', 'https://wilo-cloud-monitoring.onrender.com')
API_KEY      = 'sk_prod_7f3b8e2a9c1d4f6e5a2b9c8d7e1f3a5b'
SENSOR_ID    = 'sensor-001'
LOCAL_DATA_DIR = r'C:\Users\lewis\OneDrive\Desktop\SEMESTER 4\WILO\data'
try:
    if not os.path.exists(LOCAL_DATA_DIR):
        os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
    test_file = os.path.join(LOCAL_DATA_DIR, '.write_test')
    with open(test_file, 'w') as f:
        f.write('test')
    os.remove(test_file)
except Exception:
    LOCAL_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Data'))

# ---------------------------------------------
# MOTOR CONSTANTS  (Havells MHPE355LB8)
# ---------------------------------------------
MOTOR = {
    'power_kw'         : 200.0,
    'poles'            : 8,
    'supply_freq_hz'   : 50.0,
    'sync_rpm'         : 750.0,
    'rated_rpm'        : 735.0,
    'rated_current_a'  : 375.0,         # Full-load amps
    'locked_rotor_mult': 6.5,           # LRC = 6.5 × FLA  → ~2438 A
    'voltage_v'        : 415.0,
    'power_factor'     : 0.82,
    'efficiency'       : 0.955,
    'insulation_class' : 'F',
    # Derived frequencies (Hz)
    'f_rot'            : 735.0 / 60,    # 12.25 Hz  - 1× rotational
    'f_2x'            : 2 * 735.0 / 60, # 24.50 Hz  - 2× rotational (misalignment)
    'f_supply'         : 50.0,          # Supply frequency
    'f_2supply'        : 100.0,         # 2× supply  (electrical faults)
    'slip'             : (750 - 735) / 750,   # 0.02
    # Bearing: 6-ball deep-groove (typical 355-frame)
    # Using SKF 6322 equivalent geometry: Bd/Pd ~ 0.28, contact angle ~ 0°
    'bpfo'             : 52.3,          # Ball Pass Frequency Outer race (Hz)
    'bpfi'             : 72.7,          # Ball Pass Frequency Inner race (Hz)
    'bsf'              : 9.1,           # Ball Spin Frequency (Hz)
    'ftf'              : 4.4,           # Fundamental Train Frequency (Hz)
    # Pump: 6-blade impeller
    'bpf'              : 12.25 * 6,     # Blade Pass Frequency = 73.5 Hz
    # Baseline sensor values
    'accel_rms_g'      : 0.50,          # g  - healthy vibration RMS
    'accel_peak_g'     : 1.20,          # g  - healthy peak
    'current_rms_a'    : 375.0,         # A  - full-load RMS
    'audio_db'         : 82.0,          # dB(A) - healthy SPL at 1m (355-frame TEFC)
}

SAMPLE_RATE   = 700          # Hz
N_SAMPLES     = 1400         # points per 2-second window
TOTAL_UPLOADS = 50


# ---------------------------------------------
# LOGGING
# ---------------------------------------------
def setup_logger(fault_name: str) -> logging.Logger:
    logger = logging.getLogger(fault_name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(f'{fault_name}_upload.log')
        sh = logging.StreamHandler()
        fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        fh.setFormatter(fmt)
        sh.setFormatter(fmt)
        logger.addHandler(fh)
        logger.addHandler(sh)
    return logger


# ---------------------------------------------
# DEVIATION CURVE
# ---------------------------------------------
def sigmoid_deviation(upload_num: int, onset: int, steepness: float = 0.45) -> float:
    """
    Returns 0.0 (healthy) → 1.0 (critical) using a sigmoid.
    Before onset: returns essentially 0.
    Reaches ~0.99 by upload 50.
    """
    x = upload_num - onset
    return 1.0 / (1.0 + math.exp(-steepness * x))


def sensor_deviation(upload_num: int, onset: int, lag: int = 0,
                     steepness: float = 0.45) -> float:
    """Deviation for a sensor that lags the primary onset by `lag` uploads."""
    effective_onset = onset + lag
    if upload_num <= effective_onset:
        return 0.0
    return sigmoid_deviation(upload_num, effective_onset, steepness)


# ---------------------------------------------
# SIGNAL GENERATION UTILITIES
# ---------------------------------------------
def make_timestamps(start: datetime, n: int = N_SAMPLES,
                    fs: float = SAMPLE_RATE) -> list:
    dt = 1.0 / fs
    return [start + timedelta(seconds=i * dt) for i in range(n)]


def gaussian_noise(sigma: float, n: int = N_SAMPLES) -> list:
    return [random.gauss(0, sigma) for _ in range(n)]


def sinusoid(freq_hz: float, amplitude: float, phase: float = 0.0,
             n: int = N_SAMPLES, fs: float = SAMPLE_RATE) -> list:
    return [amplitude * math.sin(2 * math.pi * freq_hz * i / fs + phase)
            for i in range(n)]


def add_impulses(signal: list, rate: float, magnitude: float,
                 decay: float = 0.85) -> list:
    """
    Add decaying impulse train (simulates bearing/cavitation impacts).
    rate: average impulses per second
    """
    out = list(signal)
    n = len(out)
    fs = SAMPLE_RATE
    interval_samples = max(1, int(fs / rate))
    i = random.randint(0, interval_samples)
    while i < n:
        mag = magnitude * random.uniform(0.7, 1.3)
        j = i
        while j < n and (j - i) < int(0.05 * fs):   # 50 ms decay window
            out[j] += mag * (decay ** (j - i))
            j += 1
        i += interval_samples + random.randint(-interval_samples // 4,
                                                interval_samples // 4)
    return out


def amplitude_modulate(carrier: list, mod_freq: float, mod_depth: float,
                        fs: float = SAMPLE_RATE) -> list:
    """Amplitude-modulate a signal at mod_freq Hz - used for sidebands."""
    n = len(carrier)
    return [carrier[i] * (1.0 + mod_depth * math.sin(2 * math.pi * mod_freq * i / fs))
            for i in range(n)]


def compute_max_min(signal: list) -> tuple:
    """Return (max_value, min_value) from a signal array."""
    return max(signal), min(signal)


def save_csv(filepath: str, timestamps: list, values: list):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
        f.write('timestamp,value\n')
        for ts, v in zip(timestamps, values):
            f.write(f'{ts.isoformat()},{v:.6f}\n')


def save_max_min_csvs(sensor_name: str, data_dir: str,
                      timestamps: list, signal: list):
    """
    From a full 1400-point signal, extract max and min windows
    and save as max_{sensor}.csv and min_{sensor}.csv.
    Each output file contains 1400 rows - the window around the max/min region.
    To simulate real hardware behaviour the max file uses the first half of the
    recording session and the min file uses the second half (as per project spec).
    """
    half = N_SAMPLES // 2
    max_signal = signal[:half]
    min_signal = signal[half:]
    max_ts = timestamps[:half]
    min_ts = timestamps[half:]

    # Pad both halves back to N_SAMPLES by repeating with slight noise
    def pad(sig, target):
        out = list(sig)
        while len(out) < target:
            base = out[-(len(sig)): ]
            out.extend([v + random.gauss(0, abs(v) * 0.002 + 1e-6)
                        for v in base[:target - len(out)]])
        return out[:target]

    def pad_ts(ts_list, target, start_dt):
        out = list(ts_list)
        dt = timedelta(seconds=1.0 / SAMPLE_RATE)
        last = out[-1]
        while len(out) < target:
            last += dt
            out.append(last)
        return out[:target]

    max_signal_full = pad(max_signal, N_SAMPLES)
    min_signal_full = pad(min_signal, N_SAMPLES)
    max_ts_full = pad_ts(max_ts, N_SAMPLES, max_ts[0])
    min_ts_full = pad_ts(min_ts, N_SAMPLES, min_ts[0])

    save_csv(os.path.join(data_dir, f'max_{sensor_name}.csv'),
             max_ts_full, max_signal_full)
    save_csv(os.path.join(data_dir, f'min_{sensor_name}.csv'),
             min_ts_full, min_signal_full)


# ---------------------------------------------
# UPLOAD CLIENT
# ---------------------------------------------
class RemoteUploadClient:
    def __init__(self, server_url=SERVER_URL, api_key=API_KEY,
                 sensor_id=SENSOR_ID, fault_name: str = '', logger=None):
        self.server_url  = server_url.rstrip('/')
        self.api_key     = api_key
        self.sensor_id   = sensor_id
        self.fault_name  = fault_name   # forwarded as X-Fault-Name header
        self.session     = requests.Session()
        self.logger      = logger or logging.getLogger(__name__)

    def _headers(self, is_failure: bool = False):
        h = {'X-API-Key': self.api_key}
        if self.fault_name:
            h['X-Fault-Name'] = self.fault_name
        if is_failure:
            h['X-Fault-Failure'] = 'true'
        return h

    def check_health(self) -> bool:
        try:
            r = self.session.get(f'{self.server_url}/health',
                                 timeout=5, verify=False)
            return r.status_code == 200
        except Exception:
            return False

    def upload_sensor(self, sensor_name: str, data_dir: str, is_failure: bool = False) -> bool:
        max_file = os.path.join(data_dir, f'max_{sensor_name}.csv')
        min_file = os.path.join(data_dir, f'min_{sensor_name}.csv')
        if not os.path.exists(max_file) or not os.path.exists(min_file):
            self.logger.error(f'Missing files for {sensor_name}')
            return False

        for attempt in range(3):
            try:
                with open(max_file, 'rb') as fm, open(min_file, 'rb') as fn:
                    files = [
                        ('files', (f'max_{sensor_name}.csv', fm, 'text/csv')),
                        ('files', (f'min_{sensor_name}.csv', fn, 'text/csv')),
                    ]
                    r = self.session.post(
                        f'{self.server_url}/api/upload',
                        files=files,
                        headers=self._headers(is_failure),
                        timeout=30,
                        verify=False,
                    )
                if r.status_code == 201:
                    self.logger.info(f'[OK] {sensor_name}: {r.json()}')
                    return True
                elif r.status_code in (401, 403):
                    self.logger.error(f'Auth error {r.status_code}')
                    return False
                else:
                    self.logger.warning(f'{sensor_name} attempt {attempt+1} '
                                        f'failed ({r.status_code})')
                    if attempt < 2:
                        time.sleep(5 * (2 ** attempt))
            except requests.exceptions.Timeout:
                self.logger.error(f'Timeout - {sensor_name} attempt {attempt+1}')
                if attempt < 2:
                    time.sleep(5)
            except requests.exceptions.ConnectionError as e:
                self.logger.error(f'Connection error: {e}')
                if attempt < 2:
                    time.sleep(10)
        return False

    def upload_all(self, data_dir: str, max_cycle_retries: int = 5, is_failure: bool = False) -> bool:
        """
        Upload all 3 sensors for a cycle.
        Only retries sensors that failed -- never re-uploads a sensor that already
        succeeded (which would create a duplicate DB row).
        Guarantees equal row counts across sensors as long as a retry eventually works.
        """
        SENSORS = ('acceleration', 'current', 'audio')
        results = {s: False for s in SENSORS}

        for attempt in range(max_cycle_retries):
            pending = [s for s in SENSORS if not results[s]]
            for sensor in pending:
                results[sensor] = self.upload_sensor(sensor, data_dir, is_failure)

            ok = sum(v for v in results.values())
            failed = [s for s in SENSORS if not results[s]]

            if not failed:
                self.logger.info(f'Batch result: {ok}/3 sensors uploaded')
                return True

            if attempt < max_cycle_retries - 1:
                wait = 10 * (attempt + 1)
                self.logger.warning(
                    f'Batch attempt {attempt + 1}/{max_cycle_retries}: '
                    f'{failed} failed -- retrying in {wait}s'
                )
                time.sleep(wait)

        self.logger.error(
            f'Batch INCOMPLETE after {max_cycle_retries} attempts: '
            f'{[s for s in SENSORS if not results[s]]} not uploaded -- '
            f'DB will have unequal row counts for this cycle'
        )
        return False

    def get_status(self):
        try:
            r = self.session.get(f'{self.server_url}/api/upload/status',
                                 timeout=5, verify=False)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None


# ---------------------------------------------
# BACKUP UTILITY
# ---------------------------------------------
def backup_existing(data_dir: str, logger: logging.Logger):
    backup_dir = os.path.join(os.path.dirname(data_dir), 'data_backup')
    os.makedirs(backup_dir, exist_ok=True)
    for sensor in ('acceleration', 'current', 'audio'):
        for prefix in ('max', 'min'):
            src = os.path.join(data_dir, f'{prefix}_{sensor}.csv')
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(backup_dir,
                                                f'{prefix}_{sensor}.csv'))
                logger.info(f'Backed up {prefix}_{sensor}.csv')


# ---------------------------------------------
# SIMULATION RUNNER
# ---------------------------------------------
def run_fault_simulation(fault_name: str,
                          generate_fn,
                          sleep_seconds: int = 3,
                          data_dir: str = LOCAL_DATA_DIR):
    """
    Generic simulation loop.
    generate_fn(upload_num, onset, data_dir, logger) must write all 6 CSV files.
    After every complete 3-sensor batch the server automatically creates a fault
    event via the X-Fault-Name header - no manual trigger required.
    Inter-batch sleep defaults to 3 seconds.
    """
    # Force sleep_seconds to 3 for all uploads to meet the lag interval requirement
    sleep_seconds = 3

    logger = setup_logger(fault_name)
    logger.info('=' * 60)
    logger.info(f'Fault Simulation: {fault_name.upper()}')
    logger.info(f'Motor: Havells MHPE355LB8 | 200kW | 8-pole | 735 RPM')
    logger.info('=' * 60)

    os.makedirs(data_dir, exist_ok=True)
    backup_existing(data_dir, logger)

    client = RemoteUploadClient(fault_name=fault_name, logger=logger)
    if client.check_health():
        logger.info('[READY] Server reachable')
    else:
        logger.warning('Server not reachable - proceeding anyway')

    # Randomise fault onset between upload 10 and 25
    onset = random.randint(10, 25)
    logger.info(f'Fault onset set at upload {onset} '
                f'(critical by upload {TOTAL_UPLOADS})')

    for upload_num in range(1, TOTAL_UPLOADS + 1):
        logger.info(f'\n{"-"*50}')
        logger.info(f'Upload cycle {upload_num}/{TOTAL_UPLOADS}  |  '
                    f'Fault onset: {onset}')

        # Check if generator returned failure state
        is_failure = generate_fn(upload_num, onset, data_dir, logger)
        if not isinstance(is_failure, bool):
            # Fallback calculation: map fault name to its default threshold and steepness
            # so all 11 fault simulations halt at their designated critical stage.
            threshold_map = {
                'pump_cavitation': (0.75, 0.43),
                'pump_seal_leakage': (0.65, 0.41),
                'pump_impeller_damage': (0.80, 0.43),
                'motor_bearing_failure': (0.80, 0.40),
                'motor_shaft_misalignment': (0.80, 0.42),
                'motor_overheating': (0.75, 0.35),
                'motor_winding_failure': (0.85, 0.44),
                'motor_stall': (0.50, 0.50),
                'motor_electrical_fault': (0.80, 0.42),
                'motor_vibration_anomaly': (0.80, 0.42),
                'custom': (0.75, 0.43),
                'custom_fault': (0.75, 0.43)
            }
            thresh, steep = threshold_map.get(fault_name.lower(), (0.80, 0.45))
            effective_dev = sensor_deviation(upload_num, onset, lag=0, steepness=steep)
            is_failure = effective_dev >= thresh

        success = client.upload_all(data_dir, is_failure=is_failure)

        status = f'{"SUCCESS" if success else "FAILED"}'
        logger.info(f'[{status}] Cycle {upload_num}/{TOTAL_UPLOADS}')

        if is_failure:
            logger.info(f"💥 FAILURE COMMITTED on cycle {upload_num}/{TOTAL_UPLOADS}!")
            logger.info("Auto-event trigger complete. Stopping simulation runner.")
            break

        status_data = client.get_status()
        if status_data:
            logger.info(f'Server status: {json.dumps(status_data, indent=2)}')

        if upload_num < TOTAL_UPLOADS:
            logger.info(f'Sleeping {sleep_seconds}s ...')
            time.sleep(sleep_seconds)

    logger.info('=' * 60)
    logger.info(f'Simulation complete: {fault_name}')
    logger.info('=' * 60)
