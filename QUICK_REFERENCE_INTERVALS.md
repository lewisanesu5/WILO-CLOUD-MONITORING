# ⚡ Quick Reference - Sequential Fault Monitoring

## 🎯 The Problem (What Was Wrong)

```
OLD BEHAVIOR:
┌─────────────────────────────────────┐
│ Fault 1 starts                      │
│ Interval: 1, 2, 3, ... 12 (FAILURE) │
│ Data saved to Data/Fault1/          │
│ Frontend shows: Plot 1-12           │
└─────────────────────────────────────┘
        ↓ (Manually switch to Fault 2)
┌─────────────────────────────────────┐
│ Fault 2 starts                      │
│ Interval: 1, 2, 3, ... (but...)     │  ← ISSUE: Old data mixed in
│ Data saved to Data/Fault2/          │
│ Frontend shows: Plot 1-12 + Fault2  │  ← ISSUE: Not reset properly
└─────────────────────────────────────┘
```

## ✅ The Solution (What's Fixed)

```
NEW BEHAVIOR:
┌─────────────────────────────────────────────────────────────┐
│ FAULT 1 (Motor Stall)                                       │
│ ✓ Clear old data: Data/Motor Stall/ × Events/Motor Stall/ ✓│
│ ✓ Initialize fresh: interval_count = 0                     │
│ ✓ Generate: Intervals 1-15                                 │
│ ✓ Detect: Failure at interval 7                            │
│ ✓ Status: [███████░░░░░░░░░] 7/15 🔥 FAILURE               │
└─────────────────────────────────────────────────────────────┘
        ↓ (5-second pause + clean transition)
┌─────────────────────────────────────────────────────────────┐
│ FAULT 2 (Pump Cavitation)                                   │
│ ✓ Clear old data: Data/Pump Cavitation/ × Events/... ✓      │
│ ✓ Initialize fresh: interval_count = 0  ← RESET!           │
│ ✓ Generate: Intervals 1-15  ← STARTS FROM 1!               │
│ ✓ Detect: Failure at interval 11                           │
│ ✓ Status: [███████████░░░░░░] 11/15 🔥 FAILURE              │
│ ✓ Frontend plot: 1-15 range (CLEAN! No old data)           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 How to Run

### **Option 1: Run All 11 Faults Sequentially (RECOMMENDED)** ✨
```bash
python run_sequence_generator.py

# Choose: 1 (Single Cycle)
# Output: All 11 faults run one-by-one with interval reset

⏱️  Takes ~6-7 minutes (30 sec × 11 faults + pauses)
```

### **Option 2: Run Multiple Cycles**
```bash
python run_sequence_generator.py

# Choose: 2 (Continuous Cycles)
# Enter: 3 (runs 3 times through all 11 faults)

⏱️  Takes ~20-21 minutes (3 cycles)
```

### **Option 3: Debug Single Fault**
```bash
python run_sequence_generator.py

# Choose: 3 (Single Fault)
# Select: 1 (Motor Stall)

# Runs ONLY that fault with proper data reset
```

### **Option 4: Original Parallel Mode**
```bash
python run_all_generators.py
# All 11 faults run simultaneously (NOT recommended for plotting intervals 1-15)
```

---

## 📊 What You'll See in Logs

```
2024-01-15 10:23:45 - [Generator-Motor Stall] - INFO - 📊 Plot Interval Range: 1-15
2024-01-15 10:23:45 - [Generator-Motor Stall] - INFO - ⚠️  Fault Detection Range: 5-15
2024-01-15 10:23:45 - [Generator-Motor Stall] - INFO - ⏱️  Interval Duration: ~30 seconds

