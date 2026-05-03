"""
app/__init__.py
Makes the app/ directory a Python package for the new engine sub-modules.
The actual Flask app lives in app.py at the project root.
(db and models are defined in app.py)
"""
from app.engine import EligibilityOrchestrator
from app.engine.eligibility import (
    EligibilityEngine, EligibilityOutput, evaluate_single,
    PASS_R, FAIL_R, UNKNOWN_C,
    ELIGIBLE, POSSIBLE, INELIGIBLE,
)
from app.engine.scorer import ResultRanker, RankedScheme
from app.engine.context import ContextualReasoner
from app.engine.questions import QuestionEngine, Question
from app.engine.profile_normalizer import ProfileNormalizer

import sys
import os
import importlib.util

_normalizer = ProfileNormalizer.get_instance()
_issues = _normalizer.validate()
if _issues:
    print("⚠️  Registry validation issues:")
    for issue in _issues:
        print(f"  - {issue}")
    print("  (Continuing — fix before next deploy)")


_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_app_py = os.path.join(_root, 'app.py')
if _root not in sys.path:
    sys.path.insert(0, _root)

_flask_app_mod = importlib.util.spec_from_file_location("flask_app", _app_py)
_flask_app = importlib.util.module_from_spec(_flask_app_mod)
_flask_app_mod.loader.exec_module(_flask_app)

app = _flask_app.app
db = _flask_app.db
User = _flask_app.User
UserDocument = _flask_app.UserDocument
Scheme = _flask_app.Scheme
Admin = _flask_app.Admin
SchemeSource = _flask_app.SchemeSource
SchemeTranslation = _flask_app.SchemeTranslation
PendingScheme = _flask_app.PendingScheme
AdminNotification = _flask_app.AdminNotification
ScrapeLog = _flask_app.ScrapeLog
Condition = _flask_app.Condition
EligibilityResult = _flask_app.EligibilityResult
SchemeFlag = _flask_app.SchemeFlag
UserProfileAttribute = _flask_app.UserProfileAttribute
QuestionAnswer = _flask_app.QuestionAnswer
Feedback = _flask_app.Feedback
ApplicationFeedback = _flask_app.ApplicationFeedback
init_db = _flask_app.init_db
calculate_profile_score = _flask_app.calculate_profile_score

__all__ = [
    "EligibilityOrchestrator",
    "EligibilityEngine", "EligibilityOutput", "evaluate_single",
    "PASS_R", "FAIL_R", "UNKNOWN_C",
    "ELIGIBLE", "POSSIBLE", "INELIGIBLE",
    "ResultRanker", "RankedScheme",
    "ContextualReasoner",
    "QuestionEngine", "Question",
    "app", "db",
    "User", "UserDocument", "Scheme", "Admin",
    "SchemeSource", "SchemeTranslation", "PendingScheme",
    "AdminNotification", "ScrapeLog", "Condition",
    "EligibilityResult", "SchemeFlag", "UserProfileAttribute",
    "QuestionAnswer", "Feedback", "ApplicationFeedback",
    "init_db", "calculate_profile_score",
]
