# EventManager vs trend_extractor - Architecture Comparison

## Quick Answer

**Current System:** Uses `EventManager` (simple, uniform stability checks)  
**Alternative Available:** Uses `trend_extractor` (advanced, fault-specific weights)  
**Status:** EventManager is active; trend_extractor is available but not integrated

---

## Side-by-Side Comparison

### EventManager (Current - ACTIVE)
```python
# Location: event_manager.py
# Method: EventManager.create_event(fault_name, failure_time_iso, description)

# Stability Check:
for each data point:
    for sensor in [acceleration, current, audio]:
        for feature in [mean, max, min, std_dev, variance, skewness, kurtosis]:
            calculate_slope(value)
            if slope > 0.001:  ← Instability detected
                break
    if all_21_slopes_below_0.001:
        count_stable += 1
        if count_stable >= 3:
            extract_data_backward(100_points_max)
```

**Philosophy:** All parameters equally important
- Mean matters same as Kurtosis
- Acceleration matters same as Current
- Works universally for all fault types

### trend_extractor (Alternative - AVAILABLE)
```python
# Location: trend_extractor.py
# Method: run_trend_extraction_for_event(conn, fault_name)

# Stability Check:
WEIGHTS = {
    'motor_bearing_failure': {
        'acceleration_kurtosis': 1.0,      # MOST important
        'acceleration_skewness': 0.7,      # Important
        'acceleration_mean': 0.5,          # Somewhat important
        'audio_kurtosis': 0.7,             # Important
        'current_mean': 0.0,               # Not relevant
    },
    'motor_electrical_fault': {
        'current_skewness': 1.0,           # MOST important
        'current_kurtosis': 0.9,           # Important
        'acceleration_mean': 0.0,          # Not relevant
    }
}

deviation_score = sum(weight * z_score[param] for param, weight in WEIGHTS.items())
if deviation_score > threshold:
    extract_pre_fault_window()
```

**Philosophy:** Different faults have different signatures
- Bearing Failure: Watch Kurtosis and Skewness
- Electrical Fault: Watch Current Skewness
- Overheating: Watch Current Mean
- Each fault type has optimized parameter set

---

## Detailed Comparison Table

| Aspect | EventManager | trend_extractor |
|--------|--------------|-----------------|
| **Stability Detection** | Uniform threshold (0.001) | Fault-specific weighted scoring |
| **Parameters** | All 7 equally weighted | Fault-specific weights (0.0-1.0) |
| **Sensors** | All 3 checked uniformly | Fault-specific sensor importance |
| **Baseline Calculation** | First N points | Robust percentile window |
| **Z-Score Normalization** | Not used | Full Z-score normalization |
| **ML-Ready Output** | Basic (just extracted data) | Advanced (normalized features + severity score) |
| **File Handling** | MAX only | MAX + MIN (MIN for electrical faults) |
| **Integration** | ✓ Active in production | Available, not integrated |
| **Complexity** | Low | High |
| **Accuracy** | Good (general purpose) | Better (fault-specific) |
| **Development Status** | Stable, tested | Advanced/Ready |

---

## When to Use Each

### Use EventManager (Current)
✓ Fast deployment
✓ Works for all fault types
✓ Simple troubleshooting
✓ General anomaly detection
✓ Testing and validation

**Best for:** Quick MVP, general system health monitoring

### Use trend_extractor (Future)
✓ When accuracy matters more than speed
✓ Production ML pipeline
✓ Need fault severity scoring
✓ Different faults need different weights
✓ Training ML classifier on historical data

**Best for:** Advanced analytics, ML model training, precision maintenance

---

## Code Examples

### EventManager Usage (CURRENT)
```python
from event_manager import EventManager

event_manager = EventManager(events_dir, data_dir)

result = event_manager.create_event(
    event_name="Motor Bearing Failure",
    failure_time_iso="2026-06-13T14:30:00",
    description="Observed high vibration"
)

print(result)
# {
#   'success': True,
#   'event_id': 'evt_123',
#   'fault_id': 'f_456',
#   'total_rows_inserted': 42,
#   'rows_per_sensor': {
#       'acceleration': 42,
#       'current': 42,
#       'audio': 42
#   }
# }
```

### trend_extractor Usage (AVAILABLE)
```python
from trend_extractor import run_trend_extraction_for_event
from database import get_connection

conn = get_connection()
result = run_trend_extraction_for_event(
    conn=conn,
    fault_name='motor_bearing_failure',
    pre_fault_window=10,
    limit=200
)

if not result.get('error'):
    print(result)
    # {
    #   'severity_score': 8.7,  # 0-10 scale
    #   'pre_fault_records': [...],  # Trend window for CSV
    #   'model_features': {...},  # ML-ready features with Z-scores
    #   'deviation_point': 143,  # When fault started
    #   'baseline': {...}  # Computed baseline stats
    # }
else:
    print(f"Error: {result['error']}")

conn.close()
```

---

## Physical Fault Signatures (Why trend_extractor Weights Matter)

### Motor Bearing Failure
- **Primary signals:** High Kurtosis + Skewness (impacting/spalling)
- **Secondary:** Audio frequencies (raceway noise)
- **Irrelevant:** Current parameters
- **trend_extractor weights:** acceleration_kurtosis=1.0, audio_kurtosis=0.7

### Electrical Fault
- **Primary signals:** Skewed current (harmonic distortion)
- **Secondary:** Harmonic amplitudes
- **Irrelevant:** Vibration (motor still running)
- **trend_extractor weights:** current_skewness=1.0, current_amplitude2-3=0.8

### Motor Overheating
- **Primary signals:** Rising current mean (more resistance)
- **Secondary:** Current std_dev (increasing variations)
- **Irrelevant:** Vibration kurtosis (running normal)
- **trend_extractor weights:** current_mean=1.0, current_std_dev=0.7

### Motor Stall
- **Primary signals:** Current jumps up, vibration stops
- **Secondary:** Loss of rotational harmonics
- **trend_extractor weights:** current_mean=1.0, acceleration_mean=-1.0 (DOWN)

---

## Migration Path (If You Want to Upgrade)

**Phase 1 (Now):** Keep EventManager
- Working, tested, deployed
- Sufficient for initial monitoring

**Phase 2 (Later):** Run trend_extractor in parallel
- Compare results
- Validate severity scoring
- Tune fault-specific weights

**Phase 3 (Production):** Switch to trend_extractor (optional)
- Better accuracy
- ML model training
- Advanced analytics

---

## Recommendation

**Current Status:** ✓ EventManager is the right choice
- Simpler logic = easier to debug
- All 3 sensors checked uniformly
- Sufficient fault detection
- Deployment-ready

**Keep trend_extractor available** for:
- Future enhancement
- ML pipeline when needed
- Reference for advanced features
- Potential hybrid approach

**No change needed for Render deployment** - ship with EventManager as-is!
