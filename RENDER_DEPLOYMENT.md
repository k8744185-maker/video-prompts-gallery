# 🚀 Render.com Deployment Guide

Complete step-by-step guide to deploy your Video Prompts Gallery on Render.com

---

## 📋 Prerequisites

- ✅ GitHub repository created and pushed
- ✅ Your `credentials.json` file content ready
- ✅ All environment variables from `.env` file

---

## Step 1️⃣: Sign Up on Render.com

1. Visit: **https://render.com/**
2. Click **"Get Started for Free"**
3. Sign up with **GitHub** (recommended)
4. Authorize Render to access your GitHub repositories

---

## Step 2️⃣: Create New Web Service

1. After login, click **"New +"** button (top right)
2. Select **"Web Service"**
3. Connect your GitHub repository:
   - If first time: Click "Configure account" → Select repositories
   - Choose: **k8744185-maker/video-prompts-gallery**
4. Click **"Connect"**

---

## Step 3️⃣: Configure Service Settings

### Basic Configuration:

```
Name: video-prompts-gallery
Region: Oregon (US West) or Singapore (Asia)
Branch: main
Root Directory: (leave blank)
Runtime: Python 3
```

### Build & Start Commands:

```
Build Command: pip install -r requirements.txt
Start Command: ./start.sh
```

Or alternatively:
```
Start Command: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

### Instance Type:
```
Plan: Free (512 MB RAM, 0.1 CPU)
```

---

## Step 4️⃣: Add Environment Variables

Click **"Advanced"** → **"Add Environment Variable"**

Add these variables one by one:

### 1. Admin Password
```
Key: ADMIN_PASSWORD
Value: mySecurePassword123
```

### 2. Google Sheet ID
```
Key: GOOGLE_SHEET_ID
Value: 1PSZdOhikbe5C2QbsicpXDKESY7qj_pZ9k7W3td90ebE
```

### 3. Base URL (Update after deployment)
```
Key: BASE_URL
Value: https://video-prompts-gallery.onrender.com
```
**Note:** You'll get your actual URL after deployment. Come back and update this!

### 4. Google Ads Client ID (Optional)
```
Key: GOOGLE_ADS_CLIENT_ID
Value: ca-pub-xxxxxxxxxxxxxxxxx
```

### 5. Email Configuration (Optional)
```
Key: EMAIL_USER
Value: k8744185@gmail.com

Key: EMAIL_PASSWORD
Value: bmjc fdhr hoos fyfm
```

### 6. Google Credentials (IMPORTANT!)

Open your `credentials.json` file and copy the **entire content** (the whole JSON object).

```
Key: GOOGLE_CREDENTIALS
Value: (paste entire credentials.json content - should be one long line of JSON)
```

**Example format:**
```json
{"type":"service_account","project_id":"your-project","private_key_id":"abc123...","private_key":"-----BEGIN PRIVATE KEY-----\nMIIE...","client_email":"your-email@project.iam.gserviceaccount.com","client_id":"123...","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://..."}
```

**⚠️ Important:** 
- Must be valid JSON (one line, no line breaks except in private_key)
- Keep the `\n` characters in private_key
- No extra spaces or formatting

---

## Step 5️⃣: Deploy!

1. Click **"Create Web Service"**
2. Wait 5-10 minutes for first deployment
3. Watch the build logs in real-time
4. When you see "Your service is live 🎉", it's ready!

---

## Step 6️⃣: Get Your Live URL

1. After deployment, you'll see your app URL:
   ```
   https://video-prompts-gallery.onrender.com
   ```
   (or similar - the name might have random characters)

2. **Update BASE_URL:**
   - Go to your service → **"Environment"** tab
   - Find `BASE_URL` variable
   - Click **"Edit"** → Update with your actual URL
   - Click **"Save Changes"**
   - Service will automatically restart

---

## Step 7️⃣: Test Your Deployment

1. Open your Render URL
2. Check if:
   - ✅ Page loads without errors
   - ✅ Hero section displays properly
   - ✅ Can authenticate as admin
   - ✅ Can add new prompts
   - ✅ Google Sheets updates
   - ✅ Share links work
   - ✅ Placeholder ads appear

---

## 🔧 Troubleshooting

### Build Failed?

**Check build logs for errors:**

1. **Missing dependencies:**
   - Error: `ModuleNotFoundError`
   - Fix: Check `requirements.txt` has all packages

2. **Python version:**
   - Add `runtime.txt` file with content: `python-3.11.0`

3. **Start command failed:**
   - Make sure `start.sh` is executable
   - Or use direct command: `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`

### App Not Loading?

1. **Check service status:**
   - Dashboard → Your service → "Events" tab
   - Look for errors in logs

2. **Port binding error:**
   - Make sure start command includes `--server.port=$PORT`

3. **CORS issues:**
   - Already handled in `start.sh` with `--server.enableCORS=false`

### Google Sheets Not Working?

1. **Check GOOGLE_CREDENTIALS:**
   - Must be valid JSON
   - No formatting errors
   - Private key has `\n` characters

2. **Service Account Access:**
   - Verify service account email has access to the sheet
   - Sheet must be shared with the service account email

3. **Test credentials:**
   - View logs: Dashboard → Service → "Logs" tab
   - Look for authentication errors

### Environment Variables Not Working?

1. **Verify all variables are set:**
   - Environment tab → Check all required variables exist
   - No typos in variable names (case-sensitive)

2. **Update variables:**
   - Edit → Save Changes
   - Service auto-restarts after changes

---

## 📊 Monitoring

### View Logs:
```
Dashboard → Your Service → "Logs" tab
```
Real-time logs show:
- App startup
- Requests
- Errors
- System messages

### View Metrics:
```
Dashboard → Your Service → "Metrics" tab
```
Shows:
- CPU usage
- Memory usage
- Response times
- Request count

---

## 🔄 Updating Your App

### Auto-deploy from GitHub:

1. Make changes locally
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Update message"
   git push
   ```
