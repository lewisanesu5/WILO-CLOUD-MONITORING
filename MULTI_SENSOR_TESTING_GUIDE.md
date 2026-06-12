# Quick Start: Testing Multi-Sensor Implementation

## Prerequisites Checklist

- [ ] Database populated with aggregated data (acceleration, current, audio tables)
- [ ] Data from last 24 hours available in database
- [ ] Flask backend running: `python app.py` (runs on localhost:5001)
- [ ] Database connection confirmed (check `config.json` for DATABASE_URL)

## What's New: All Features Used for Stability Detection

The multi-sensor extraction now queries database tables and uses **ALL 7 statistical features + FFT data**:
- Statistical: mean, max, min, std_dev, variance, skewness, kurtosis
- FFT: frequency1-5, amplitude1-5

This means **21 slopes** are checked per data point (7 features × 3 sensors), making fault detection more robust and comprehensive.

## Step 1: Generate Sample Data

Run one of the fault generators to create max_acceleration*.csv, max_current*.csv, max_audio*.csv:

```bash
# Option A: Run all 11 faults in sequence
python run_sequence_generator.py
# Select: Mode 1 (Single Cycle)

# Option B: Run single fault for testing
python run_single_generator.py
# Select: Motor Stall (or any fault)

# Wait for generator to complete (should see "system_failure_state=true")
```

**What this creates:**
- Data/max_acceleration*.csv (multiple files)
- Data/max_current*.csv
- Data/max_audio*.csv
- Each file contains: timestamp, mean, max, min, std_dev, variance, skewness, kurtosis

## Step 2: Test Multi-Sensor Extraction Locally

```python
# Run in Python terminal
from event_manager import EventManager
import datetime

# Initialize
em = EventManager('Events', 'Data')

# Load all sensor data
sensor_data = em._load_all_sensor_data()

# Check what was loaded
for sensor, data in sensor_data.items():
    print(f"{sensor}: {len(data)} points")

# Get last timestamp (approximate failure time)
if sensor_data['acceleration']:
    last_point = sensor_data['acceleration'][-1]
    failure_time_ms = last_point['timestamp']
    failure_dt = datetime.datetime.fromtimestamp(failure_time_ms / 1000)
    print(f"Failure time: {failure_dt.isoformat()}")

# Extract multi-sensor trends
trends = em._extract_multi_sensor_trends(sensor_data)

# Show results
for sensor, trend_points in trends.items():
    print(f"\n{sensor}: {len(trend_points)} points extracted")
    if trend_points:
        first = trend_points[0]
        last = trend_point[-1]
        print(f"  Time range: {first['time_delta']}s to {last['time_delta']}s")
        print(f"  Mean range: {first['mean']} to {last['mean']}")
```

**Expected output:**
```
acceleration: 15 points
current: 15 points
audio: 15 points

acceleration: 15 points extracted
  Time range: -120.5s to 0.0s
  Mean range: 2.1 to 9.8

current: 15 points extracted
  Time range: -120.5s to 0.0s
  Mean range: 1.5 to 8.3

audio: 15 points extracted
  Time range: -120.5s to 0.0s
  Mean range: 1.2 to 7.9
```

## Step 3: Test Event Creation Endpoint

```bash
# Create an event via REST API
curl -X POST http://localhost:5001/create-event \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "Motor Stall",
    "failure_time_iso": "2025-11-27T14:30:00",
    "description": "Test multi-sensor extraction"
  }'
```

**Expected response:**
```json
{
  "success": true,
  "event_id": "Motor_Stall_20251127_143000",
  "fault_id": 42,
  "total_rows_inserted": 156,
  "rows_per_sensor": {
    "acceleration": 52,
    "current": 52,
    "audio": 52
  },
  "metadata": {
    "event_name": "Motor Stall",
    "failure_time_iso": "2025-11-27T14:30:00",
    "total_data_points_all_sensors": 156,
    "fault_id_in_database": 42,
    ...
  }
}
```

