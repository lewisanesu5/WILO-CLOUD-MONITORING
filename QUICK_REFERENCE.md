# 🚀 Remote Sensor Upload - Quick Reference

## What You Get

```
REMOTE SENSOR SITE              PREDICTIVE MAINTENANCE SERVER
─────────────────────────       ──────────────────────────────

Motor + Sensors ──┐
                  ├─→ CSV Files (6/batch)
Generation Script ┘
     ↓ Every 2 hrs
     
Upload Client ────────HTTP POST──→ POST /api/upload
  • Validates CSV          ↓ Secure Upload
  • Retries 3x        GET /api/upload/status
  • Logs results      ↓
                 ┌────────────────────┐
                 │ Data Storage       │
                 │ + Upload Logs      │
                 │ + Audit Trail      │
                 └────────────────────┘
                       ↓
                  Frontend UI
                  (FFT Graphs)
```

---

## 📋 One-Page Setup

### Server (Already Done)
```bash
# Running on http://localhost:5001
python app.py
```

### Client Setup (3 Steps)
```bash
# 1. Copy config
cp .env.example .env

# 2. Edit .env with server URL and API key
nano .env
# SERVER_URL=http://your-server:5001
# API_KEY=sk_prod_xxxxx

# 3. Install and run
pip install -r client_requirements.txt
python remote_client_uploader.py
```

---

## 🔐 API Reference

### Upload Files
```bash
curl -X POST http://localhost:5001/api/upload \
  -H "X-API-Key: sk_prod_7f3b8e2a9c1d4f6e5a2b9c8d7e1f3a5b" \
  -F "files=@max_acceleration.csv" \
  -F "files=@min_acceleration.csv"
```

**Response (201):**
```json
{
  "status": "success",
  "files": ["max_acceleration.csv", "min_acceleration.csv"],
  "timestamp": "2026-06-02T12:00:00",
  "validation_report": [
    {"file": "max_acceleration.csv", "rows": 1400, "size_kb": 52.3, "status": "success"}
  ]
}
```

### Check Status
```bash
curl http://localhost:5001/api/upload/status
```

---

## ⏰ Upload Schedule

```
Every 2 Hours (12x daily):

06:00 ──→ 08:00 ──→ 10:00 ──→ 12:00 ──→ 14:00 ──→ 16:00
        │              │              │              │
      +2h            +2h            +2h            +2h
      
       ↓              ↓              ↓              ↓
     18:00 ──→ 20:00 ──→ 22:00 ──→ 00:00 ──→ 02:00 ──→ 04:00
```

### Monitoring Rules
| Condition | Alert | Action |
|-----------|-------|--------|
| No upload >150 min | ⚠️ Warning | Check network |
| No upload >270 min (2x) | 🔴 Critical | Restart service |
| CSV validation fail | 🔴 Critical | Check format |
| Upload latency >10s | ⚠️ Warning | Check bandwidth |

---

## 📊 Data Efficiency

| Metric | Value |
|--------|-------|
| Per batch (6 files) | 300 KB raw, 36 KB gzipped |
| Daily (12 uploads) | 3.6 MB raw, 0.43 MB gzipped |
| Monthly | 108 MB raw, 13 MB gzipped |
| Yearly | 1.3 GB raw, 156 MB gzipped |
| Upload time @1Mbps | 0.3 seconds |

---

## 🛠️ Deployment Options

### Linux (Recommended: Systemd)
```bash
sudo nano /etc/systemd/system/sensor-uploader.service
# [Service]
# ExecStart=/usr/bin/python3 /opt/uploader/remote_client_uploader.py
# Restart=always

sudo systemctl enable sensor-uploader
sudo systemctl start sensor-uploader
```

### Windows
```powershell
# Task Scheduler: Create task
# Trigger: Every 2 hours starting 06:00
# Action: C:\Python312\python.exe C:\uploader\remote_client_uploader.py
```

### Docker
```bash
docker build -t uploader .
docker run -d --name uploader \
  -e SERVER_URL=http://server:5001 \
  -e API_KEY=sk_prod_... \
  uploader
```

---

## ✅ Testing Checklist

- [ ] **Health Check**: `curl http://localhost:5001/health`
- [ ] **Valid Key**: Upload with correct API key → 201
- [ ] **Invalid Key**: Upload with wrong key → 403
- [ ] **Missing Files**: Upload 1 file instead of 2 → 400
- [ ] **Bad CSV**: Upload with wrong columns → 400
- [ ] **Check Status**: `curl /api/upload/status` → shows history
- [ ] **Client Run**: `python remote_client_uploader.py` → all 6 files uploaded

---

## 📁 Files Provided

### Core
- `app.py` - Backend with upload endpoints
- `remote_client_uploader.py` - Client scheduler
- `client_requirements.txt` - Dependencies

### Config
- `.env.example` - Configuration template

### Documentation
- `UPLOAD_ARCHITECTURE.md` - Full technical spec (15+ pages)
- `CLIENT_SETUP_GUIDE.md` - Step-by-step guide (10+ pages)
- `IMPLEMENTATION_SUMMARY.md` - Overview with diagrams

### Testing
- `test_upload_endpoint.bat` - 4 test scenarios

---

## 🔒 Security Keys

### Production Setup
```python
UPLOAD_API_KEYS = {
    'sensor-001': 'sk_prod_7f3b8e2a9c1d4f6e5a2b9c8d7e1f3a5b',
    'sensor-002': 'sk_prod_2c5d8f1a4e7b9a3d6f2e5c8b1a4d7f3e',
    'sensor-003': 'sk_prod_xxxxx...'
}
```

### Key Rotation
- Monthly expiration recommended
- Generate new keys before expiry
- Update all clients before deactivating old keys

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| 401 Unauthorized | Check API key in .env |
| 400 Bad Request | Verify filenames are `max_<sensor>.csv`, `min_<sensor>.csv` |
| Connection refused | Check server running: `curl http://localhost:5001/health` |
| Timeout | Increase timeout to 60s, use gzip compression |
| Missing uploads | Verify cron job: `crontab -l` |

---

## 📊 Monitoring Commands

```bash
# View recent uploads
curl http://localhost:5001/api/upload/status | jq '.recent_uploads[-10:]'

# Check client logs
tail -f upload_client.log

# View server logs
tail -f /var/log/flask_app.log

# Disk usage
du -sh UploadLogs/ Data/
```

---

## 🎯 Next Steps (Optional Enhancements)

1. **HTTPS** - Add SSL certificates for production
2. **Compression** - Enable gzip to reduce bandwidth 90%
3. **Rate Limiting** - Prevent abuse (max 20 uploads/day)
4. **Alerts** - Integrate Slack/email notifications
5. **Dashboard** - Add Grafana monitoring
6. **Backup** - Auto-archive old files monthly

---

## 📞 Documentation Links

- **Full Architecture**: See `UPLOAD_ARCHITECTURE.md`
- **Setup Instructions**: See `CLIENT_SETUP_GUIDE.md`
- **Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`
- **API Examples**: See examples throughout this document

---

## 🚀 Start Now

```bash
# 1. Verify backend running
curl http://localhost:5001/health

# 2. Configure client
cp .env.example .env
nano .env  # Edit SERVER_URL and API_KEY

# 3. Test immediate upload
python remote_client_uploader.py

# 4. Schedule production run (Cron/Systemd/Docker)
# See CLIENT_SETUP_GUIDE.md for your platform
```

**Backend**: ✅ Running on port 5001
**Client**: ✅ Ready to deploy
**Docs**: ✅ Complete and comprehensive

---

Generated: 2026-06-02 | Version: 1.0
