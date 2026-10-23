#!/usr/bin/env bash
# ==============================================================================
# PrintX Backend Production Build Script for Render / Cloud Hosts
# ==============================================================================
set -o errexit

echo "📦 Installing backend Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Ensure admin_side static files are bundled if present in root
if [ -d "../admin_side" ] && [ ! -d "admin_side" ]; then
    echo "📋 Copying admin_side portal assets..."
    cp -r ../admin_side ./admin_side
fi

echo "🗄️ Running database migrations..."
python manage.py migrate --noinput

echo "🎨 Collecting static files for WhiteNoise..."
python manage.py collectstatic --noinput

echo "✅ Backend build completed successfully!"
