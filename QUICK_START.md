# YojanaMitra - Quick Start Guide

## ✅ Status: SYSTEM OPERATIONAL

The database is initialized and the Flask app is ready to run.

---

## Start the Application

### Method 1: Run the Flask App (Recommended for Development)

```bash
python app.py
```

The app will start on `http://localhost:5000`

**Output:**
```
 * Running on http://127.0.0.1:5000
 * Press CTRL+C to quit
```

### Method 2: Run with Gunicorn (Recommended for Production)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

## Test the Application

### Option 1: Quick Startup Test
```bash
python test_startup.py
```
Tests database + models without running server.

### Option 2: Server Test
```bash
python test_server.py
```
Starts server briefly, tests homepage, then shuts down.

### Option 3: Full System Verification
```bash
python verify_complete_system.py
```
Comprehensive check of database, app, server, and API.

---

## Initialize Database (If Needed)

**WARNING**: This will DROP and recreate all tables!

```bash
python init_database.py
```

---

## Default Admin Credentials

- **Email**: admin@yojanamitra.gov.in
- **Password**: admin123

(Only works after running init_database.py or first app startup)

---

## What Changed

### Database
- ✅ All 16 tables created with complete schemas
- ✅ User table: 78 columns (all eligibility attributes)
- ✅ Scheme table: 43 columns (all scheme criteria)
- ✅ Database location: `instance/yojanamitra.db`

### Code
- ✅ Disabled scheme seeding (was causing startup error)
- ✅ All JavaScript fixes from previous session maintained
- ✅ All API credentials properly configured

### Scripts
- ✅ Added init_database.py for database initialization
- ✅ Added test scripts for verification
- ✅ Added comprehensive system verification script

---

## Troubleshooting

### Issue: Database file not found

**Solution:**
```bash
python init_database.py
```

### Issue: "no such table: user"

**Solution:** Run initialization:
```bash
python init_database.py
```

### Issue: Port 5000 already in use

**Solution:** Specify a different port:
```bash
python app.py --port 5001
```

Or kill the existing process:
```bash
lsof -ti:5000 | xargs kill -9   # Linux/Mac
netstat -ano | findstr :5000    # Windows
```

### Issue: "ImportError: No module named..."

**Solution:** Install dependencies:
```bash
pip install -r requirements.txt
```

---

## API Endpoints to Test

### Register User
```bash
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Test User",
    "email":"test@example.com",
    "password":"password123"
  }'
```

### Login
```bash
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "email":"test@example.com",
    "password":"password123"
  }'
```

### Get User Profile
```bash
curl -X GET http://localhost:5000/api/user \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Recommendations
```bash
curl -X GET http://localhost:5000/api/recommendations \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Key Files

| File | Purpose |
|------|---------|
| app.py | Main Flask application |
| instance/yojanamitra.db | SQLite database |
| static/dashboard.html | Frontend UI |
| init_database.py | Database initialization |
| test_startup.py | Startup verification |
| verify_complete_system.py | Full system test |
| SYSTEM_RECOVERY_REPORT.md | Detailed recovery report |

---

## Database Schema Overview

### User Table (78 columns)
Demographics, eligibility attributes, banking info, documents, achievements

### Scheme Table (43 columns)
Scheme details, beneficiary criteria, income ranges, education levels, occupations

### Support Tables (14 additional)
- conditions: Eligibility criteria
- question_answers: User responses
- scheme_flags: Problem schemes
- admin_notification: Notifications
- eligibility_results: Cached results

---

## Production Deployment

### Before Going Live

1. ✅ Change default admin password
2. ✅ Set environment variables for secrets
3. ✅ Migrate to PostgreSQL database
4. ✅ Set up HTTPS/SSL certificates
5. ✅ Configure backups
6. ✅ Set up monitoring/logging

### Deploy

```bash
# Production server example (using Gunicorn)
gunicorn --workers 4 --bind 0.0.0.0:5000 app:app

# Or with Nginx reverse proxy
# Point nginx to gunicorn on 127.0.0.1:8000
```

---

## Support & Debugging

### Check Database Status
```bash
python -c "from app import db, User, Scheme; print(f'Users: {User.query.count()}, Schemes: {Scheme.query.count()}')"
```

### View Recent Errors
```bash
tail -f app.log  # If logging is configured
```

### Check System Resources
```bash
ps aux | grep python      # Linux/Mac
Get-Process python        # Windows
```

---

## Quick Reference Commands

```bash
# Initialize database
python init_database.py

# Start app
python app.py

# Run tests
python test_startup.py
python test_server.py
python verify_complete_system.py

# Verify database
sqlite3 instance/yojanamitra.db ".tables"
sqlite3 instance/yojanamitra.db "SELECT COUNT(*) FROM user;"
```

---

**Status**: ✅ READY FOR TESTING  
**Last Updated**: April 7, 2026  
**Maintained By**: YojanaMitra Development Team

