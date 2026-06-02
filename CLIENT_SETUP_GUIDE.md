# Quick Start Guide: Remote Sensor Upload

## 📋 Table of Contents
1. [Server Setup](#server-setup)
2. [Client Setup](#client-setup)
3. [Testing](#testing)
4. [Deployment](#deployment)
5. [Troubleshooting](#troubleshooting)

---

## Server Setup

### Step 1: Enable Upload Endpoint
The server already has the secure upload endpoint configured. Verify it's working:

```bash
# Check if server is running
curl http://localhost:5001/health

# Should return:
# {"status": "ok"}
```

### Step 2: Generate API Keys
Contact your administrator to get:
- Server URL (e.g., `http://maintenance-server:5001`)
- API Key (e.g., `sk_prod_7f3b8e2a9c1d4f6e5a2b9c8d7e1f3a5b`)
- Sensor ID (e.g., `sensor-001`)

### Step 3: Verify Upload Directory
```bash
# Check upload logs directory exists
ls -la UploadLogs/

# Should contain:
# - upload_history.log (audit trail)
```

---

## Client Setup (Remote Sensor)

### Step 1: Install Dependencies
```bash
# Clone or download the client script
cd /opt/sensor-uploader/

# Install Python packages
pip install -r client_requirements.txt
```

**Required packages:**
- requests (HTTP client)
- schedule (cron-like scheduling)
- python-dotenv (configuration)

### Step 2: Configure Client
```bash
# Copy environment template
cp .env.example .env

# Edit with your settings
nano .env
```

**Edit these values:**
```
SERVER_URL=http://your-server-ip:5001
API_KEY=sk_prod_xxxxxxxxxxxxxxxx
SENSOR_ID=sensor-001
LOCAL_DATA_DIR=/path/to/csv/files
```

### Step 3: Verify File Structure
```bash
# Your sensor should generate these files every 2 seconds:
ls -la /path/to/csv/files/

# Expected files:
# max_acceleration.csv
# min_acceleration.csv
# max_current.csv
# min_current.csv
# max_audio.csv
# min_audio.csv
```

---

## Testing

### Test 1: Local Connectivity
```bash
# Verify server is reachable
curl -v http://localhost:5001/health
```

Expected response (201 status):
```json
{"status": "ok"}
```

### Test 2: API Key Authentication
```bash
# Test with correct API key
curl -X POST http://localhost:5001/api/upload \
  -H "X-API-Key: sk_prod_7f3b8e2a9c1d4f6e5a2b9c8d7e1f3a5b" \
  -F "files=@max_acceleration.csv" \
  -F "files=@min_acceleration.csv"
```

Expected response (201 status):
```json
{
  "status": "success",
  "message": "Uploaded 2 file(s)",
  "sensor_id": "sensor-001",
  "files": ["max_acceleration.csv", "min_acceleration.csv"],
  "timestamp": "2026-06-02T12:00:00.000000",
  "validation_report": [
    {
      "file": "max_acceleration.csv",
      "rows": 1400,
      "size_kb": 52.3,
      "status": "success"
    },
    {
      "file": "min_acceleration.csv",
      "rows": 1400,
      "size_kb": 51.8,
      "status": "success"
    }
  ],
  "next_expected_upload": "2026-06-02T14:00:00.000000"
}
```

### Test 3: Invalid API Key (Should Fail)
```bash
# Test with wrong API key
curl -X POST http://localhost:5001/api/upload \
  -H "X-API-Key: invalid-key-12345" \
  -F "files=@max_acceleration.csv"
```

Expected response (403 status):
```json
{"status": "error", "message": "Invalid API key"}
```

### Test 4: Missing Files (Should Fail)
```bash
# Upload only 1 file instead of 2
curl -X POST http://localhost:5001/api/upload \
  -H "X-API-Key: sk_prod_..." \
  -F "files=@max_acceleration.csv"
```

Expected response (400 status):
```json
{"error": "Expected 2 files, got 1"}
```

### Test 5: Run Client Script (Immediate Upload)
```bash
# Edit remote_client_uploader.py - uncomment test section:
# if __name__ == '__main__':
#     client = RemoteUploadClient(SERVER_URL, API_KEY, SENSOR_ID)
#     client.upload_all_sensors()

python remote_client_uploader.py

# Expected output:
# ==================================================
# Starting upload batch at 2026-06-02 12:00:00
# ==================================================
# Uploading acceleration batch (attempt 1/3)
# ✓ Upload successful: {'status': 'success', ...}
# ...
```

### Test 6: Check Upload Status
```bash
# View upload history and sensor stats
curl http://localhost:5001/api/upload/status | jq

# Expected output:
{
  "status": "success",
  "total_uploads": 15,
  "sensor_stats": {
    "sensor-001": {
      "count": 5,
      "last_upload": "2026-06-02T12:00:00"
    }
  },
  "recent_uploads": [...]
}
```

---

## Deployment

### Option 1: Linux Cron Job (Simple)
```bash
# Edit crontab
crontab -e

# Add this line to run every 2 hours at :00 minute
0 */2 * * * cd /opt/sensor-uploader && /usr/bin/python3 remote_client_uploader.py >> /var/log/sensor-upload.log 2>&1

# Verify cron job
crontab -l
```

### Option 2: Linux Systemd Service (Recommended)
```bash
# Create service file
sudo nano /etc/systemd/system/sensor-uploader.service
```

**File content:**
```ini
[Unit]
Description=Sensor Data Upload Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=sensoruser
WorkingDirectory=/opt/sensor-uploader
ExecStart=/usr/bin/python3 /opt/sensor-uploader/remote_client_uploader.py
Restart=always
RestartSec=60
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable sensor-uploader
sudo systemctl start sensor-uploader

# Check status
sudo systemctl status sensor-uploader

# View logs
sudo journalctl -u sensor-uploader -f
```

### Option 3: Windows Task Scheduler
```powershell
# Create scheduled task
$action = New-ScheduledTaskAction -Execute "C:\Python312\python.exe" `
  -Argument "C:\sensor-uploader\remote_client_uploader.py"

$trigger = New-ScheduledTaskTrigger -At 06:00 -RepetitionInterval (New-TimeSpan -Hours 2) -RepetitionDuration (New-TimeSpan -Days 365)

Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "SensorUpload" -Description "Upload sensor files every 2 hours"
```

### Option 4: Docker Deployment
```bash
# Build container
docker build -t sensor-uploader:1.0 .

# Run container
docker run -d \
  --name sensor-uploader \
  --restart always \
  -e SERVER_URL=http://maintenance-server:5001 \
  -e API_KEY=sk_prod_... \
  -v /path/to/sensor/data:/app/sensor_data \
  sensor-uploader:1.0

# Check logs
docker logs -f sensor-uploader
```

---

## Troubleshooting

### Issue: "Connection refused"
```
Error: Failed to connect to http://localhost:5001
```

**Solution:**
1. Verify server is running: `curl http://localhost:5001/health`
2. Check firewall: `sudo ufw allow 5001`
3. Verify correct SERVER_URL in .env

### Issue: "Authentication failed: Invalid API key"
```
Error: 403 Forbidden - Invalid API key
```

**Solution:**
1. Verify API_KEY in .env matches your assigned key
2. Check for trailing/leading spaces
3. Request new key from admin if expired

### Issue: "Expected 2 files, got 1"
```
Error: 400 Bad Request - Expected 2 files, got 2
```

**Solution:**
1. Ensure max_<sensor>.csv AND min_<sensor>.csv both exist
2. Verify filenames exactly match the pattern
3. Check LOCAL_DATA_DIR path is correct

### Issue: "Upload hangs/timeout"
```
Error: Connection timeout after 30 seconds
```

**Solution:**
1. Check network latency: `ping maintenance-server`
2. Enable compression: `USE_COMPRESSION=true` in .env
3. Increase timeout: `CONNECTION_TIMEOUT=60` in code
4. Check server logs for errors

### Issue: "No data directory or missing files"
```
Error: Files not found for acceleration
```

**Solution:**
```bash
# Verify data directory
ls -la $LOCAL_DATA_DIR

# Should contain 6 files:
ls $LOCAL_DATA_DIR | grep -E "max_|min_"

# If missing, check sensor data generation process
```

### Issue: "CSV validation failed: Invalid data row"
```
Error: Invalid data row: timestamp,value,extra_field
```

**Solution:**
1. Verify CSV has exactly 2 columns: timestamp, value
2. Remove extra columns from generation process
3. Check timestamp format is ISO 8601

### Debug Logging
```bash
# View client logs in real-time
tail -f upload_client.log

# View server logs
tail -f /var/log/flask_app.log

# Check server upload history
curl http://localhost:5001/api/upload/status | jq '.recent_uploads[-5:]'
```

---

## Monitoring Checklist

Daily:
- [ ] Check upload_client.log for errors
- [ ] Verify last upload timestamp is within 130 minutes
- [ ] Monitor upload success rate (>95%)

Weekly:
- [ ] Review API quota usage
- [ ] Check storage growth (expect ~10 MB/week)
- [ ] Audit access logs

Monthly:
- [ ] Rotate API keys (if policy requires)
- [ ] Archive old upload logs
- [ ] Performance review (latency, success rate)

---

## Support Contacts
- **Server Admin**: admin@example.com
- **Network Team**: network@example.com
- **Monitoring**: ops@example.com
