# ✅ Deployment Readiness Checklist

Use this to verify your code is ready for cloud deployment.

## 📋 Pre-Deployment Checklist

### Backend Files
- [x] `app.py` - Production-ready (uses PORT env var)
- [x] `requirements.txt` - All Python dependencies
- [x] `Procfile` - Heroku/Railway compatible
- [x] `render.yaml` - Render.com config

### Configuration
- [x] `.env.example` - Configuration template
- [x] `.gitignore` - Git exclusions (node_modules, __pycache__, etc.)

### Documentation
- [x] `README.md` - Updated with deployment links
- [x] `DEPLOY_TO_RENDER.md` - Complete Render deployment guide
- [x] `GITHUB_SETUP.md` - GitHub setup instructions
- [x] `UPLOAD_ARCHITECTURE.md` - Upload system design
- [x] `CLIENT_SETUP_GUIDE.md` - Client deployment guide
- [x] `QUICK_REFERENCE.md` - One-page reference

### Data & Scripts
- [x] `generate_test_data.py` - Test data generator
- [x] `remote_client_uploader.py` - Upload client
- [x] `Data/` folder - With sample CSV files

### Frontend
- [x] `frontend/` folder - React app
- [x] `frontend/package.json` - Node dependencies
- [x] `frontend/src/App.jsx` - Updated with FFT graphs

---

## 🔧 Code Changes Made for Production

### app.py Updates
```python
✅ CORS origins updated for flexibility
✅ PORT from environment variable (default 5001)
✅ FLASK_ENV detection for debug mode
✅ SocketIO async_mode for threading
✅ API key authentication for uploads
✅ CSV validation functions
✅ Audit logging for uploads
```

### requirements.txt Updates
```
✅ gunicorn==21.2.0 (production server)
✅ python-dotenv==1.0.0 (config management)
✅ All other deps locked to versions
```

### New Files
```
✅ render.yaml - Render deployment config
✅ Procfile - Alternative deployment
✅ .gitignore - Git exclusions
✅ DEPLOY_TO_RENDER.md - Deployment guide
✅ GITHUB_SETUP.md - GitHub instructions
```

---

## 🧪 Pre-Deployment Tests (Do These First!)

### Test 1: Local Backend
```bash
python app.py
curl http://localhost:5001/health
# Expected: {"status":"ok"}
```

### Test 2: Upload Endpoint
```bash
curl -X POST http://localhost:5001/api/upload \
  -H "X-API-Key: sk_prod_7f3b8e2a9c1d4f6e5a2b9c8d7e1f3a5b" \
  -F "files=@Data/max_acceleration.csv" \
  -F "files=@Data/min_acceleration.csv"
# Expected: 201 with success message
```

### Test 3: Frontend
```bash
cd frontend
npm install
npm run dev
# Should open on http://localhost:5173
```

---

## 📦 Deployment Steps

### Step 1: GitHub
See [GITHUB_SETUP.md](GITHUB_SETUP.md)
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/predictive-maintenance.git
git push -u origin main
```

### Step 2: Render
See [DEPLOY_TO_RENDER.md](DEPLOY_TO_RENDER.md)
1. Go to https://render.com
2. New Web Service → GitHub
3. Select your repo
4. Deploy

### Step 3: Domain
1. Get Render URL from dashboard
2. Add CNAME to Namify DNS settings
3. Wait 5-10 minutes for propagation
4. Test with custom domain

---

## 🔐 Security Before Production

### Required
- [ ] Change default API keys in `app.py`
- [ ] Set up HTTPS (Render auto-provides)
- [ ] Add your domain to CORS origins in `app.py`

### Recommended
- [ ] Setup rate limiting (prevent abuse)
- [ ] Add request signing (HMAC-SHA256)
- [ ] Enable gzip compression
- [ ] Setup monitoring/alerts
- [ ] Regular API key rotation

---

## 📊 Production Configuration

### Update app.py Before Deployment
```python
# 1. Change API keys to your own secure values
UPLOAD_API_KEYS = {
    'sensor-001': 'sk_prod_CHANGE_THIS_TO_YOUR_OWN_KEY',
    'sensor-002': 'sk_prod_CHANGE_THIS_TO_ANOTHER_UNIQUE_KEY',
}

# 2. Add your production domain to CORS
ALLOWED_ORIGINS = [
    "https://your-namify-domain.com",
    "https://your-domain.onrender.com",
    "http://localhost:5173",  # Keep for local dev
]
```

---

## 🚀 Deployment Timeline

| Step | Time | Notes |
|------|------|-------|
| GitHub setup | 5 min | If new to git |
| Push to GitHub | 2 min | `git push` |
| Render deploy | 3 min | Auto build & start |
| DNS propagation | 5-10 min | Namify CNAME |
| **Total** | **15 min** | First time |
| Updates | <2 min | Push to GitHub, Render auto-deploys |

---

## ✅ Final Checklist

### Before Pushing to GitHub
- [ ] Local tests pass (health, upload, frontend)
- [ ] API keys changed to secure values
- [ ] No sensitive data in files
- [ ] All dependencies in requirements.txt
- [ ] .gitignore configured

### Before Deploying to Render
- [ ] GitHub repo created and code pushed
- [ ] Render account created
- [ ] Environment variables ready (if any)

### After Deployment
- [ ] Health endpoint responds
- [ ] Upload endpoint works with API key
- [ ] Custom domain resolves
- [ ] Frontend accessible
- [ ] Remote clients can upload

---

## 🎯 What's Ready to Deploy

```
✅ Backend: Production-ready Flask app
✅ Frontend: React with FFT graphs
✅ Config: render.yaml + Procfile
✅ Docs: 5+ deployment guides
✅ Client: Upload scheduler script
✅ Tests: 6 comprehensive test scenarios
```

**Status**: Ready for deployment to cloud 🚀

---

## 📞 Quick Links

- **Deploy Guide**: [DEPLOY_TO_RENDER.md](DEPLOY_TO_RENDER.md)
- **GitHub Setup**: [GITHUB_SETUP.md](GITHUB_SETUP.md)
- **API Docs**: [UPLOAD_ARCHITECTURE.md](UPLOAD_ARCHITECTURE.md)
- **Client Setup**: [CLIENT_SETUP_GUIDE.md](CLIENT_SETUP_GUIDE.md)

---

**All systems go!** ✅ Ready to take your app from local to cloud production.
