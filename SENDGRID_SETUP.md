# SendGrid Email Setup Guide

Complete guide for setting up SendGrid to handle email notifications for PIN verification and geofence alerts.

## 🎯 Why SendGrid?

- **Free Tier**: 100 emails per day forever (perfect for small-scale deployments)
- **Reliable**: Industry-standard email delivery service
- **Simple API**: Easy integration with Python
- **No SMTP hassles**: No need to configure SMTP servers or deal with ISP blocks
- **Analytics**: Track email delivery, opens, and clicks
- **Professional**: Better deliverability than Gmail SMTP

## 📋 SendGrid Free Tier Limits

- **100 emails/day** - Sufficient for small teams and testing
- **2,000 contacts**
- **Email API access**
- **Email validation**
- **Dedicated IP not included** (shared IPs used)

## 🚀 Setup Instructions

### Step 1: Create SendGrid Account

1. Go to [https://sendgrid.com/](https://sendgrid.com/)
2. Click **"Start for Free"** or **"Sign Up"**
3. Fill in your details:
   - Email address
   - Password
   - First and Last name
4. Verify your email address
5. Complete the onboarding questionnaire:
   - Select **"Web App"** as integration type
   - Choose **"Marketing"** or **"Transactional"** (we're using Transactional)
   - Select your programming language: **Python**

### Step 2: Verify Single Sender Email Address

Before you can send emails, SendGrid requires you to verify at least one sender email address:

1. Go to **Settings** → **Sender Authentication**
2. Click **"Verify a Single Sender"**
3. Fill in the form:
   - **From Name**: `BLE Tracker` or your app name
   - **From Email Address**: Your email (e.g., `noreply@yourdomain.com` or `your-email@gmail.com`)
   - **Reply To**: Same as From Email or your support email
   - **Company Address**: Your address details
   - **Nickname**: `BLE Tracker Notifications`
4. Click **"Create"**
5. Check your email and click the verification link
6. Wait for verification (usually instant)

**Important**: All emails will be sent FROM this verified email address.

### Step 3: Create API Key

1. Go to **Settings** → **API Keys**
2. Click **"Create API Key"**
3. Configure the API key:
   - **Name**: `BLE-Tracker-Production` (or any descriptive name)
   - **API Key Permissions**: Choose **"Restricted Access"**
   - Under **Mail Send**, enable: ✅ **Mail Send** (Full Access)
   - Leave other permissions disabled
4. Click **"Create & View"**
5. **IMPORTANT**: Copy the API key immediately - you won't see it again!
   - It looks like: `SG.xxxxxxxxxxxxxxxxxxxxx.yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy`
6. Store it securely (we'll use it in the next step)

### Step 4: Configure Backend

#### For Local Development:

Edit `gps-tracker/backend/.env`:

```bash
# SendGrid Configuration (Production)
SENDGRID_API_KEY=SG.your-actual-api-key-here
FROM_EMAIL=your-verified-email@domain.com

# SMTP Fallback (MailHog for local testing)
SMTP_HOST=mailhog
SMTP_PORT=1025
```

#### For Digital Ocean Production:

Add to GitHub Secrets (Repository → Settings → Secrets and variables → Actions):

| Secret Name | Value | Example |
|------------|-------|---------|
| `SENDGRID_API_KEY` | Your SendGrid API key | `SG.abcd1234...` |
| `FROM_EMAIL` | Your verified sender email | `noreply@yourdomain.com` |

### Step 5: Test Email Sending

#### Test 1: Backend Health Check

```bash
# Start your backend
cd gps-tracker
docker-compose up -d

# Check logs - should see: "📧 Email Service: Using SendGrid API"
docker-compose logs backend | grep "Email Service"
```

#### Test 2: Send Verification PIN

```bash
# Register a new user to trigger PIN email
curl -X POST http://localhost:5001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!@#"
  }'

# Check SendGrid Activity Feed
# Go to: Activity → Activity Feed in SendGrid dashboard
```

#### Test 3: Send Geofence Alert

1. Add a POI/geofence in the mobile app
2. Arm the geofence for a tracker
3. Move tracker into the geofence area (simulate or actual)
4. Check your email for the geofence alert

### Step 6: Monitor Email Delivery

SendGrid provides detailed analytics:

1. Go to **Activity** → **Activity Feed**
2. View real-time email events:
   - ✅ **Processed**: Email accepted by SendGrid
   - ✅ **Delivered**: Email delivered to recipient
   - ⚠️ **Bounced**: Email bounced
   - ❌ **Dropped**: Email blocked

3. Go to **Stats** → **Overview** for aggregate metrics

## 🔧 Configuration Details

### How Email Service Works

The backend automatically chooses the email provider:

1. **If `SENDGRID_API_KEY` is set** → Uses SendGrid API ✅
2. **If `SENDGRID_API_KEY` is NOT set** → Falls back to SMTP (MailHog for local dev)

### Environment Variables

```bash
# Required for SendGrid
SENDGRID_API_KEY=SG.your-api-key-here
FROM_EMAIL=your-verified-sender@domain.com

# Optional: SMTP Fallback (for local development)
SMTP_HOST=mailhog
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
```

### Emails Sent by the System

| Email Type | Trigger | From | Subject |
|-----------|---------|------|---------|
| **Verification PIN** | User registration | your-verified-email | `Your BLE Tracker Verification Code` |
| **Welcome Email** | Account verified | your-verified-email | `Welcome to BLE Tracker` |
| **Geofence Entry Alert** | Tracker enters POI | your-verified-email | `🟢 Geofence Alert: [Tracker] entered [POI]` |
| **Geofence Exit Alert** | Tracker exits POI | your-verified-email | `🔴 Geofence Alert: [Tracker] exited [POI]` |

## 🚨 Troubleshooting

### Error: "Sender identity pending verification"

**Solution**: Go to SendGrid → Settings → Sender Authentication → Verify your single sender email

### Error: "API key does not have permission"

**Solution**: Create a new API key with **Mail Send** (Full Access) permission

### Emails not arriving

1. Check SendGrid Activity Feed for delivery status
2. Check your spam/junk folder
3. Verify `FROM_EMAIL` matches your verified sender
4. Check backend logs: `docker-compose logs backend | grep "Email"`

### Testing locally but want to use real emails

Set `SENDGRID_API_KEY` in your local `.env` file instead of using MailHog.

### Want to switch back to SMTP

Simply remove or comment out `SENDGRID_API_KEY` from your `.env` file:
```bash
# SENDGRID_API_KEY=SG.xxx  # Commented out - will use SMTP
```

## 📈 Scaling Beyond Free Tier

If you exceed 100 emails/day:

### Option 1: SendGrid Essentials Plan
- **40,000 emails/month** for $19.95/month
- Dedicated IP available
- Email validation

### Option 2: Multiple Free Accounts (Not Recommended)
- SendGrid TOS may prohibit this
- Not sustainable for production

### Option 3: Alternative Email Services
- **Mailgun**: 5,000 emails/month free for 3 months
- **Amazon SES**: $0.10 per 1,000 emails (very cheap)
- **Postmark**: 100 emails/month free

## 🔒 Security Best Practices

1. **Never commit API keys to Git**
   - Already in `.gitignore`: `*.env`
   
2. **Use environment variables**
   - Store API key in `.env` file locally
   - Store in GitHub Secrets for CI/CD
   
3. **Restrict API key permissions**
   - Only enable "Mail Send" permission
   - Don't give full account access
   
4. **Rotate API keys periodically**
   - Create new key every 90 days
   - Delete old keys
   
5. **Monitor usage**
   - Check SendGrid dashboard regularly
   - Set up alerts for unusual activity

## 📝 SendGrid Dashboard Overview

- **Activity Feed**: Real-time email events
- **Stats**: Delivery metrics and analytics
- **Templates**: Email templates (not used in this project)
- **Suppressions**: Bounced/blocked/unsubscribed emails
- **Settings**: API keys, sender authentication, webhooks

## 🎓 Additional Resources

- [SendGrid Python Library Documentation](https://github.com/sendgrid/sendgrid-python)
- [SendGrid API Reference](https://docs.sendgrid.com/api-reference)
- [Email Deliverability Best Practices](https://sendgrid.com/resource/email-deliverability-guide/)

## ✅ Verification Checklist

- [ ] SendGrid account created
- [ ] Single sender email verified
- [ ] API key created with "Mail Send" permission
- [ ] `SENDGRID_API_KEY` added to `.env` (local) or GitHub Secrets (production)
- [ ] `FROM_EMAIL` set to verified sender email
- [ ] Backend restarted with new configuration
- [ ] Backend logs show: "📧 Email Service: Using SendGrid API"
- [ ] Test email sent successfully (registration PIN)
- [ ] Email delivered (check inbox and SendGrid Activity Feed)
- [ ] Geofence alert tested (if applicable)

---

**Need help?** Check the [SendGrid Support Center](https://support.sendgrid.com/) or contact the development team.
