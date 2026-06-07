# ⚡ Sequential Fault Runner - Testing & Verification Guide

## 🚀 Quick Start (5 minutes)

### **Prerequisites**
- Backend dependencies installed: `pip install -r requirements.txt`
- Frontend dependencies installed: `npm install` (in frontend/)
- Backend NOT running
- Frontend NOT running

### **Setup Steps**

#### **Step 1: Start Backend**
```bash
cd d:\Wilo\WILO-CLOUD-MONITORING
python app.py
```

**Expected Output:**
```
WARNING in app config: ...
 * Running on http://127.0.0.1:5000
 * Use a debugger to set breakpoints ...
```

**Key:** Server should show running on port 5000 ✓

---

#### **Step 2: Start Frontend** (new terminal)
```bash
cd d:\Wilo\WILO-CLOUD-MONITORING\frontend
npm run dev
```

**Expected Output:**
```
  VITE v... build ...
  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

**Key:** Frontend should show running on port 5173 ✓

---

#### **Step 3: Open Dashboard**
```
http://localhost:5173
```

**Expected:** Dashboard loads with left sidebar showing multiple cards

---

## ✅ Verification Test 1: UI Elements Visible

### **Check Sequential Runner Card Exists**

**Location:** Left sidebar (scroll if needed)

**Expected to See:**
```
┌─────────────────────────────────────┐
│ ⚡ Sequential Fault Runner          │
├─────────────────────────────────────┤
│                                     │
│ Number of Cycles: [_] cycles        │
│                                     │
│ [▶️ Start]  [⏹️ Stop]              │
│                                     │
│ ℹ️ How it works:                   │
│ ✓ Runs all 11 faults sequentially │
│ ✓ Each fault: intervals 1-15      │
│ ✓ Fault detection: 5-16/15 range  │
│ ✓ Automatic data reset per fault  │
│                                     │
└─────────────────────────────────────┘
```

**Verify:**
- [ ] Card title is visible
- [ ] Cycles input field is present
- [ ] [▶️ Start] button is visible and GREEN
- [ ] [⏹️ Stop] button is visible and GRAY (disabled)
- [ ] Info box explains how it works

✓ **TEST PASSED** if all elements visible

---

## ✅ Verification Test 2: Start Button Works

### **Action: Click [▶️ Start]**

**Expected Sequence:**

1. **Immediately** (within 1 second):
   - Cycles input becomes DISABLED
   - [▶️ Start] button becomes GRAY (disabled)
   - [⏹️ Stop] button becomes RED (enabled)

2. **Within 5 seconds**:
   - Progress bar appears
   - Status shows "Running"
   - "Current Fault:" section appears

3. **Within 10 seconds**:
   - Progress bar shows 1/11
   - "Current Fault:" shows "Motor Stall"
   - "Live Logs:" section shows first log

**UI should transform:**
```
FROM:                              TO:
┌──────────────┐        ┌─────────────────────┐
│ [▶️ Start]   │   →    │ [▶️ Start disabled] │
│ [⏹️ Stop]    │        │ [⏹️ Stop enabled]  │
└──────────────┘        │ Progress: 1/11      │
                        │ Current: Motor Stall│
                        │ Status: Running...  │
                        └─────────────────────┘
