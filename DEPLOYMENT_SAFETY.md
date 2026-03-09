# 🔒 Deployment Safety Guide

## Critical Rule: Main Branch = Production Ready

**NEVER commit development URLs (localhost, 192.168.x.x, etc.) to the main branch.**

## Current Configuration ✅

Your repository is properly configured:

- **Flutter App**: Production URL (`https://pinplot.me`) is hardcoded as default in `lib/config/environment.dart`
- **Main Branch**: Always contains production-ready configuration
- **Git Hooks**: Automatically prevent localhost URLs from being committed

## How It Works

### 1. Environment Configuration

The Flutter app uses `lib/config/environment.dart` which:

```dart
// Production URL is the DEFAULT (safe for deployment)
static const String _productionUrl = 'https://pinplot.me';

// Development URL only loads with explicit flag
static String get apiBaseUrl {
  // Returns production unless ENV=dev is set
}
```

### 2. Development Workflow

**For Local Development:**

```bash
cd gps-tracker/mobile-app/ble_tracker_app

# Run with development environment (uses localhost:8000)
flutter run --dart-define=ENV=dev

# Build web for local testing
flutter build web --dart-define=ENV=dev
```

**For Production Deployment:**

```bash
# Build ALWAYS defaults to production (no flags needed)
flutter build web --release

# Or explicitly specify production
flutter build web --release --dart-define=ENV=prod
```

### 3. Git Hook Protection

Install the pre-commit hook:

```bash
# From repository root
cd /Users/carl/Documents/MobileCode/mobileGPS
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit
```

This hook automatically:
- ✅ Scans staged files for localhost URLs
- ❌ Blocks commits containing development URLs
- ✅ Allows production URLs (`https://pinplot.me`)

### 4. Backend Configuration

Backend uses Docker Compose environment variables:

**Development (docker-compose.yml):**
```yaml
# Uses .env file for local development
env_file:
  - ./backend/.env
```

**Production (docker-compose.production.yml):**
```yaml
# Uses environment variables from hosting platform
environment:
  DATABASE_URL: ${DATABASE_URL}
  SECRET_KEY: ${SECRET_KEY}
  # Never hardcoded secrets
```

## Testing Before Deployment

### Pre-Deployment Checklist

Run these commands before pushing to main:

```bash
# 1. Check for localhost in Flutter code
grep -r "localhost" gps-tracker/mobile-app/ble_tracker_app/lib/services/

# 2. Verify production URL is set
grep "baseUrl\|apiBaseUrl" gps-tracker/mobile-app/ble_tracker_app/lib/**/*.dart

# 3. Build production version
cd gps-tracker/mobile-app/ble_tracker_app
flutter build web --release

# 4. Check built files for localhost (should find nothing)
grep -r "localhost" build/web/

# 5. Check backend environment
cd ../../
grep "DATABASE_URL" backend/.env  # Should NOT be in git
git status  # Verify no .env files staged
```

## Common Mistakes to Avoid

### ❌ DON'T DO THIS:

```dart
// WRONG - Hardcoded localhost in service file
static const String baseUrl = 'http://localhost:8000';
```

### ✅ DO THIS:

```dart
// CORRECT - Use environment configuration
import 'package:ble_tracker_app/config/environment.dart';

class AuthService {
  static String get baseUrl => Environment.apiBaseUrl;
}
```

## Fixing Backend Connection

Currently, backend is failing due to password mismatch. Fix:

```bash
cd gps-tracker/backend

# Check current password in .env
grep "DATABASE_URL" .env

# Should match docker-compose.yml default:
# DATABASE_URL=postgresql://ble_user:ble_password@db:5432/ble_tracker

# Restart services
cd ..
docker compose down
docker compose up -d
```

## CI/CD Integration

Add this to your GitHub Actions workflow to prevent deployment with wrong URLs:

```yaml
- name: Verify Production Configuration
  run: |
    # Fail if localhost found in services
    if grep -r "localhost" gps-tracker/mobile-app/ble_tracker_app/lib/services/; then
      echo "❌ ERROR: localhost found in production code"
      exit 1
    fi
    
    # Verify production URL exists
    if ! grep -q "https://pinplot.me" gps-tracker/mobile-app/ble_tracker_app/lib/config/environment.dart; then
      echo "❌ ERROR: Production URL not found"
      exit 1
    fi
```

## Summary

✅ **Main branch is safe**: Production URL is hardcoded as default  
✅ **Local dev is easy**: Use `--dart-define=ENV=dev` flag  
✅ **Git hooks protect**: Auto-block commits with localhost  
✅ **CI/CD verifies**: Automated checks before deployment  

**Remember**: If it's not production-ready, it shouldn't be in the main branch!
