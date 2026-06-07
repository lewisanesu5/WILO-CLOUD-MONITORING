# Fault Generators System

## Overview

Comprehensive fault-specific data generation system for the WILO Cloud Monitoring predictive maintenance platform. Each generator simulates realistic sensor behavior for a specific motor/pump failure mode.

## Architecture

### Directory Structure

```
fault_generators/
├── __init__.py
├── base_generator.py              # Base class with common functionality
├── motor_stall_generator.py        # SUDDEN: Locked rotor (15 intervals)
├── pump_cavitation_generator.py    # SUDDEN: Bubble collapse (15 intervals)
├── pump_impeller_damage_generator.py # SUDDEN: Mechanical damage (15 intervals)
├── pump_seal_leakage_generator.py  # SUDDEN: Seal rupture (15 intervals)
├── motor_bearing_failure_generator.py # GRADUAL: Friction increase (15 intervals)
├── motor_shaft_misalignment_generator.py # GRADUAL: 2x frequency growth (15 intervals)
├── motor_overheating_generator.py   # GRADUAL: Thermal degradation (15 intervals)
├── motor_winding_failure_generator.py # GRADUAL: Insulation breakdown (15 intervals)
├── motor_vibration_anomaly_generator.py # GRADUAL: Chaotic vibrations (15 intervals)
├── motor_electrical_fault_generator.py # GRADUAL: Electrical spikes (15 intervals)
└── custom_event_generator.py        # CUSTOM: User-defined events
```

## Motor Specifications

**Havells Three Phase 270 HP Foot Mounted IE3 Squirrel Cage Induction Motor (MHPE355LB8)**
- Rated Power: 270 HP (~200 kW)
- Poles: 8 (50 Hz → ~730 RPM)
- Typical Rated Current: ~410 A (3-phase)
- Operating Baseline:
  - Acceleration: 0.3-0.5 m/s²
  - Current: 15-20 A (normal load)
  - Audio: 85-90 dB

## Sampling Configuration

- **Sampling Rate:** 700 Hz
- **Window Duration:** 2 seconds
- **Samples per Interval:** 1,400 points
- **Generation Interval:** 30 seconds (for rapid testing)
- **Files per Interval:** 6 CSV files
  - `max_acceleration.csv` / `min_acceleration.csv`
  - `max_current.csv` / `min_current.csv`
  - `max_audio.csv` / `min_audio.csv`

## Fault Categories

### SUDDEN FAULTS (4)

Trigger at a random interval (1-15) with an instant spike, then progress to system failure.

| Fault | Mode | Characteristics |
|-------|------|-----------------|
| **Motor Stall** | Locked Rotor | Current 40-100A, Accel 300%↑, Audio shriek |
| **Pump Cavitation** | Bubble Collapse | Irregular spikes, Popcorn-like audio |
| **Pump Impeller Damage** | Mechanical Imbalance | BPF spike (9 Hz), Grinding audio |
| **Pump Seal Leakage** | Seal Rupture | Pressure drop, Cavitation roar |

### GRADUAL FAULTS (6)

Linear progression over 15 intervals → CRITICAL → System failure.

| Fault | Mode | Progression |
|-------|------|-------------|
| **Motor Bearing Failure** | Friction Increase | Kurtosis + RMS: 0.5 → 2.0 m/s² |
| **Motor Shaft Misalignment** | 2x Frequency Growth | 2x amplitude: 0.3 → 1.8 m/s² |
| **Motor Overheating** | Thermal Degradation | Vibration: 0.6 → 2.2 m/s² |
| **Motor Winding Failure** | Insulation Breakdown | Arc probability: 0.1% → 5% |
| **Motor Vibration Anomaly** | Chaotic Motion | Broadband energy: 0.8 → 2.5 m/s² |
| **Motor Electrical Fault** | Phase Imbalance | Spike probability: 0.5% → 8.5% |

### CUSTOM

User-defined events for manual testing.

## Usage

### Run All Generators (Master Control)

```bash
python run_all_generators.py
```

Launches all 11 generators in parallel processes. Each runs indefinitely with 30-second intervals.

**Output:** Continuous logging to `fault_generators.log` and console.

### Run Single Generator (Testing)

```bash
python run_single_generator.py "Motor Stall"
```

**Available fault names:**
- Motor Stall
- Pump Cavitation
- Pump Impeller Damage
- Pump Seal Leakage
- Motor Bearing Failure
- Motor Shaft Misalignment
- Motor Overheating
- Motor Winding Failure
- Motor Vibration Anomaly
- Motor Electrical Fault
- Custom Event

### Run Individual Generator (Python)

```python
from fault_generators import MotorStallGenerator

generator = MotorStallGenerator()
generator.run_indefinitely()
```

## Data Flow

### 1. Generation (Every 30 seconds)

