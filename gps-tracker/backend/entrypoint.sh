#!/bin/bash
set -e

echo "🔧 Initializing admin user..."
python init_admin.py || true

echo "🚀 Starting backend server..."
exec "$@"
