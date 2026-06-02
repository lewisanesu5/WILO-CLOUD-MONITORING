# GitHub Setup Guide

Quick instructions to push your code to GitHub and deploy.

## Step 1: Create GitHub Account (if you don't have one)

1. Go to **https://github.com/signup**
2. Create free account
3. Verify email

## Step 2: Install Git

### Windows
1. Download: **https://git-scm.com/download/win**
2. Run installer (use default settings)
3. Restart terminal/VS Code

Verify installation:
```bash
git --version
# Should show: git version 2.x.x
```

## Step 3: Configure Git

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@gmail.com"
```

## Step 4: Create Repository on GitHub

1. Go to **https://github.com/new**
2. Fill in:
   - **Repository name**: `predictive-maintenance`
   - **Description**: `Real-time sensor monitoring with FFT analysis`
   - **Public** (for easy sharing)
   - Click **Create repository**

3. GitHub will show you commands to run. Copy them.

## Step 5: Push Your Code

In terminal, navigate to your project:

```bash
cd C:\Users\DELL\OneDrive\Desktop\wilo2\Wilo-Cloud-Monitoring

# Initialize git repo
git init

# Add all files
git add .

# Create first commit
git commit -m "Initial commit - Predictive Maintenance System"

# Rename branch to main
git branch -M main

# Add remote (use the URL from your GitHub repo)
git remote add origin https://github.com/YOUR-USERNAME/predictive-maintenance.git

# Push to GitHub
git push -u origin main
```

**Replace `YOUR-USERNAME` with your actual GitHub username!**

## Step 6: Verify on GitHub

1. Go to **https://github.com/YOUR-USERNAME/predictive-maintenance**
2. Should see all your files there ✅

## Step 7: Deploy to Render

Now that code is on GitHub:
1. Go to **https://render.com**
2. Click **+ New** → **Web Service**
3. Select **GitHub** (connect account if prompted)
4. Search for `predictive-maintenance`
5. Click **Connect**
6. Set Build Command: `pip install -r requirements.txt`
7. Set Start Command: `gunicorn app:app`
8. Click **Create Web Service**

**Wait 2-3 minutes for deployment** ✅

## Making Changes Later

After you deploy, updating is easy:

```bash
# Make changes to files locally
nano app.py

# Push to GitHub
git add .
git commit -m "Fix upload validation"
git push origin main
```

Render automatically redeploys within 2 minutes! 🚀

## Common Git Commands

```bash
# Check status
git status

# See what changed
git diff

# Add specific file
git add filename.py

# Undo last commit (be careful!)
git reset --soft HEAD~1

# See commit history
git log --oneline
```

## Troubleshooting

### "fatal: not a git repository"
```bash
git init
```

### "Permission denied (publickey)"
Setup SSH key:
1. https://github.com/settings/keys
2. Follow GitHub's SSH key setup guide

Or use HTTPS instead (easier):
```bash
git remote set-url origin https://github.com/YOUR-USERNAME/predictive-maintenance.git
```

### "nothing added to commit"
```bash
git add .
git commit -m "message"
```

### Still need help?
GitHub has excellent guides: https://docs.github.com/en

---

✅ **Once code is on GitHub**, follow [DEPLOY_TO_RENDER.md](DEPLOY_TO_RENDER.md) to go live!