3. Render automatically detects and deploys!
4. Watch deployment progress in dashboard

### Manual deploy:
```
Dashboard → Your Service → "Manual Deploy" → "Deploy latest commit"
```

---

## 💰 Free Tier Limits

Render.com Free Plan:
- ✅ **750 hours/month** (enough for 1 app running 24/7)
- ✅ **512 MB RAM**
- ✅ **0.1 CPU**
- ✅ **Free SSL certificate**
- ✅ **Automatic deployments**
- ⚠️ **Service sleeps after 15 min inactivity** (wakes on first request)
- ⚠️ **Cold start:** 30-60 seconds wake time

### To keep service always awake (optional):
- Use a ping service like **UptimeRobot** (free)
- Pings your URL every 5 minutes
- Prevents sleeping

---

## 🎯 Next Steps After Deployment

### 1. Test Everything
- [ ] App loads correctly
- [ ] Admin login works
- [ ] Can add/edit/delete prompts
- [ ] Share links work
- [ ] Google Sheets syncs

### 2. Apply for Google AdSense
- [ ] Now you have a public URL!
- [ ] Visit: https://www.google.com/adsense/
- [ ] Apply with your Render URL
- [ ] Wait for approval (1-2 days)

### 3. Update AdSense ID
- [ ] Get your Publisher ID (ca-pub-...)
- [ ] Update `GOOGLE_ADS_CLIENT_ID` in Render environment
- [ ] Real ads will appear!

### 4. Share Your Website
- [ ] Share URL on Instagram
- [ ] Add to bio
- [ ] Start sharing prompt links!

---

## 🔐 Security Best Practices

1. **Never commit sensitive files:**
   - `.env` ✅ (already in .gitignore)
   - `credentials.json` ✅ (already in .gitignore)

2. **Environment variables only in Render:**
   - Never hardcode credentials
   - Use environment variables

3. **Update admin password:**
   - Change from default after first login
   - Update in Render environment

4. **Monitor access:**
   - Check logs regularly
   - Watch for suspicious activity

---

## 📞 Support

### Render Support:
- Docs: https://render.com/docs
- Community: https://community.render.com/
- Email: support@render.com

### Your App Issues:
- Check logs first
- Review environment variables
- Test locally with same config

---

## 🎉 Success Checklist

After successful deployment:
- [x] Code pushed to GitHub
- [x] Render service created
- [x] All environment variables added
- [x] App deployed successfully
- [x] Live URL working
- [x] BASE_URL updated
- [x] All features tested
- [ ] Google AdSense applied
- [ ] Publisher ID updated
- [ ] Website shared!

---

**Congratulations! 🎊 Your Video Prompts Gallery is now LIVE!** 🚀

Your app URL: `https://video-prompts-gallery.onrender.com`
(or your custom URL)

---

## Quick Reference Commands

```bash
# Push updates to GitHub (auto-deploys to Render)
git add .
git commit -m "Your update message"
git push

# View your GitHub repo
https://github.com/k8744185-maker/video-prompts-gallery

# Access Render Dashboard
https://dashboard.render.com/
```

---

**Ready to earn with your prompts! 💰🎬**
