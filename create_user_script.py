"""
Create test user - simplified version
Write results to output file
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, db, User
    from werkzeug.security import generate_password_hash
    
    with app.app_context():
        # Check if user exists
        existing = User.query.filter_by(email='testuser@example.com').first()
        
        if existing:
            user = existing
            result = f"""
USER ALREADY EXISTS
User ID: {user.id}
Email: {user.email}
Password: (existing password)
State: {user.state}
Income: {user.income}
"""
        else:
            # Create user with Karnataka (moderate scheme count) and high income
            user = User(
                name='test user',
                email='testuser@example.com',
                password_hash=generate_password_hash('test123'),
                mobile='9999999999',
                age=30,
                gender='Male',
                state='Karnataka',
                income=5000000,  # 50 lakh - high income
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
            
            result = f"""
USER CREATED SUCCESSFULLY
User ID: {user.id}
Email: testuser@example.com
Password: test123
State: {user.state}
Income: {user.income}
"""
        
        # Write to file
        with open('user_credentials.txt', 'w') as f:
            f.write(result)
        
        print(result.strip())
        
except Exception as e:
    error_msg = f"ERROR: {str(e)}\n"
    with open('user_credentials.txt', 'w') as f:
        f.write(error_msg)
    print(error_msg)
    import traceback
    traceback.print_exc()
