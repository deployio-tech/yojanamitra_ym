from app import app, db
with app.app_context():
    title_conds = db.session.execute(db.text(
        "SELECT scheme_id, field, value FROM conditions WHERE source='title_inference'"
    )).fetchall()
    print("Title Inference Conditions:")
    for sid, field, value in title_conds:
        print(f"  Scheme {sid}: {field} = {value}")
    print()
    sources = db.session.execute(db.text(
        "SELECT source, COUNT(*) as cnt FROM conditions GROUP BY source ORDER BY cnt DESC"
    )).fetchall()
    print("Source Distribution:")
    for src, cnt in sources:
        print(f"  {src}: {cnt}")
    print()
    total = db.session.execute(db.text("SELECT COUNT(*) FROM conditions")).scalar()
    fields = db.session.execute(db.text("SELECT COUNT(DISTINCT field) FROM conditions")).scalar()
    print("=" * 50)
    print(f"Total: {total}")
    print(f"Unique fields: {fields}")
