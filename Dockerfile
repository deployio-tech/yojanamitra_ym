# YojanaMitra SQLite Docker Image
FROM python:3.11-slim

WORKDIR /app

# Install only curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Initialize database on startup
RUN python -c "from app import app, db; app.app_context().push(); db.create_all(); print('✅ Database tables created')" || echo "⚠️ Database initialization skipped"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Expose port
EXPOSE 5000

# Environment
ENV FLASK_APP=app.py \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
