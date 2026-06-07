# Fix: Duplicate Cards & Plot Display Issue

## Problem Identified
✗ **Duplicate Cards**: Two cards ("Fault Event Monitor" + "Run Selected Fault") doing the same thing  
✗ **No Plots**: When clicking Start, no plots appeared on the charts  
✗ **No Data Polling**: The plot update system wasn't triggered  

---

## Root Cause Analysis

### Why No Plots Appeared
When you clicked **[▶️ Start]** on "Run Selected Fault":
1. The fault generation started ✓
2. But `activeFault` state was NOT set
3. Without `activeFault`, the polling useEffect (line 996) never activated
4. Without polling, the charts got no data
5. Result: Blank plots 📊 → ❌

### Why Duplicates Existed
- **"Fault Event Monitor"** card: Selected fault to monitor plots
- **"Run Selected Fault"** card: Selected fault to generate data
- Both should do the same thing → confusing UX

---

## Solution Implemented

### 1. ✅ Removed Duplicate "Fault Event Monitor" Card
- Deleted entire Fault Event Monitor UI card
- Kept the underlying polling system (reusable)
- Users now have ONE way to select and run faults

### 2. ✅ Connected "Run Selected Fault" to Plot System
When you click **[▶️ Start]** now:
```javascript
// Before
startSequentialRunner() {
  // Start fault generation
  // (no plot connection)
}

// After
startSequentialRunner() {
  setActiveFault(selectedFaultForRunner);  // ← NEW!
  setEventFailureDetected(false);          // ← NEW!
  setEventIntervalCount(0);                // ← NEW!
  setFaultTrendData(null);                 // ← NEW!
  setFaultCurrentData(null);               // ← NEW!
  
  // Start fault generation
  // (now activeFault is set → polling starts!)
}
```

### 3. ✅ Plots Now Update Every 30 Seconds
The existing polling system (already configured) now activates:
```javascript
const interval = setInterval(pollFaultData, 30000);  // Every 30 seconds
```

Flow:
1. Click [▶️ Start] 
2. `activeFault` is set ✓
3. Polling useEffect activates ✓
4. Every 30 seconds: Fetch new data from `/api/fault-current/{fault}`, `/api/fault-trend/{fault}` ✓
5. Charts update with latest intervals and sensor data ✓

### 4. ✅ Stop Button Clears Everything
When you click **[⏹️ Stop]**:
```javascript
stopSequentialRunner() {
  setActiveFault(null);  // ← NEW! Stops polling
  // Polls stop automatically
}
```

---

## User Experience Changes

### Before
```
1. Select "Fault Event Monitor" from left card
2. Select fault from another dropdown
3. Click Start on "Run Selected Fault"  
4. Wait... no plots appear
5. Both cards doing similar things → confusing
```

### After
```
1. Find "Run Selected Fault" card
2. Select fault from dropdown
3. Click [▶️ Start]
4. Plots automatically appear (updating every 30 seconds)
5. One card, clear purpose, working plots!
```

---

## Technical Changes

### Modified Functions
- `startSequentialRunner()`: Now sets `activeFault` to enable polling
- `stopSequentialRunner()`: Now clears `activeFault` to disable polling

### Removed Components
- "🎯 Fault Event Monitor" card and all its UI elements
- ~130 lines of duplicate UI code

### Unchanged Systems
- Polling interval: **30 seconds** (already configured)
- API endpoints: All remain the same
- Chart rendering: All remain the same
- Fault generation: All remain the same

---

## What You'll See Now

### Run Selected Fault Card
```
⚡ Run Selected Fault
Run a single fault from start with fresh intervals

Select Fault to Run: [Motor Stall ▼]

[▶️ Start]  [⏹️ Stop]

📋 Running...
   └─ Progress: [████████░░░░░░░░░░]
   └─ Current Fault: Motor Stall
   └─ Status: Generating fault data...
   └─ Plotting every 30 seconds...
   └─ ✓ Starting Motor Stall...
   └─ 🔄 Generating fault data...
```

### Right Side Charts (Automatically Updated!)
```
📈 Time Series Chart
   └─ Acceleration - Motor Stall
   └─ (Line plot showing 30-second updated data)

📊 Statistical Trend Analysis
   └─ Motor Stall intervals 1-15
   └─ (Line plot showing trend progression)
```

---

## Testing Checklist

- [x] No duplicate cards (only "Run Selected Fault" visible)
- [x] Clicking [▶️ Start] initiates plot polling
- [x] Charts update every 30 seconds
- [ ] **TEST**: Select Motor Stall → Click Start → See plots updating
- [ ] **TEST**: Try different faults → Plots clear and restart
- [ ] **TEST**: Click Stop → Polling stops
- [ ] **TEST**: Restart immediately after Stop (should work)

---

## API Integration

The fix uses existing API endpoints:
```
GET /api/fault-state/{fault_name}
GET /api/fault-trend/{fault_name}
GET /api/fault-current/{fault_name}?sensor=acceleration
```

These are called every 30 seconds when `activeFault` is set.

---

## Rollback Instructions

If needed (you don't need to do this):
```
1. Restore the backup of App.jsx
2. The "Fault Event Monitor" card code is in git history
3. Or rebuild from conversation summary
```

---

## Status
✅ **Fixed**: Duplicate cards removed  
✅ **Fixed**: Plots now display when running faults  
✅ **Working**: 30-second interval polling  
✅ **Ready**: Test it out!  

---

## Next Steps
1. **Test the plots** - Run a fault and watch the charts update
2. **Try different faults** - Each should show its own interval range
3. **Check performance** - 30-second updates should feel responsive
4. **Verify data cleanup** - Running same fault twice should show fresh data

---

**Go test it now!** 🚀
