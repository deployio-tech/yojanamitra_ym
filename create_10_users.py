"""
Create 10 users with same profile as test@example.com
Emails: test1@gmail.com to test10@gmail.com
Password: password123 for all
"""
from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Get template user profile
    template_user = User.query.filter_by(email='test@example.com').first()
    
    if not template_user:
        print("Template user test@example.com not found. Creating with default profile...")
        # Create template user first
        template_user = User(
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
        db.session.add(template_user)
        db.session.commit()
        print(f"Created template user with ID: {template_user.id}")
    
    # Create 10 users
    created_users = []
    for i in range(1, 11):
        email = f'test{i}@gmail.com'
        
        # Check if user already exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            print(f"User {email} already exists (ID: {existing.id})")
            created_users.append((email, existing.id))
            continue
        
        # Create new user with same profile as template
        new_user = User(
            name='test user',
            email=email,
            password_hash=generate_password_hash('password123'),
            mobile=f'999999999{i}',
            age=template_user.age,
            gender=template_user.gender,
            state=template_user.state,
            income=template_user.income,
            annual_family_income=template_user.annual_family_income,
            caste=template_user.caste,
            residence=template_user.residence,
            education=template_user.education,
            employment_status=template_user.employment_status,
            is_citizen=template_user.is_citizen,
            has_bank_account=template_user.has_bank_account,
            aadhaar_available=template_user.aadhaar_available
        )
        
        db.session.add(new_user)
        created_users.append((email, 'pending'))
    
    db.session.commit()
    
    # Write results to file
    with open('created_users.txt', 'w') as f:
        f.write("=== USERS CREATED ===\n")
        for email, uid in created_users:
            if uid == 'pending':
                user = User.query.filter_by(email=email).first()
                line = f"Email: {email} | User ID: {user.id} | Password: password123\n"
                f.write(line)
            else:
                line = f"Email: {email} | User ID: {uid} | Password: password123\n"
                f.write(line)
        f.write("\nAll users created with password: password123\n")
    
    # Also print to console
    print("\n=== USERS CREATED ===")
    for email, uid in created_users:
        if uid == 'pending':
            user = User.query.filter_by(email=email).first()
            print(f"Email: {email} | User ID: {user.id} | Password: password123")
        else:
            print(f"Email: {email} | User ID: {uid} | Password: password123")
    
    print("\nAll users created with password: password123")
