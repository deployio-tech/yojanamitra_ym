from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    users_data = []
    
    for i in range(1, 11):
        email = f'test{i}@gmail.com'
        
        # Check if exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            print(f'{email} already exists - ID: {existing.id}')
            users_data.append(f'{email} | ID: {existing.id} | Password: password123')
            continue
        
        # Create user
        user = User()
        user.name = 'test user'
        user.email = email
        user.password_hash = generate_password_hash('password123')
        user.mobile = f'999999999{i}'
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
        users_data.append(f'{email} | ID: (will commit) | Password: password123')
    
    db.session.commit()
    
    # Get actual IDs
    print('\n=== CREATED USERS ===')
    for i in range(1, 11):
        email = f'test{i}@gmail.com'
        user = User.query.filter_by(email=email).first()
        if user:
            print(f'{email} | User ID: {user.id} | Password: password123')
    
    print('\nAll users created with password: password123')
