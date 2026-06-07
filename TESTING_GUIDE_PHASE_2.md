# PHASE 2 & 3 TESTING GUIDE - Fault Event Monitoring System

## Overview
Phase 2 (Backend Polling) is fully implemented and Phase 3 (UI Polish) is in progress.

**Status**: ✅ BACKEND COMPLETE | ✅ FRONTEND POLLING COMPLETE | 🟡 UI POLISH COMPLETE

## Components Implemented

### Backend (Phase 1)
- ✅ 11 Fault Generators running in parallel
- ✅ Statistics calculation per interval
- ✅ JSON export to `Events/<Fault>/stats.json`
- ✅ System failure detection and auto-stop
- ✅ 3 REST API endpoints:
  - `GET /api/fault-state/<fault_name>` - Current state
  - `GET /api/fault-trend/<fault_name>` - Historical trend
  - `GET /api/fault-current/<fault_name>` - Current interval data

### Frontend (Phase 2 + 3)
- ✅ Fault Event Selector dropdown (LEFT SIDEBAR)
- ✅ 30-second polling loop when fault selected
- ✅ Real-time status display (MONITORING/STOPPED)
- ✅ Interval counter updates
- ✅ Failure detection alerts
- ✅ Automatic stop on failure

## Quick Start Testing

### 1. Start All Services

```bash
# Terminal 1: Start generators (MUST BE RUNNING)
python run_all_generators.py

# Terminal 2: Start Flask backend  
python app.py

# Terminal 3: Start React frontend (from frontend/ directory)
npm run dev
```

Wait 30 seconds for all services to be online.

### 2. Test the System

1. **Open Frontend**: http://localhost:5174
2. **Locate**: LEFT SIDEBAR → "Fault Event Monitor" card
3. **Click**: Select a fault (e.g., "Motor Stall")
4. **Observe**:
   - Dropdown shows selected fault
   - Status badge appears: "🟢 MONITORING ACTIVE"
   - Interval counter begins counting (0, 1, 2, 3...)
   - Every 30 seconds graphs update with new data

### 3. Wait for Failure

**SUDDEN Faults** (Motor Stall, Pump Cavitation, etc.):
- Failure triggers randomly at interval 1-15
- Watch for sudden spike in acceleration RMS
- Status changes to "🔥 FAILURE DETECTED at interval N"

**GRADUAL Faults** (Motor Bearing, Shaft Misalignment, etc.):
- Linear progression over 15 intervals
- Progressive increase in acceleration RMS/kurtosis
- Failure at interval 15 or when reaching critical threshold

### 4. Expected Behavior

```
Timeline:
0s  - User selects fault
30s - First poll, interval 0 data fetched
60s - Second poll, interval 1 data
90s - Third poll, interval 2 data
...
450s - Intervals 14-15 range (failure window)
~480-510s - Failure detected!
    - Status: "🔥 FAILURE DETECTED"
    - Polling stops automatically
    - Graph frozen at failure point
```

## Testing Checklist

### Basic Functionality
- [ ] Dropdown shows all 11 faults
- [ ] Can select a fault
- [ ] Status badge appears immediately
- [ ] Interval counter visible
- [ ] Message shows "Starting monitoring..."

### Polling & Updates
- [ ] Browser console shows API calls every 30s (set log level in browser DevTools)
- [ ] Trend graph updates (new points appear)
- [ ] Time series graph updates (new raw data)
- [ ] Interval counter increments every 30s
- [ ] Status message updates: "Monitoring - Interval N"

### Failure Detection
- [ ] After ~5-10 minutes, failure message appears
- [ ] Status shows "🔥 FAILURE DETECTED at interval N"
- [ ] Failure badge appears with red styling
- [ ] Polling stops (no more API calls in console)
- [ ] Graphs freeze (no updates after failure)

### Deselection & Restart
- [ ] Click dropdown → "-- No Monitoring --" → stops polling
- [ ] All badges disappear
- [ ] Can select same fault again → restarts from 0
- [ ] Can select different fault → monitors new one

