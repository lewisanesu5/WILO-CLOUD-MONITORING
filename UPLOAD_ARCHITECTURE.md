# Remote Sensor File Upload - Architecture & Recommendations

## Overview
Architecture for remote servers to upload sensor CSV files (max/min pairs) to the Predictive Maintenance system every 2 hours.

---

## ✅ Implementation Details

### 1. **Secure Upload Endpoint**
```
POST /api/upload
Headers: X-API-Key: sk_prod_xxxxxxxxxxxxxxxx
Body: multipart/form-data with 2 files
Response: 201 (success) | 400 (validation) | 401 (auth) | 413 (size)
```

**Features Implemented:**
- ✓ API key authentication (per sensor)
- ✓ CSV format validation (headers, data rows)
- ✓ File size limits (10 MB max)
- ✓ Filename pattern validation (max_<sensor>.csv, min_<sensor>.csv)
- ✓ Upload logging and audit trail
- ✓ Batch upload validation (expects exactly 2 files)
- ✓ Detailed validation reports

### 2. **Upload Monitor Endpoint**
```
GET /api/upload/status
Response: Upload history, sensor stats, last uploads
```

**Allows:**
- View last 50 upload events
- Track upload frequency per sensor
- Identify failed uploads
- Monitor compliance with 2-hour schedule

---

## 📋 Recommendations

### **A. Upload Frequency & Timing**

| Parameter | Recommendation | Rationale |
|-----------|---|---|
| **Interval** | Every 2 hours (120 min) | Provides 36 data uploads/day = 72 total files |
| **Buffer** | 5-10 min tolerance | Network delays, processing time |
| **Best Time** | Avoid peak hours | Off-peak network (e.g., 2am, 4am, 6am) |
| **Timezone** | UTC recommended | Eliminates DST issues |
| **Retry Window** | +30 min after miss | 5-min retry intervals (exponential backoff) |

**Schedule Example:**
```
06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00, 00:00, 02:00, 04:00
```

### **B. Authentication & Security**

#### API Key Management
```python
# Store per-sensor unique keys (rotate monthly)
UPLOAD_API_KEYS = {
    'sensor-001': 'sk_prod_7f3b8e2a9c1d4f6e5a2b9c8d7e1f3a5b',
    'sensor-002': 'sk_prod_2c5d8f1a4e7b9a3d6f2e5c8b1a4d7f3e',
    'sensor-003': 'sk_prod_xxxxx...'
}
```

#### Production Security Checklist
- [ ] **HTTPS Only**: Use TLS 1.3 (never HTTP in production)
- [ ] **Certificate Pinning**: Client validates server certificate
- [ ] **Rate Limiting**: Max 20 uploads/day per sensor (prevent abuse)
- [ ] **IP Whitelisting**: Only allow known sensor IPs
- [ ] **Request Signing**: Include HMAC-SHA256 signature
- [ ] **Key Rotation**: Monthly expiration, auto-renewal before expiry
- [ ] **Audit Logging**: All upload attempts (success/failure)
- [ ] **Alert on Anomalies**: Missing uploads after 150 min

#### Request Signing Example
```python
import hmac
import hashlib

def sign_request(api_key, timestamp, file_hash):
    message = f"{timestamp}:{file_hash}"
    signature = hmac.new(
        api_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature
```

### **C. File Transfer Protocol**

#### Protocol Options

| Protocol | Pros | Cons | Recommendation |
|----------|------|------|---|
| **HTTP POST** (current) | Simple, standard | No built-in compression | ✓ For <5 Mbps |
| **HTTP + Gzip** | Reduces size 80-90% | Minimal overhead | ✓ For <1 Mbps |
| **SFTP** | Secure, resume support | Requires SSH setup | For high-volume |
| **S3/Azure Blob** | Scalable, CDN | Cloud dependency | For distributed |

#### Recommended: HTTP POST + Gzip Compression
```python
# Client-side compression
import gzip

with open('max_acceleration.csv', 'rb') as f:
    compressed = gzip.compress(f.read())

files = [('files', ('max_acceleration.csv.gz', compressed, 'text/csv'))]
```

