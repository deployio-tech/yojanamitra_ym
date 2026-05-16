#!/bin/bash
# Entrypoint script for YojanaMitra Docker container
# Initializes database and starts gunicorn

set -e

echo "🚀 Starting YojanaMitra..."

# Initialize database if needed
echo "📦 Checking database..."
python -c "
from app import app, db
import os

app.app_context().push()

# Check if tables exist
try:
    # Try a simple query
    db.session.execute('SELECT 1 FROM sqlite_master LIMIT 1')
    print('✅ Database already initialized')
except:
    print('⚙️ Creating database tables...')
    db.create_all()
    print('✅ Database tables created successfully')
finally:
    db.session.close()
"

echo "🌐 Starting Gunicorn server..."
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 --access-logfile - --error-logfile - app:app
