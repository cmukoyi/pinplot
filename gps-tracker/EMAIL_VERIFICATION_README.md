# BLE Tag Tracker - Email Verification & User Management

## New Features

### 1. SMTP Email Service (MailHog)
- **MailHog** is now included in Docker setup for email testing
- **Web UI**: http://localhost:8025 - View all sent emails
- **SMTP Port**: 1025 (internal Docker network)
- No authentication required for development

### 2. Email Verification System
Users can now sign up using **passwordless authentication** with PIN verification:

#### Flow:
1. User enters email address
2. System sends 6-digit PIN to email
3. User enters PIN (valid for 10 minutes)
4. User is logged in automatically

#### Endpoints:
```http
POST /api/v1/auth/send-verification-code
Content-Type: application/json

{
  "email": "user@example.com"
}
```

```http
POST /api/v1/auth/verify-pin
Content-Type: application/json

{
  "email": "user@example.com",
  "pin": "123456"
}
```

### 3. User Database Schema

#### Users Table
- `id` - UUID (Primary Key)
- `email` - Unique email address
- `hashed_password` - Optional (for traditional login)
- `first_name` - User's first name
- `last_name` - User's last name
- `phone` - Phone number
- `is_active` - Account status
- `is_admin` - Admin flag
- `email_verified` - Email verification status
- `created_at` - Account creation timestamp
- `updated_at` - Last update timestamp

#### Verification PINs Table
- `id` - UUID (Primary Key)
- `user_id` - Foreign Key to users
- `email` - Email address
- `pin` - 6-digit verification code
- `is_used` - Whether PIN has been used
- `expires_at` - Expiration timestamp (10 minutes)
- `created_at` - Creation timestamp

#### BLE Tags Table
- `id` - UUID (Primary Key)
- `user_id` - Foreign Key to users (owner)
- `imei` - Unique IMEI number
- `device_name` - Custom device name
- `device_model` - Device model
- `mac_address` - Bluetooth MAC address
- `is_active` - Active status
- `last_seen` - Last contact timestamp
- `latitude` - Last known latitude
- `longitude` - Last known longitude
- `battery_level` - Battery percentage
- `added_at` - When tag was added to account
- `updated_at` - Last update timestamp

### 4. BLE Tag Management Endpoints

#### Add BLE Tag to User Account
```http
POST /api/v1/ble-tags
Authorization: Bearer {token}
Content-Type: application/json

{
  "imei": "123456789012345",
  "device_name": "My Car Tag",
  "device_model": "BLE-TAG-001",
  "mac_address": "AA:BB:CC:DD:EE:FF"
}
```

#### List User's BLE Tags
```http
GET /api/v1/ble-tags
Authorization: Bearer {token}
```

#### Get Specific Tag Details
```http
GET /api/v1/ble-tags/{tag_id}
Authorization: Bearer {token}
```

#### Remove Tag from Account
```http
DELETE /api/v1/ble-tags/{tag_id}
Authorization: Bearer {token}
```

## Setup Instructions

### 1. Start Docker Services
```bash
cd /Users/carl/Documents/MobileCode/mobileGPS/gps-tracker
docker compose up -d --build
```

Services will be available at:
- **Backend API**: http://localhost:8000
- **Admin Portal**: http://localhost:3001
- **Customer Portal**: http://localhost:3000
- **MailHog Web UI**: http://localhost:8025
- **PostgreSQL**: localhost:5432

### 2. Check Services Status
```bash
docker compose ps
```

### 3. View Backend Logs
```bash
docker compose logs -f backend
```

### 4. View Emails in MailHog
Open http://localhost:8025 in your browser to see all emails sent by the system.

### 5. Run Database Migrations
```bash
docker compose exec backend alembic upgrade head
```

## Testing Email Verification

### Using cURL:
```bash
# 1. Send verification code
curl -X POST http://localhost:8000/api/v1/auth/send-verification-code \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# 2. Check MailHog UI at http://localhost:8025 for the PIN

# 3. Verify PIN
curl -X POST http://localhost:8000/api/v1/auth/verify-pin \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "pin": "123456"}'

# Response will include access token:
# {"access_token": "eyJ...", "token_type": "bearer"}

# 4. Use token to access protected endpoints
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJ..."
```

### Using Flutter App:
1. Click "Get Started"
2. Enter your email address
3. Click "Send Verification Code"
4. Check MailHog at http://localhost:8025
5. Copy the 6-digit PIN from the email
6. Enter PIN in the app
7. You're logged in!

## Database Access

### Connect to PostgreSQL:
```bash
docker compose exec db psql -U postgres -d ble_tracker
```

### View Users:
```sql
SELECT id, email, email_verified, created_at FROM users;
```

### View Verification PINs:
```sql
SELECT email, pin, is_used, expires_at, created_at 
FROM verification_pins 
ORDER BY created_at DESC;
```

### View BLE Tags:
```sql
SELECT u.email, b.imei, b.device_name, b.added_at 
FROM ble_tags b 
JOIN users u ON b.user_id = u.id
ORDER BY b.added_at DESC;
```

## Production Configuration

For production, replace MailHog with a real SMTP service:

### Update `.env`:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@yourdomain.com
```

### Supported SMTP Providers:
- **Gmail**: smtp.gmail.com:587
- **SendGrid**: smtp.sendgrid.net:587
- **AWS SES**: email-smtp.us-east-1.amazonaws.com:587
- **Mailgun**: smtp.mailgun.org:587

## Security Notes

1. **PIN Expiration**: PINs expire after 10 minutes
2. **One-Time Use**: Each PIN can only be used once
3. **Password Hashing**: Passwords are hashed using bcrypt
4. **JWT Tokens**: Access tokens expire after 30 days
5. **HTTPS Required**: Use HTTPS in production

## Troubleshooting

### MailHog not receiving emails:
```bash
# Check if MailHog is running
docker compose ps mailhog

# Check backend logs
docker compose logs backend | grep -i mail

# Restart services
docker compose restart backend mailhog
```

### Database migration errors:
```bash
# Reset database (WARNING: Deletes all data)
docker compose down -v
docker compose up -d
docker compose exec backend alembic upgrade head
```

### Port conflicts:
If ports are already in use, update `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Backend
  - "8026:8025"  # MailHog Web UI
```

## API Documentation

Interactive API docs available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
