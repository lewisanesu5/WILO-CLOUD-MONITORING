# ✨ Single Fault Runner - Updated Implementation

## 🎯 What Changed

The system now allows you to **select and run a SINGLE fault** instead of all 11 sequentially. Each selected fault starts fresh with intervals 1-15.

### **Before (Sequential All 11):**
```
[▶️ Start] → Motor Stall (1-15) 
          → Pump Cavitation (1-15)
          → ... all 11 faults
```

### **After (Single Fault Selection):**
```
Dropdown: [Motor Stall ▼]
[▶️ Start] → Motor Stall (1-15) - DONE
            Ready for next selection
```

---

## 🚀 How to Use

### **Step 1: Start Backend & Frontend**
```bash
# Terminal 1: Backend
python app.py

# Terminal 2: Frontend
cd frontend && npm run dev

# Browser: http://localhost:5173
```

### **Step 2: Use the New Control Card**

In the left sidebar, find **"⚡ Run Selected Fault"** card:

```
┌─────────────────────────────┐
│ ⚡ Run Selected Fault        │
│ Run single fault from start  │
├─────────────────────────────┤
│                             │
│ Select Fault to Run:        │
│ ┌───────────────────────┐  │
│ │ Motor Stall [▼]       │  │
│ │ • Motor Bearing...    │  │
│ │ • Motor Overheating   │  │
│ │ • ...                 │  │
│ └───────────────────────┘  │
│                             │
│ [▶️ Start] [⏹️ Stop]       │
│                             │
└─────────────────────────────┘
```

### **Step 3: Select a Fault**

Click the dropdown to choose:

**Motor Failures (7 options):**
- Motor Stall
- Motor Bearing Failure
- Motor Overheating
- Motor Winding Failure
- Motor Shaft Misalignment
- Motor Vibration Anomaly
- Motor Electrical Fault

**Pump Failures (3 options):**
- Pump Seal Leakage
- Pump Cavitation
- Pump Impeller Damage

**Other (1 option):**
- Custom Event

### **Step 4: Click [▶️ Start]**

The selected fault will:
1. ✓ Clear all previous data
2. ✓ Start fresh interval counter (1, 2, 3, ... 15)
3. ✓ Generate sensor data (acceleration, current, audio)
4. ✓ Trigger fault detection (typically at interval 5-15)
5. ✓ Complete and show success status

### **Step 5: Monitor Progress**

While running, the card shows:

```
Progress: [████████░░░░░] Running...

Current Fault:
Motor Stall

Status:
Sudden fault - trigger at interval 7

Live Logs:
✓ Starting Motor Stall...
Sudden fault - trigger at interval 7
[████░░░░░░░░░░░░░] Interval 4/15 | ✓ NORMAL
[████░░░░░░░░░░░░░] Interval 5/15 | ⚠️  RISING
[██████░░░░░░░░░░░] Interval 7/15 | 🔴 DETECTED
✓ Motor Stall completed at interval 7
```

### **Step 6: Select Different Fault and Repeat**

After completion:
1. Change dropdown selection
2. Click [▶️ Start] again
3. New fault starts fresh
4. No data carryover from previous fault

---

## 📊 Data Cleanup

Each time you select a fault and click Start:

### **Automatically Deleted:**
```
Data/Motor Stall/
  ├── max_acceleration.csv  ← DELETED
  ├── max_current.csv       ← DELETED
  ├── max_audio.csv         ← DELETED
  ├── min_acceleration.csv  ← DELETED
  ├── min_audio.csv         ← DELETED
  ├── min_current.csv       ← DELETED
  └── statistics.json       ← DELETED

Events/Motor Stall/
  ├── timestamp_*.json      ← ALL DELETED
  ├── ...
```

### **Automatically Created:**
```
Data/Motor Stall/
  ├── max_acceleration.csv  ← FRESH DATA
  ├── max_current.csv       ← FRESH DATA
  ├── max_audio.csv         ← FRESH DATA
  ├── min_acceleration.csv  ← FRESH DATA
  ├── min_audio.csv         ← FRESH DATA
  ├── min_current.csv       ← FRESH DATA
  └── statistics.json       ← FRESH STATS

Events/Motor Stall/
  ├── timestamp_*.json      ← NEW EVENT FILES
  ├── ...
```

**Result:** Every fault run starts with completely clean data!

---

## 🎮 UI States

### **State 1: Idle (Ready)**
```
[Dropdown enabled]
[▶️ Start] GREEN
[⏹️ Stop] GRAY (disabled)
Info box visible
```

### **State 2: Running**
```
[Dropdown disabled]
[▶️ Start] GRAY (disabled)
[⏹️ Stop] RED
Progress bar: animated
Current Fault: displayed
Logs: updating live
```

### **State 3: Completed**
```
[Dropdown enabled]
[▶️ Start] GREEN
[⏹️ Stop] GRAY (disabled)
Status: ✓ Completed
Can select new fault and start again
```

---

## 🔄 Combined Usage with Fault Event Monitor