2024-01-15 10:24:15 - [Generator-Motor Stall] - INFO - [█░░░░░░░░░░░░░░░] Interval 1/15 | ✓ NORMAL
2024-01-15 10:24:45 - [Generator-Motor Stall] - INFO - [██░░░░░░░░░░░░░░] Interval 2/15 | ✓ NORMAL
2024-01-15 10:25:15 - [Generator-Motor Stall] - INFO - [███░░░░░░░░░░░░░] Interval 3/15 | ✓ NORMAL
2024-01-15 10:25:45 - [Generator-Motor Stall] - INFO - [████░░░░░░░░░░░░] Interval 4/15 | ✓ NORMAL
2024-01-15 10:26:15 - [Generator-Motor Stall] - INFO - [█████░░░░░░░░░░░] Interval 5/15 | ✓ NORMAL
2024-01-15 10:26:45 - [Generator-Motor Stall] - INFO - [██████░░░░░░░░░░] Interval 6/15 | ✓ NORMAL
2024-01-15 10:27:15 - [Generator-Motor Stall] - INFO - [███████░░░░░░░░░] Interval 7/15 | 🔥 FAILURE  ← TRIGGERED!

✓ Fault 'Motor Stall' completed at interval 7

⏳ Waiting 5 seconds before next fault...

✓ Cleared all data for 'Pump Cavitation' - starting fresh

[Generator-Pump Cavitation] - INFO - 📊 Plot Interval Range: 1-15
[Generator-Pump Cavitation] - INFO - ⏱️  Interval Duration: ~30 seconds

2024-01-15 10:27:45 - [Generator-Pump Cavitation] - INFO - [█░░░░░░░░░░░░░░░] Interval 1/15 | ✓ NORMAL  ← RESETS!
2024-01-15 10:28:15 - [Generator-Pump Cavitation] - INFO - [██░░░░░░░░░░░░░░] Interval 2/15 | ✓ NORMAL
...
```

**✓ Notice:** Pump Cavitation starts at Interval 1/15 (NOT continues from 7!)

---

## 🧪 Testing Steps

```
STEP 1: Start Backend
$ python app.py
→ Check: Flask running on http://localhost:5001

STEP 2: Start Frontend (new terminal)
$ cd frontend && npm run dev
→ Check: Frontend running on http://localhost:5173

STEP 3: Start Sequential Generator (new terminal)
$ python run_sequence_generator.py
→ Select: Mode 1 (Single Cycle)
→ Check: Logs show progress bars and interval counts

STEP 4: Watch Frontend
→ Open http://localhost:5173
→ Select "Motor Stall" from dropdown
→ Observe:
   ✓ Interval counter: 1, 2, 3, ..., 7 then stops
   ✓ Plot shows 1-7 range
   ✓ Select "Pump Cavitation"
   ✓ Interval counter resets to 1 ← THIS IS THE FIX!
   ✓ Plot resets to 1-15 range

STEP 5: Verify All 11
→ Continue through all 11 faults
→ Verify each starts at 1, detects at random 5-15
```

---

## 📁 File Structure After Run

```
Data/
  Motor Stall/
    ├─ max_acceleration.csv
    ├─ min_acceleration.csv
    ├─ max_current.csv
    ├─ min_current.csv
    ├─ max_audio.csv
    └─ min_audio.csv
  
  Pump Cavitation/
    ├─ max_acceleration.csv
    ├─ min_acceleration.csv
    ... (same 6 files, but for Pump Cavitation)
  
  Motor Bearing Failure/
    ... (and so on for all 11 faults)

Events/
  Motor Stall/
    ├─ stats.json (contains 7 interval records)
    └─ metadata.json
  
  Pump Cavitation/
    ├─ stats.json (contains 11 interval records)
    └─ metadata.json
  
  ... (all 11 faults have their own directory)