```

**Verify:**
- [ ] Cycles input disabled
- [ ] Start button disabled (gray)
- [ ] Stop button enabled (red)
- [ ] Progress bar appears
- [ ] "Motor Stall" appears in Current Fault

✓ **TEST PASSED** if state changes occur

---

## ✅ Verification Test 3: Progress Updates Work

### **Action: Wait and Watch (30-60 seconds)**

**Expected:** Progress bar increments

**Timeline:**
```
T=0s   → Progress: 1/11 | Current: Motor Stall
T=30s  → Progress: 1/11 | Current: Motor Stall (still running)
T=60s  → Progress: 2/11 | Current: Pump Cavitation (changed!)
```

**Details:**
- Each fault takes ~30 seconds
- Progress bar should show incremental movement
- Current Fault name should change after ~30s

**Verify:**
- [ ] Progress bar updates
- [ ] Current Fault changes over time
- [ ] Status message updates

✓ **TEST PASSED** if progress bar increments

---

## ✅ Verification Test 4: Logs Display Real Activity

### **Check Live Logs Section**

**Expected to see logs like:**
```
Live Logs:
━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Sequential runner started
Starting Motor Stall...
Sudden fault - trigger at interval 7
✓ Motor Stall completed at interval 7
Starting Pump Cavitation...
...
```

**Details:**
- Logs show fault start/completion
- Shows trigger intervals
- Updates every 2 seconds

**Verify:**
- [ ] At least 3-4 log entries visible
- [ ] Contains "Starting" and "completed" messages
- [ ] Shows trigger intervals

✓ **TEST PASSED** if logs appear

---

## ✅ Verification Test 5: Stop Button Works

### **Action: Click [⏹️ Stop] (while running)**

**Expected Immediate Changes:**
1. [⏹️ Stop] button becomes GRAY (disabled)
2. Status message shows "Stopped by user"
3. Progress bar stops advancing

**Within 5 seconds:**
- [▶️ Start] button becomes GREEN (enabled again)
- Cycles input becomes ENABLED

**Verify:**
- [ ] Stop button disables
- [ ] Status changes to "Stopped"
- [ ] Start button re-enables

✓ **TEST PASSED** if stopping works

---

## ✅ Verification Test 6: Restart After Stop

### **Action: Click [▶️ Start] Again**

**Expected:**
- Sequence resumes from Fault 1
- Progress bar shows 1/11
- Motor Stall appears again
- All UI state changes (buttons disable/enable)

**Verify:**
- [ ] Can restart sequence
- [ ] Starts from beginning
- [ ] All UI state correct

✓ **TEST PASSED** if restart works

---

## ✅ Verification Test 7: Full Sequence Completion

### **Action: Let Full Sequence Run (6-7 minutes)**

**Expected Timeline:**
```
Min 0:00 - Motor Stall (1/11)
Min 0:35 - Pump Cavitation (2/11)
Min 1:10 - Pump Impeller Damage (3/11)
Min 1:45 - Pump Seal Leakage (4/11)
Min 2:20 - Motor Bearing Failure (5/11)
Min 2:55 - Motor Shaft Misalignment (6/11)
Min 3:30 - Motor Overheating (7/11)
Min 4:05 - Motor Winding Failure (8/11)
Min 4:40 - Motor Vibration Anomaly (9/11)
Min 5:15 - Motor Electrical Fault (10/11)
Min 5:50 - Custom Event (11/11)
Min 6:25 - Sequence Completed!
```

**Final State:**
```
┌─────────────────────────┐
│ ✓ Sequence Completed!   │
│ All 11 faults generated │
│                         │
│ [▶️ Start enabled]      │
│ [⏹️ Stop disabled]      │
└─────────────────────────┘
```

**Verify:**
- [ ] All 11 faults appear in logs
- [ ] Final progress shows 11/11
- [ ] Success message displays
- [ ] Start button enabled for restart

✓ **TEST PASSED** if full sequence completes

---

## ✅ Verification Test 8: Data Files Created

### **Check Generated Data**

After sequence completes, verify files were created:

```bash
# In 'd:\Wilo\WILO-CLOUD-MONITORING' directory

ls Events/Motor\ Stall/          # Should have event files
ls Events/Pump\ Cavitation/      # Should have event files
ls Data/Motor\ Stall/            # Should have CSV files
ls Data/Pump\ Cavitation/        # Should have CSV files

# Should see files like:
# - *.csv (acceleration, current, audio data)
# - *.json (statistics)
# - timestamps.json (interval timings)
```

**Expected Structure:**
```
Events/
  Motor Stall/
    timestamp_1234567890.json
    timestamp_1234567891.json
    ...
  Pump Cavitation/
    timestamp_1234567892.json
    ...

Data/
  Motor Stall/
    max_acceleration.csv
    max_current.csv
    max_audio.csv
    ...statistics.json
  Pump Cavitation/
    max_acceleration.csv
    ...
```

**Verify:**
- [ ] Events/ folder has data for each fault
- [ ] Data/ folder has CSV files
- [ ] Files have recent timestamps

✓ **TEST PASSED** if data files exist

---

## ✅ Verification Test 9: Integration with Fault Monitor

### **While Sequential is Running, Select Specific Fault**

**Steps:**
1. Start Sequential Runner
2. Wait ~30 seconds (after Motor Stall completes)
3. In Fault Event Monitor card, select "Motor Stall" from dropdown
4. Observe plots

**Expected:**
- Plots show Motor Stall data
- Interval counter shows: 1, 2, 3, ... (from the Motor Stall run)
- Plots update every 30 seconds as sequence progresses

**Then:**
5. Wait for sequence to move to next fault
6. Select "Pump Cavitation" from dropdown
7. Observe plots RESET to show intervals 1, 2, 3, ...

**Expected:**
- Plots show Pump Cavitation data
- Interval counter RESETS to 1
- Fresh data (no carryover from Motor Stall)

**Verify:**
- [ ] Can select faults while sequencing
- [ ] Plots update for selected fault
- [ ] Intervals reset per fault (key feature!)
- [ ] No data mixing between faults

✓ **TEST PASSED** if intervals reset correctly

---

## ✅ Verification Test 10: Multiple Cycles

### **Run with 2 Cycles**

**Steps:**
1. Set Cycles = 2
2. Click [▶️ Start]
3. Watch full sequence (total 22 faults)

**Expected Timeline:**
```
Cycle 1: Motor Stall, Pump Cavitation, ..., Custom Event (11 faults)
   ↓ (5 second pause between cycles)
