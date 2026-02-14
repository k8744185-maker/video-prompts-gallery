# 🚀 Complete Deployment Guide - Local to GitHub to Streamlit Cloud

## 📍 Current Situation
- ✅ Project is ready in your office laptop: `/home/venkadesan.k/Documents/Personalcode`
- 🎯 Goal: Push to GitHub → Deploy on Streamlit Cloud

---

## Step 1️⃣: Prepare Your Project Files

### Create .gitignore file (Important!)

This prevents sensitive files from being uploaded to GitHub:

```bash
cd /home/venkadesan.k/Documents/Personalcode
```

Create `.gitignore` file with this content:

```
# Environment variables (SENSITIVE - DO NOT COMMIT)
.env

# Google credentials (SENSITIVE - DO NOT COMMIT)
credentials.json

# Python cache
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Virtual environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/

# OS files
.DS_Store
Thumbs.db

# Streamlit
.streamlit/secrets.toml
```

---

## Step 2️⃣: Initialize Git Repository

Run these commands in terminal:

```bash
cd /home/venkadesan.k/Documents/Personalcode

# Initialize git
git init

# Add all files (except those in .gitignore)
git add .

# Create first commit
git commit -m "Initial commit - Video Prompts Gallery with Google Ads"

# Check status
git status
```

---

## Step 3️⃣: Create GitHub Repository

### Option A: Using GitHub Website

1. Go to: https://github.com/
2. Click **"New"** button (or + icon → New repository)
3. Repository name: `video-prompts-gallery` (or any name you like)
4. Description: `AI Video Prompts Gallery with Google Ads Integration`
5. Select: **Private** (recommended) or Public
6. **DON'T** check "Initialize with README" (already have files)
7. Click **"Create repository"**

### Option B: Using GitHub CLI (if installed)

```bash
gh repo create video-prompts-gallery --private --source=. --remote=origin --push
```

---

## Step 4️⃣: Connect Local to GitHub

After creating GitHub repo, you'll see commands. Run these:

```bash
# Add GitHub remote
git remote add origin https://github.com/YOUR-USERNAME/video-prompts-gallery.git

# Rename branch to main
git branch -M main

# Push to GitHub
git push -u origin main
```

**Replace `YOUR-USERNAME`** with your actual GitHub username!

### If Git asks for credentials:

```bash
# Set your name
git config --global user.name "Your Name"

# Set your email
git config --global user.email "your-email@example.com"
```

### For authentication:
- GitHub may ask for **Personal Access Token** instead of password
- Generate token: GitHub → Settings → Developer settings → Personal access tokens → Generate new token
- Use token as password when pushing

---

## Step 5️⃣: Create Streamlit Secrets File

