#!/bin/bash
# Pre-deployment Backup Script for Beacon Telematics
# Run this before deployment to backup critical data

set -e

BACKUP_DIR=~/beacon-telematics-backups
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_PATH="$BACKUP_DIR/backup-$TIMESTAMP"

echo "🔒 Starting Beacon Telematics Pre-Deployment Backup..."
echo "📁 Backup location: $BACKUP_PATH"

# Create backup directory
mkdir -p "$BACKUP_PATH"

# Backup environment files
echo "📝 Backing up environment files..."
if [ -f ~/beacon-telematics/gps-tracker/backend/.env ]; then
    cp ~/beacon-telematics/gps-tracker/backend/.env "$BACKUP_PATH/backend.env"
    echo "✅ Backend .env backed up"
else
    echo "⚠️  Backend .env not found"
fi

if [ -f ~/beacon-telematics/gps-tracker/.env ]; then
    cp ~/beacon-telematics/gps-tracker/.env "$BACKUP_PATH/root.env"
    echo "✅ Root .env backed up"
fi

# Backup database
echo "💾 Backing up PostgreSQL database..."
if docker ps | grep -q beacon_telematics_db; then
    docker exec beacon_telematics_db pg_dump -U beacon_user beacon_telematics > "$BACKUP_PATH/database.sql"
    echo "✅ Database backed up ($(du -h $BACKUP_PATH/database.sql | cut -f1))"
else
    echo "⚠️  Database container not running, skipping DB backup"
fi

# Backup docker-compose.yml
if [ -f ~/beacon-telematics/gps-tracker/docker-compose.yml ]; then
    cp ~/beacon-telematics/gps-tracker/docker-compose.yml "$BACKUP_PATH/docker-compose.yml"
    echo "✅ docker-compose.yml backed up"
fi

# List all containers state
echo "📊 Recording container states..."
docker ps -a | grep beacon_telematics > "$BACKUP_PATH/containers-state.txt" || true

# Keep only last 5 backups
echo "🧹 Cleaning old backups (keeping last 5)..."
cd "$BACKUP_DIR"
ls -dt backup-* | tail -n +6 | xargs rm -rf 2>/dev/null || true

echo "✅ Backup complete: $BACKUP_PATH"
echo "📋 Backup contains:"
ls -lh "$BACKUP_PATH"

# Record last backup path
echo "$BACKUP_PATH" > ~/beacon-telematics-backups/LAST_BACKUP
