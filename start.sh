#!/usr/bin/env bash
# ==============================================================================
# Supply Chain AI Platform - Unified Startup Runner
# One command to run migrations, seed data, and launch all platform services.
# Usage: ./start.sh
# ==============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "========================================================================"
echo "🚀 INITIATING SUPPLY CHAIN & INVENTORY AI PLATFORM"
echo "========================================================================"

# 1. Virtual Environment Activation
if [ -d "venv" ]; then
    echo "📦 Activating Python virtual environment..."
    source venv/bin/activate
elif [ -d "../venv" ]; then
    source ../venv/bin/activate
else
    echo "⚠️  No venv found. Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# 2. Database Migrations
echo "🗄️  [Step 1/3] Applying database migrations..."
python manage.py migrate --noinput

# 3. Check and Seed Initial Data
echo "🌱 [Step 2/3] Checking catalog data..."
python manage.py shell -c "
from inventory_core.models import Product
from django.core.management import call_command
if Product.objects.count() == 0:
    print('Catalog empty: seeding synthetic supply chain data...')
    call_command('seed_supply_chain_data')
else:
    print('Catalog populated with', Product.objects.count(), 'SKUs.')
"

# 4. Launch Services in Concurrency
echo "🌐 [Step 3/3] Launching Web Server, Celery Worker, and Beat Scheduler..."

CELERY_PIDS=()

cleanup() {
    echo ""
    echo "🛑 Shutting down Supply Chain AI Platform..."
    for pid in "${CELERY_PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid" 2>/dev/null || true
        fi
    done
    wait 2>/dev/null || true
    echo "👋 All processes terminated."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Start Celery Worker in background if Redis is running or in dev mode
if command -v celery &> /dev/null; then
    celery -A supply_chain_ai worker -l info --concurrency=2 &
    CELERY_PIDS+=($!)

    celery -A supply_chain_ai beat -l info &
    CELERY_PIDS+=($!)
fi

echo ""
echo "========================================================================"
echo "✨ Web UI Dashboard:   http://127.0.0.1:8000/"
echo "📡 REST API Root:      http://127.0.0.1:8000/api/v1/"
echo "📊 Telemetry Endpoint: http://127.0.0.1:8000/api/v1/dashboard/replenishment/"
echo "📋 Django Admin:       http://127.0.0.1:8000/admin/"
echo "========================================================================"
echo "Press Ctrl+C to stop all services."
echo ""

# Run Django in foreground
exec python manage.py runserver 0.0.0.0:8000