```
Generator → timestamps + values → 6 CSV files in Data/Fault_Name/
```

### 2. Statistics Calculation

```
app.py → load CSV → calculate_statistics() → store in database
```

### 3. Trend Analysis

```
Database → extract historical stats → plot on frontend
- Sudden: Horizontal line → Spike → System failure
- Gradual: Linear upward slope over 15 intervals → System failure
```

## Key Features

✅ **Realistic Motor/Pump Physics**
- Based on actual Havells MHPE355LB8 specifications
- Frequency components match mechanical properties
- Baseline noise ±5% per interval

✅ **Fault-Specific Signatures**
- Each fault has unique acceleration, current, and audio patterns
- Statistical features (kurtosis, RMS, peak) behave realistically

✅ **Linear Progression (Gradual)**
- Predictable degradation for testing trend detection
- 15 intervals to failure (easily adjustable)

✅ **Random Spike Trigger (Sudden)**
- Different spike interval each run (1-15)
- Transitions to system failure state post-spike
- Enables testing of sudden event detection

✅ **Multi-Process Execution**
- All 11 generators run in parallel
- Independent random seeds per fault
- Logging isolation per generator

## Configuration

Edit `fault_generators/base_generator.py`:

```python
FREQUENCY = 700  # Hz - sampling rate
DURATION = 2  # seconds - data window
GENERATION_INTERVAL = 30  # seconds - time between file generations
```

## Logging

**Main Log File:** `fault_generators.log`

**Log Levels:**
- INFO: Interval completion, spike triggers, system failures
- DEBUG: File creation details
- WARNING: Critical events (spikes, failures)
- ERROR: Critical errors

**Sample Output:**
```
2026-06-07 10:30:15 - [Generator-Motor Stall] - INFO - Initialized generator for: Motor Stall
2026-06-07 10:30:15 - [Generator-Motor Stall] - INFO - Spike will occur at interval: 7
2026-06-07 10:30:45 - [Generator-Motor Stall] - INFO - Interval 1: Generated 6 files | State: NORMAL
2026-06-07 10:31:15 - [Generator-Motor Stall] - INFO - Interval 2: Generated 6 files | State: NORMAL
...
2026-06-07 10:33:45 - [Generator-Motor Stall] - WARNING - ⚡ STALL SPIKE TRIGGERED at interval 7!
2026-06-07 10:34:15 - [Generator-Motor Stall] - INFO - Interval 8: Generated 6 files | State: SYSTEM_FAILURE
```

## Integration with Existing System

### Data Flow

```
Generators → Data/ directories (6 files per interval)
         ↓
      app.py (load_csv_data)
         ↓
  calculate_statistics()
         ↓
  save_statistics() → database
         ↓
Frontend API → get latest stats
         ↓
App.jsx → display trends + flag alerts
```

### Required Endpoints

- `/get-latest-files` - Returns most recent statistics
- `/get-file-stats` - Returns detailed stats for a specific file
- `/get-trends` - Returns historical statistics for trend plotting

## Testing Checklist

- [ ] Run all generators for 5 minutes, verify 6 files per interval
- [ ] Check sudden fault spike triggers between intervals 1-15
- [ ] Verify gradual faults show linear progression
- [ ] Check statistics values are physically realistic
- [ ] Verify system failure state is triggered post-failure
- [ ] Validate CSV file format (timestamp, value columns)
- [ ] Check log file for errors
- [ ] Verify frontend displays files correctly

## Troubleshooting

### No files being generated

1. Check data directory permissions: `ls -la Data/Motor\ Stall/`
2. Verify generator process is running: `ps aux | grep python`
3. Check for errors in `fault_generators.log`

### Generators crash immediately

1. Ensure NumPy and SciPy are installed: `pip install numpy scipy`
2. Check Python version: `python --version` (requires Python 3.7+)
3. Run single generator for detailed error: `python run_single_generator.py "Motor Stall"`

### CSV files corrupted

1. Check disk space: `df -h`
2. Verify file write permissions
3. Kill generator and manually delete corrupted files

## Performance Notes

- **Disk Usage:** ~1-2 MB per interval per fault = ~22-44 MB total per minute
- **CPU Usage:** Minimal (~1-2% per process)
- **Memory Usage:** ~50-100 MB per generator process

## Future Enhancements

- [ ] Add HTTP endpoint to trigger spikes manually
- [ ] Add configuration file for threshold tuning
- [ ] Add signal processing (FFT, wavelet analysis)
- [ ] Add multi-motor scenarios
- [ ] Add sensor failure modes (stuck sensor, sensor noise)

---

**System:** WILO Cloud Monitoring - Predictive Maintenance Platform  
**Motor:** Havells MHPE355LB8 (270 HP)  
**Sampling:** 700 Hz, 2-second windows, 30-second intervals
