# 🎯 Google Ads Integration Guide

This guide will help you set up Google AdSense to monetize your Video Prompts Gallery website.

## 📋 Prerequisites

- A website or app that complies with Google AdSense policies
- Original content
- Age requirement: 18+ years old

## 🚀 Step-by-Step Setup

### 1️⃣ Create Google AdSense Account

1. Visit [Google AdSense](https://www.google.com/adsense/)
2. Click "Get Started" or "Sign Up Now"
3. Sign in with your Google account
4. Fill in your website URL: `your-deployed-url.com`
5. Select your country/region
6. Review and accept the AdSense Terms and Conditions

### 2️⃣ Add Your Site to AdSense

1. After signing up, you'll be taken to your AdSense dashboard
2. Go to **Sites** in the left menu
3. Click "Add site" if not already added
4. Enter your website URL
5. Copy the AdSense code provided

### 3️⃣ Get Your Publisher ID (Client ID)

1. In your AdSense dashboard, look for your **Publisher ID**
2. It will look like: `ca-pub-1234567890123456`
3. You can find it at:
   - Top right corner of AdSense dashboard
   - Account → Account information
   - Or in the ad code: `data-ad-client="ca-pub-xxxxxxxxxxxxxxxxx"`

### 4️⃣ Configure in Your App

1. Open your `.env` file
2. Replace the placeholder with your actual Publisher ID:

```env
# Google Ads Configuration
GOOGLE_ADS_CLIENT_ID=ca-pub-1234567890123456
```

**⚠️ Important:** Replace `ca-pub-xxxxxxxxxxxxxxxxx` with your actual Publisher ID!

### 5️⃣ Create Ad Units (Optional but Recommended)

1. In AdSense dashboard, go to **Ads** → **Overview**
2. Click "By ad unit" → "Display ads"
3. Create ad units for different locations:
   - **Hero Ad** - Horizontal banner (728x90 or responsive)
   - **Content Ad** - Square or rectangle (300x250 or responsive)
   - **Single Prompt Ad** - Responsive rectangle

4. For each ad unit, copy the **Ad slot ID** (e.g., `1234567890`)

5. Update the ad slots in `app.py`:

```python
# After hero section
show_google_ad(ad_slot="YOUR_HERO_AD_SLOT", ad_format="horizontal")

# In View All tab
show_google_ad(ad_slot="YOUR_CONTENT_AD_SLOT", ad_format="auto")

# In single prompt view
show_google_ad(ad_slot="YOUR_SINGLE_AD_SLOT", ad_format="auto")
```

### 6️⃣ Verify Your Site

1. Deploy your app to a public URL (not localhost)
2. In AdSense, go to **Sites**
3. Click "Ready" next to your site
4. AdSense will verify that the code is properly installed
5. Verification can take **1-2 days**

## 📍 Ad Placement Locations

Your app currently shows ads in these strategic locations:

1. **Hero Ad** - After the main header on the homepage
2. **Content Ads** - Before prompts list in "View All" tab
3. **Recurring Ads** - After every 3 prompts in the list
4. **Single Prompt Ad** - In individual prompt pages shared via link

## 💰 Monetization Tips

### ✅ Best Practices

- **Content Quality**: Create original, valuable content
- **User Experience**: Don't overload with ads (current setup is balanced)
- **Mobile Friendly**: Ads are responsive and work on all devices
- **Ad Formats**: Mix of display formats for better performance
- **Regular Updates**: Add new prompts regularly to attract visitors

### ❌ Don't Do This

- Never click your own ads
- Don't ask others to click ads
- Don't place ads on pages with prohibited content
- Don't modify the ad code manually

## 📊 Ad Performance

### Tracking Revenue

1. Go to AdSense dashboard
2. View **Reports** → **Overview**
3. Monitor:
   - Page views
   - Impressions
   - Clicks
   - CPC (Cost Per Click)
   - RPM (Revenue Per Thousand Impressions)
   - Estimated earnings

### Optimization

- **A/B Test**: Try different ad placements
- **Ad Formats**: Test various sizes and formats
- **Content Strategy**: Focus on high-traffic topics
- **SEO**: Optimize for search engines to increase traffic

## 🔧 Troubleshooting

### Ads Not Showing

**Possible Reasons:**

1. **Site Not Verified**
   - Solution: Wait for AdSense verification (1-2 days)

2. **Wrong Publisher ID**
   - Solution: Double-check your `GOOGLE_ADS_CLIENT_ID` in `.env`

3. **Running on Localhost**
   - Solution: Deploy to a public URL

4. **Ad Blocker Enabled**
   - Solution: Disable ad blocker to test

5. **Insufficient Content**
   - Solution: Add more prompts and pages

### Placeholder Ads Showing

If you see "📢 Advertisement Space" boxes:

```
📢 Advertisement Space
Configure GOOGLE_ADS_CLIENT_ID in .env to show ads
```

**Solution:** Add your real Publisher ID to `.env` file and restart the app.

### Account Under Review

- New accounts take 1-3 days for initial review
- Your site needs sufficient content
- Keep adding quality content during review

## 🌐 Going Live

### Before Launching

- [ ] AdSense account approved
- [ ] Publisher ID added to `.env`
- [ ] App deployed to public URL (not localhost)
- [ ] Site verified in AdSense
- [ ] At least 10-15 quality prompts added
- [ ] Tested on mobile and desktop

### After Launch

1. Monitor ad performance daily for first week
2. Check for policy violations
3. Optimize based on reports
4. Ensure compliance with AdSense policies

## 📖 Additional Resources

- [AdSense Help Center](https://support.google.com/adsense)
- [AdSense Policies](https://support.google.com/adsense/answer/48182)
- [Ad Balance Guide](https://support.google.com/adsense/answer/10502938)
- [Revenue Optimization](https://support.google.com/adsense/answer/17957)

## 🎓 Ad Format Types

### Auto Ads (Recommended for Beginners)
- Google automatically places ads
- Optimized for best performance
- Less manual configuration

### Manual Ad Units (Current Setup)
- Full control over placement
- Better for specific layouts
- Requires ad slot IDs

### In-feed Ads
- Blends with content naturally
- Good for list views
- Higher engagement

### In-article Ads
- Placed within content
- Less intrusive
- Good for long-form content

## 💡 Current Implementation

Your app uses **manual ad units** with responsive design:

```python
def show_google_ad(ad_slot="", ad_format="auto", full_width=True):
    # Displays Google AdSense ads
    # Shows placeholder if not configured
```

**Ad Locations:**
- ✅ Homepage hero section
- ✅ View All tab (before prompts)
- ✅ Every 3rd prompt in list
- ✅ Single prompt pages

## 🔐 Security Note

**⚠️ Never commit your actual Publisher ID to public repositories!**

Your `.env` file is already in `.gitignore` to protect your credentials.

## 📞 Support

If you encounter issues:

1. Check [AdSense Help Center](https://support.google.com/adsense)
2. Visit [AdSense Community](https://support.google.com/adsense/community)
3. Contact AdSense Support from your dashboard

---

**Remember:** Quality content and genuine traffic are key to successful monetization! 🎯💰
