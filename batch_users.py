import sys
sys.path.insert(0, r'C:\yojanamitra_complete')

from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Get template user
    template = User.query.filter_by(email='test@example.com').first()
    
    if not template:
        print("Template user not found, creating default profile")
        template = User(
            name='test user',
            email='test@example.com',
            password_hash=generate_password_hash('password123'),
            mobile='9999999999',
            age=30,
            gender='Male',
            state='Karnataka',
            income=5000000,
            annual_family_income=5000000,
            caste='General',
            residence='Urban',
            education='Graduation',
            employment_status='Employed',
            is_citizen='Yes',
            has_bank_account='Yes',
            aadhaar_available='Yes'
        )
        db.session.add(template)
        db.session.commit()
    
    print("Creating 10 users...")
    results = []
    
    for i in range(1, 11):
        email = f'test{i}@gmail.com'
        existing = User.query.filter_by(email=email).first()
        
        if existing:
            results.append(f'{email} | ID: {existing.id} | Password: password123')
            continue
        
        user = User(
            name='test user',
            email=email,
            password_hash=generate_password_hash('password123'),
            mobile=f'999999999{i}',
            age=template.age,
            gender=template.gender,
            state=template.state,
            income=template.income,
            annual_family_income=template.annual_family_income,
            caste=template.caste,
            residence=template.residence,
            education=template.education,
            employment_status=template.employment_status,
            is_citizen=template.is_citizen,
            has_bank_account=template.has_bank_account,
            aadhaar_available=template.aadhaar_available
        )
        db.session.add(user)
    
    db.session.commit()
    
    print("\n=== USER CREDENTIALS ===")
    for i in range(1, 11):
        email = f'test{i}@gmail.com'
        user = User.query.filter_by(email=email).first()
        if user:
            print(f'{email} | User ID: {user.id} | Password: password123')
    
    print("\nAll users created with password: password123")
