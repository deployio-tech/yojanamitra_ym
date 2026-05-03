from app import app, db, Scheme
with app.app_context():
    s = Scheme.query.filter(Scheme.name.like('%Indirect Tax Internship%')).first()
    if s:
        print(f"ID: {s.id}, Name: {s.name}")
    else:
        print("Not found")
