# 🎯 Frontend Sequential Fault Runner Integration

## 📋 Overview

The Sequential Fault Runner is now fully integrated into the frontend dashboard. Users can trigger the automated sequential fault generation directly from the UI with a dedicated control card.

**Location:** Left sidebar, below "Fault Event Monitor" card  
**Component:** "⚡ Sequential Fault Runner" card  
**Status:** Real-time monitoring with live progress updates

---

## 🎮 How to Use (From Frontend)

### **Step 1: Open Dashboard**
```
1. Start backend: python app.py
2. Start frontend: npm run dev (in frontend/)
3. Open http://localhost:5173
```

### **Step 2: Access Sequential Fault Runner Card**
In the left sidebar, you'll see:
```
┌─────────────────────────────────────┐
│ ⚡ Sequential Fault Runner          │
│ Run all 11 faults one-by-one        │
├─────────────────────────────────────┤
│                                     │
│  Number of Cycles: [1] cycles       │
│                                     │
│  [▶️ Start]  [⏹️ Stop]              │
│  (Stop button disabled until running)
│                                     │
│  ℹ️ How it works:                   │
│  ✓ Runs all 11 faults sequentially │
│  ✓ Each fault: intervals 1-15      │
│  ✓ Fault detection: 5-16/15 range  │
│  ✓ Automatic data reset per fault  │
│                                     │
└─────────────────────────────────────┘
```

### **Step 3: Configure Cycles**
**Input field:** "Number of Cycles"  
**Default:** 1  
**Range:** 1-10 cycles  
**Purpose:** How many times to run all 11 faults  

**Examples:**
- **1 cycle:** All 11 faults once (~6 minutes)
- **2 cycles:** All 11 faults twice (~12 minutes)
- **3 cycles:** All 11 faults three times (~18 minutes)

### **Step 4: Start the Sequence**
1. Set desired number of cycles
2. Click **▶️ Start** button
3. Card transforms to show live progress

---

## 📊 Live Monitoring (While Running)

Once started, the card displays real-time updates:

```
┌─────────────────────────────────────┐
│ ⚡ Sequential Fault Runner          │
├─────────────────────────────────────┤
│                                     │
│ Progress: 7/11                      │
│ [███████░░░░░░░░░] 63%              │
│                                     │
│ Current Fault:                      │
│ ┌──────────────────────────────────┐│
│ │ Motor Overheating                 ││
│ └──────────────────────────────────┘│
│                                     │
│ Status:                             │
│ Gradual fault - critical at...      │
│                                     │
│ Live Logs:                          │
│ ✓ Motor Stall completed at int 7   │
│ ✓ Pump Cavitation at interval 12   │
│ Starting Pump Impeller Damage...   │
│                                     │
│                                     │
│ [Stop disabled] [⏹️ Stop] enabled  │
│                                     │
└─────────────────────────────────────┘
```

### **UI Elements During Execution:**

| Element | Purpose |
|---------|---------|
| **Progress Bar** | Visual indicator of fault completion (current/11) |
| **Current Fault** | Which fault is running now |
| **Status Message** | Detailed info about current fault |
| **Live Logs** | Recent activity (last 8 logs) |
| **▶️ Start** | Disabled during execution |
| **⏹️ Stop** | Enabled - stops sequence immediately |

---

## ⏸️ Stopping the Sequence

**Option 1: UI Button**
```
While running, click [⏹️ Stop]
→ Sequence stops after current fault completes
→ Status updates to "Stopped by user"
→ Can restart with [▶️ Start] again
```

**Option 2: Manual Interrupt**
```
Ctrl+C in terminal running: python run_sequence_generator.py
→ Frontend shows connection error
→ Click [▶️ Start] again to restart
```

---

## ✅ Completion State

When all faults finish:

