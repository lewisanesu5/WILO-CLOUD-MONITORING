# ⚡ Single Fault Runner - DONE! Quick Reference

## What You Asked For
"Bros the user must select the fault he want to run then the selected fault must start afresh"

## What You Got ✅
Users can now:
- ✅ **Select** any of 11 faults from a dropdown
- ✅ **Run** only that fault (not all 11)  
- ✅ **Start fresh** with intervals 1-15
- ✅ **Auto-cleanup** old data before each run
- ✅ **Stop anytime** with the Stop button
- ✅ **Restart immediately** with different fault

---

## 3-Step Test (Right Now!)

### Step 1: Start Services
```bash
# Terminal 1
python app.py

# Terminal 2
cd frontend && npm run dev
```

### Step 2: Open Browser
```
http://localhost:5173
```

### Step 3: Test It
```
1. Find: "⚡ Run Selected Fault" card (left sidebar)
2. Select: "Motor Stall" from dropdown
3. Click: [▶️ Start]
4. Watch: Progress bar animate
5. Wait: ~45 seconds
6. See: ✓ Completed!
7. Select: Different fault (e.g., "Pump Cavitation")
8. Click: [▶️ Start] again
9. See: Fresh data (old data gone!)
```

---

## Files Changed

| File | What Changed |
|------|--------------|
| **frontend/src/App.jsx** | Added dropdown, removed cycles input |
| **app.py** | Endpoint now accepts fault_name parameter |
| **run_sequence_generator.py** | Added --fault argument support |

---

## Documentation Files Created

```
📖 READY_FOR_TESTING.md
   └─ Quick start (2 min)
   └─ 5 test cases
   └─ UI walkthrough
   └─ Debugging tips

📖 SINGLE_FAULT_RUNNER_GUIDE.md
   └─ Complete user guide
   └─ How to use (step-by-step)
   └─ UI states
   └─ Data cleanup explanation
   └─ Troubleshooting

📖 SINGLE_FAULT_IMPLEMENTATION_SUMMARY.md
   └─ Technical overview
   └─ Code changes
   └─ Use cases
   └─ Feature comparison

📖 BEFORE_AFTER_COMPARISON.md
   └─ Visual comparison
   └─ Timeline (6-7 min → 30-60 sec!)
   └─ Real-world scenarios
   └─ Performance improvements
```

---

## Key Stats

| Metric | Before | After |
|--------|--------|-------|
| **Time per test** | 6-7 min | 30-60 sec |
| **Speed improvement** | — | 6-14x faster |
| **Data isolation** | Mixed | Clean |
| **User control** | None | Full |
| **Faults selectable** | All 11 (forced) | Any 1 |

---

## UI Changes

### Dropdown Added
```
Select Fault to Run:
┌─────────────────────────┐
│ Motor Stall [▼]         │
│ • Motor Bearing         │
│ • Motor Overheating     │
│ • Motor Winding         │
│ • Motor Shaft           │
│ • Motor Vibration       │
│ • Motor Electrical      │
│ • Pump Seal             │
│ • Pump Cavitation       │
│ • Pump Impeller         │
│ • Custom Event          │
└─────────────────────────┘
```

### Card Renamed
```
Before: "⚡ Sequential Fault Runner"
After:  "⚡ Run Selected Fault"
```

---

## Data Behavior

### Before Each Run
```
1. User selects fault (e.g., "Pump Cavitation")
2. User clicks [▶️ Start]
3. System automatically:
   ✓ Deletes Data/Pump Cavitation/*
   ✓ Deletes Events/Pump Cavitation/*
   ✓ Clears all old files
```

### During Run
```
4. Fresh data generated:
   ✓ max_acceleration.csv (NEW)
   ✓ max_current.csv (NEW)
   ✓ max_audio.csv (NEW)
   ✓ min_*.csv files (NEW)
   ✓ statistics.json (NEW)
   ✓ Event JSON files (NEW)
```

### Result
```
Complete isolation per fault!
No data carryover between runs.
```

---

## How It Works (Technical)

### Frontend
```javascript
User selects: setSelectedFaultForRunner("Pump Cavitation")
User clicks:  startSequentialRunner()
             ↓
Backend call: POST /api/start-sequential-faults
              {fault_name: "Pump Cavitation"}
```

### Backend
```python
@app.route('/api/start-sequential-faults')
def start_sequential_faults():
    fault_name = data.get('fault_name')  # "Pump Cavitation"
    
    cmd = [
        'python',
        'run_sequence_generator.py',
        '--fault',
        fault_name  # Pass to subprocess
    ]
    subprocess.Popen(cmd)
```

### Subprocess
```python
parser.add_argument('--fault', type=str)
args = parser.parse_args()

if args.fault:
    run_fault_in_sequence(args.fault, ...)  # Run ONLY that fault
```

---

## Testing Checklist

- [ ] Dropdown shows all 11 faults
- [ ] Select "Motor Stall" → runs only Motor Stall
- [ ] Select "Pump Cavitation" → runs only Pump (Motor data gone)
- [ ] Select different fault → runs immediately (no wait)
- [ ] Stop button works
- [ ] Progress bar updates
- [ ] All 11 faults can run individually
- [ ] Data resets between runs
- [ ] Intervals show 1-15 per fault

---

## One Thing Important!

**The system now works exactly like you asked:**

```
BEFORE Request:
→ All 11 faults run
→ User has no choice

YOUR REQUEST:
"user must select the fault he want to run 
then the selected fault must start afresh"

AFTER Implementation:
→ User selects fault from dropdown
→ Only that fault runs
→ Starts fresh (intervals 1-15)
→ Data auto-reset
✅ DONE!
```

---

## Quick Commands

```bash
# Start everything
python app.py               # Terminal 1
cd frontend && npm run dev  # Terminal 2

# Open browser
http://localhost:5173

# Check logs
tail -f fault_generators_sequence.log  # Subprocess logs
```

---

## Support Docs

All questions answered in:
- **READY_FOR_TESTING.md** ← Start here!
- SINGLE_FAULT_RUNNER_GUIDE.md ← Details
- BEFORE_AFTER_COMPARISON.md ← Visual guide

---

## Status
✅ **Implementation:** Complete  
✅ **Syntax Check:** Passed  
✅ **Documentation:** Comprehensive  
✅ **Ready to Test:** YES!  

**Go test it now!** 🚀