#### File Size Estimates
```
Per sensor, 2-second sample (700 Hz, 1400 points):
- CSV size: ~50 KB (timestamp + value per line)
- Gzipped: ~5-8 KB (85-90% compression)
- 6 files per batch: ~40 KB total
- Upload time @1Mbps: ~0.3 seconds
```

### **D. Retry Strategy**

#### Exponential Backoff
```python
# Retry schedule on failure
Attempt 1: Immediate
Attempt 2: Wait 5 seconds
Attempt 3: Wait 10 seconds
Max 3 attempts, then alert
```

#### Network Resilience
- **Connection Timeout**: 30 seconds
- **Read Timeout**: 60 seconds
- **Retry Backoff**: 5s, 10s, 20s (exponential)
- **Total Retry Window**: ~35 seconds
- **Local Queue**: Store failed uploads locally for manual retry

#### Pseudo-Code
```python
for attempt in range(3):
    try:
        response = post(url, files, timeout=30)
        if response.status_code == 201:
            return success
    except (Timeout, ConnectionError):
        wait(5 * (2 ** attempt))
    else:
        return failure
```

### **E. Monitoring & Alerting**

#### Key Metrics to Track
```
1. Upload Success Rate: >95% (alert if <90%)
2. Upload Latency: <5 seconds (alert if >10s)
3. File Size Variance: ±20% of baseline (detect anomalies)
4. Failed Uploads: Alert after 2 consecutive misses
5. CSV Validation Errors: Alert on format issues
```

#### Alert Conditions
- ⚠️ **Warning**: Upload missed (>130 min without upload)
- 🔴 **Critical**: 2 consecutive misses (>260 min gap)
- 🔴 **Critical**: CSV validation failure (format error)
- ⚠️ **Warning**: Upload latency >10 seconds

#### Example Alert Format
```json
{
  "alert_type": "UPLOAD_MISSED",
  "sensor_id": "sensor-001",
  "last_upload": "2026-06-02T12:00:00Z",
  "expected_upload": "2026-06-02T14:00:00Z",
  "delay_minutes": 135,
  "action": "Verify sensor network connectivity"
}
```

### **F. Data Validation Pipeline**

#### Server-Side Validation
```
1. ✓ File exists & readable
2. ✓ File size 1 KB - 10 MB
3. ✓ CSV headers present (timestamp, value)
4. ✓ Data rows > 1000 (1400 expected)
5. ✓ Timestamp format ISO 8601
6. ✓ Values numeric (float/int)
7. ✓ No duplicate timestamps
8. ✓ Monotonic timestamp progression
```

#### Client-Side Pre-Validation
```python
def validate_before_upload(filepath):
    # Check file size
    if not (1000 < size < 10_000_000):
        return False
    
    # Check row count
    if not (1300 < row_count < 1500):
        return False
    
    # Check timestamp sequence
    if not is_monotonic(timestamps):
        return False
    
    return True
```

### **G. Scheduling Approaches**

#### Option 1: Cron Job (Linux/Mac)
```bash
# Every 2 hours
0 */2 * * * /usr/bin/python3 /opt/uploader/remote_client_uploader.py
```

#### Option 2: Windows Task Scheduler
```
Task: Sensor Upload
Trigger: Every 2 hours starting 06:00
Action: python remote_client_uploader.py
Retry: 3 times @ 5-min intervals on failure
```

#### Option 3: Systemd Service (Linux)
```ini
[Unit]
Description=Sensor Data Upload Service
After=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/uploader/remote_client_uploader.py
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

#### Option 4: Docker Container
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY remote_client_uploader.py .
RUN pip install requests schedule
CMD ["python", "remote_client_uploader.py"]
```

```yaml
# docker-compose.yml
version: '3.9'
services:
  sensor-uploader:
    build: .
    environment:
      - SERVER_URL=http://maintenance-server:5001
      - API_KEY=${SENSOR_API_KEY}
      - SENSOR_ID=sensor-001
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### **H. Testing Strategy**

#### Step 1: Local Endpoint Test
```bash
# Test upload endpoint
curl -X POST http://localhost:5001/api/upload \
  -H "X-API-Key: sk_prod_7f3b8e2a9c1d4f6e5a2b9c8d7e1f3a5b" \
  -F "files=@max_acceleration.csv" \
  -F "files=@min_acceleration.csv"
