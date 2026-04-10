# Security Features

## 🔐 Implemented Security Measures

### 1. **Input Validation & Sanitization**
- HTML escaping to prevent XSS (Cross-Site Scripting) attacks
- Removal of malicious script tags and event handlers
- Path traversal attack prevention
- Maximum length validation for all inputs
- Suspicious pattern detection

### 2. **Authentication Security**
- **Password Hashing**: Admin password is hashed using SHA-256
- **Rate Limiting**: Maximum 5 login attempts before lockout
- **Lockout Period**: 5 minutes after exceeding login attempts
- **Session Timeout**: Auto-logout after 30 minutes of inactivity

### 3. **Session Management**
- Automatic session expiration
- Activity tracking to prevent session hijacking
- Secure session state management

### 4. **Data Protection**
- Google Service Account authentication (no user passwords stored)
- Environment variables for sensitive data
- Credentials stored in separate files (not in code)

### 5. **Content Security**
- Maximum prompt length: 5000 characters
- Maximum name length: 200 characters
- Input sanitization for all user-provided data
- Prevention of HTML/JavaScript injection

## 🛡️ Security Best Practices

### Environment Variables (.env)
```bash
# NEVER commit these to version control
ADMIN_PASSWORD=your_secure_password_here
GOOGLE_CREDENTIALS_PATH=./credentials.json
GOOGLE_SHEET_ID=your_sheet_id
BASE_URL=https://yourdomain.com
```

### File Permissions
```bash
# Restrict access to sensitive files
chmod 600 .env
chmod 600 credentials.json
```

### Production Deployment
1. **Use HTTPS**: Always deploy with SSL/TLS
2. **Strong Passwords**: Use complex admin passwords (min 16 characters)
3. **Update Dependencies**: Regularly update all packages
4. **Monitor Logs**: Check for suspicious activities
5. **Backup Data**: Regular Google Sheets backups
6. **Access Control**: Limit Google Sheets API access

## 🔒 Rate Limiting Details

- **Max Login Attempts**: 5 attempts
- **Lockout Duration**: 5 minutes (300 seconds)
- **Session Timeout**: 30 minutes (1800 seconds)

## ⚠️ Security Warnings

### DO NOT:
- ❌ Commit .env or credentials.json to version control
- ❌ Share admin password in plaintext
- ❌ Use default passwords in production
- ❌ Expose Google Sheets to public write access
- ❌ Disable security features

### DO:
- ✅ Use strong, unique passwords
- ✅ Keep dependencies updated
- ✅ Monitor login attempts
- ✅ Use HTTPS in production
- ✅ Regular security audits

## 🚨 Incident Response

If you suspect a security breach:
1. Immediately change admin password
2. Revoke and regenerate Google Service Account credentials
3. Check Google Sheets for unauthorized modifications
4. Review Streamlit logs for suspicious activity
5. Update all dependencies

## 📝 Security Configuration

Current security settings in code:
```python
MAX_LOGIN_ATTEMPTS = 5          # Maximum failed login attempts
LOCKOUT_TIME = 300             # Lockout duration in seconds (5 min)
SESSION_TIMEOUT = 1800         # Session timeout in seconds (30 min)
MAX_PROMPT_LENGTH = 5000       # Maximum prompt character limit
MAX_NAME_LENGTH = 200          # Maximum name character limit
```

## 🔄 Regular Security Maintenance

- [ ] Update Python packages monthly
- [ ] Review access logs weekly
- [ ] Rotate admin password quarterly
- [ ] Audit Google Sheets permissions monthly
- [ ] Test security features after updates

## 📞 Security Contact

For security concerns or vulnerability reports, please secure your instance immediately and review logs.

---

**Last Updated**: February 2026
**Security Level**: Production-Ready
**Compliance**: OWASP Best Practices