### **Workflow:**
```
1. Select fault from "Run Selected Fault" dropdown
   Example: Motor Stall

2. Click [▶️ Start]
   Motor Stall begins running
   Intervals: 1, 2, 3, ...

3. While it's running, go to "Fault Event Monitor"
   Select: Motor Stall (same fault)

4. Watch plots update in real-time
   Interval 1: Normal readings
   Interval 2: Normal readings
   ...
   Interval 7: Fault detected! (shows anomaly)

5. When done, select different fault
   Example: Pump Cavitation

6. Click [▶️ Start] again
   Previous Motor Stall data CLEARED
   Pump Cavitation starts fresh (intervals 1-15)

7. Select Pump Cavitation in Event Monitor
   Plots RESET to show only Pump data
   Clean intervals 1, 2, 3, ...
```

**Key Benefit:** No data mixing between faults!

---

## ⚙️ Technical Details

### **Frontend Changes:**
```javascript
// State: selectedFaultForRunner
const [selectedFaultForRunner, setSelectedFaultForRunner] = useState('Motor Stall');

// Function: startSequentialRunner (no parameter, uses state)
const startSequentialRunner = async () => {
  const response = await fetch(`/api/start-sequential-faults`, {
    method: 'POST',
    body: JSON.stringify({
      fault_name: selectedFaultForRunner  // Send selected fault
    })
  });
};
```

### **Backend Changes:**
```python
@app.route('/api/start-sequential-faults', methods=['POST'])
def start_sequential_faults():
    fault_name = data.get('fault_name', 'Motor Stall')
    
    cmd = [
        'python',
        'run_sequence_generator.py',
        '--fault',
        fault_name  # Pass fault name as argument
    ]
    
    subprocess.Popen(cmd)
```

### **Subprocess Changes:**
```python
# run_sequence_generator.py accepts --fault argument
if args.fault:
    for fault_name, generator_class, fault_type in FAULT_SEQUENCE:
        if fault_name.lower() == args.fault.lower():
            run_fault_in_sequence(fault_name, generator_class, fault_type, 1, 1)
            return
```

---

## 🧪 Quick Test

### **Test 1: Run Single Fault**
1. Select "Motor Stall" from dropdown
2. Click [▶️ Start]
3. Watch progress bar animate
4. Wait ~30-60 seconds
5. Status shows: ✓ Completed
6. Expected: Motor Stall data created in Data/Motor Stall/

### **Test 2: Run Different Fault**
1. Select "Pump Cavitation" from dropdown
2. Click [▶️ Start]
3. Watch progress bar animate
4. After completion, check Data/Pump Cavitation/
5. Expected: Fresh data, no Motor Stall data here

### **Test 3: Verify Data Cleanup**
1. Run "Motor Stall"
2. Check Data/Motor Stall/ - has files ✓
3. Run "Motor Stall" again
4. Check Data/Motor Stall/ - has NEW files with recent timestamps ✓
5. Expected: Old files were deleted, new ones created

### **Test 4: Stop Mid-Execution**
1. Click [▶️ Start]
2. Wait 10 seconds
3. Click [⏹️ Stop]
4. Status changes to "Stopped by user"
5. [▶️ Start] button becomes enabled again
6. Can start new fault immediately

---

## 📊 Expected File Structure After Running Motor Stall

```
d:\Wilo\WILO-CLOUD-MONITORING\
├── Data/
│   └── Motor Stall/
│       ├── max_acceleration.csv      (700 Hz samples x 15 intervals)
│       ├── max_current.csv           (700 Hz samples x 15 intervals)
│       ├── max_audio.csv             (700 Hz samples x 15 intervals)
│       ├── min_acceleration.csv
│       ├── min_current.csv
│       ├── min_audio.csv
│       └── statistics.json           {mean, std, min, max per sensor}
│
├── Events/
│   └── Motor Stall/
│       ├── timestamp_1234567890.json {interval_data}
│       ├── timestamp_1234567891.json {interval_data}
│       └── ...                       (20-30 JSON files)
│
└── .sequential_runner_status.json    {active, current_fault, etc}
```

---

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| **Dropdown doesn't change** | Refresh page (F5) or restart frontend |
| **Start button doesn't work** | Check if backend is running: `http://localhost:5000` |
| **No progress shown** | Check backend logs for errors |
| **Stop button unresponsive** | May take 5-10 seconds for current interval to complete |
| **Data not generated** | Check Events/ and Data/ directories have write permissions |
| **Same fault runs twice** | Previous run didn't complete; wait for status to show "Completed" |

---

## ✨ Key Advantages

✅ **Run Any Fault** - Select from 11 faults, not just first one
✅ **Fresh Start** - Each fault starts with interval 1 (no carryover)
✅ **Clean Data** - Old files deleted automatically
✅ **Fast Testing** - Run individual faults for specific testing
✅ **Combined UI** - Works with Fault Event Monitor for live viewing
✅ **Easy Selection** - Organized dropdown (Motor/Pump/Other)
✅ **Immediate Restart** - Run another fault right after completion
✅ **Status Tracking** - Real-time progress and logs

---

## 📞 Support

**For usage questions:**
→ Read sections above or check implementation code

**For debugging:**
→ Check backend logs: `fault_generators_sequence.log`
→ Check subprocess output in terminal where `python app.py` runs

**For testing:**
→ Follow "Quick Test" section above
→ All 4 tests should pass

---

**Status:** ✅ Ready for Testing
**Mode:** Single Fault Selection
**Faults Available:** 11 (7 Motor + 3 Pump + 1 Custom)

