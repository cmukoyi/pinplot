# GitHub Secrets Configuration

This document lists all the GitHub Secrets required for the deployment pipeline to work correctly.

## Required Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

### Server Access

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `DO_SERVER_IP` | Digital Ocean server IP address | `161.35.38.209` |
| `DO_USER` | SSH user for server access | `root` |
| `DO_SSH_PRIVATE_KEY` | SSH private key for authentication | (your private SSH key content) |

### Database Configuration

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `POSTGRES_PASSWORD` | PostgreSQL database password | `your-secure-random-password-min-32-chars` |

### Application Secrets

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `SECRET_KEY` | JWT secret key for authentication | `your-super-secret-jwt-key-min-32-chars-long-for-production` |

### Email Configuration (SendGrid)

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `SENDGRID_API_KEY` | SendGrid API key for sending emails | `SG.xxxxxxxxxxxxxxxxxxxxxxx.yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy` |
| `FROM_EMAIL` | Email address to send from | `noreply@pinplot.me` |

### MZone API Configuration

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `MZONE_CLIENT_SECRET` | MZone API client secret | `your-mzone-client-secret-value` |

## How to Set Up Secrets

1. Navigate to your GitHub repository
2. Click on **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Enter the **Name** and **Secret** value
5. Click **Add secret**
6. Repeat for all secrets listed above

## Current Values

The current production values are stored securely on the server:
- Root `.env`: `/root/gps-tracker/.env`
- Backend `.env`: `/root/gps-tracker/backend/.env`

## Testing Deployment

After setting up all secrets:

1. Push changes to the `main` branch
2. Go to **Actions** tab in GitHub
3. Watch the deployment workflow run
4. Verify deployment at: http://161.35.38.209/

Or manually trigger deployment:
1. Go to **Actions** tab
2. Click on **Deploy to Digital Ocean** workflow
3. Click **Run workflow**
4. Select `main` branch
5. Click **Run workflow**

## Security Notes

- Never commit actual secret values to the repository
- Keep SSH private keys secure
- Rotate SendGrid API keys periodically
- Use strong, randomly generated passwords
- Consider using environment-specific secrets for staging/production

## Verification Commands

After deployment, verify the application:

```bash
# Check backend health
curl http://161.35.38.209/api/health

# Check Flutter web app
curl http://161.35.38.209/

# Check admin dashboard
curl http://161.35.38.209/admin/

# Test verification email
curl -X POST http://161.35.38.209/api/v1/auth/send-verification-code \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'
```
