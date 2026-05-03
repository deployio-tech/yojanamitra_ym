"""
generate_db_fixes.py
====================
Generates db_fixes_v2.json — a complete list of DB field corrections
derived by parsing each scheme's eligibility text.

Fixes generated:
  1. allowed_states  — corrects scraper default 'Karnataka' to true state
  2. min_age         — extracts from eligibility text when DB field is null
  3. max_age         — same
  4. max_income      — extracts from eligibility text when DB field is null
  5. allowed_occupations — narrow strict patterns only (no false farmer matches)
  6. allowed_genders — specific known-bad records (scheme 2237)
"""

import json
import re
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from scheme_rule_adapter import _resolve_true_state
from collections import Counter


# ── PARSER: AGE ────────────────────────────────────────────────────────────────

def parse_age_from_text(elig: str):
    """Extract (min_age, max_age) from eligibility text. Returns (None, None) if not found."""
    t = elig.lower()

    # Remove residency-year context: "resident for X years", "residing for X years"
    # so these don't pollute age parsing
    t = re.sub(
        r'(?:resident|residing|domicile|lived?|stay(?:ed)?|settled?)\s+(?:in|of|for)\s+[^.]{0,60}?\d+\s*years?',
        '', t
    )
    # Also remove "X years of experience / service / work"
    t = re.sub(r'\d+\s*years?\s+(?:of\s+)?(?:experience|service|working|work\s+experience)', '', t)

    min_age, max_age = None, None

    # Pattern: between X and Y years
    m = re.search(r'between\s+(\d+)\s+(?:to|and|-)\s+(\d+)\s*years?', t)
    if m:
        return int(m.group(1)), int(m.group(2))

    # Pattern: age group X-Y
    m = re.search(r'age\s+group\s+(?:of\s+)?(\d+)\s*[-to]+\s*(\d+)', t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if a < b <= 100:
            return a, b

    # Pattern: aged X to Y
    m = re.search(r'aged\s+(\d+)\s+(?:to|-)\s+(\d+)', t)
    if m:
        return int(m.group(1)), int(m.group(2))

    # Pattern: X to Y years of age
    m = re.search(r'(\d+)\s*(?:to|-)\s*(\d+)\s*years?\s*of\s*age', t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if 1 <= a <= 100 and 1 <= b <= 100 and a < b:
            return a, b

    # Pattern: X to Y years (only when "age" appears in context window)
    for m in re.finditer(r'(\d+)\s*(?:to|-)\s*(\d+)\s*years?', t):
        a, b = int(m.group(1)), int(m.group(2))
        context = t[max(0, m.start()-50):m.end()+20]
        if re.search(r'\bage\b', context) and 5 <= a <= 80 and a < b <= 100:
            return a, b

    # Min age patterns
    min_patterns = [
        r'minimum\s+age[^0-9]{0,15}(\d+)',
        r'age[^0-9]{0,10}at\s+least\s+(\d+)',
        r'at\s+least\s+(\d+)\s*years?\s*of\s*age',
        r'(?:above|over|more\s+than|completed)\s+(\d+)\s*years?\s*of\s*age',
        r'above\s+the\s+age\s+of\s+(\d+)',
        r'age(?:\s+should\s+be)?\s+(?:more\s+than|above|over)\s+(\d+)',
        r'aged\s+(\d+)\s*years?\s*(?:or\s*above|or\s*more|and\s*above)',
        r'(?:should\s+be|must\s+be)\s+(?:above|over|more\s+than)\s+(\d+)\s*years?',
    ]
    for pat in min_patterns:
        m = re.search(pat, t)
        if m:
            v = int(m.group(1))
            if 5 <= v <= 100:
                min_age = v
                break

    # Max age patterns
    max_patterns = [
        r'not\s+more\s+than\s+(\d+)\s*years?',
        r'maximum\s+age[^0-9]{0,15}(\d+)',
        r'(?:below|under|upto|up\s+to)\s+(\d+)\s*years?\s*(?:of\s*age)?',
        r'age\s+(?:should\s+be\s+)?(?:less\s+than|below|under|not\s+more\s+than)\s+(\d+)',
        r'(?:should\s+be|must\s+be)\s+(?:below|under|less\s+than)\s+(\d+)\s*years?',
    ]
    for pat in max_patterns:
        m = re.search(pat, t)
        if m:
            v = int(m.group(1))
            if 5 <= v <= 100:
                max_age = v
                break

    return min_age, max_age


# ── PARSER: INCOME ─────────────────────────────────────────────────────────────

def parse_income_from_text(elig: str):
    """Extract max_income (INR) from eligibility text. Returns None if not found."""
    t = elig.lower()

    def lakh_to_int(s: str) -> int:
        s = s.strip().replace(',', '')
        if not s:
            return 0
        return int(float(s) * 100_000)

    def valid(v) -> bool:
        return v is not None and 10_000 <= v <= 50_000_000

    # X lakh(s) — must be in income context within 60 chars
    for m in re.finditer(r'(\d+(?:\.\d+)?)\s*lakh', t):
        context = t[max(0, m.start()-60):m.start()+30]
        if any(kw in context for kw in ['income', 'salary', 'earning', 'annual', 'family', 'household', 'per annum']):
            v = lakh_to_int(m.group(1))
            if valid(v):
                return v

    # not exceed / less than / below Rs. X
    m = re.search(r'(?:not\s+exceed(?:ing)?|less\s+than|below|upto|up\s+to)\s+rs\.?\s*([\d,]+)', t)
    if m:
        raw = m.group(1).replace(',', '')
        if raw:
            v = int(raw)
            if valid(v):
                return v

    # annual/family/household income ... Rs. X
    m = re.search(r'(?:annual|family|household)\s+income.{0,50}?(?:rs\.?\s*)?([\d,]+)', t)
    if m:
        raw = m.group(1).replace(',', '')
        if raw:
            v = int(raw)
            if valid(v):
                return v

    # Rs. X per annum — must have income context nearby
    m = re.search(r'rs\.?\s*([\d,]+)\s*(?:per\s*annum|p\.a\.|annually|per\s*year)', t)
    if m:
        context = t[max(0, m.start()-60):m.start()]
        if any(kw in context for kw in ['income', 'salary', 'earn']):
            raw = m.group(1).replace(',', '')
            if raw:
                v = int(raw)
                if valid(v):
                    return v

    return None


# ── PARSER: OCCUPATION ─────────────────────────────────────────────────────────

# Strict patterns only — must indicate the scheme is EXCLUSIVELY for that occupation
# (not just mentioning the occupation as one of many beneficiaries or in passing)
STRICT_OCC_PATTERNS = [
    # farmer — only if explicitly exclusive
    (r'(?:only\s+for\s+farmers?|exclusively\s+for\s+farmers?|'
     r'registered\s+farmer|beneficiary\s+must\s+be\s+a\s+farmer|'
     r'applicant\s+must\s+be\s+a\s+farmer)',
     'farmer'),
    # fisherman
    (r'(?:registered\s+fisher(?:man|men|folk)|fish(?:erman|ermen)\s+must|'
     r'marine\s+fisherman|active\s+fisherman)',
     'fisherman'),
    # construction worker
    (r'(?:registered\s+(?:under\s+)?bocw|construction\s+worker\s+(?:registered|must|who\s+is)|'
     r'building\s+and\s+other\s+construction\s+worker)',
     'construction_worker'),
    # street vendor
    (r'(?:registered\s+street\s+vendor|street\s+vendor\s+(?:holding|with|who\s+has))',
     'street_vendor'),
    # weaver
    (r'(?:registered\s+(?:handloom\s+)?weaver|handloom\s+weaver\s+(?:working|must|who\s+is)|'
     r'powerloom\s+weaver)',
     'weaver'),
    # artisan
    (r'(?:registered\s+(?:traditional\s+)?artisan|vishwakarma\s+(?:artisan|craftsman)|'
     r'traditional\s+artisan\s+who)',
     'artisan'),
    # anganwadi
    (r'(?:anganwadi\s+(?:worker|sevika|helper)\s+(?:who|must|working)|'
     r'asha\s+worker\s+(?:who|must|registered))',
     'anganwadi_worker'),
    # safai karamchari
    (r'(?:safai\s+karamchari|manual\s+scavenger|sanitation\s+worker\s+(?:who|must|employed))',
     'safai_karamchari'),
]

def parse_occupation_from_text(elig: str, name: str) -> list:
    t = (elig + ' ' + name).lower()
    occs = []
    for pat, tag in STRICT_OCC_PATTERNS:
        if re.search(pat, t):
            occs.append(tag)
    return occs if occs else None


# ── MAIN ───────────────────────────────────────────────────────────────────────

def main():
    with open('all_schemes_export.json', encoding='utf-8') as f:
        data = json.load(f)

    fixes = []
    errors = []

    for s in data:
        sid  = s['id']
        elig = s.get('eligibility') or ''
        name = s.get('name') or ''
        desc = s.get('description') or ''

        # 1. STATE
        db_states = s.get('allowed_states') or []
        try:
            resolved = _resolve_true_state(name, elig, desc, db_states)
            if resolved != db_states:
                fixes.append({'id': sid, 'field': 'allowed_states',
                               'old': db_states, 'new': resolved})
        except Exception as e:
            errors.append(f'state [{sid}]: {e}')

        # 2. AGE (only if both null in DB)
        if not s.get('min_age') and not s.get('max_age'):
            try:
                min_age, max_age = parse_age_from_text(elig)
                if min_age and not (5 <= min_age <= 100):
                    min_age = None
                if max_age and not (5 <= max_age <= 100):
                    max_age = None
                if min_age and max_age and min_age >= max_age:
                    min_age = None
                    max_age = None
                if min_age:
                    fixes.append({'id': sid, 'field': 'min_age', 'old': None, 'new': min_age})
                if max_age:
                    fixes.append({'id': sid, 'field': 'max_age', 'old': None, 'new': max_age})
            except Exception as e:
                errors.append(f'age [{sid}]: {e}')

        # 3. INCOME (only if null)
        if not s.get('max_income'):
            try:
                income = parse_income_from_text(elig)
                if income:
                    fixes.append({'id': sid, 'field': 'max_income', 'old': None, 'new': income})
            except Exception as e:
                errors.append(f'income [{sid}]: {e}')

        # 4. OCCUPATION (only if empty, strict patterns only)
        if not (s.get('allowed_occupations') or []):
            try:
                occs = parse_occupation_from_text(elig, name)
                if occs:
                    fixes.append({'id': sid, 'field': 'allowed_occupations',
                                   'old': [], 'new': occs})
            except Exception as e:
                errors.append(f'occupation [{sid}]: {e}')

    # 5. Known specific bad records
    fixes.append({
        'id': 2237, 'field': 'allowed_genders',
        'old': ['Female'], 'new': ['Male', 'Female', 'Transgender'],
        'note': 'SC/General open to all genders; only ST sub-clause is women-only'
    })

    # Summary
    by_field = Counter(f['field'] for f in fixes)
    print('FIXES GENERATED:')
    for field, count in sorted(by_field.items(), key=lambda x: -x[1]):
        print(f'  {field:<30} {count:4d}')
    print(f'  {"TOTAL":<30} {len(fixes):4d}')
    if errors:
        print(f'\n  Errors: {len(errors)}')
        for e in errors[:5]:
            print(f'    {e}')

    with open('db_fixes_v2.json', 'w', encoding='utf-8') as f:
        json.dump(fixes, f, indent=2, ensure_ascii=False)
    print('\nSaved → db_fixes_v2.json')
    return fixes


if __name__ == '__main__':
    main()
