from app import app, db
import os
print("CWD:", os.getcwd())
with app.app_context():
    print("Database URI:", app.config['SQLALCHEMY_DATABASE_URI'])
    print("SQLAlchemy Metadata Tables:", db.metadata.tables.keys())
    print("Checking for missing tables...")
    db.create_all()
    print("Database tables synchronized.")
