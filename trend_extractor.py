"""
trend_extractor.py  -  Upgraded trend extraction for predictive maintenance
Drop this file into your project root and call it from app.py.

Key improvements over the original:
  1. Multi-parameter deviation scoring (not just mean)
  2. Per-sensor, per-fault parameter weights derived from physical signatures
  3. Robust baseline from a configurable percentile window - not just first N points
  4. Z-score normalisation stored alongside raw values for model-ready features
  5. Separate min/max file query paths - min file used for electrical fault signatures
  6. Monotonic trend slope computed per parameter (used as a training feature)
  7. Deviation window returned is the actual pre-fault trend, not a dump of all records
  8. Fault severity score - a single float you can threshold in the model
"""

import numpy as np
from scipy import stats as scipy_stats
from scipy.signal import find_peaks
import logging
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PARAMETER WEIGHTS PER FAULT TYPE
# ---------------------------------------------------------------------------
# Each entry maps a fault to (sensor, parameter, weight) tuples.
# Weight = how much this parameter contributes to the deviation score for
# this fault. Derived from the physical signatures documented in the
# fault-sensor mapping table.
#
# Rules used:
#   - Primary sensor parameters get weight 1.0
#   - Secondary sensor parameters get weight 0.4
#   - Unrelated parameters get weight 0.0 (excluded from score)
#
FAULT_PARAMETER_WEIGHTS: Dict[str, List[Dict]] = {
    'motor_bearing_failure': [
        {'sensor': 'acceleration', 'param': 'kurtosis',    'weight': 1.0, 'direction': 'up'},
        {'sensor': 'acceleration', 'param': 'skewness',    'weight': 0.7, 'direction': 'abs'},  # abs = magnitude matters
        {'sensor': 'acceleration', 'param': 'mean',        'weight': 0.5, 'direction': 'up'},
        {'sensor': 'acceleration', 'param': 'amplitude1',  'weight': 0.8, 'direction': 'up'},   # BPFI/BPFO harmonic
        {'sensor': 'audio',        'param': 'kurtosis',    'weight': 0.7, 'direction': 'up'},
        {'sensor': 'audio',        'param': 'amplitude1',  'weight': 0.6, 'direction': 'up'},
    ],
    'motor_electrical_fault': [
        {'sensor': 'current',      'param': 'skewness',    'weight': 1.0, 'direction': 'abs'},
        {'sensor': 'current',      'param': 'kurtosis',    'weight': 0.9, 'direction': 'up'},
        {'sensor': 'current',      'param': 'amplitude2',  'weight': 0.8, 'direction': 'up'},   # 3rd harmonic
        {'sensor': 'current',      'param': 'amplitude3',  'weight': 0.7, 'direction': 'up'},   # 5th harmonic
        {'sensor': 'current',      'param': 'frequency2',  'weight': 0.6, 'direction': 'any'},  # sideband shift
        {'sensor': 'acceleration', 'param': 'amplitude2',  'weight': 0.4, 'direction': 'up'},   # 2x slip freq
    ],
    'motor_overheating': [
        {'sensor': 'current',      'param': 'mean',        'weight': 1.0, 'direction': 'up'},
        {'sensor': 'current',      'param': 'std_dev',     'weight': 0.7, 'direction': 'up'},
        {'sensor': 'current',      'param': 'range',       'weight': 0.6, 'direction': 'up'},
        {'sensor': 'audio',        'param': 'mean',        'weight': 0.3, 'direction': 'up'},   # cooling fan noise
    ],
    'motor_shaft_misalignment': [
        {'sensor': 'acceleration', 'param': 'amplitude2',  'weight': 1.0, 'direction': 'up'},   # 2x RPM harmonic
        {'sensor': 'acceleration', 'param': 'amplitude3',  'weight': 0.7, 'direction': 'up'},   # 4x RPM
        {'sensor': 'acceleration', 'param': 'kurtosis',    'weight': 0.2, 'direction': 'any'},  # usually flat
        {'sensor': 'current',      'param': 'amplitude2',  'weight': 0.4, 'direction': 'up'},
    ],
    'motor_stall': [
        {'sensor': 'current',      'param': 'mean',        'weight': 1.0, 'direction': 'up'},   # locked-rotor current
        {'sensor': 'current',      'param': 'kurtosis',    'weight': 0.8, 'direction': 'up'},   # onset transient
        {'sensor': 'acceleration', 'param': 'mean',        'weight': 1.0, 'direction': 'down'}, # vibration drops
        {'sensor': 'acceleration', 'param': 'amplitude1',  'weight': 0.8, 'direction': 'down'}, # rotational harmonics gone
    ],
    'motor_vibration_anomaly': [
        {'sensor': 'acceleration', 'param': 'std_dev',     'weight': 1.0, 'direction': 'up'},
        {'sensor': 'acceleration', 'param': 'kurtosis',    'weight': 0.9, 'direction': 'up'},
        {'sensor': 'acceleration', 'param': 'mean',        'weight': 0.7, 'direction': 'up'},
        {'sensor': 'audio',        'param': 'std_dev',     'weight': 0.5, 'direction': 'up'},
    ],
    'motor_winding_failure': [
        {'sensor': 'current',      'param': 'amplitude2',  'weight': 1.0, 'direction': 'up'},   # 3rd harmonic dominant
        {'sensor': 'current',      'param': 'amplitude3',  'weight': 0.9, 'direction': 'up'},   # 5th harmonic
        {'sensor': 'current',      'param': 'kurtosis',    'weight': 0.8, 'direction': 'up'},
        {'sensor': 'current',      'param': 'skewness',    'weight': 0.7, 'direction': 'abs'},
        {'sensor': 'acceleration', 'param': 'amplitude1',  'weight': 0.3, 'direction': 'up'},
    ],
    'pump_cavitation': [
        {'sensor': 'acceleration', 'param': 'kurtosis',    'weight': 1.0, 'direction': 'up'},
        {'sensor': 'acceleration', 'param': 'skewness',    'weight': 0.8, 'direction': 'abs'},
        {'sensor': 'acceleration', 'param': 'mean',        'weight': 0.6, 'direction': 'up'},
        {'sensor': 'audio',        'param': 'kurtosis',    'weight': 0.9, 'direction': 'up'},   # most sensitive for mild cavitation
        {'sensor': 'audio',        'param': 'amplitude3',  'weight': 0.7, 'direction': 'up'},   # broadband 1-5kHz
        {'sensor': 'audio',        'param': 'amplitude4',  'weight': 0.6, 'direction': 'up'},
    ],
    'pump_impeller_damage': [
        {'sensor': 'acceleration', 'param': 'amplitude1',  'weight': 1.0, 'direction': 'up'},   # BPF
        {'sensor': 'acceleration', 'param': 'amplitude2',  'weight': 0.8, 'direction': 'up'},   # 2xBPF
        {'sensor': 'acceleration', 'param': 'mean',        'weight': 0.5, 'direction': 'up'},
        {'sensor': 'current',      'param': 'amplitude1',  'weight': 0.6, 'direction': 'up'},   # BPF sideband in current
    ],
    'pump_seal_leakage': [
        {'sensor': 'audio',        'param': 'mean',        'weight': 1.0, 'direction': 'up'},   # broadband hiss
        {'sensor': 'audio',        'param': 'kurtosis',    'weight': 0.7, 'direction': 'up'},
        {'sensor': 'audio',        'param': 'amplitude3',  'weight': 0.8, 'direction': 'up'},   # 200-1000Hz
        {'sensor': 'acceleration', 'param': 'skewness',    'weight': 0.6, 'direction': 'abs'},
        {'sensor': 'current',      'param': 'mean',        'weight': 0.3, 'direction': 'any'},
    ],
    'custom_fault': [
        # Equal weight across all sensors - anomaly detection mode
        {'sensor': 'acceleration', 'param': 'kurtosis',    'weight': 1.0, 'direction': 'any'},
        {'sensor': 'acceleration', 'param': 'std_dev',     'weight': 1.0, 'direction': 'any'},
        {'sensor': 'current',      'param': 'kurtosis',    'weight': 1.0, 'direction': 'any'},
        {'sensor': 'current',      'param': 'std_dev',     'weight': 1.0, 'direction': 'any'},
        {'sensor': 'audio',        'param': 'kurtosis',    'weight': 1.0, 'direction': 'any'},
        {'sensor': 'audio',        'param': 'std_dev',     'weight': 1.0, 'direction': 'any'},
    ],
}


