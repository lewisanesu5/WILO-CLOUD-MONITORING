# Diagnosis: Data Not Getting Plotted

## Root Cause

**The charts expect `raw_values` and `raw_timestamps` but they are empty.**

---

## Data Flow Issue

### Before (Old System - Files Persisted)
```
Remote Client uploads CSV files
    ↓
Server saves files to: /Data/max_acceleration.csv, etc.
    ↓
Frontend requests: GET /api/sensor-data?mode=max
    ↓
Backend loads CSV files from disk
    ↓
Returns: {
  acceleration: {
    max: {
      stats: {...},              ✓ Has this
      raw_values: [...],         ✓ Has this (from CSV file)
      raw_timestamps: [...]      ✓ Has this (from CSV file)
    }
  }
}
    ↓
Frontend TimeSeriesChart receives raw_values + raw_timestamps
    ↓
Charts render successfully ✓
```

### After (New System - In-Memory Processing on Render)
```
Remote Client uploads CSV files
    ↓
Server processes IN-MEMORY → Calculates statistics
    ↓
Saves to Neon Database: statistics only (mean, max, std_dev, frequency, amplitude)
    ✗ CSV files NOT saved to disk (ephemeral filesystem)
    ↓
Frontend requests: GET /api/sensor-data?mode=max
    ↓
Backend tries to load CSV files from disk using load_csv_data()
    ↓
Files don't exist → Returns empty arrays
    ↓
Returns: {
  acceleration: {
    max: {
      stats: {...},              ✓ Has this
      raw_values: [],            ✗ EMPTY (files not on disk)
      raw_timestamps: []         ✗ EMPTY (files not on disk)
    }
  }
}
    ↓
Frontend TimeSeriesChart checks: if (rawValues.length === 0)
    ↓
Shows: "No raw sensor data available" ✗
```

---

## Technical Details

### 1. Upload Endpoint Changed (`/api/upload`)
**File:** `app.py` lines 1240-1400

```python
def process_uploaded_csv_and_save_to_db(uploaded_files):
    # Processes CSV IN-MEMORY
    # Calculates statistics
    # Saves to database
    # Does NOT save CSV files to disk
```

**Why:** Render free tier has ephemeral filesystem (files lost on dyno restart)

---

### 2. Statistics Tables Structure
**Tables:** `acceleration`, `current`, `audio`

**Columns Stored:**
- ✓ x_min, x_max (aggregated)
- ✓ mean, std_dev, skewness, kurtosis (aggregated)
- ✓ frequency1-5, amplitude1-5 (FFT)
- ✓ file_type (max/min/combined)
- ✗ **NO raw sensor readings** (individual data points)

**Example Row:**
```json
{
  "x_min": 9.5,
  "x_max": 11.2,
  "mean": 10.31,
  "std_dev": 0.42,
  "file_type": "max",
  "created_at": "2026-06-10 18:48:32"
}
```

This is ONE summary row representing ~1400 raw sensor readings.
The original ~1400 individual readings are NOT stored.

---

### 3. Frontend TimeSeriesChart Component
**File:** `frontend/src/App.jsx` lines 108-200

```javascript
function TimeSeriesChart({ sensor, sensorData }) {
  const rawValues = sensorData?.raw_values || [];      // Expects array of readings
  const rawTimestamps = sensorData?.raw_timestamps || [];  // Expects timestamps
  
  if (rawValues.length === 0) {
    return <p>No raw sensor data available</p>  // ← Shows this now
  }
}
```

---

### 4. API Endpoint Trying to Load CSV Files
**File:** `app.py` lines 778-890 (`get_sensor_data_with_raw_data`)

```python
def get_sensor_data_with_raw_data(mode='max'):
    for sensor in SENSORS:
        # This tries to load from disk:
        max_timestamps, max_values, max_file_ts = load_csv_data(f"max_{sensor}.csv")
        min_timestamps, min_values, min_file_ts = load_csv_data(f"min_{sensor}.csv")
        
        # On Render:
        # - load_csv_data() checks: os.path.exists(filepath)
        # - filepath = /data/events/Data/max_acceleration.csv
        # - File doesn't exist (never saved in new upload flow)
        # - Returns: [], [], None  (empty arrays)
```

---

## Why This Happened

The system was redesigned to solve the **Render ephemeral filesystem problem**:

**Old Problem:**
- Remote client uploads CSV → Saved to `/data/events/Data/`
- Error: "No such file or directory: '/data/events/Data/max_acceleration.csv'"
- On Render restart → Files disappear → Data lost

**Solution Implemented:**
- Process CSV in-memory
- Save statistics to Neon database (persistent)
- Skip file save step
- **Unintended consequence:** TimeSeriesChart now has no raw data source

---

## Data Flow Comparison

| Aspect | Old | New |
|--------|-----|-----|
| CSV upload | Saved to disk | Processed in-memory |
| Storage | Ephemeral filesystem | Neon database |
| Data saved | Full CSV + statistics | Statistics only |
| Raw readings stored | ✓ Yes (CSV files) | ✗ No (only aggregates) |
| Plotting capability | ✓ Charts render | ✗ No data for charts |

---

## Summary for User

**What's Missing:**
The statistics tables store only aggregated data (mean, max, min, frequency, amplitude), not the individual sensor readings needed for time-series charts.

**Why It Happened:**
1. Moved from file-based storage to database-based storage to solve Render's ephemeral filesystem issue
2. Upload endpoint now processes CSV data in-memory instead of saving to disk
3. Frontend still expects `raw_values` and `raw_timestamps` from old system
4. Those arrays are now empty because the CSV files were never saved

**Impact:**
- ✓ Event creation works (statistics saved to database)
- ✓ MAX row filtering works
- ✗ Time-series charts show "No raw sensor data available"
- ✗ Statistical parameter charts likely work (they use aggregate stats)

---

## What Would Be Needed to Fix

### Option 1: Store Raw Sensor Data in Database
- Add `raw_values` ARRAY column to statistics tables
- Store individual sensor readings (1400 per stat row)
- Pros: Persistent, retrieves raw data easily
- Cons: Database grows large (~1400 rows per stat row)

### Option 2: Save CSV Files to Persistent Location
- Use Render's persistent disk (if upgraded from free plan)
- Keep file-based storage approach
- Pros: Minimal database changes
- Cons: Requires paid Render plan

### Option 3: Modify Frontend Charts
- Remove time-series charts (raw_values dependent)
- Show only statistical parameter charts (use aggregate stats)
- Pros: No backend changes needed
- Cons: Less visual data

---

**Status:** Issue identified. Changes made for database persistence inadvertently removed raw data source for charts.
