"""
Quick summary extraction from full audit
"""
import os
import sys
sys.path.insert(0, os.getcwd())

from app import app, User, Scheme
from app.engine.eligibility import EligibilityEngine, get_profile_value, evaluate_single, FIELD_MAP
from app.engine.context import ContextualReasoner
from app.engine.questions import QuestionEngine, is_user_answerable

def get_summary():
    with app.app_context():
        user = User.query.filter_by(email='shreyas6504@gmail.com').first()
        profile = user.get_profile_dict()
        
        all_schemes = Scheme.query.filter_by(is_active=True).all()
        engine = EligibilityEngine()
        ctx = ContextualReasoner()
        
        from app.engine_compat import get_orchestrator
        candidates = get_orchestrator(app.config).prefilter(user, all_schemes)
        
        false_eligible = 0
        false_ineligible = 0
        total = 0
        
        for scheme in candidates:
            total += 1
            eo = engine.evaluate(scheme, profile, ctx.score(scheme, profile))
            
            if eo.result == 'possible':
                qengine = QuestionEngine(ctx, max_questions=None)
                questions = qengine.select_questions([(scheme, eo)], profile)
                answered_profile = dict(profile)
                for q in questions:
                    answered_profile[q.field] = True
                    answered_profile[FIELD_MAP.get(q.field, q.field)] = True
                eo = engine.evaluate(scheme, answered_profile, ctx.score(scheme, answered_profile))
            
            # Check conditions
            hard_user_fail = 0
            hard_user_pass = 0
            hard_user_total = 0
            
            for cond in scheme.conditions:
                if not is_user_answerable(cond.field):
                    continue
                cond_type = getattr(cond, 'condition_type', None) or ('HARD' if getattr(cond, 'is_hard', False) else 'SOFT')
                if cond_type.upper() != 'HARD':
                    continue
                
                hard_user_total += 1
                actual = get_profile_value(cond.field, profile)
                if actual is None:
                    continue
                result = evaluate_single(cond, profile)
                if result.status == 'pass':
                    hard_user_pass += 1
                elif result.status == 'fail':
                    hard_user_fail += 1
            
            if eo.result == 'eligible' and hard_user_fail > 0:
                false_eligible += 1
            if eo.result == 'ineligible' and hard_user_total > 0 and hard_user_pass == hard_user_total:
                false_ineligible += 1
        
        print(f"Total Schemes: {total}")
        print(f"False Eligible (HARD USER FAIL but ELIGIBLE): {false_eligible}")
        print(f"False Ineligible (ALL HARD PASS but INELIGIBLE): {false_ineligible}")

if __name__ == "__main__":
    get_summary()