```

#### Step 2: Client Script Test (Immediate)
```python
# Uncomment in remote_client_uploader.py
client = RemoteUploadClient(SERVER_URL, API_KEY, SENSOR_ID)
client.upload_all_sensors()
```

#### Step 3: Network Delay Simulation
```bash
# Linux: Simulate 500ms latency
sudo tc qdisc add dev eth0 root netem delay 500ms

# Test with delay
python remote_client_uploader.py
```

#### Step 4: Failure Scenarios
- [ ] Simulate network disconnect (turn off WiFi mid-upload)
- [ ] Simulate corrupted CSV (remove header row)
- [ ] Simulate file size exceeding limit
- [ ] Simulate invalid API key
- [ ] Simulate server timeout (stop server)

### **I. Production Deployment Checklist**

#### Pre-Deployment
- [ ] HTTPS enabled on server (SSL certificate valid)
- [ ] API keys generated and distributed
- [ ] Client script configured with correct SERVER_URL
- [ ] Upload directory permissions verified (755)
- [ ] Logging configured and rotated
- [ ] Database connection pool sized
- [ ] Rate limiting implemented and tested

#### Post-Deployment
- [ ] Monitor first 24 uploads for success
- [ ] Verify upload latency baseline (<5 sec)
- [ ] Confirm data integrity (file counts match)
- [ ] Test alert notifications
- [ ] Document API keys securely (vault, secrets manager)
- [ ] Set up monitoring dashboard

---

## 📊 Bandwidth & Storage Estimation

### Data Flow per 2-Hour Cycle
```
Sensors: 3 (acceleration, current, audio)
Files per sensor: 2 (max, min)
Total files per batch: 6

Per file (2-second sample):
- Raw CSV: ~50 KB
- Compressed (gzip): ~6 KB
- 
Per batch:
- Uncompressed: 300 KB
- Compressed: 36 KB

Upload time @1 Mbps: 0.3 seconds
Upload time @100 Kbps: 3 seconds
```

### Daily Storage Growth
```
Per day (12 uploads/day):
- Uncompressed: 3.6 MB
- With Gzip: 0.43 MB

Per month (30 days):
- Uncompressed: 108 MB
- With Gzip: 13 MB

Per year:
- Uncompressed: 1.31 GB
- With Gzip: 156 MB
```

---

## 🔧 Implementation Checklist

### Backend (Server)
- [x] POST /api/upload endpoint
- [x] API key authentication
- [x] CSV validation
- [x] File size limits
- [x] Upload logging
- [x] GET /api/upload/status monitoring
- [ ] Rate limiting middleware
- [ ] HTTPS setup
- [ ] Alert system integration
- [ ] Database cleanup (old files archival)

### Client
- [x] Remote upload script (remote_client_uploader.py)
- [x] Retry logic with exponential backoff
- [x] Scheduler integration
- [ ] Pre-upload validation
- [ ] Request signing (HMAC)
- [ ] Gzip compression
- [ ] Local queue for failed uploads
- [ ] Health check before upload

### Operations
- [ ] Cron/Task Scheduler setup
- [ ] Monitoring dashboard
- [ ] Alert notifications
- [ ] Documentation
- [ ] Key rotation process
- [ ] Disaster recovery plan
- [ ] API key secure storage

---

## 🚨 Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Wrong/expired API key | Verify key in header matches config |
| 400 Bad Request | Wrong filename format | Use: max_<sensor>.csv, min_<sensor>.csv |
| 413 Payload Too Large | File >10 MB | Check for duplicate/corrupted data |
| Connection Timeout | Network latency | Increase timeout to 60s, use gzip |
| Duplicate Uploads | Client retrying too fast | Implement idempotency (checksums) |
| Missing Uploads | Scheduler not running | Verify cron job, check process logs |

---

## 📞 Support & Monitoring

### Access Logs
```bash
# Check last 20 uploads
curl http://localhost:5001/api/upload/status | jq '.recent_uploads[-20:]'

# View upload history
tail -100 UploadLogs/upload_history.log
```

### Debug Commands
```bash
# Test connectivity
ping maintenance-server

# Verify endpoint
curl -v http://localhost:5001/health

# Check port
netstat -an | grep 5001
```

---

## References
- RFC 7578: multipart/form-data
- RFC 8018: PBKDF2 (password-based encryption)
- OWASP API Security Top 10