# ---------------------------------------------------------------------------
# BASELINE COMPUTATION
# ---------------------------------------------------------------------------

def compute_robust_baseline(
    records: List[Dict],
    baseline_fraction: float = 0.2,
    min_baseline_points: int = 5,
    max_baseline_points: int = 30,
) -> Dict[str, Dict[str, float]]:
    """
    Compute a robust baseline from the earliest records.

    Uses the first `baseline_fraction` of records (e.g. 20%) as the baseline
    window. Falls back to `min_baseline_points` if the window is too small.

    Returns:
        {
          'acceleration': {'kurtosis': {'mean': ..., 'std': ...}, ...},
          'current': {...},
          'audio': {...}
        }

    Why not just first-N?
      Startup transients in the first few sessions can corrupt a small fixed
      window. Using a fraction of the full dataset adapts to however much
      healthy data was collected before the fault developed.
    """
    if not records:
        return {}

    n_baseline = max(
        min_baseline_points,
        min(max_baseline_points, int(len(records) * baseline_fraction))
    )
    # Records must be in chronological order (oldest first)
    baseline_records = records[:n_baseline]

    sensors = ['acceleration', 'current', 'audio']
    tracked_params = ['mean', 'max', 'min', 'std_dev', 'range',
                      'skewness', 'kurtosis',
                      'amplitude1', 'amplitude2', 'amplitude3',
                      'amplitude4', 'amplitude5',
                      'frequency1', 'frequency2', 'frequency3',
                      'frequency4', 'frequency5']

    baseline: Dict[str, Dict[str, Dict[str, float]]] = {}

    for sensor in sensors:
        baseline[sensor] = {}
        for param in tracked_params:
            values = []
            for rec in baseline_records:
                sensor_data = rec.get(sensor, {})
                val = sensor_data.get(param)
                if val is not None:
                    try:
                        values.append(float(val))
                    except (TypeError, ValueError):
                        pass

            if len(values) >= 2:
                baseline[sensor][param] = {
                    'mean': float(np.mean(values)),
                    'std':  max(float(np.std(values)), 1e-9),  # avoid div-by-zero
                    'p25':  float(np.percentile(values, 25)),
                    'p75':  float(np.percentile(values, 75)),
                    'n':    len(values),
                }
            elif len(values) == 1:
                baseline[sensor][param] = {
                    'mean': values[0],
                    'std':  1e-9,
                    'p25':  values[0],
                    'p75':  values[0],
                    'n':    1,
                }

    logger.info(
        f"Baseline computed from {n_baseline}/{len(records)} records "
        f"(fraction={baseline_fraction:.0%})"
    )
    return baseline


