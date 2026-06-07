# Sequential Fault Monitoring - Implementation Guide

## 🎯 Problem Statement

**Issue:** Fault plotting was not resetting intervals properly when running multiple faults sequentially
- Plot intervals were not showing clear 1-15 range per fault
- When switching faults, the interval count wasn't starting fresh
- Fault detection logic wasn't properly isolated to each fault cycle
- No clear visual indicator of which fault was running and when failure occurred

## ✅ Solution Implemented

### **1. New Sequential Fault Runner Script** (`run_sequence_generator.py`)

**Purpose:** Run each of the 11 faults ONE-BY-ONE with proper interval reset

**Key Features:**
- ✓ Each fault starts fresh with interval count = 1
- ✓ Plots data for intervals 1-15 only (per fault)
- ✓ Detects fault in the 5-16/15 detection range
- ✓ Clears previous fault data before starting new fault
- ✓ Adds 5-second pause between faults for clean transitions
- ✓ Supports single cycle or continuous cycles
- ✓ Interactive menu for choosing run mode

**Three Run Modes:**
```
Mode 1: Single Cycle
  └─ Runs all 11 faults sequentially once, then stops
  
Mode 2: Continuous Cycles  
  └─ Runs all 11 faults, repeats N times (user specifies)
  
Mode 3: Single Fault
  └─ Choose one fault and run it
```

### **2. Enhanced BaseGenerator** (`base_generator.py`)

**New Method: `log_interval_progress(interval_max=15)`**
```python
# Visual progress bar showing current interval position
# Example output:
# [████░░░░░░░░░░░░░] Interval 4/15 | ✓ NORMAL
# [██████████████░░░] Interval 13/15 | 🔥 FAILURE
```

**Improved `run_indefinitely()` Method:**
- Shows plot range: 1-15
- Shows fault detection range: 5-15
- Shows interval duration: ~30 seconds
- Displays progress after each interval
- Final summary when fault completes

### **3. Data Reset Strategy**

**On Each Fault Start:**
```
✓ Clear Data/<FaultName>/ directory (old CSVs)
✓ Clear Events/<FaultName>/ directory (old stats.json)
✓ Create fresh directories
✓ Initialize new generator (interval_count = 0)
✓ Start plotting from interval 1
```

## 📊 Data Flow (Sequential Mode)

```
START SEQUENCE
    │
    ├─→ FAULT 1 (Motor Stall)
    │   ├─ Clear old data
    │   ├─ Initialize: interval_count = 0
    │   ├─ Generate intervals 1-15
    │   ├─ Detect fault at random interval (5-15)
    │   └─ Completion
    │
    ├─→ [5 second pause]
    │
    ├─→ FAULT 2 (Pump Cavitation)
    │   ├─ Clear old data  ← KEY: Fresh start
    │   ├─ Initialize: interval_count = 0  ← KEY: Reset counter
    │   ├─ Generate intervals 1-15  ← KEY: Plot 1-15 range
    │   ├─ Detect fault at random interval (5-15)
    │   └─ Completion
    │
    ├─→ [5 second pause]
    │
    ├─→ FAULT 3... through FAULT 11
    │
    └─→ SEQUENCE COMPLETE
```

## 🚀 How to Use

### **Option A: Run Sequential Cycle (Recommended for Testing)**

```bash
# Navigate to project directory
cd D:\Wilo\WILO-CLOUD-MONITORING

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Start the sequential runner
python run_sequence_generator.py
```

**Menu Interaction:**
```
CHOOSE RUN MODE:
1. Single Cycle (Run all 11 faults once, then stop)      ← Start with this
2. Continuous Cycles (Run all 11 faults repeatedly)
3. Run Specific Fault Only (Choose one fault)
4. Exit

Select mode (1-4): 1
```

### **Option B: Run Multiple Cycles**

```bash
python run_sequence_generator.py

Select mode (1-4): 2
How many cycles? (default: 2): 3
```
This will run all 11 faults three times sequentially.

### **Option C: Debug Single Fault**

```bash
python run_sequence_generator.py

Select mode (1-4): 3

SELECT A FAULT TO RUN:
 1. Motor Stall                    (SUDDEN)
 2. Pump Cavitation               (SUDDEN)
 3. Pump Impeller Damage          (SUDDEN)
 ...

Select fault (1-11) or 'q' to quit: 1
```

### **Option D: Continue Using Original Runners**

```bash
# Run all 11 faults in PARALLEL (original behavior)
python run_all_generators.py

# Run ONE fault at a time (user selects)
python run_selected_generator.py
```

## 📈 Expected Output Example

