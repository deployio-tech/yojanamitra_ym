"""
UI/UX QUESTIONS WITH ANSWER OPTIONS
====================================

Display the 13 questions that will actually be shown in the UI
with their answer options and impact on scheme matching
"""

import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, Scheme
from app.engine.eligibility import EligibilityEngine
from app.engine.questions import QuestionEngine, QUESTION_TEMPLATES

print("\n" + "=" * 140)
print("ADAPTIVE QUESTIONING - UI/UX DISPLAY")
print("=" * 140)

with app.app_context():
    minimal_profile = {"age": 25, "state": "Karnataka"}
    
    engine = EligibilityEngine()
    possible_schemes = []
    schemes = Scheme.query.limit(200).all()
    
    for scheme in schemes:
        result = engine.evaluate(scheme, minimal_profile)
        if result.result.lower() == 'possible':
            possible_schemes.append((scheme, result))
    
    qengine = QuestionEngine()
    questions = qengine.select_questions(possible_schemes, minimal_profile)
    
    # Sort by schemes affected (descending) for UI priority
    questions.sort(key=lambda q: len(q.schemes_affected), reverse=True)
    
    # ========================================
    # Define Answer Options for Each Question
    # ========================================
    
    ANSWER_OPTIONS = {
        # Boolean questions (Yes/No)
        "is_student": {
            "type": "boolean",
            "options": [
                {"label": "Yes", "value": True},
                {"label": "No", "value": False}
            ],
            "help": "Are you currently pursuing any education?"
        },
        
        "is_disabled": {
            "type": "boolean",
            "options": [
                {"label": "Yes, I have a disability certificate", "value": True},
                {"label": "No", "value": False}
            ],
            "help": "Do you have an official disability certificate (UDID, state issued, or equivalent)?"
        },
        
        "is_rural": {
            "type": "boolean",
            "options": [
                {"label": "Rural (village/agricultural area)", "value": True},
                {"label": "Urban (city/municipality)", "value": False}
            ],
            "help": "Is your place of residence in a rural or urban area?"
        },
        
        "is_farmer": {
            "type": "boolean",
            "options": [
                {"label": "Yes, I am a farmer", "value": True},
                {"label": "No", "value": False}
            ],
            "help": "Are you engaged in agricultural activities?"
        },
        
        "is_pensioner": {
            "type": "boolean",
            "options": [
                {"label": "Yes, I receive a pension", "value": True},
                {"label": "No", "value": False}
            ],
            "help": "Do you currently receive any pension (government, private, etc)?"
        },
        
        "marital_status": {
            "type": "single_choice",
            "options": [
                {"label": "Single", "value": "Single"},
                {"label": "Married", "value": "Married"},
                {"label": "Widowed", "value": "Widowed"},
                {"label": "Separated/Divorced", "value": "Separated"},
                {"label": "Prefer not to say", "value": "Other"}
            ],
            "help": "What is your current marital status?"
        },
        
        "gender": {
            "type": "single_choice",
            "options": [
                {"label": "Male", "value": "Male"},
                {"label": "Female", "value": "Female"},
                {"label": "Transgender", "value": "Transgender"},
                {"label": "Prefer not to say", "value": "Other"}
            ],
            "help": "What is your gender?"
        },
        
        "disability_percentage": {
            "type": "number",
            "options": [],
            "input": {
                "type": "number",
                "min": 0,
                "max": 100,
                "unit": "%",
                "step": 5
            },
            "help": "Enter your disability percentage as mentioned in your certificate"
        },
        
        # Select/dropdown questions with preset options
        "category": {
            "type": "single_choice",
            "options": [
                {"label": "General (Open)", "value": "General"},
                {"label": "SC (Scheduled Caste)", "value": "SC"},
                {"label": "ST (Scheduled Tribe)", "value": "ST"},
                {"label": "OBC (Other Backward Class)", "value": "OBC"},
                {"label": "EWS (Economically Weaker Section)", "value": "EWS"},
                {"label": "Prefer not to disclose", "value": "Other"}
            ],
            "help": "Select your caste/community category for scheme eligibility"
        },
        
        "occupation": {
            "type": "single_choice",
            "options": [
                {"label": "Student", "value": "Student"},
                {"label": "Farmer", "value": "Farmer"},
                {"label": "Agricultural Worker", "value": "Agricultural Worker"},
                {"label": "Manual/Skilled Worker", "value": "Manual Worker"},
                {"label": "Construction Worker", "value": "Construction Worker"},
                {"label": "Self-employed/Business", "value": "Self Employed"},
                {"label": "Government Employee", "value": "Government Employee"},
                {"label": "Private Employee", "value": "Private Employee"},
                {"label": "Homemaker", "value": "Homemaker"},
                {"label": "Unemployed/Looking for work", "value": "Unemployed"},
                {"label": "Retired", "value": "Retired"},
                {"label": "Other", "value": "Other"}
            ],
            "help": "What is your primary occupation or source of livelihood?"
        },
        
        "education_level": {
            "type": "single_choice",
            "options": [
                {"label": "Below 10th grade / Illiterate", "value": "Below 10"},
                {"label": "10th Standard (SSLC)", "value": "10th"},
                {"label": "12th Standard (PUC/HSC)", "value": "12th"},
                {"label": "Diploma", "value": "Diploma"},
                {"label": "Bachelor's Degree", "value": "Bachelor"},
                {"label": "Master's Degree", "value": "Master"},
                {"label": "PhD / Research", "value": "PhD"},
                {"label": "Other Professional Course", "value": "Professional"}
            ],
            "help": "What is your highest level of education completed?"
        },
        
        "annual_income": {
            "type": "number",
            "options": [],
            "input": {
                "type": "number",
                "min": 0,
                "max": 10000000,
                "unit": "₹",
                "step": 50000
            },
            "help": "Enter your annual family income (or approximate)"
        },
        
        "is_bpl": {
            "type": "boolean",
            "options": [
                {"label": "Yes, I have BPL card", "value": True},
                {"label": "No, I have APL card", "value": False},
                {"label": "I have Antyodaya card", "value": True}
            ],
            "help": "Do you have a Below Poverty Line (BPL) or Antyodaya card?"
        },
        
        "is_construction_worker": {
            "type": "boolean",
            "options": [
                {"label": "Yes, I am a registered construction worker (BOCW)", "value": True},
                {"label": "No", "value": False}
            ],
            "help": "Are you registered under the Building and Other Construction Workers Act?"
        },
        
        "is_minority": {
            "type": "boolean",
            "options": [
                {"label": "Yes, I belong to a minority community", "value": True},
                {"label": "No", "value": False}
            ],
            "help": "Do you belong to a notified minority community?"
        },
        
        "is_self_employed": {
            "type": "boolean",
            "options": [
                {"label": "Yes, I am self-employed or run my own business", "value": True},
                {"label": "No, I am an employee", "value": False}
            ],
            "help": "Are you self-employed or running your own business?"
        },
        
        "bank_account": {
            "type": "boolean",
            "options": [
                {"label": "Yes, I have a bank account", "value": True},
                {"label": "No", "value": False}
            ],
            "help": "Do you have an active bank account (preferably linked to Aadhaar)?"
        },
        
        "citizenship": {
            "type": "boolean",
            "options": [
                {"label": "Yes, I am an Indian citizen", "value": True},
                {"label": "No, I am a non-citizen", "value": False}
            ],
            "help": "Are you an Indian citizen?"
        },
        
        "loan_default_history": {
            "type": "boolean",
            "options": [
                {"label": "No, I have never defaulted on a loan", "value": False},
                {"label": "Yes, I have a history of defaulting", "value": True}
            ],
            "help": "Do you have any history of defaulting on loans or advances?"
        },
    }
    
    # ========================================
    # Display Questions with Options
    # ========================================
    
    print(f"\n📋 TOTAL QUESTIONS: {len(questions)}")
    print(f"⏱️  Estimated time to complete: 3-5 minutes")
    print(f"📊 These answers will match you to {len(possible_schemes)} possible schemes\n")
    
    print("=" * 140)
    print(f"{'#':<3} {'Question':<45} {'Type':<15} {'Schemes':<8} {'Priority'}")
    print("=" * 140)
    
    for idx, q in enumerate(questions, 1):
        q_type = q.field_type.replace('_', ' ').title()
        num_schemes = len(q.schemes_affected)
        
        # Determine priority based on schemes affected
        if num_schemes >= 20:
            priority = "🔴 CRITICAL"
        elif num_schemes >= 10:
            priority = "🟠 HIGH"
        elif num_schemes >= 5:
            priority = "🟡 MEDIUM"
        else:
            priority = "🟢 LOW"
        
        print(f"{idx:<3} {q.text[:43]:<45} {q_type:<15} {num_schemes:<8} {priority}")
    
    # ========================================
    # Detailed Questions with Answer Options
    # ========================================
    
    print("\n" + "=" * 140)
    print("DETAILED QUESTIONS WITH ANSWER OPTIONS")
    print("=" * 140)
    
    for idx, q in enumerate(questions, 1):
        field = q.field
        options = ANSWER_OPTIONS.get(field, {})
        text = options.get("text", q.text)
        help_text = options.get("help", "")
        field_type = options.get("type", q.field_type)
        answer_options = options.get("options", [])
        num_schemes = len(q.schemes_affected)
        
        print(f"\n{'─' * 140}")
        print(f"\n❓ QUESTION {idx} of {len(questions)}")
        print(f"\n   Field: {field}")
        print(f"   Impact: Affects {num_schemes} schemes")
        print(f"   Type: {field_type.replace('_', ' ').title()}")
        
        print(f"\n   📝 {q.text}")
        if help_text:
            print(f"      ℹ️  {help_text}")
        
        if field_type == "boolean":
            print(f"\n   Answer Options:")
            for opt in answer_options:
                print(f"      ☐ {opt['label']}")
        
        elif field_type == "single_choice":
            print(f"\n   Answer Options:")
            for i, opt in enumerate(answer_options, 1):
                print(f"      {i}. {opt['label']}")
        
        elif field_type == "number":
            input_cfg = options.get("input", {})
            unit = input_cfg.get("unit", "")
            min_val = input_cfg.get("min", 0)
            max_val = input_cfg.get("max", 1000000)
            print(f"\n   Answer Format: Numeric input")
            print(f"      Range: {min_val:,} {unit} to {max_val:,} {unit}")
        
        # Show sample schemes affected
        print(f"\n   📍 Sample schemes this question helps with:")
        for scheme_id in sorted(q.schemes_affected)[:5]:
            scheme = Scheme.query.get(scheme_id)
            if scheme:
                print(f"      • {scheme.name}")
        if len(q.schemes_affected) > 5:
            print(f"      ... and {len(q.schemes_affected) - 5} more")
    
    # ========================================
    # UI/UX Suggestions
    # ========================================
    
    print(f"\n\n" + "=" * 140)
    print("UI/UX RECOMMENDATIONS")
    print("=" * 140)
    
    print(f"""
✅ DISPLAY RECOMMENDATIONS:

1. QUESTION PRESENTATION:
   • Show one question at a time (not all 13 together)
   • Display progress bar: "Question X of 13"
   • Estimated time: "~30 seconds per question"
   • Option to skip or come back later

2. ANSWER FORMATTING:
   • Boolean fields: Radio buttons or toggle switches (not checkboxes)
   • Single choice: Dropdown for many options (>5), radio for few
   • Number inputs: Suggest common ranges as buttons
   • Icons: Use visual cues (✓/✗ for yes/no)

3. FIELD-SPECIFIC UX:
   
   🟢 QUICK ANSWERS (Yes/No):
      • is_student, is_disabled, is_rural, is_farmer, is_pensioner
      • is_bpl, is_construction_worker, is_minority, is_self_employed
      • bank_account, citizenship, loan_default_history
      → Display as large clickable buttons
   
   🟡 SELECTION FIELDS (Dropdown):
      • category, occupation, education_level  
      • marital_status, gender
      → Display as searchable dropdown or radio group
   
   🔴 NUMERIC FIELDS:
      • annual_income, disability_percentage
      → Display as number input with currency/percentage formatting
      → Provide slider or preset buttons for quick selection

4. FLOW OPTIMIZATION:
   • Start with HIGH IMPACT questions (affects most schemes)
   • Order: 1→category (27 schemes), 2→education_level (26), 3→occupation (24)
   • Progress indicator: Show "This helps with X schemes"
   • Allow back/next navigation

5. MOBILE OPTIMIZATION:
   • Single column layout (not side-by-side)
   • Large touch targets (min 44x44 dp)
   • Collapse help text by default, expandable
   • Show progress as visual circle/bar

6. ACCESSIBILITY:
   • All options have clear labels
   • Help text explains why this info is needed
   • Keyboard navigation support
   • Color not the only differentiator

7. CONFIRMATION SCREEN:
   Before showing results:
   • Summary of answers given
   • Option to edit if needed
   • "Find matching schemes" button
   • Estimated number of matching schemes

""")
    
    # ========================================
    # JSON Format for Frontend
    # ========================================
    
    print("=" * 140)
    print("JSON FORMAT FOR FRONTEND API")
    print("=" * 140)
    
    import json
    
    questions_json = {
        "total_questions": len(questions),
        "estimated_time_minutes": 5,
        "questions": []
    }
    
    for idx, q in enumerate(questions, 1):
        field = q.field
        options_config = ANSWER_OPTIONS.get(field, {})
        
        q_data = {
            "question_number": idx,
            "question_id": q.question_id,
            "field": q.field,
            "text": q.text,
            "help": options_config.get("help", ""),
            "type": options_config.get("type", q.field_type),
            "schemes_affected": len(q.schemes_affected),
            "required": True,
            "skip_allowed": False
        }
        
        if options_config.get("type") in ["boolean", "single_choice"]:
            q_data["options"] = options_config.get("options", [])
        elif options_config.get("type") == "number":
            q_data["input"] = options_config.get("input", {})
        
        questions_json["questions"].append(q_data)
    
    print("\n// Example API Response Format:")
    print(json.dumps(questions_json, indent=2)[:1500] + "\n... (truncated)")

print("\n" + "=" * 140)