Cycle 2: Motor Stall, Pump Cavitation, ..., Custom Event (11 faults)
   ↓
Completion after ~12-14 minutes
```

**Progress Bar Behavior:**
```
Progress: 1/11  (start of cycle 1)
Progress: 5/11
Progress: 11/11 (end of cycle 1)
Progress: 1/11  (start of cycle 2) ← RESETS!
Progress: 5/11
Progress: 11/11 (end of cycle 2)
✓ Sequence Completed!
```

**Verify:**
- [ ] Progress bar completes to 11/11
- [ ] Progress bar resets to 1/11 for cycle 2
- [ ] Takes roughly 2× time for 2 cycles
- [ ] Final completion message appears

✓ **TEST PASSED** if multiple cycles work

---

## 🔍 Troubleshooting

### **Issue: Start Button Does Nothing**

**Diagnosis:**
```
1. Check backend logs:
   - Should show: "Starting subprocess: python run_sequence_generator.py"
   - If not: backend didn't receive click

2. Check browser console (F12):
   - Look for network errors
   - POST to /api/start-sequential-faults should succeed (200 OK)

3. Check if backend is running:
   - Open: http://localhost:5000/api/status
   - Should return JSON, not error
```

**Fix:**
- [ ] Restart backend: `python app.py`
- [ ] Clear browser cache: Ctrl+Shift+Delete
- [ ] Reload page: F5

---

### **Issue: Progress Bar Stuck at 1/11**

**Diagnosis:**
```
1. Check subprocess is running:
   - Open Task Manager (Ctrl+Shift+Esc)
   - Look for: python run_sequence_generator.py
   - If not there: subprocess didn't start

2. Check status file:
   - File: d:\Wilo\WILO-CLOUD-MONITORING\.sequential_runner_status.json
   - Should exist and be recent
   - If old timestamp: subprocess crashed
```

**Fix:**
- [ ] Check backend logs for subprocess error
- [ ] Kill any existing python processes: `taskkill /F /IM python.exe`
- [ ] Restart backend

---

### **Issue: No Logs Appearing**

**Diagnosis:**
```
1. Check subprocess output:
   - File: fault_generators_sequence.log
   - Should have recent entries
   - If old/empty: subprocess not running

2. Check status file permissions:
   - Should be readable/writable
   - Check file exists: .sequential_runner_status.json
```

**Fix:**
- [ ] Check run_sequence_generator.py is in correct directory
- [ ] Verify write permissions on project folder
- [ ] Check fault_generators/ imports are correct

---

### **Issue: Stop Button Doesn't Work**

**Diagnosis:**
```
1. Check subprocess status:
   - Task Manager: is python still running?
   - Wait 30 seconds (current fault may take time to stop)

2. Check backend logs:
   - Should show: "Terminating subprocess..."
   - If not: backend didn't receive stop request
```

**Fix:**
- [ ] Wait up to 60 seconds for current fault to complete
- [ ] Manually kill process: `taskkill /F /IM python.exe`
- [ ] Refresh frontend to resync state

---

## 📊 Expected Test Results Summary

| Test # | Test Name | Pass/Fail | Notes |
|--------|-----------|-----------|-------|
| 1 | UI Elements Visible | ✓ | All card elements present |
| 2 | Start Button Works | ✓ | State changes occur |
| 3 | Progress Updates | ✓ | Bar increments every 30s |
| 4 | Logs Display | ✓ | Activity logged in real-time |
| 5 | Stop Button Works | ✓ | Sequence stops cleanly |
| 6 | Restart Works | ✓ | Can run again immediately |
| 7 | Full Completion | ✓ | All 11 faults complete |
| 8 | Data Files Created | ✓ | CSV and JSON files exist |
| 9 | Fault Monitor Integration | ✓ | Intervals reset per fault |
| 10 | Multiple Cycles | ✓ | Can run 2+ cycles |

**Success Criteria:** All 10 tests PASS

---

## 🎯 Next Steps

After verification complete:

1. **Document Results:**
   - Screenshot of completed sequence
   - Note any issues encountered
   - Record timing information

2. **Deploy to Production:**
   - Push code to GitHub
   - Deploy frontend to Netlify/Vercel
   - Deploy backend to Render

3. **Monitor:**
   - Check frontend/backend logs regularly
   - Monitor for subprocess crashes
   - Verify data generation continues

---

## 📞 Support

If tests fail:
1. Check [FRONTEND_SEQUENTIAL_GUIDE.md](FRONTEND_SEQUENTIAL_GUIDE.md) for usage
2. Check [SEQUENTIAL_FAULT_GUIDE.md](SEQUENTIAL_FAULT_GUIDE.md) for technical details
3. Review backend logs: `fault_generators_sequence.log`
4. Check subprocess logs: Terminal where `python app.py` runs