```
┌─────────────────────────────────────┐
│ ⚡ Sequential Fault Runner          │
├─────────────────────────────────────┤
│                                     │
│ ✓ Sequence Completed!              │
│ All faults have been generated.    │
│                                     │
│ [▶️ Start] enabled                  │
│ [⏹️ Stop] disabled                  │
│                                     │
│ Final Logs:                         │
│ ✓ Motor Electrical Fault at int 8 │
│ ✓ Custom Event completed at 15    │
│ ✅ All 11 faults completed         │
│                                     │
└─────────────────────────────────────┘
```

**Actions available:**
- Click **▶️ Start** to run sequence again
- Select specific fault from "Fault Event Monitor" dropdown
- Monitor fault plots as they update

---

## 🔄 Combined with Fault Event Monitor

The Sequential Runner works together with the Fault Event Monitor:

### **Scenario: Auto-Monitor While Sequencing**

```
STEP 1: Start Sequential Runner
  └─ Click [▶️ Start]

STEP 2: Select First Fault
  └─ In "Fault Event Monitor" dropdown, select "Motor Stall"
  └─ Plots start showing interval data for Motor Stall
  └─ Interval counter shows: 1, 2, 3, ...

STEP 3: Watch Fault Complete
  └─ Plots update every 30 seconds
  └─ Fault triggers at interval 7
  └─ Sequential Runner pauses 5 seconds

STEP 4: Select Next Fault
  └─ Sequential Runner starts Pump Cavitation
  └─ Select "Pump Cavitation" from dropdown
  └─ Plots RESET to show intervals 1-15
  └─ Interval counter: 1, 2, 3, ... (RESETS!)
  └─ This is the key feature - clean slate per fault

STEP 5: Continue Through All Faults
  └─ Repeat for each of the 11 faults
  └─ Each one plots 1-15 range, fault detected 5-15
  └─ No data carryover between faults
```

---

## 📱 UI States

### **State 1: Idle (Ready)**
```
- Cycles input: ENABLED
- [▶️ Start]: ENABLED (green)
- [⏹️ Stop]: DISABLED (gray)
- Info box: How it works
```

### **State 2: Running**
```
- Cycles input: DISABLED
- [▶️ Start]: DISABLED (gray)
- [⏹️ Stop]: ENABLED (red)
- Progress bar: Updating
- Logs: Live updates every 2 seconds
```

### **State 3: Completed**
```
- Cycles input: ENABLED
- [▶️ Start]: ENABLED (green) - can restart
- [⏹️ Stop]: DISABLED (gray)
- Success message: "Sequence Completed!"
- All logs visible
```

### **State 4: Stopped by User**
```
- Cycles input: ENABLED
- [▶️ Start]: ENABLED (green) - can restart
- [⏹️ Stop]: DISABLED (gray)
- Status: "Stopped by user"
- Partial logs visible
```

---

## 🔌 Backend Communication

### **How Frontend Talks to Backend**

**When [▶️ Start] is clicked:**
```http
POST /api/start-sequential-faults
Content-Type: application/json

{
  "cycles": 1
}

Response:
{
  "status": "started",
  "message": "Sequential fault runner started",
  "cycles": 1,
  "pid": 12345
}
```

**Frontend Polling (every 2 seconds):**
```http
GET /api/sequential-faults-status

Response:
{
  "active": true,
  "status": "running",
  "current_fault": "Motor Stall",
  "current_fault_number": 1,
  "total_faults": 11,
  "cycles": 1,
  "last_log": "Starting Motor Stall..."
}
```

**When [⏹️ Stop] is clicked:**
```http
POST /api/stop-sequential-faults

Response:
{
  "status": "stopped",
  "message": "Sequential fault runner stopped successfully"
}
```

---

## 🧪 Testing Workflow

### **Test 1: Basic Start/Stop**
```
1. Click [▶️ Start] (cycles = 1)
2. Observe progress bar fills
3. After ~30 seconds, see "Motor Stall" in "Current Fault"
4. Click [⏹️ Stop]
5. Status changes to "Stopped by user"
✓ PASS if stop works within 5 seconds
```

