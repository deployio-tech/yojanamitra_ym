import os
import json
import sqlite3
from types import SimpleNamespace
from eligibility_engine_strict_v21 import StrictEligibilityEngine, UserProfile
from scheme_rule_adapter import build_rule

DB_PATH = r"C:\scrollyym\yojana-mitra-backend\instance\yojanamitra.db"

def final_verify():
    # Mock user data for shreyas6504@gmail.com
    user = UserProfile(
        user_id="shreyas6504@gmail.com",
        age=21,
        gender="Male",
        state="KA",
        income_annual=0,
        occupation=["Student"],
        caste_category="general",
        residence="urban",
        is_disabled=False,
        is_senior_citizen=False,
        is_minority=False,
        is_widow=False
    )

    engine = StrictEligibilityEngine()
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    target_names = [
        "Pradhan Mantri Jeevan Jyoti Bima Yojana (PMJJBY)",
        "Pradhan Mantri Suraksha Bima Yojana (PMSBY)",
        "Atal Pension Yojana (APY)"
    ]
    
    print("--- Final System Verification (Deterministic vs AI Baseline) ---")
    for name in target_names:
        cursor.execute("SELECT * FROM scheme WHERE name LIKE ?", (f"%{name}%",))
        row = cursor.fetchone()
        if not row:
            print(f"Scheme not found in DB: {name}")
            continue
            
        # Convert sqlite3.Row to an object with attributes
        s = SimpleNamespace(**dict(row))
        
        rule = build_rule(s)
        result = engine.evaluate(user, rule)
        print(f"Scheme: {s.name}")
        print(f"Deterministic Result: {result.eligibility_class}")
        print(f"Rejection/Detail: {result.rejection_detail}")
        print("-" * 30)
    
    conn.close()

if __name__ == "__main__":
    final_verify()
