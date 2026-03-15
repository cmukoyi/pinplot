#!/bin/bash
################################################################################
# BEACON TELEMATICS - SIMPLE ROLLBACK SCRIPT
# 
# Purpose: Quickly restore app and database to last working state
# Usage: bash rollback.sh
################################################################################

set -e

cd /root/beacon-telematics/gps-tracker || { echo "❌ Directory not found"; exit 1; }

echo ""
echo "🚨 ROLLBACK INITIATED"
echo ""

# Find latest backup
LATEST_BACKUP=$(ls -t backups/*/db_backup_*.sql 2>/dev/null | head -1 || ls -t backups/*/beacon_db.sql 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
  echo "❌ ERROR: No database backup found in backups/"
  echo "   Checked: /root/beacon-telematics/gps-tracker/backups/*/*.sql"
  exit 1
fi

BACKUP_DIR=$(dirname "$LATEST_BACKUP")
echo "📦 Using backup: $LATEST_BACKUP"
echo ""

# Confirm
read -p "⚠️  This will restore database and revert code. Continue? (yes/no): " response
if [[ "$response" != "yes" && "$response" != "y" ]]; then
  echo "Rollback cancelled"
  exit 0
fi

echo ""
echo "🔄 Step 1: Stopping containers..."
docker compose down -q
echo "✅ Containers stopped"

echo ""
echo "🔄 Step 2: Restoring database from backup..."
docker compose up -d db > /dev/null 2>&1
sleep 8

# Drop and restore database
docker compose exec -T db psql -U beacon_user -c "DROP DATABASE IF EXISTS beacon_telematics;" 2>/dev/null || true
docker compose exec -T db psql -U beacon_user -c "CREATE DATABASE beacon_telematics;" 2>/dev/null || true
docker compose exec -T db psql -U beacon_user -d beacon_telematics < "$LATEST_BACKUP" 2>/dev/null

echo "✅ Database restored"

echo ""
echo "🔄 Step 3: Reverting code to last git tag..."
git stash > /dev/null 2>&1 || true
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "HEAD~1")
git checkout "$LAST_TAG" > /dev/null 2>&1
echo "✅ Code reverted to: $LAST_TAG"

echo ""
echo "🔄 Step 4: Restarting all services..."
docker compose up -d > /dev/null 2>&1
sleep 12

echo "✅ Services restarted"

echo ""
echo "================================"
echo "✅ ROLLBACK COMPLETE!"
echo "================================"
echo ""
echo "Verify app:"
echo "  🔗 https://beacontelematics.co.uk"
echo ""
echo "View logs if needed:"
echo "  📋 docker compose logs -f backend"
echo ""
