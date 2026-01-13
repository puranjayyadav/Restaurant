#!/bin/bash
# Build script for Render deployment

set -e  # Exit on error

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Running migrations..."
python manage.py migrate --noinput || echo "Migration failed, continuing..."

echo "Build complete!"