### **Test 2: Full Sequence (Single Cycle)**
```
1. Set cycles = 1
2. Click [▶️ Start]
3. Wait ~6-7 minutes (11 faults × ~35 sec each)
4. Watch progress bar go from 0 to 11
5. See all fault names appear in logs
6. Final message: "Sequence Completed!"
✓ PASS if all 11 faults run
```

### **Test 3: Multiple Cycles**
```
1. Set cycles = 2
2. Click [▶️ Start]
3. Observe fault progression
4. After fault 11 completes, sequence restarts
5. Progress: 1/11, 2/11, ..., 11/11, then 1/11 again
6. Takes ~12-14 minutes total
✓ PASS if all 22 faults run (11 × 2 cycles)
```

### **Test 4: Monitor Specific Fault While Sequencing**
```
1. Click [▶️ Start]
2. Select "Motor Stall" from Fault Event Monitor
3. Plots show interval 1, 2, 3...
4. When Motor Stall completes, select next fault
5. Plot RESETS to interval 1 for new fault
✓ PASS if each fault shows clean 1-15 range
```

### **Test 5: Auto-Stop on Completion**
```
1. Set cycles = 1
2. Click [▶️ Start]
3. Wait for completion
4. Observe card auto-updates to "Completed" state
5. [▶️ Start] is now enabled again
✓ PASS if ready for another run
```

---

## 📊 Live Monitoring Tips

### **Watch Progress Bar Fill**
- Each completed fault advances the bar
- Shows X/11 ratio
- Visual indicator of long operation

### **Read Live Logs**
- Shows last 8 activities
- Displays trigger intervals
- Helps verify fault completion

### **Check Current Fault Name**
- Clearly displays which fault is running
- Updates within 2 seconds
- Matches "Fault Event Monitor" dropdown

### **Monitor Timestamps**
- Status logs show timestamps
- Verify ~30 second intervals between updates
- Ensures sequence is progressing

---

## ⚠️ Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Progress bar stuck at 0% | Check if backend is running: `python app.py` |
| No logs appearing | Ensure run_sequence_generator.py output is writing to file |
| Stop button doesn't work | May take up to 30 seconds for current fault to end |
| Frontend shows "Completed" but logs empty | Refresh page to reload status |
| Can't restart after completion | Click [▶️ Start] again - it's enabled |
| Cycles not changing | Check that field is not disabled (only disabled during run) |

---

## 🔧 Configuration

### **Adjusting Polling Interval** (frontend code)
```javascript
// In App.jsx, Sequential Runner polling:
const interval = setInterval(pollSequentialStatus, 2000);  // 2 seconds
// Change 2000 to 5000 for slower polling, 1000 for faster
```

### **Adjusting Max Cycles**
```javascript
// In Sequential Runner card input:
<input type="number" min="1" max="10" />
// Change max="10" to max="20" for more cycles
```

---

## 📖 Related Documentation

- [SEQUENTIAL_FAULT_GUIDE.md](SEQUENTIAL_FAULT_GUIDE.md) - Backend technical guide
- [INTERVAL_PLOTTING_FIXES.md](INTERVAL_PLOTTING_FIXES.md) - Problem analysis
- [QUICK_REFERENCE_INTERVALS.md](QUICK_REFERENCE_INTERVALS.md) - Quick reference

---

## 🎓 Key Points to Remember

1. **Sequential** = One fault after another (not parallel)
2. **Intervals Reset** = Each fault shows 1-15, no carryover
3. **Polling** = Frontend checks status every 2 seconds
4. **Live Progress** = Progress bar updates in real-time
5. **Auto-Save** = Status written to `.sequential_runner_status.json`
6. **Always-Ready** = [▶️ Start] available after completion
7. **Combined Use** = Works with Fault Event Monitor dropdown
8. **Clean Data** = Each fault starts with fresh data directory

