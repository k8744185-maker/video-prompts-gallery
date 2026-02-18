# 🔄 Render Free Tier: Understanding Sleep Mode

Quick guide to understanding and managing Render's free tier sleep behavior.

---

## 🤔 Why Does Your Site "Reboot"?

**It's not actually rebooting - it's waking up from sleep!**

### How Render Free Tier Works:

1. **Active Usage (15 minutes):**
   - Your app runs normally
   - Fast response times
   - Everything works perfectly

2. **Inactivity (15 minutes):**
   - No visitors for 15 minutes
   - Render puts your app to "sleep"
   - Saves resources (this is how they offer free hosting)

3. **Next Visitor Arrives:**
   - App "wakes up" (cold start)
   - Takes 30-60 seconds
   - Then runs normally again

---

## 👥 What Users Experience

### Scenario 1: Active Site (Within 15 Minutes)
```
User visits → Instant load → See prompts ✅
```
**User experience:** Perfect, fast, no issues

### Scenario 2: Sleeping Site (After 15+ Minutes Idle)
```
User visits → Wait 30-60 sec → App wakes → See prompts ✅
```
**User experience:** Longer initial load, then normal

**IMPORTANT:** Users do NOT go offline! They just wait a bit longer for the first page load.

---

## ✅ Users Still See Your Prompts

### What Happens During Wake-Up:

1. **User clicks your link**
2. **Browser shows:** Loading indicator (spinning wheel)
3. **Behind the scenes:** Render starts your app (30-60 sec)
4. **Result:** Page loads, user sees all prompts perfectly

**Users are NOT disconnected.** They just experience a slightly longer initial load time.

---

## 💡 Solutions to Sleep Mode

### Option 1: Accept It (FREE) ✅
**Best for:** Starting out, testing, low traffic

**Pros:**
- Completely free
- No setup needed
- Works fine for most users

**Cons:**
- First visitor after 15 min waits 30-60 sec
- Might affect AdSense review (reviewers could hit cold start)

**When to choose:** You're just launching, testing features, or have patient users.

---

### Option 2: UptimeRobot (FREE) ⭐ Recommended
**Best for:** AdSense application period, professional appearance

**What it does:**
- Pings your site every 5 minutes
- Keeps app awake 24/7
- Completely automated

**How to set up:**