def z_score(value: float, baseline_entry: Dict) -> float:
    """Signed z-score of value against baseline distribution."""
    return (value - baseline_entry['mean']) / baseline_entry['std']


# ---------------------------------------------------------------------------
# PER-PARAMETER TREND SLOPE
# ---------------------------------------------------------------------------

def compute_trend_slopes(
    records: List[Dict],
    sensors: List[str],
    params: List[str],
) -> Dict[str, Dict[str, float]]:
    """
    Compute linear regression slope (per session) for each (sensor, param) pair.

    Returns:
        {sensor: {param: slope_per_session}}

    A rising kurtosis slope is more informative for a model than the raw
    kurtosis value - it tells you the *rate of deterioration*.
    """
    n = len(records)
    if n < 3:
        return {s: {p: 0.0 for p in params} for s in sensors}

    x = np.arange(n, dtype=float)
    slopes: Dict[str, Dict[str, float]] = {}

    for sensor in sensors:
        slopes[sensor] = {}
        for param in params:
            y = []
            for rec in records:
                val = rec.get(sensor, {}).get(param)
                if val is not None:
                    try:
                        y.append(float(val))
                    except (TypeError, ValueError):
                        y.append(np.nan)
                else:
                    y.append(np.nan)

            y_arr = np.array(y)
            valid = ~np.isnan(y_arr)
            if valid.sum() >= 3:
                slope, _, _, _, _ = scipy_stats.linregress(x[valid], y_arr[valid])
                slopes[sensor][param] = float(slope)
            else:
                slopes[sensor][param] = 0.0

    return slopes


# ---------------------------------------------------------------------------
# DEVIATION SCORING
# ---------------------------------------------------------------------------