## Step 4: Verify Database Insertion

```sql
-- Connect to Neon database

-- Check motor_stall table
SELECT sensor_type, COUNT(*) as rows, MIN(timestamp) as first, MAX(timestamp) as last
FROM motor_stall
WHERE fault_id = 42
GROUP BY sensor_type;

-- Expected output (3 rows):
-- acceleration  | 52  | 2025-11-27 14:28:00 | 2025-11-27 14:30:00
-- current       | 52  | 2025-11-27 14:28:00 | 2025-11-27 14:30:00
-- audio         | 52  | 2025-11-27 14:28:00 | 2025-11-27 14:30:00

-- Check sample data values
SELECT fault_id, sensor_type, timestamp, mean, max, std_dev, kurtosis
FROM motor_stall
WHERE fault_id = 42
ORDER BY sensor_type, timestamp
LIMIT 15;
```

## Step 5: Verify Dashboard

1. Open http://localhost:3000 (React frontend)
2. Navigate to event section
3. Look for recent event (should show 3 sensors)
4. Verify three separate trend lines for acceleration, current, audio
5. Confirm all three sensors have ~52 data points

## Troubleshooting

### Problem: "No acceleration data available"
**Cause:** max_acceleration*.csv files not found in Data/
**Fix:**
```bash
# Check files exist
ls Data/max_*.csv

# If missing, run generator:
python run_single_generator.py
```

### Problem: Only 1-4 points extracted instead of 13+
**Cause:** All points look stable (noise in data)
**Fix:** 
- Check if fault generators ran long enough (should be 15+ intervals)
- Verify max_*.csv files have enough data
- May need to adjust NEGLIGIBLE_SLOPE_THRESHOLD in _extract_multi_sensor_trends()

### Problem: Database insertion failed
**Cause:** Neon connection issue or schema missing
**Fix:**
```bash
# Verify connection
python -c "from database import get_connection; conn = get_connection(); print('Connected!')"

# Recreate schema
python init_event_tables.py
```

### Problem: Different point counts per sensor
**Cause:** Sensor files have misaligned timestamps
**Fix:**
- Ensure all sensors have same time resolution
- Check that max_acceleration*.csv, max_current*.csv, max_audio*.csv all run in parallel
- May need to interpolate missing timestamps

## Success Criteria

✅ Multi-sensor extraction working:
- [ ] All three sensors have data
- [ ] Extraction returns 13+ points per sensor
- [ ] Points have aggregated features (mean, max, std_dev, kurtosis)

✅ Database integration working:
- [ ] Event creation endpoint returns 201
- [ ] Database has rows for all three sensors
- [ ] All rows have same fault_id
- [ ] sensor_type column populated correctly

✅ Dashboard integration working:
- [ ] Recent events show three sensors
- [ ] Each sensor shows correct number of points
- [ ] Trend lines visible for all sensors
- [ ] Statistics accurate

## Next Steps

1. Once testing complete, commit changes:
   ```bash
   git add -A
   git commit -m "Implement multi-sensor trend extraction for acceleration, current, audio"
   git push
   ```

2. Deploy to Render:
   - Changes auto-detected
   - Monitor logs for errors

3. Validate in production:
   - Test /create-event endpoint
   - Check Neon database
   - Verify dashboard displays multi-sensor data

## Important Notes

- **Breaking Change**: insert_event_data() signature changed
  - Old: `insert_event_data(failure_type, slope_data, event_statistics, sensor_type)`
  - New: `insert_event_data(failure_type, multi_sensor_trends)`
  - Only used by event_manager.py's create_event() method
  
- **Data Format**: All three sensors MUST have aligned timestamps
  - Fault generators must run in parallel
  - CSV files updated simultaneously
  
- **Stability Threshold**: Fixed at 0.001 per second
  - May need adjustment based on real-world noise
  - Consider feature-specific thresholds in future
  
- **Backward Compatibility**: Database schema already supports multi-sensor
  - No schema changes needed
  - Can coexist with old single-sensor data