## API Testing (Manual)

### Test fault-state endpoint
```bash
curl http://localhost:5001/api/fault-state/Motor%20Stall

# Expected response:
{
  "fault_name": "Motor Stall",
  "interval_count": 5,
  "system_failure_state": false,
  "failure_interval": null,
  "is_generating": true,
  "current_stats": {...},
  "start_time": "2024-...",
  "current_time": "2024-..."
}
```

### Test fault-trend endpoint
```bash
curl http://localhost:5001/api/fault-trend/Motor%20Stall

# Expected response:
{
  "fault_name": "Motor Stall",
  "intervals": [
    {"interval": 0, "timestamp": "...", "accel_rms": 0.5, ...},
    {"interval": 1, "timestamp": "...", "accel_rms": 0.6, ...},
    ...
  ]
}
```

### Test fault-current endpoint
```bash
curl "http://localhost:5001/api/fault-current/Motor%20Stall?sensor=acceleration"

# Expected response:
{
  "fault_name": "Motor Stall",
  "sensor_type": "acceleration",
  "timestamps": [1.0, 1.01, 1.02, ...],
  "values": [0.1, 0.15, 0.08, ...],
  "data_points": 1400
}
```

## File Structure Reference

```
Events/
├── Motor Stall/
│   ├── metadata.json          # Fault info
│   ├── stats.json             # Per-interval statistics
│   ├── interval_0.csv         # 1400 acceleration samples
│   ├── interval_1.csv
│   └── ...
├── Motor Bearing Failure/
│   ├── metadata.json
│   ├── stats.json
│   └── ...
└── ...11 faults total...
```

## Troubleshooting

### Polls not happening?
1. Check browser console (F12)
2. Look for API errors (5xx codes)
3. Verify backend is running: `curl http://localhost:5001/api/fault-state/Motor%20Stall`
4. Check that `Events/<Fault>/stats.json` exists and is updating

### No data in graphs?
1. Make sure generators are running
2. Verify `Events/<Fault>/stats.json` has data
3. Check that trends have ≥2 data points
4. Try refreshing page and selecting fault again

### Failure not detecting?
1. Wait longer (could be gradual fault taking 15 intervals)
2. Try a SUDDEN fault (Motor Stall) which fails quickly
3. Check that `stats.json` has `system_failure_state: true`
4. Verify failure interval matches displayed value

### Graphs not updating?
1. Check if `faultTrendData` and `faultCurrentData` state is being set
2. Open browser DevTools → Console → verify no errors
3. Manually check API response: `curl http://localhost:5001/api/fault-trend/Motor%20Stall`

## Performance Notes

- **Polling Interval**: 30 seconds (matches generator output interval)
- **File Generation**: 1400 data points per interval (700 Hz × 2 seconds)
- **Graph Redraw**: Every 30 seconds when new data arrives
- **Memory**: Minimal (polling 3 endpoints per cycle)

## Next Steps

1. **Test All 11 Faults**:
   - Motor Bearing Failure (GRADUAL)
   - Motor Overheating (GRADUAL)
   - Motor Winding Failure (GRADUAL)
   - Motor Shaft Misalignment (GRADUAL)
   - Motor Vibration Anomaly (GRADUAL)
   - Motor Stall (SUDDEN) ✅
   - Motor Electrical Fault (GRADUAL)
   - Pump Seal Leakage (GRADUAL)
   - Pump Cavitation (SUDDEN) ✅
   - Pump Impeller Damage (SUDDEN) ✅
   - Custom Event Generator (VARIES)

2. **Verify Graph Data**:
   - Trend graph shows progression from interval 0→N
   - Time series shows raw waveform updates
   - Statistics reflect increasing/spiking values

3. **End-to-End Flow**:
   - Start fresh dashboard
   - Select fault
   - Monitor progression
   - Observe failure detection
   - Verify stop and restart works