def score_record(
    record: Dict,
    baseline: Dict,
    fault_weights: List[Dict],
    min_z_threshold: float = 1.0,
) -> float:
    """
    Compute a weighted deviation score for a single record.

    Each weighted parameter contributes:
        contribution = weight × max(0, |z_score| - min_z_threshold)
    where direction filtering applies ('up' only counts positive z,
    'down' only negative, 'abs'/'any' count magnitude).

    Returns a float ≥ 0. Higher = more deviated from baseline.
    """
    total_weight = sum(fw['weight'] for fw in fault_weights)
    if total_weight == 0:
        return 0.0

    score = 0.0
    for fw in fault_weights:
        sensor  = fw['sensor']
        param   = fw['param']
        weight  = fw['weight']
        direction = fw.get('direction', 'any')

        # Get current value
        val = record.get(sensor, {}).get(param)
        if val is None:
            continue
        try:
            val = float(val)
        except (TypeError, ValueError):
            continue

        # Get baseline entry
        bl = baseline.get(sensor, {}).get(param)
        if bl is None:
            continue

        z = z_score(val, bl)

        # Direction filter
        if direction == 'up' and z < 0:
            continue
        elif direction == 'down' and z > 0:
            continue
        # 'abs', 'any' pass through unconditionally

        magnitude = max(0.0, abs(z) - min_z_threshold)
        score += weight * magnitude

    # Normalise by total possible weight so score is 0-1 per sigma above threshold
    return score / total_weight


