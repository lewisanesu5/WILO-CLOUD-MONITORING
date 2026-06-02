# Deploy to Render (Free)

## Quick Start (5 Minutes)

### 1. Prepare for GitHub
```bash
cd C:\Users\DELL\OneDrive\Desktop\wilo2\Wilo-Cloud-Monitoring

# Initialize git repo
git init
git add .
git commit -m "Initial commit - Predictive Maintenance System"
git branch -M main
```

### 2. Create GitHub Repository
1. Go to **https://github.com/new**
2. Name: `predictive-maintenance`
3. Click **Create repository**
4. Copy the commands and run in terminal:

```bash
git remote add origin https://github.com/YOUR-USERNAME/predictive-maintenance.git
git push -u origin main
```

### 3. Deploy on Render.com
1. Go to **https://render.com** (sign up for free)
2. Click **+ New** → **Web Service**
3. Select **GitHub** (connect your account)
4. Search for `predictive-maintenance` repo
5. Click **Connect**
6. Fill in settings:
   - **Name**: `predictive-maintenance`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
7. Click **Create Web Service**

**Wait 2-3 minutes for deployment** ✅

### 4. Get Your Live URL
After deployment, Render will show:
```
Your service is live at: https://predictive-maintenance-xxxx.onrender.com
```

---

## Add Your Namify Domain

### 1. In Render Dashboard
1. Go to your service settings
2. Click **Custom Domain** → **Add Custom Domain**
3. Enter your Namify domain (e.g., `maintenance.yoursite.com`)

### 2. In Namify Panel
1. Go to your domain's **DNS Settings**
2. Add **CNAME** record:
   - **Name**: `maintenance` (or your subdomain)
   - **Value**: `predictive-maintenance-xxxx.onrender.com` (from Render)
3. Save and wait 5-10 minutes for DNS propagation

### 3. Test It
```bash
# Should work within 5 minutes
curl https://maintenance.yoursite.com/health
# Should return: {"status":"ok"}
```

---

## Update Client Configuration

### For Remote Sensors
Edit `remote_client_uploader.py`:
```python
SERVER_URL = 'https://maintenance.yoursite.com'  # Your domain
API_KEY = 'sk_prod_7f3b8e2a9c1d4f6e5a2b9c8d7e1f3a5b'
```

Or in `.env`:
```
SERVER_URL=https://maintenance.yoursite.com
API_KEY=sk_prod_7f3b8e2a9c1d4f6e5a2b9c8d7e1f3a5b
```

---

## What's Included for Deployment

✅ **requirements.txt** - All Python dependencies  
✅ **Procfile** - For Heroku/Railway (if you switch later)  
✅ **render.yaml** - Render-specific config  
✅ **app.py** - Updated for production (uses PORT env var)  
✅ **.gitignore** - Excludes unnecessary files  

---

## Files Ready to Deploy

```
predictive-maintenance/
├── app.py                    ✅ Production-ready
├── requirements.txt          ✅ All deps included
├── render.yaml              ✅ Render config
├── Procfile                 ✅ Alternative config
├── .gitignore               ✅ Git exclusions
├── .env.example             ✅ Config template
├── remote_client_uploader.py ✅ Client script
├── generate_test_data.py    ✅ Test data generator
├── Data/
│   ├── max_*.csv
│   ├── min_*.csv
│   └── ...
└── frontend/
    ├── src/
    ├── package.json
    └── ...
```

---

## Test Deployment

After Render shows "Your service is live":

### Test Health Check
```bash
curl https://your-domain.com/health
# Expected: {"status":"ok"}
```

### Test Upload Endpoint
```bash
curl -X POST https://your-domain.com/api/upload \
  -H "X-API-Key: sk_prod_7f3b8e2a9c1d4f6e5a2b9c8d7e1f3a5b" \
  -F "files=@Data/max_acceleration.csv" \
  -F "files=@Data/min_acceleration.csv"
# Expected: 201 success response
```

### Test Status Endpoint
```bash
curl https://your-domain.com/api/upload/status
# Expected: JSON with upload history
```

---

## Troubleshooting

### "Service Build Failed"
Check the build logs in Render dashboard:
- Missing `requirements.txt` ✅ We have it
- Missing `app.py` ✅ We have it
- Python version issue → Render uses Python 3.12 by default

**Solution**: Click **Retry Deploy**

### "Custom Domain Not Working"
- DNS takes 5-10 minutes to propagate
- Check DNS records in Namify panel
- Make sure CNAME points to Render's address

**Solution**: Wait 10 minutes, clear browser cache, try again

### "Upload Returns 502 Error"
Indicates server crash. Check Render logs:
1. Click your service in Render
2. Go to **Logs** tab
3. Look for error messages

**Common causes**:
- Missing Data folder
- Permission issue with UploadLogs folder

**Solution**: Click **Retry Deploy** or push a fix to GitHub

### "CORS Error on Frontend"
Update the `ALLOWED_ORIGINS` in `app.py`:

```python
ALLOWED_ORIGINS = [
    "https://your-frontend-domain.com",
    "https://your-domain.com"
]
```

Then push to GitHub and Render auto-redeploys.

---

## Free Tier Limits (Render.com)

| Feature | Limit |
|---------|-------|
| **Requests/month** | Unlimited |
| **Bandwidth** | 100 GB/month |
| **CPU** | 0.1 shared |
| **RAM** | 512 MB |
| **Storage** | Ephemeral (resets on restart) |

**For persistent data**: Use Render's SQLite or PostgreSQL (optional)

---

## Making Changes After Deployment

### To Update Your Code:
```bash
# Make changes locally
nano app.py

# Push to GitHub
git add .
git commit -m "Fix upload validation"
git push origin main
```

Render automatically redeploys within 2 minutes! ✅

---

## Next Steps (Optional Enhancements)

- [ ] Add HTTPS certificate (Render auto-provides)
- [ ] Add database for permanent storage
- [ ] Setup monitoring alerts
- [ ] Add Slack notifications for uploads
- [ ] Custom email domain for errors

---

## Support

**Render.com Help**: https://render.com/docs  
**Namify DNS Help**: Your domain panel → Help/Support  
**Our API Docs**: See `UPLOAD_ARCHITECTURE.md`

---

## Summary

✅ Code is production-ready  
✅ All dependencies included  
✅ GitHub deployment configured  
✅ Render ready (no extra config needed)  
✅ Auto-redeploy on push enabled  
✅ Domain support included  

**Total setup time: ~10 minutes**  
**Cost: FREE** 🎉
