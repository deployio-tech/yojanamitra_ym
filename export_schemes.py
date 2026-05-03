"""
export_schemes.py — exports all scheme DB columns to all_schemes_export.json
Run: python export_schemes.py
"""
from app import app, db
from app import Scheme
import json


def jl(v):
    if isinstance(v, str) and v:
        try:
            return json.loads(v)
        except Exception:
            return [v]
    return v or []


with app.app_context():
    schemes = Scheme.query.all()
    data = []
    for s in schemes:
        data.append({
            'id': s.id,
            'name': s.name,
            'category': s.category,
            'description': s.description,
            'eligibility': s.eligibility,
            'benefits': s.benefits,
            'application_process': s.application_process,
            'documents_required': s.documents_required,
            'exclusions': s.exclusions,
            'portal_link': s.application_link,
            'min_age': s.min_age,
            'max_age': s.max_age,
            'max_income': s.max_income,
            'min_income': s.min_income,
            'allowed_genders': jl(s.allowed_genders),
            'allowed_castes': jl(s.allowed_castes),
            'allowed_states': jl(s.allowed_states),
            'allowed_occupations': jl(s.allowed_occupations),
            'allowed_ration_card_types': jl(s.allowed_ration_card_types),
            'allowed_religions': jl(s.allowed_religions),
            'allowed_marital_status': jl(s.allowed_marital_status),
            'allowed_father_occupations': jl(s.allowed_father_occupations),
            'allowed_mother_occupations': jl(s.allowed_mother_occupations),
            'min_education_level': s.min_education_level,
            'disability_requirement': s.disability_requirement,
            'disability_percentage_min': s.disability_percentage_min,
            'residence_requirement': s.residence_requirement,
            'minority_requirement': s.minority_requirement,
            'senior_citizen_requirement': s.senior_citizen_requirement,
            'widow_requirement': s.widow_requirement,
            'tribal_requirement': s.tribal_requirement,
            'orphan_requirement': s.orphan_requirement,
            'aadhaar_required': s.aadhaar_required,
            'bank_account_required': s.bank_account_required,
            'confidence_score': 0,
        })

    with open('all_schemes_export.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    s2237 = next((d for d in data if d['id'] == 2237), None)
    print(f'Exported {len(data)} schemes to all_schemes_export.json')
    if s2237:
        print(f'Scheme 2237 allowed_genders : {s2237["allowed_genders"]}')
        print(f'Scheme 2237 allowed_states  : {s2237["allowed_states"]}')
        print(f'Scheme 2237 min_age         : {s2237["min_age"]}')
        print(f'Scheme 2237 max_income      : {s2237["max_income"]}')