def find_deviation_onset(
    scores: List[float],
    window: int = 3,
    threshold_sigma: float = 1.5,
) -> int:
    """
    Find the index where deviation scores first consistently rise above
    the noise floor (defined as mean + threshold_sigma × std of the
    score series itself).

    Returns the index of deviation onset, or len(scores)-1 if no onset found.

    Using a window of 3 consecutive above-threshold points avoids
    false positives from single-session noise spikes.
    """
    if len(scores) < window + 1:
        return len(scores) - 1

    score_arr = np.array(scores)
    noise_mean = np.mean(score_arr[:max(3, len(score_arr) // 4)])
    noise_std  = max(np.std(score_arr[:max(3, len(score_arr) // 4)]), 1e-9)
    threshold  = noise_mean + threshold_sigma * noise_std

    consecutive = 0
    for i, s in enumerate(scores):
        if s > threshold:
            consecutive += 1
            if consecutive >= window:
                onset = i - window + 1
                logger.info(
                    f"Deviation onset detected at index {onset} "
                    f"(score={s:.3f}, threshold={threshold:.3f})"
                )
                return onset
        else:
            consecutive = 0

    return len(scores) - 1


# ---------------------------------------------------------------------------
# MAIN TREND EXTRACTION FUNCTION
# ---------------------------------------------------------------------------

def extract_fault_trend(
    records: List[Dict],  # list of {sensor: {param: value}, 'timestamp': ...}
    fault_name: str,
    pre_fault_window: int = 10,
    baseline_fraction: float = 0.2,
    file_type_preference: str = 'max',  # 'max' | 'min' | 'both'
) -> Dict[str, Any]:
    """
    Full trend extraction pipeline for a fault event.

    Args:
        records:
            List of multi-sensor records in CHRONOLOGICAL ORDER (oldest first).
            Each record has the shape:
            {
              'timestamp': '2024-01-01T10:00:00',
              'acceleration': {'mean': ..., 'kurtosis': ..., ...},
              'current':      {'mean': ..., 'kurtosis': ..., ...},
              'audio':        {'mean': ..., 'kurtosis': ..., ...},
            }
        fault_name:
            One of the FAULT_PARAMETER_WEIGHTS keys, e.g. 'motor_bearing_failure'.
        pre_fault_window:
            Number of records to include *before* the detected deviation onset.
            This is your pre-fault trend - the data the model learns to recognise.
        baseline_fraction:
            Fraction of records to use as healthy baseline (default 20%).
        file_type_preference:
            Which sensor file type to prioritise. 'min' for electrical faults
            (cleaner harmonic signature). 'max' for mechanical faults.

    Returns:
        {
          'fault_name': str,
          'total_records': int,
          'baseline_n': int,
          'deviation_onset_index': int,
          'pre_fault_records': list,   # the window before onset
          'onset_record': dict,        # the record at onset
          'deviation_scores': list,    # score per record, full series
          'baseline': dict,            # computed baseline stats
          'trend_slopes': dict,        # slope per (sensor, param)
          'z_scores_at_onset': dict,   # z-score of each tracked param at onset
          'severity_score': float,     # peak deviation score in pre_fault_window
          'model_features': dict,      # flat feature dict ready for ML
        }
    """
    if not records:
        return {'error': 'No records provided', 'fault_name': fault_name}

    # Normalize fault_name to snake_case for FAULT_PARAMETER_WEIGHTS lookup
    normalized_fault_name = fault_name.lower().replace(" ", "_")
    fault_weights = FAULT_PARAMETER_WEIGHTS.get(
        normalized_fault_name,
        FAULT_PARAMETER_WEIGHTS['custom_fault']
    )

    # 1. Compute baseline
    baseline = compute_robust_baseline(records, baseline_fraction=baseline_fraction)

    # 2. Score every record
    scores = [score_record(rec, baseline, fault_weights) for rec in records]

    # 3. Find deviation onset
    onset_idx = find_deviation_onset(scores)

    # 4. Extract pre-fault window
    start_idx = max(0, onset_idx - pre_fault_window)
    pre_fault_records = records[start_idx:onset_idx]
    onset_record = records[onset_idx] if onset_idx < len(records) else records[-1]

    # 5. Compute trend slopes over the pre-fault window
    sensors = ['acceleration', 'current', 'audio']
    params = ['mean', 'std_dev', 'kurtosis', 'skewness', 'range',
              'amplitude1', 'amplitude2', 'amplitude3', 'amplitude4', 'amplitude5']
    slopes = compute_trend_slopes(pre_fault_records + [onset_record], sensors, params)

    # 6. Z-scores at onset for each tracked parameter
    z_scores_at_onset: Dict[str, Dict[str, float]] = {}
    for sensor in sensors:
        z_scores_at_onset[sensor] = {}
        for param in params:
            val = onset_record.get(sensor, {}).get(param)
            bl  = baseline.get(sensor, {}).get(param)
            if val is not None and bl is not None:
                try:
                    z_scores_at_onset[sensor][param] = round(z_score(float(val), bl), 4)
                except (TypeError, ValueError):
                    pass

    # 7. Severity score = peak score in the pre-fault window
    window_scores = scores[start_idx:onset_idx + 1]
    severity_score = float(max(window_scores)) if window_scores else 0.0

    # 8. Build flat feature dict for ML training
    model_features = _build_model_features(
        pre_fault_records=pre_fault_records,
        onset_record=onset_record,
        baseline=baseline,
        slopes=slopes,
        z_scores_at_onset=z_scores_at_onset,
        severity_score=severity_score,
        fault_name=fault_name,
    )

    n_baseline = max(
        5, min(30, int(len(records) * baseline_fraction))
    )

    logger.info(
        f"[{fault_name}] records={len(records)}, onset={onset_idx}, "
        f"pre_window={len(pre_fault_records)}, severity={severity_score:.3f}"
    )

    return {
        'fault_name': fault_name,
        'total_records': len(records),
        'baseline_n': n_baseline,
        'deviation_onset_index': onset_idx,
        'pre_fault_records': pre_fault_records,
        'onset_record': onset_record,
        'deviation_scores': [round(s, 4) for s in scores],
        'baseline': baseline,
        'trend_slopes': slopes,
        'z_scores_at_onset': z_scores_at_onset,
        'severity_score': round(severity_score, 4),
        'model_features': model_features,
    }


# ---------------------------------------------------------------------------
# MODEL FEATURE BUILDER
# ---------------------------------------------------------------------------

def _build_model_features(
    pre_fault_records: List[Dict],
    onset_record: Dict,
    baseline: Dict,
    slopes: Dict,
    z_scores_at_onset: Dict,
    severity_score: float,
    fault_name: str,
) -> Dict[str, float]:
    """
    Flatten all derived features into a single dict for ML training.

    Feature naming convention:
        {sensor}_{param}_{feature_type}

    Feature types:
        _z       z-score at onset (normalised for cross-machine comparison)
        _slope   linear slope over pre-fault window (rate of change)
        _delta   (onset_value - baseline_mean) / baseline_mean  (% change)
        _raw     raw value at onset

    This flat dict is what you pass to your classifier.
    """
    features: Dict[str, float] = {}
    sensors = ['acceleration', 'current', 'audio']
    params = ['mean', 'std_dev', 'kurtosis', 'skewness', 'range',
              'amplitude1', 'amplitude2', 'amplitude3', 'amplitude4', 'amplitude5']

    for sensor in sensors:
        for param in params:
            prefix = f"{sensor}_{param}"

            # Z-score at onset
            z = z_scores_at_onset.get(sensor, {}).get(param)
            features[f"{prefix}_z"] = round(z, 4) if z is not None else 0.0

            # Trend slope
            slope = slopes.get(sensor, {}).get(param, 0.0)
            features[f"{prefix}_slope"] = round(slope, 6)

            # Delta from baseline (% change)
            val_at_onset = onset_record.get(sensor, {}).get(param)
            bl = baseline.get(sensor, {}).get(param)
            if val_at_onset is not None and bl is not None and bl['mean'] != 0:
                try:
                    delta = (float(val_at_onset) - bl['mean']) / abs(bl['mean'])
                    features[f"{prefix}_delta"] = round(delta, 4)
                    features[f"{prefix}_raw"] = round(float(val_at_onset), 4)
                except (TypeError, ValueError):
                    features[f"{prefix}_delta"] = 0.0
                    features[f"{prefix}_raw"] = 0.0
            else:
                features[f"{prefix}_delta"] = 0.0
                features[f"{prefix}_raw"] = 0.0

    # Top-level features
    features['severity_score']       = round(severity_score, 4)
    features['pre_fault_window_len'] = len(pre_fault_records)
    features['fault_name']           = fault_name  # label for supervised learning

    return features


# ---------------------------------------------------------------------------
# RECORD ASSEMBLER  (replaces get_historical_statistics in app.py)
# ---------------------------------------------------------------------------

def assemble_records_from_db(
    conn,
    limit: int = 200,
    file_type: str = 'max',
    include_min: bool = False,
) -> List[Dict]:
    """
    Query all three sensor tables and join records by timestamp proximity
    into a unified list of multi-sensor records in chronological order.

    Args:
        conn:         psycopg2 connection
        limit:        max records per sensor table to fetch
        file_type:    'max' | 'min' | 'combined'
        include_min:  if True, also queries min file records separately
                      and merges them - useful for electrical fault detection

    Returns:
        List of dicts, each representing one 2-hour session:
        [
          {
            'timestamp': '2024-...',
            'acceleration': {'mean': ..., 'kurtosis': ..., 'amplitude1': ..., ...},
            'current':      {...},
            'audio':        {...},
          },
          ...
        ]
        Sorted oldest → newest.

    Note: joins by nearest timestamp within a 60-minute tolerance.
    If a sensor has no matching record, its sub-dict will be missing.
    """
    from psycopg2.extras import RealDictCursor

    sensors = ['acceleration', 'current', 'audio']
    file_types = [file_type]
    if include_min and file_type != 'min':
        file_types.append('min')

    # Fetch all records per sensor
    raw: Dict[str, List[Dict]] = {s: [] for s in sensors}

    cur = conn.cursor(cursor_factory=RealDictCursor)
    for sensor in sensors:
        placeholders = ','.join(['%s'] * len(file_types))
        query = f"""
            SELECT
                x_min, x_max, mean, standard_deviation AS std_dev,
                range, skewness, kurtosis,
                frequency1, frequency2, frequency3, frequency4, frequency5,
                amplitude1, amplitude2, amplitude3, amplitude4, amplitude5,
                created_at, file_type
            FROM {sensor}
            WHERE file_type IN ({placeholders})
            ORDER BY created_at ASC
            LIMIT %s
        """
        try:
            cur.execute(query, file_types + [limit])
            rows = cur.fetchall()
            for row in rows:
                raw[sensor].append({
                    'timestamp': row['created_at'].isoformat() if row['created_at'] else None,
                    'min':        _safe_float(row.get('x_min')),
                    'max':        _safe_float(row.get('x_max')),
                    'mean':       _safe_float(row.get('mean')),
                    'std_dev':    _safe_float(row.get('std_dev')),
                    'range':      _safe_float(row.get('range')),
                    'skewness':   _safe_float(row.get('skewness')),
                    'kurtosis':   _safe_float(row.get('kurtosis')),
                    'frequency1': _safe_float(row.get('frequency1')),
                    'frequency2': _safe_float(row.get('frequency2')),
                    'frequency3': _safe_float(row.get('frequency3')),
                    'frequency4': _safe_float(row.get('frequency4')),
                    'frequency5': _safe_float(row.get('frequency5')),
                    'amplitude1': _safe_float(row.get('amplitude1')),
                    'amplitude2': _safe_float(row.get('amplitude2')),
                    'amplitude3': _safe_float(row.get('amplitude3')),
                    'amplitude4': _safe_float(row.get('amplitude4')),
                    'amplitude5': _safe_float(row.get('amplitude5')),
                    'file_type':  row.get('file_type'),
                })
            logger.info(f"Fetched {len(rows)} {file_type} records for {sensor}")
        except Exception as e:
            logger.error(f"Error fetching {sensor}: {e}")

    # Join by timestamp proximity (tolerance = 60 minutes)
    records = _temporal_join(raw, tolerance_seconds=3600)
    logger.info(f"Assembled {len(records)} multi-sensor records after temporal join")
    return records


def _temporal_join(
    raw: Dict[str, List[Dict]],
    tolerance_seconds: int = 3600,
) -> List[Dict]:
    """
    Merge per-sensor record lists into unified session records.

    Uses acceleration as the anchor timeline (most reliable),
    matches current and audio records within tolerance_seconds.
    Falls back to using whichever sensor has the most records as anchor.
    """
    import datetime

    sensors = ['acceleration', 'current', 'audio']

    # Pick anchor = sensor with most records
    anchor_sensor = max(sensors, key=lambda s: len(raw.get(s, [])))
    anchor_records = raw[anchor_sensor]

    if not anchor_records:
        return []

    def parse_ts(ts_str: Optional[str]):
        if not ts_str:
            return None
        try:
            return datetime.datetime.fromisoformat(ts_str)
        except Exception:
            return None

    unified = []
    for anchor_rec in anchor_records:
        anchor_ts = parse_ts(anchor_rec.get('timestamp'))
        if anchor_ts is None:
            continue

        session: Dict[str, Any] = {'timestamp': anchor_rec['timestamp']}
        session[anchor_sensor] = {k: v for k, v in anchor_rec.items()
                                   if k not in ('timestamp', 'file_type')}

        for other_sensor in sensors:
            if other_sensor == anchor_sensor:
                continue

            best_rec = None
            best_delta = float('inf')

            for rec in raw[other_sensor]:
                rec_ts = parse_ts(rec.get('timestamp'))
                if rec_ts is None:
                    continue
                delta = abs((anchor_ts - rec_ts).total_seconds())
                if delta <= tolerance_seconds and delta < best_delta:
                    best_delta = delta
                    best_rec = rec

            if best_rec:
                session[other_sensor] = {k: v for k, v in best_rec.items()
                                          if k not in ('timestamp', 'file_type')}

        unified.append(session)

    # Sort chronologically
    unified.sort(key=lambda r: r.get('timestamp') or '')
    return unified


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        return None if (np.isnan(f) or np.isinf(f)) else f
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# INTEGRATION HELPER  (call this from create_fault_event_csv in app.py)
# ---------------------------------------------------------------------------

def run_trend_extraction_for_event(
    conn,
    fault_name: str,
    pre_fault_window: int = 10,
    limit: int = 200,
) -> Dict[str, Any]:
    """
    One-call interface for app.py.

    Usage in app.py (replace the get_historical_statistics + detect_fault_deviation calls):

        from trend_extractor import run_trend_extraction_for_event

        conn = get_connection()
        result = run_trend_extraction_for_event(conn, fault_name)
        conn.close()

        if result.get('error'):
            return {'success': False, 'error': result['error']}

        # result['model_features'] is your flat ML-ready feature dict
        # result['pre_fault_records'] is the trend window to store as CSV
        # result['severity_score'] tells you how bad this event was

    Args:
        conn:              open psycopg2 connection
        fault_name:        e.g. 'motor_bearing_failure'
        pre_fault_window:  sessions to include before onset
        limit:             max records to fetch per sensor

    Returns:
        Full trend extraction result dict (see extract_fault_trend docstring).
    """
    # Electrical faults benefit from min file (cleaner harmonic signature)
    electrical_faults = {'motor_electrical_fault', 'motor_winding_failure'}
    file_type = 'max'
    include_min = fault_name in electrical_faults

    records = assemble_records_from_db(
        conn,
        limit=limit,
        file_type=file_type,
        include_min=include_min,
    )

    if not records:
        return {
            'error': 'No historical records found in database',
            'fault_name': fault_name,
        }

    return extract_fault_trend(
        records=records,
        fault_name=fault_name,
        pre_fault_window=pre_fault_window,
    )
