print("Starting script...")
print("Hello from Python")

# Try to import app
try:
    from app import app, db, User
    from werkzeug.security import generate_password_hash
    print("Imports successful")
    
    with app.app_context():
        print("In app context")
        
        # Check existing users
        count = User.query.count()
        print(f"Existing users: {count}")
        
        # Create user
        user = User(
            name='test user',
            email='testuser@example.com',
            password_hash=generate_password_hash('test123'),
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
        
        db.session.add(user)
        db.session.commit()
        print(f"User created with ID: {user.id}")
        print(f"\n--- CREDENTIALS ---")
        print(f"User ID: {user.id}")
        print(f"Email: testuser@example.com")
        print(f"Password: test123")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
