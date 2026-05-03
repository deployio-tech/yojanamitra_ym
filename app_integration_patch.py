"""
app_integration_patch.py
=========================
How to integrate ai_condition_evaluator into your existing Flask app.

This shows exactly which parts of your app.py to modify.
Copy-paste the relevant sections — do NOT replace your entire app.py.

STEP 1: Initialize the evaluator at app startup (add to app.py top section)
STEP 2: Replace the eligible_schemes query with AI evaluator filter
STEP 3: Replace the readiness analysis AI API call with evaluator call
"""

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1: Add to your app.py — near the top, after your imports
# ══════════════════════════════════════════════════════════════════════════════

STEP1_CODE = '''
# ── AI Condition Evaluator (add near top of app.py) ──────────────────────────
from ai_condition_evaluator import AIConditionEvaluator
from yojanamitra_eligibility_engine_v2 import ProfileNormalizer

_ai_evaluator = None
_profile_normalizer = ProfileNormalizer()

def get_ai_evaluator():
    global _ai_evaluator
    if _ai_evaluator is None:
        try:
            _ai_evaluator = AIConditionEvaluator("scheme_conditions.json")
            app.logger.info(f"AI evaluator loaded: {len(_ai_evaluator._conditions)} schemes")
        except FileNotFoundError:
            app.logger.warning("scheme_conditions.json not found. Run scheme_condition_extractor.py first.")
    return _ai_evaluator
'''

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2: Replace your dashboard/eligible schemes endpoint
# Find where you currently build eligible_schemes list and replace with this
# ══════════════════════════════════════════════════════════════════════════════

STEP2_CODE = '''
# ── Dashboard eligible schemes endpoint (REPLACE existing logic) ──────────────
@app.route("/api/eligible-schemes")
@login_required
def get_eligible_schemes():
    user = current_user  # or however you get the user

    # Build UserProfile from your User model
    profile = _profile_normalizer.normalize({
        "user_id": str(user.id),
        "dob": str(user.dob),
        "gender": user.gender or "male",
        "state": user.state or "Karnataka",
        "district": user.district or "",
        "income_annual": user.income_annual or 0,
        "annual_family_income": user.annual_family_income or user.income_annual or 0,
        "occupation": user.occupation or [],
        "caste_category": user.caste_category or "general",
        "is_farmer": user.is_farmer or False,
        "land_owned_acres": float(user.land_owned_acres or 0),
        "is_bpl": user.is_bpl or False,
        "is_govt_employee": user.is_govt_employee or False,
        "is_income_taxpayer": user.is_income_taxpayer or False,
        "is_student": user.is_student or False,
        "is_disabled": user.is_disabled or False,
        "disability_percentage": user.disability_percentage or 0,
        "is_widow": user.is_widow or False,
        "is_minority": user.is_minority or False,
        "is_orphan": user.is_orphan or False,
        "is_tribal": user.is_tribal or False,
        "is_senior_citizen": getattr(user, "is_senior_citizen", False),
        "is_self_employed": getattr(user, "is_self_employed", False),
        "is_bocw_registered": getattr(user, "is_bocw_registered", False),
        "is_migrant_worker": getattr(user, "is_migrant_worker", False),
        "is_pensioner": getattr(user, "is_pensioner", False),
        "is_single_woman": getattr(user, "is_single_woman", False),
        "has_pucca_house": getattr(user, "has_pucca_house", False),
        "is_landless": getattr(user, "is_landless", False),
        "is_abandoned_woman": getattr(user, "is_abandoned_woman", False),
        "is_first_gen_student": getattr(user, "is_first_gen_student", False),
        "is_school_dropout": getattr(user, "is_school_dropout", False),
        "marital_status": user.marital_status or "single",
        "num_children": user.num_children or 0,
        "education_level": user.education_level or "graduation",
        "has_aadhaar": getattr(user, "has_aadhaar", True),
        "aadhaar_verified": getattr(user, "aadhaar_verified", True),
        "has_pan": getattr(user, "has_pan", False),
        "has_bank_account": getattr(user, "has_bank_account", True),
        "documents_uploaded": getattr(user, "documents_uploaded", []) or [],
        "residence": user.residence or "urban",
        "religion": getattr(user, "religion", "") or "",
        "exam_percentage": float(getattr(user, "exam_percentage", 0) or 0),
    })

    evaluator = get_ai_evaluator()
    all_schemes = Scheme.query.filter_by(is_active=True).all()

    eligible = []
    for scheme in all_schemes:
        # Use AI evaluator if conditions are available
        if evaluator and evaluator.has_scheme(scheme.id):
            result = evaluator.evaluate(profile, scheme.id)
            if result.is_eligible:
                eligible.append({
                    "id": scheme.id,
                    "name": scheme.name,
                    "category": scheme.category,
                    "match_score": result.score,
                    "readiness_score": result.readiness_score,
                    "benefits": scheme.benefits,
                    "portal_link": scheme.portal_link,
                })
        # Fallback: use existing deterministic engine for schemes not yet extracted
        else:
            # Your existing engine logic here
            pass

    # Sort by readiness score descending
    eligible.sort(key=lambda x: x["readiness_score"], reverse=True)

    return jsonify({
        "schemes": eligible,
        "total": len(eligible),
        "profile_complete": profile.profile_completeness >= 0.7
    })
'''

# ══════════════════════════════════════════════════════════════════════════════
# STEP 3: Replace the AI readiness analysis call in your modal endpoint
# Find where you currently call Gemini/Claude for readiness and replace
# ══════════════════════════════════════════════════════════════════════════════

STEP3_CODE = '''
# ── Readiness analysis endpoint (REPLACE AI call with evaluator) ──────────────
@app.route("/api/schemes/<int:scheme_id>/readiness")
@login_required
def get_readiness_analysis(scheme_id: int):
    user = current_user
    evaluator = get_ai_evaluator()

    if evaluator and evaluator.has_scheme(scheme_id):
        # Pure deterministic — no AI call, instant response
        profile = _build_profile(user)  # same helper as above
        analysis = evaluator.get_readiness_analysis(profile, scheme_id)

        return jsonify({
            "readiness_score": analysis["readiness_score"],
            "is_eligible": analysis["is_eligible"],
            "items": analysis["items"],
            "notes": analysis["notes"],
            "source": "deterministic"  # for debugging
        })
    else:
        # Fallback to AI if conditions not extracted yet
        # (during transition period while extractor runs)
        return _ai_readiness_fallback(scheme_id, user)
'''

# ══════════════════════════════════════════════════════════════════════════════
# STEP 4: Run the extractor (one-time setup)
# ══════════════════════════════════════════════════════════════════════════════

STEP4_COMMANDS = """
# Test on 10 schemes first
python scheme_condition_extractor.py --limit 10

# If that works, process all schemes (takes ~2 hours for 4324 schemes at 45 RPM)
python scheme_condition_extractor.py --resume

# To debug a specific scheme
python scheme_condition_extractor.py --scheme-id 239

# If it crashes midway, just run with --resume to continue
python scheme_condition_extractor.py --resume
"""

if __name__ == "__main__":
    print("This is a reference file showing integration steps.")
    print("See STEP1_CODE, STEP2_CODE, STEP3_CODE for the actual code to add.")
    print("\nExtractor commands:")
    print(STEP4_COMMANDS)