Create `.streamlit/secrets.toml` file locally (for reference, won't be uploaded):

```bash
mkdir -p .streamlit
```

Create file: `.streamlit/secrets.toml`

```toml
# Copy these to Streamlit Cloud Secrets

ADMIN_PASSWORD = "mySecurePassword123"
GOOGLE_SHEET_ID = "1PSZdOhikbe5C2QbsicpXDKESY7qj_pZ9k7W3td90ebE"
BASE_URL = "https://your-app-name.streamlit.app"
GOOGLE_ADS_CLIENT_ID = "ca-pub-xxxxxxxxxxxxxxxxx"

EMAIL_USER = "k8744185@gmail.com"
EMAIL_PASSWORD = "bmjc fdhr hoos fyfm"

# Google Credentials JSON (paste entire content)
[GOOGLE_CREDENTIALS]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR-PRIVATE-KEY\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "your-cert-url"
```

---

## Step 6️⃣: Update app.py for Streamlit Cloud

Your app needs to read credentials from Streamlit secrets:

**Add this at the top of app.py** (after imports):

```python
import streamlit as st
import json

# Load environment variables
if os.path.exists('.env'):
    # Local development
    load_dotenv()
    GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', './credentials.json')
else:
    # Streamlit Cloud - use secrets
    GOOGLE_CREDENTIALS_PATH = None
    # Create credentials from secrets
    if hasattr(st, 'secrets') and 'GOOGLE_CREDENTIALS' in st.secrets:
        creds_dict = dict(st.secrets['GOOGLE_CREDENTIALS'])
        GOOGLE_CREDENTIALS_PATH = creds_dict
```

**Update get_google_sheet() function:**

```python
def get_google_sheet():
    """Connect to Google Sheets"""
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        
        # Check if running on Streamlit Cloud
        if isinstance(GOOGLE_CREDENTIALS_PATH, dict):
            # Streamlit Cloud - use secrets
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                GOOGLE_CREDENTIALS_PATH, scope)
        else:
            # Local development - use file
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                GOOGLE_CREDENTIALS_PATH, scope)
        
        client = gspread.authorize(creds)
        
        # Get sheet ID from environment or secrets
        sheet_id = os.getenv('GOOGLE_SHEET_ID') or st.secrets.get('GOOGLE_SHEET_ID')
        sheet = client.open_by_key(sheet_id).sheet1
        
        # Ensure headers exist
        if not sheet.row_values(1):
            sheet.update('A1:E1', [['Timestamp', 'Unique ID', 'Prompt Name', 'Prompt', 'Video ID']])
        
        return sheet
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {str(e)}")
        return None
```

**Update all environment variable reads:**

```python
# Replace os.getenv() with this pattern:
admin_password = os.getenv('ADMIN_PASSWORD') or st.secrets.get('ADMIN_PASSWORD', 'admin123')
base_url = os.getenv('BASE_URL') or st.secrets.get('BASE_URL', 'http://localhost:8501')
ads_client = os.getenv('GOOGLE_ADS_CLIENT_ID') or st.secrets.get('GOOGLE_ADS_CLIENT_ID', '')
```

Save and commit changes:

```bash
git add .
git commit -m "Add Streamlit Cloud compatibility"
git push
```

---

## Step 7️⃣: Deploy on Streamlit Cloud

### 1. Go to Streamlit Cloud
Visit: https://share.streamlit.io/

### 2. Sign in
- Click **"Sign in"**
- Choose **"Continue with GitHub"**
- Authorize Streamlit to access your GitHub

### 3. Deploy New App
- Click **"New app"** button
- Select:
  - **Repository**: `YOUR-USERNAME/video-prompts-gallery`
  - **Branch**: `main`
  - **Main file path**: `app.py`
- Click **"Advanced settings"** (IMPORTANT!)

### 4. Add Secrets
In the **Secrets** section, paste your secrets:

```toml
ADMIN_PASSWORD = "mySecurePassword123"
GOOGLE_SHEET_ID = "1PSZdOhikbe5C2QbsicpXDKESY7qj_pZ9k7W3td90ebE"
BASE_URL = "https://your-app-name.streamlit.app"
GOOGLE_ADS_CLIENT_ID = "ca-pub-xxxxxxxxxxxxxxxxx"

EMAIL_USER = "k8744185@gmail.com"
EMAIL_PASSWORD = "bmjc fdhr hoos fyfm"

[GOOGLE_CREDENTIALS]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR-KEY\n-----END PRIVATE KEY-----\n"
client_email = "your-email@project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "your-cert-url"
```

**⚠️ Important:** 
- Copy values from your `.env` and `credentials.json`
- For `private_key`, keep the `\n` characters as they are
- Update `BASE_URL` with your actual Streamlit app URL (you'll get this after deployment)

### 5. Deploy!
- Click **"Deploy!"**
- Wait 2-5 minutes for deployment
- Your app will be live at: `https://your-app-name.streamlit.app`

---

## Step 8️⃣: Update BASE_URL

After deployment, you'll get your app URL. Update it:

1. Copy your Streamlit app URL: `https://your-app-name.streamlit.app`
2. Go to Streamlit Cloud → Your app → Settings → Secrets
3. Update `BASE_URL` to your actual URL
4. Click **"Save"**
5. App will automatically restart

---

## Step 9️⃣: Test Your Deployed App

1. Open your app URL
2. Try adding a prompt (should work)
3. Check if Google Sheets updates
4. Verify share links work
5. Check if placeholder ads appear

---

## 🔧 Troubleshooting

### App won't start?
**Check logs:** Streamlit Cloud → Your app → Manage app → View logs

### Common issues:

1. **Module not found**
   - Check `requirements.txt` has all dependencies
   - Should include: `streamlit`, `gspread`, `oauth2client`, `python-dotenv`

2. **Google Sheets error**
   - Verify secrets are correctly formatted
   - Check `private_key` has proper `\n` characters
   - Ensure service account has access to the sheet

3. **Import error**
   - Make sure `app.py` is the main file name
   - Check all Python files are pushed to GitHub

### View logs:
```bash
# In Streamlit Cloud dashboard
Click your app → "︙" menu → "View logs"
```

---

## 📝 Quick Command Summary

```bash
# Navigate to project
cd /home/venkadesan.k/Documents/Personalcode

# Create .gitignore (copy from Step 1)
nano .gitignore

# Initialize and commit
git init
git add .
git commit -m "Initial commit"

# Connect to GitHub (after creating repo on GitHub)
git remote add origin https://github.com/YOUR-USERNAME/video-prompts-gallery.git
git branch -M main
git push -u origin main

# For future updates
git add .
git commit -m "Your update message"
git push
```

---

## ✅ Checklist

Before deploying:
- [ ] `.gitignore` created (excludes `.env` and `credentials.json`)
- [ ] Git initialized and committed
- [ ] GitHub repository created
- [ ] Code pushed to GitHub
- [ ] `app.py` updated for Streamlit Cloud compatibility
- [ ] Secrets prepared from `.env` and `credentials.json`

During deployment:
- [ ] Signed in to Streamlit Cloud with GitHub
- [ ] Selected correct repository and branch
- [ ] Added all secrets correctly
- [ ] Deployed successfully

After deployment:
- [ ] App URL works
- [ ] Updated `BASE_URL` in secrets
- [ ] Tested all features
- [ ] Google Sheets integration works
- [ ] Ready for Google AdSense application

---

## 🎯 Next Steps

Once deployed:
1. ✅ You'll have a public URL
2. ✅ Apply for Google AdSense with this URL
3. ✅ Get Publisher ID
4. ✅ Update `GOOGLE_ADS_CLIENT_ID` in Streamlit secrets
5. ✅ Start earning! 💰

---

## 💡 Tips

- **Private vs Public repo:** Either works, but private is more secure
- **Free tier limits:** Streamlit Cloud free tier has resource limits
- **Secrets are secure:** They're encrypted and not visible in GitHub
- **Auto-deploy:** When you push to GitHub, Streamlit auto-updates your app
- **Custom domain:** You can add your own domain later

---

**Need help at any step? Just ask!** 🚀
