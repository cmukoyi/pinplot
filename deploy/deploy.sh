#!/bin/bash
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Beacon Telematics Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ -z "$SSH_HOST" ] || [ -z "$SSH_USER" ] || [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: SSH_HOST, SSH_USER, and DATABASE_URL must be set"
    exit 1
fi

echo "Deploying to: $SSH_USER@$SSH_HOST"
echo ""

echo "Step 1: Testing SSH connection..."
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes -o StrictHostKeyChecking=no "$SSH_USER@$SSH_HOST" true 2>/dev/null; then
    echo "❌ SSH connection failed"
    exit 1
fi
echo "✅ SSH OK"
echo ""

echo "Step 2: Creating environment file on server..."

# Create .env file locally first
cat > /tmp/.env << EOF
DATABASE_URL=$DATABASE_URL
SECRET_KEY=$SECRET_KEY
POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=$POSTGRES_DB
SENDGRID_API_KEY=$SENDGRID_API_KEY
ALLOWED_ORIGINS=$ALLOWED_ORIGINS
MZONE_CLIENT_ID=$MZONE_CLIENT_ID
MZONE_CLIENT_SECRET=$MZONE_CLIENT_SECRET
MZONE_USERNAME=$MZONE_USERNAME
MZONE_PASSWORD=$MZONE_PASSWORD
FROM_EMAIL=$FROM_EMAIL
DEBUG=False
ENVIRONMENT=production
EOF

ssh -o StrictHostKeyChecking=no "$SSH_USER@$SSH_HOST" 'mkdir -p ~/beacon-telematics/gps-tracker/backend'
scp -o StrictHostKeyChecking=no /tmp/.env "$SSH_USER@$SSH_HOST:~/beacon-telematics/gps-tracker/backend/.env"
ssh -o StrictHostKeyChecking=no "$SSH_USER@$SSH_HOST" 'chmod 600 ~/beacon-telematics/gps-tracker/backend/.env'
rm /tmp/.env

echo "✅ .env created"

echo ""
echo "Step 3: Syncing code to server..."
rsync -avz --delete \
    --exclude '.git' \
    --exclude '.github' \
    --exclude 'node_modules' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude 'backend/.env' \
    --exclude '.dart_tool' \
    --exclude 'beacon_telematics_postgres_data' \
    ./gps-tracker/ \
    "$SSH_USER@$SSH_HOST:~/beacon-telematics/gps-tracker/" > /dev/null

echo "✅ Code synced"
echo ""

echo "Step 4: Deploying containers on server..."
ssh -o StrictHostKeyChecking=no "$SSH_USER@$SSH_HOST" << 'DEPLOYEOF'
set -e
cd ~/beacon-telematics/gps-tracker
if [ ! -f backend/.env ]; then
    echo "❌ .env not found!"
    exit 1
fi
docker compose down --remove-orphans || true
docker images --format '{{.Repository}}:{{.Tag}}' | grep -E 'flutter|admin' | xargs -r docker rmi -f 2>/dev/null || true
echo "Building containers..."
docker compose build --no-cache flutter-web admin-portal
docker compose build backend customer
echo "Starting services..."
docker compose up -d
sleep 20
docker compose ps
echo "✅ Deployment complete!"
DEPLOYEOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DEPLOYMENT SUCCESSFUL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Access points:"
echo "  http://$SSH_HOST:8001/api/health     (Backend API)"
echo "  http://$SSH_HOST:3010/                (Admin Portal)"
echo "  http://$SSH_HOST:3011/                (Customer Dashboard)"
echo "  http://$SSH_HOST:3012/                (Flutter Web)"
echo ""