1. **Go to [UptimeRobot.com](https://uptimerobot.com)**

2. **Sign up:** Free account

3. **Add Monitor:**
   ```
   Monitor Type: HTTP(s)
   Friendly Name: Video Prompts Gallery
   URL: https://your-app.onrender.com
   Monitoring Interval: 5 minutes
   ```

4. **Save:** That's it!

**Result:**
- Your app never sleeps
- Always fast for visitors
- Better for AdSense review

**Cost:** $0 (Free forever)

**Recommendation:** **Set this up before applying to AdSense** so reviewers don't experience cold starts.

---

### Option 3: Render Paid Plan ($7/month)
**Best for:** Production apps, high traffic, professional sites

**What you get:**
- No sleep mode
- More RAM (512MB → custom)
- More CPU (0.1 → custom)
- Faster performance
- Better uptime SLA

**When to upgrade:**
- Getting consistent traffic
- Making money from AdSense
- Want professional-grade hosting

**Current need:** Not necessary yet. Try UptimeRobot first!

---

## 📊 Comparison Table

| Feature | Free (No Ping) | Free + UptimeRobot | Paid Plan ($7/mo) |
|---------|---------------|-------------------|-------------------|
| **Cost** | $0 | $0 | $84/year |
| **Sleeps?** | Yes (15 min) | No ✅ | No ✅ |
| **Cold Start** | 30-60 sec | Never | Never |
| **RAM** | 512MB | 512MB | 1GB+ |
| **Setup** | None | 5 minutes | Upgrade |
| **Best For** | Testing | Launch/AdSense | Production |

---

## 🎯 Recommendations

### Right Now (Pre-AdSense):
**Use: Free + UptimeRobot** ⭐

**Why:**
- Costs nothing
- Keeps site always awake
- Better experience during AdSense review
- Professional appearance

**How:**
1. Set up UptimeRobot (takes 5 minutes)
2. Let it run for a few days
3. Test that cold starts are gone
4. Apply for AdSense

---

### After AdSense Approval:

**If earning < $7/month:**
- Keep using UptimeRobot
- Monitor performance
- Stay on free plan

**If earning > $7/month:**
- Consider upgrading to Render paid plan
- Better performance
- More reliable
- Professional hosting

---

## 🧪 Testing Sleep Mode

### See It Yourself:

1. **Visit your site:** https://your-app.onrender.com
2. **Note the time**
3. **Wait 20 minutes** (do something else)
4. **Visit again:** You'll experience the cold start
5. **Refresh immediately after:** Fast, no delay

This shows the sleep → wake → active cycle.

---

## ❓ Common Questions

### Q: Do I lose data when it sleeps?
**A:** No! All data is in Google Sheets. Sleep only affects the web server.

### Q: Can users still share links while it's asleep?
**A:** Yes! The links work fine. When clicked, the app wakes up and shows the prompt.

### Q: Will this affect my AdSense approval?
**A:** Potentially. If the reviewer visits during a cold start, they might think your site is slow. 

**Solution:** Set up UptimeRobot before applying to AdSense.

### Q: How do I know if my site is asleep?
**A:** If it's been 15+ minutes since the last visitor, it's probably asleep. Visit it - if it takes 30-60 seconds to load, it was sleeping.

### Q: Does UptimeRobot really work?
**A:** Yes! It visits your site every 5 minutes, so Render never puts it to sleep (15-minute threshold).

---

## 🚀 Quick Action Plan

### Today:
1. [ ] Sign up for UptimeRobot (free)
2. [ ] Add your Render URL as a monitor
3. [ ] Set interval to 5 minutes
4. [ ] Activate monitoring

### Tomorrow:
1. [ ] Test your site - should load instantly
2. [ ] Wait 20 minutes, test again - still instant!
3. [ ] Verify UptimeRobot is working (check dashboard)

### When Applying to AdSense:
1. [ ] Confirm UptimeRobot is active
2. [ ] Test site speed on multiple devices
3. [ ] Submit AdSense application
4. [ ] Keep UptimeRobot running during review (1-7 days)

### After AdSense Approval:
1. [ ] Continue using UptimeRobot (free)
2. [ ] Monitor AdSense earnings
3. [ ] If earnings > $7/month, consider Render paid plan

---

## 💰 Cost Analysis

### First 6 Months (Free):
```
Render Free Plan: $0
UptimeRobot: $0
Total: $0/month
```

### If Earning $20/month from AdSense:
```
Income: $20/month
Render Paid: $7/month (optional)
Profit: $13/month (or $20 if staying on free+UptimeRobot)
```

**Recommendation:** Stay on free plan until earnings justify paid hosting.

---

## 🎬 Summary

### The "Reboot" is Actually:
- ❌ NOT a reboot
- ❌ NOT losing data  
- ❌ NOT users going offline
- ✅ Normal sleep mode on free hosting
- ✅ Users still see everything after wake-up
- ✅ Solvable with UptimeRobot (free)

### What You Should Do:
1. **Understand:** It's normal behavior for free hosting
2. **Set up UptimeRobot:** Keeps site awake for $0
3. **Test:** Verify it works
4. **Apply to AdSense:** With confidence in site performance

---

**Your site is fine! Users aren't going offline. They just might wait a bit on the first load. Use UptimeRobot to eliminate even that delay.** 🚀

---

**Questions?** Review the [ADSENSE_APPROVAL_GUIDE.md](ADSENSE_APPROVAL_GUIDE.md) for next steps!
