# 🔐 Streamlit Cloud Secrets Configuration

## Copy Your credentials.json Content Here

To fill in the `[GOOGLE_CREDENTIALS]` section in Streamlit Cloud secrets, open your `credentials.json` file and copy the values:

### Example credentials.json:
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "abc123...",
  "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR-PRIVATE-KEY-HERE\n-----END PRIVATE KEY-----\n",
  "client_email": "your-service@project.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/your-service%40project.iam.gserviceaccount.com"
}
```

### Paste This in Streamlit Cloud Secrets:

```toml
# Admin Password
ADMIN_PASSWORD = "mySecurePassword123"

# Google Sheets Configuration
GOOGLE_SHEET_ID = "1PSZdOhikbe5C2QbsicpXDKESY7qj_pZ9k7W3td90ebE"

# Base URL (Update this with your actual Streamlit app URL after deployment)
BASE_URL = "https://your-app-name.streamlit.app"

# Google Ads Client ID (Optional - add later after getting AdSense approval)
GOOGLE_ADS_CLIENT_ID = "ca-pub-xxxxxxxxxxxxxxxxx"

# Email Configuration (Optional)
EMAIL_USER = "k8744185@gmail.com"
EMAIL_PASSWORD = "bmjc fdhr hoos fyfm"

# Google Credentials - Copy from credentials.json
[GOOGLE_CREDENTIALS]
type = "service_account"
project_id = "YOUR_PROJECT_ID_FROM_CREDENTIALS_JSON"
private_key_id = "YOUR_PRIVATE_KEY_ID_FROM_CREDENTIALS_JSON"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR-PRIVATE-KEY-HERE\n-----END PRIVATE KEY-----\n"
client_email = "YOUR_SERVICE_ACCOUNT_EMAIL@project.iam.gserviceaccount.com"
client_id = "YOUR_CLIENT_ID_FROM_CREDENTIALS_JSON"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "YOUR_CERT_URL_FROM_CREDENTIALS_JSON"
```

## ⚠️ Important Notes:

1. **private_key field:** 
   - Keep the `\n` characters as they are
   - Should look like: `"-----BEGIN PRIVATE KEY-----\nMIIEvQI...\n-----END PRIVATE KEY-----\n"`
   - Do NOT remove the newline characters

2. **Update BASE_URL:**
   - After deployment, you'll get a URL like: `https://your-app-name.streamlit.app`
   - Update the `BASE_URL` in secrets with this URL
   - Restart the app after updating

3. **Google Ads:**
   - Initially use placeholder: `ca-pub-xxxxxxxxxxxxxxxxx`
   - After getting AdSense approval, update with real Publisher ID
   - Example real ID: `ca-pub-1234567890123456`

## 📝 How to Add Secrets in Streamlit Cloud:

1. Go to: https://share.streamlit.io/
2. Click on your deployed app
3. Click **"⋮" (three dots)** → **"Settings"**
4. Click **"Secrets"** tab
5. Paste the entire content above (with your actual values)
6. Click **"Save"**
7. App will automatically restart

## 🧪 Testing:

After deployment, test:
- ✅ App loads successfully
- ✅ Can add new prompts (Google Sheets connection works)
- ✅ Share links work correctly
- ✅ Admin authentication works
- ✅ Placeholder ads appear

## 🔄 Updating Secrets Later:

To update any secret (like adding real AdSense ID):
1. Go to app Settings → Secrets
2. Edit the value
3. Click Save
4. App restarts automatically

---

**Security Reminder:** Never commit secrets to GitHub. The `.gitignore` file already excludes:
- `.env`
- `credentials.json`
- `.streamlit/secrets.toml`