```

**Key Point:** Each fault's folder contains ONLY its own data (1-15 intervals), no carryover!

---

## 🔍 Understanding the Output

### **Progress Bar Meaning**
```
[█░░░░░░░░░░░░░░░] = 1/15 filled
[██░░░░░░░░░░░░░░] = 2/15 filled
[███░░░░░░░░░░░░░] = 3/15 filled
...
[███████░░░░░░░░░] = 7/15 filled
[██████████████░░░] = 14/15 filled
[███████████████░░] = 15/15 filled
```

### **State Meaning**
```
| ✓ NORMAL  = No fault yet, generating baseline data
| 🔥 FAILURE = System failure detected, monitoring stops
```

### **Example Log Line**
```
[███████░░░░░░░░░] Interval 7/15 | 🔥 FAILURE
└─ Progress bar     └─ Interval number  └─ Current state
```

---

## 💾 Generated Files Explained

### **stats.json** (Most Important)
```json
{
  "fault_name": "Motor Stall",
  "start_time": "2024-01-15T10:23:45.123456",
  "interval_count": 7,
  "failure_interval": 7,
  "intervals": [
    {
      "interval": 1,
      "acceleration": {"mean": 0.52, "std_dev": 0.03, ...},
      "current": {"mean": 18.1, "std_dev": 0.9, ...},
      "audio": {"mean": 88.2, "std_dev": 4.1, ...}
    },
    ...
    {
      "interval": 7,
      "acceleration": {"mean": 3.8, "std_dev": 2.1, ...},  ← HIGH (failure)
      "current": {"mean": 87.3, "std_dev": 5.2, ...},      ← HIGH (failure)
      "audio": {"mean": 102.5, "std_dev": 8.3, ...}        ← HIGH (failure)
    }
  ]
}
```

### **CSV Files** (min/max acceleration, current, audio)
```
timestamp,value
0.0,0.51234
1.428571,0.52145
2.857143,0.48956
...
2857.142857,0.51423
```

---

## ⚙️ Configuration

### **To Change Inter-Fault Delay** (currently 5 seconds)
Edit `run_sequence_generator.py`:
```python
INTER_FAULT_DELAY = 5  # Change to 2 for faster, 10 for slower

# Recommended: Keep at 5 seconds (ensures clean transition)
```

### **To Change Interval Range** (currently 1-15)
Edit `run_sequence_generator.py`:
```python
INTERVAL_RANGE = (1, 15)  # Change to (1, 20) for 20 intervals per fault

# Note: Generator logic may also need updates
```

### **To Change Generation Interval** (currently 30 seconds per interval)
Edit `fault_generators/base_generator.py`:
```python
GENERATION_INTERVAL = 30  # Change to 10 for faster testing, 60 for slower

# Note: Each interval takes ~30 seconds regardless; this controls file generation
```

---

## 📞 Troubleshooting

| Problem | Solution |
|---------|----------|
| Intervals not starting at 1 | Make sure using `run_sequence_generator.py`, not `run_all_generators.py` |
| Old data still visible | Delete `Data/` and `Events/` folders, restart generator |
| Frontend not showing updates | Check http://localhost:5001 endpoints return fresh data |
| Fault doesn't trigger by 15 | Normal! Trigger interval is random 5-15; could be 15 |
| Logs not showing progress bars | Make sure terminal supports UTF-8 (most modern ones do) |
| Faults running in parallel | You're using `run_all_generators.py`; use `run_sequence_generator.py` instead |

---

## 📚 More Documentation

For comprehensive guides, see:
- **SEQUENTIAL_FAULT_GUIDE.md** - Full technical guide
- **INTERVAL_PLOTTING_FIXES.md** - Problems & solutions + suggestions
- **run_sequence_generator.py** - Detailed code comments

---

## ✅ Success Checklist

- [ ] First fault shows intervals 1-15 (or less if detects earlier)
- [ ] Fault triggers at random interval between 5-15
- [ ] 5-second pause before next fault
- [ ] Second fault ALSO shows intervals 1-X (resets!)
- [ ] Frontend dropdown shows correct interval count per fault
- [ ] Plots clear when switching faults
- [ ] All 11 faults complete without errors
- [ ] Each fault has its own stats.json with proper interval records

**If all checked:** ✓ Interval plotting is working correctly!

