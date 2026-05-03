from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Delete if exists
    old = User.query.filter_by(email='testuser@example.com').first()
    if old:
        db.session.delete(old)
        db.session.commit()
    
    # Create user with high income and common state
    user = User()
    user.name = 'test user'
    user.email = 'testuser@example.com'
    user.password_hash = generate_password_hash('test123')
    user.mobile = '9999999999'
    user.age = 30
    user.gender = 'Male'
    user.state = 'Karnataka'
    user.income = 5000000
    user.annual_family_income = 5000000
    user.caste = 'General'
    user.residence = 'Urban'
    user.education = 'Graduation'
    user.employment_status = 'Employed'
    user.is_citizen = 'Yes'
    user.has_bank_account = 'Yes'
    user.aadhaar_available = 'Yes'
    
    db.session.add(user)
    db.session.commit()
    
    print(f"User ID: {user.id}")
    print(f"Email: testuser@example.com")
    print(f"Password: test123")