```
====================================================================================================
 WILO CLOUD MONITORING - SEQUENTIAL FAULT RUNNER
====================================================================================================

📊 OPERATION MODE: Sequential (One Fault After Another)
✓ Each fault will run within interval range 1-15
✓ Fault detection happens between intervals 5-16/15
✓ After each fault completes, the next fault will START FROM INTERVAL 1
✓ Plots will reset and display only current fault data (1-15 range)
✓ 11 faults configured for sequential testing

Fault Sequence:
   1. Motor Stall                    (SUDDEN)
   2. Pump Cavitation               (SUDDEN)
   ...
====================================================================================================

[FAULT 1/11] Starting: MOTOR STALL
Type: SUDDEN
Interval Range: 1-15
Status: Plotting intervals and monitoring for fault detection...
====================================================================================================
   🎯 SUDDEN: Spike will trigger at interval 7
   📈 Monitoring starts NOW - Interval 1/15
   ⏱️  Each interval takes ~30 seconds

2024-01-15 10:23:45 - [Generator-Motor Stall] - INFO - [█░░░░░░░░░░░░░░░] Interval 1/15 | ✓ NORMAL
2024-01-15 10:24:15 - [Generator-Motor Stall] - INFO - [██░░░░░░░░░░░░░░] Interval 2/15 | ✓ NORMAL
2024-01-15 10:24:45 - [Generator-Motor Stall] - INFO - [███░░░░░░░░░░░░░] Interval 3/15 | ✓ NORMAL
...
2024-01-15 10:26:45 - [Generator-Motor Stall] - INFO - [███████░░░░░░░░░] Interval 7/15 | 🔥 FAILURE
✓ Fault 'Motor Stall' completed at interval 7

====================================================================================================

⏳ Waiting 5 seconds before next fault...

[FAULT 2/11] Starting: PUMP CAVITATION
Type: SUDDEN
Interval Range: 1-15
Status: Plotting intervals and monitoring for fault detection...
====================================================================================================
   🎯 SUDDEN: Spike will trigger at interval 12
   📈 Monitoring starts NOW - Interval 1/15  ← NOTE: Counter resets!
   ⏱️  Each interval takes ~30 seconds

2024-01-15 10:27:15 - [Generator-Pump Cavitation] - INFO - [█░░░░░░░░░░░░░░░] Interval 1/15 | ✓ NORMAL  ← NOTE: Starts from 1!
2024-01-15 10:27:45 - [Generator-Pump Cavitation] - INFO - [██░░░░░░░░░░░░░░] Interval 2/15 | ✓ NORMAL
...
```

## 🔌 Integration with Frontend

**When using run_sequence_generator.py:**

1. **Start backend:** `python app.py`
2. **Start frontend:** `npm run dev` (in frontend/)
3. **Start generators:** `python run_sequence_generator.py`
4. **Select fault in dropdown** (in UI)

**Frontend Behavior:**
- ✓ Polls `/api/fault-state/<fault_name>` every 30 seconds
- ✓ Displays interval count (1-15)
- ✓ Updates plots with fresh data per fault
- ✓ Shows failure detection at correct interval
- ✓ Auto-resets when new fault selected

## 🧪 Testing Checklist

- [ ] Run `python run_sequence_generator.py` → Select Mode 1
- [ ] Verify first fault starts at interval 1
- [ ] Verify fault detects between intervals 5-15
- [ ] Verify 5-second pause between faults
- [ ] Verify second fault ALSO starts at interval 1
- [ ] Check frontend shows interval counter 1-15 per fault
- [ ] Verify plots show only current fault (no carryover)
- [ ] Check logs show progress bars
- [ ] Verify all 11 faults complete without errors

## 📝 File Changes Summary

| File | Change | Purpose |
|------|--------|---------|
| `run_sequence_generator.py` | NEW | Sequential fault runner with interactive menu |
| `base_generator.py` | Enhanced | Added `log_interval_progress()` method + better logging in `run_indefinitely()` |
| `run_all_generators.py` | UNCHANGED | Still runs all 11 faults in parallel |
| `run_selected_generator.py` | UNCHANGED | Still runs single fault at user choice |

## 🎓 Key Concepts

### **Interval Reset Mechanism**
```python
# When each fault starts (NEW generator instance created):
generator = MotorStallGenerator()  # Calls __init__
# Inside __init__:
self.interval_count = 0  # Always resets to 0
self.failure_triggered = False
self.system_failure_state = False
self.intervals_data = []  # Fresh list
```

### **Data Isolation**
```python
# run_sequence_generator.py clears before each fault:
clear_fault_data(fault_name)  # Deletes Data/<name>/ and Events/<name>/
# Then creates fresh instance:
generator = generator_class()  # Starts completely clean
```

### **Plot Range Control**
- Intervals 1-15 are always generated
- Fault detection happens in range 5-15
- Frontend shows 1-15 on x-axis
- When new fault selected, old plot cleared and replaced with 1-15 range for new fault

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| Intervals not resetting | Use `run_sequence_generator.py` (not `run_all_generators.py`) |
| Plot shows old fault data | Clear old data with `clear_fault_data()` or delete Data/ folder |
| Interval counter shows >15 | That's expected in parallel mode; sequential mode fixes this |
| Fault doesn't trigger by 15 | It triggers at its configured random interval (5-15); may be on first try |
| Frontend not updating | Check polling endpoints return fresh interval count |

## 📞 Support

For questions or issues:
1. Check `fault_generators_sequence.log` for detailed logs
2. Verify data is clearing between faults: `ls Data/` and `ls Events/`
3. Ensure frontend is polling correct endpoint: `/api/fault-state/<fault_name>`
