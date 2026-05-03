"""
generate_fixed_conditions.py
============================
Reads the audit output (audit_report.json + all_schemes_export.json) and uses
Gemini to write working, deterministic scheme conditions for every scheme where
the engine and Gemini DISAGREED (FALSE_POSITIVE or FALSE_NEGATIVE), and also
for every scheme where the engine threw an ERROR (crashed before producing any result).

Schemes that both agreed on (AGREE_ELIGIBLE / AGREE_NOT_ELIGIBLE) are skipped —
those conditions are already correct.

Three categories handled:
  FALSE_POSITIVE  — engine said eligible, Gemini said no  → add blocking conditions
  FALSE_NEGATIVE  — engine said not eligible, Gemini said yes → relax conditions
  ENGINE_ERROR    — engine crashed (build_rule/eval exception) → write from scratch

Output:
  fixed_conditions.json     — structured conditions per scheme, ready to patch
                              into scheme_rule_adapter or your DB
  fixed_conditions.py       — drop-in build_rule() cases for each fixed scheme
  fix_summary.txt           — human-readable report of what changed and why

Usage:
  python generate_fixed_conditions.py
  python generate_fixed_conditions.py --audit audit_report.json --schemes all_schemes_export.json
  python generate_fixed_conditions.py --scheme-id 239   # debug single scheme
  python generate_fixed_conditions.py --only-fp         # only fix false positives
  python generate_fixed_conditions.py --only-fn         # only fix false negatives
  python generate_fixed_conditions.py --only-errors     # only fix engine errors
"""

import json
import time
import os
import re
import argparse
import logging
from pathlib import Path
from datetime import datetime

import google.generativeai as genai

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "PASTE_YOUR_GEMINI_API_KEY_HERE")
genai.configure(api_key=GEMINI_API_KEY)
MODEL            = genai.GenerativeModel("gemini-flash-latest")

AUDIT_JSON       = "audit_report.json"
SCHEMES_JSON     = "all_schemes_export.json"
OUT_JSON         = "fixed_conditions.json"
OUT_PY           = "fixed_conditions.py"
OUT_SUMMARY      = "fix_summary.txt"

REQUESTS_PER_MIN = 25          # conservative — flash-2.5 free tier is 10 RPM, paid ~1000
DELAY            = 60.0 / REQUESTS_PER_MIN

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fix_conditions")

# ── Profile field catalogue (what the engine knows about) ────────────────────
# These are the exact keys your ProfileNormalizer produces. Gemini uses this
# list to know which fields it can actually write conditions against.
KNOWN_PROFILE_FIELDS = """
age                    (int, years)
gender                 ("Male" / "Female" / "Other")
state                  (2-letter code: "KA", "MH", "GJ", etc.)
district               (string)
residence              ("rural" / "urban")
annual_family_income   (int, INR per year)
caste_category         ("general" / "obc" / "sc" / "st")
social_category        (string, e.g. "General", "OBC", "SC", "ST")
marital_status         ("Single" / "Married" / "Widowed" / "Divorced")
employment_status      ("Student" / "Employed" / "Unemployed" / "Self-employed" / "Retired")
occupation_type        (string)
is_farmer              ("Yes" / "No" or bool)
land_size_acres        (float)
disability             (string or None)
disability_percentage  (int, 0-100)
is_bpl                 ("Yes" / "No" or bool)
is_student             ("Yes" / "No" or bool)
is_widow               ("Yes" / "No" or bool)
is_minority            ("Yes" / "No" or bool)
is_tribal              ("Yes" / "No" or bool)
is_orphan              ("Yes" / "No" or bool)
is_senior_citizen      ("Yes" / "No" or bool)
is_govt_employee       ("Yes" / "No" or bool)
is_migrant_worker      ("Yes" / "No" or bool)
is_pregnant            ("Yes" / "No" or bool)
is_ex_serviceman       ("Yes" / "No" or bool)
is_shg_member          ("Yes" / "No" or bool)
has_critical_illness   ("Yes" / "No" or bool)
has_bank_account       ("Yes" / "No" or bool)
education_level        (string, e.g. "10th", "12th", "Graduate", "Post Graduate")
num_children           (int)
num_daughters          (int)
num_sons               (int)
years_in_state         (int)
religion               (string)
exam_percentage        (float, CGPA or percentage)
"""

# ── Condition-writing prompt ──────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert at writing deterministic eligibility rules for Indian government schemes.

You will be given:
1. A scheme's full eligibility text
2. The Gemini audit verdict explaining WHY the current engine conditions are WRONG
3. The list of profile fields the engine can evaluate

Your job: Write a COMPLETE, CORRECT set of conditions that accurately captures the scheme's true eligibility rules.

AVAILABLE PROFILE FIELDS (use ONLY these):
{known_fields}

CONDITION SCHEMA — each condition is a JSON object:
{{
  "field":    "<profile_field_name>",
  "operator": "eq" | "ne" | "lt" | "lte" | "gt" | "gte" | "in" | "not_in" | "contains" | "is_true" | "is_false" | "exists",
  "value":    <string | number | list | bool>,
  "label":    "<human-readable description of this check>"
}}

RULES:
- Only reference fields from the AVAILABLE PROFILE FIELDS list
- For age: use "age" field with numeric operators (gte, lte, eq, between)
- For state-specific schemes: use "state" field with "eq" or "in" operator and 2-letter state codes
- For income: use "annual_family_income" with "lte" for upper limits
- For boolean flags: use "is_true" or "is_false" operator
- For caste: use "caste_category" with "in" operator and lowercase values ["sc","st","obc","general"]
- If a condition cannot be expressed with available fields, OMIT it (don't invent fake fields)
- Set "required": true for mandatory conditions, false for preferred/bonus conditions
- If the scheme is for INSTITUTIONS (not individuals), return an empty conditions array with a note

OUTPUT FORMAT (JSON only):
{{
  "scheme_id": <int>,
  "scheme_name": "<name>",
  "fix_type": "FALSE_POSITIVE" | "FALSE_NEGATIVE",
  "root_cause": "<one sentence: what the engine was getting wrong>",
  "conditions": [
    {{
      "field": "<field>",
      "operator": "<operator>",
      "value": <value>,
      "label": "<description>",
      "required": true
    }}
  ],
  "logic": "AND",
  "notes": "<anything important about edge cases or assumptions made>"
}}"""


def build_fix_prompt(scheme: dict, audit_entry: dict) -> str:
    """Build the prompt asking Gemini to write corrected conditions."""
    elig = (scheme.get("eligibility") or "").strip()
    if not elig:
        elig = (scheme.get("description") or "")[:1000]

    fix_type = audit_entry["comparison"]  # FALSE_POSITIVE or FALSE_NEGATIVE
    gemini_data = audit_entry["gemini"]
    engine_data = audit_entry["engine"]

    failed_conditions = [c for c in gemini_data.get("conditions_checked", []) if not c.get("pass", True)]
    passed_conditions = [c for c in gemini_data.get("conditions_checked", []) if c.get("pass", True)]

    if fix_type == "FALSE_POSITIVE":
        problem_desc = f"""PROBLEM: FALSE POSITIVE
The engine marked this scheme ELIGIBLE (score {engine_data.get('score')}%) but the user does NOT qualify.

WHY THE ENGINE IS WRONG:
- Blocking reason: {gemini_data.get('blocking_reason', 'Unknown')}

CONDITIONS THAT FAILED (user does NOT meet these):
{json.dumps(failed_conditions, indent=2)}

CONDITIONS THAT PASSED (user does meet these):
{json.dumps(passed_conditions, indent=2)}

The engine is MISSING the blocking conditions above. Your job: write conditions that 
include the blocking ones so this scheme is correctly rejected."""

    elif fix_type == "FALSE_NEGATIVE":
        problem_desc = f"""PROBLEM: FALSE NEGATIVE  
The engine marked this scheme NOT ELIGIBLE (reason: {engine_data.get('rejection', 'unknown')}) but the user DOES qualify.

WHY THE ENGINE IS WRONG:
- Notes: {gemini_data.get('notes', '')}

CONDITIONS THAT PASSED (user meets all of these):
{json.dumps(passed_conditions, indent=2)}

The engine is OVER-RESTRICTING. Your job: write conditions that are relaxed enough 
to correctly include this user while still filtering out ineligible users."""

    else:  # ENGINE_ERROR
        problem_desc = f"""PROBLEM: ENGINE ERROR
The engine crashed when evaluating this scheme and produced no result at all.
Error: {engine_data.get('rejection', 'unknown error')}

Gemini's independent verdict: {gemini_data.get('verdict', 'UNKNOWN')} (confidence {gemini_data.get('confidence', 0):.0%})
{f"Blocking reason: {gemini_data.get('blocking_reason')}" if gemini_data.get('blocking_reason') else ""}
{f"Notes: {gemini_data.get('notes')}" if gemini_data.get('notes') else ""}

There are no existing conditions to fix — write them from scratch based solely on the
eligibility text above. If Gemini's verdict was NOT_ELIGIBLE, still write the correct
conditions so the engine can evaluate this scheme properly in future."""

    return f"""SCHEME ID: {scheme['id']}
SCHEME NAME: {scheme.get('name', '')}
CATEGORY: {scheme.get('category', '')}

ELIGIBILITY TEXT:
{elig[:3000]}

{problem_desc}

Write the correct, complete conditions for this scheme. Output JSON only."""


def call_gemini_for_conditions(scheme: dict, audit_entry: dict, retries: int = 4) -> dict:
    """Ask Gemini to write corrected conditions for a disagreed scheme."""
    system = SYSTEM_PROMPT.format(known_fields=KNOWN_PROFILE_FIELDS)
    user_prompt = build_fix_prompt(scheme, audit_entry)

    for attempt in range(retries):
        try:
            response = MODEL.generate_content(
                [system, user_prompt],
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                )
            )
            raw = response.text.strip()
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            return json.loads(raw)

        except json.JSONDecodeError as e:
            log.warning(f"JSON parse error attempt {attempt+1}: {e}")
            if attempt == retries - 1:
                return {"error": "JSON parse failed", "raw": raw[:500] if 'raw' in dir() else ""}
            time.sleep(2)

        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower() or "resource_exhausted" in err.lower():
                # Exponential backoff with jitter: 60s, 120s, 240s, 480s
                wait = (2 ** attempt) * 60 + (attempt * 7)
                log.warning(f"Rate limit (attempt {attempt+1}). Waiting {wait}s before retry...")
                time.sleep(wait)
            elif "500" in err or "503" in err or "unavailable" in err.lower():
                wait = (2 ** attempt) * 10
                log.warning(f"Server error, retrying in {wait}s...")
                time.sleep(wait)
            else:
                log.error(f"Gemini error: {e}")
                return {"error": str(e)}

    return {"error": "Max retries exceeded"}


def conditions_to_python(scheme_id: int, scheme_name: str, conditions: list, logic: str = "AND") -> str:
    """Convert structured conditions to a Python build_rule() case."""
    lines = [f"    # [{scheme_id}] {scheme_name}"]
    lines.append(f"    if scheme.id == {scheme_id}:")
    lines.append(f"        return SchemeRule(")
    lines.append(f"            scheme_id={scheme_id},")
    lines.append(f"            logic='{logic}',")
    lines.append(f"            conditions=[")

    for c in conditions:
        field    = c.get("field", "")
        operator = c.get("operator", "eq")
        value    = c.get("value")
        label    = c.get("label", "")
        required = c.get("required", True)

        # Format value correctly for Python
        if isinstance(value, str):
            val_repr = f'"{value}"'
        elif isinstance(value, list):
            val_repr = repr(value)
        else:
            val_repr = repr(value)

        lines.append(f"                Condition(field='{field}', operator='{operator}', value={val_repr}, required={required}),  # {label}")

    lines.append(f"            ]")
    lines.append(f"        )")

    return "\n".join(lines)


def run(
    audit_file: str,
    schemes_file: str,
    only_fp: bool = False,
    only_fn: bool = False,
    only_errors: bool = False,
    scheme_id: int = None,
    resume: bool = False,
) -> None:

    # ── Load inputs ───────────────────────────────────────────────────────────
    log.info(f"Loading audit report: {audit_file}")
    with open(audit_file, encoding="utf-8") as f:
        audit_report: dict = json.load(f)

    log.info(f"Loading schemes: {schemes_file}")
    with open(schemes_file, encoding="utf-8") as f:
        all_schemes: list = json.load(f)

    schemes_by_id = {s["id"]: s for s in all_schemes}

    # ── Filter to disagreed schemes only ─────────────────────────────────────
    disagreed = {
        sid: entry for sid, entry in audit_report.items()
        if entry.get("comparison") in ("FALSE_POSITIVE", "FALSE_NEGATIVE", "ERROR")
           or entry.get("engine", {}).get("class") == "ERROR"
    }

    if only_fp:
        disagreed = {sid: e for sid, e in disagreed.items() if e["comparison"] == "FALSE_POSITIVE"}
    if only_fn:
        disagreed = {sid: e for sid, e in disagreed.items() if e["comparison"] == "FALSE_NEGATIVE"}
    if only_errors:
        disagreed = {sid: e for sid, e in disagreed.items()
                     if e.get("comparison") == "ERROR" or e.get("engine", {}).get("class") == "ERROR"}
    if scheme_id:
        disagreed = {str(scheme_id): audit_report[str(scheme_id)]} if str(scheme_id) in audit_report else {}

    total_agreed    = sum(1 for e in audit_report.values() if e.get("comparison") in ("AGREE_ELIGIBLE", "AGREE_NOT_ELIGIBLE"))
    total_disagreed = len(disagreed)
    fp_count     = sum(1 for e in disagreed.values() if e["comparison"] == "FALSE_POSITIVE")
    fn_count     = sum(1 for e in disagreed.values() if e["comparison"] == "FALSE_NEGATIVE")
    error_count  = sum(1 for e in disagreed.values()
                       if e.get("comparison") == "ERROR" or e.get("engine", {}).get("class") == "ERROR")

    log.info(f"Schemes agreed (skipped):     {total_agreed}")
    log.info(f"Schemes to fix:               {total_disagreed}  ({fp_count} FP, {fn_count} FN, {error_count} engine errors)")

    # ── Resume support ────────────────────────────────────────────────────────
    existing_fixes = {}
    if resume and Path(OUT_JSON).exists():
        with open(OUT_JSON, encoding="utf-8") as f:
            existing_fixes = {str(e["scheme_id"]): e for e in json.load(f).get("fixes", [])}
        log.info(f"Resuming: {len(existing_fixes)} schemes already fixed")

    to_fix = {sid: e for sid, e in disagreed.items() if sid not in existing_fixes}
    log.info(f"Fixing {len(to_fix)} schemes via Gemini...")

    # ── Main loop ─────────────────────────────────────────────────────────────
    fixes = list(existing_fixes.values())
    errors = []
    last_call = 0.0

    for i, (sid, audit_entry) in enumerate(to_fix.items()):
        scheme = schemes_by_id.get(int(sid))
        if not scheme:
            log.warning(f"Scheme {sid} not found in schemes file — skipping")
            errors.append({"scheme_id": sid, "error": "Not found in schemes file"})
            continue

        # Throttle
        elapsed = time.time() - last_call
        if elapsed < DELAY:
            time.sleep(DELAY - elapsed)

        fix_type = audit_entry["comparison"]
        if fix_type == "ERROR" or audit_entry.get("engine", {}).get("class") == "ERROR":
            fix_type = "ENGINE_ERROR"
            # Patch the entry so build_fix_prompt sees the right type
            audit_entry = dict(audit_entry)
            audit_entry["comparison"] = "ENGINE_ERROR"
        log.info(f"[{i+1}/{len(to_fix)}] [{sid}] {scheme.get('name','')[:55]} | {fix_type}")

        result = call_gemini_for_conditions(scheme, audit_entry)
        last_call = time.time()

        if "error" in result:
            log.error(f"  Error: {result['error']}")
            errors.append({"scheme_id": int(sid), "scheme_name": scheme.get("name",""), "error": result["error"]})
            continue

        # Enrich with metadata
        # fix_type already normalised above
        result["fix_type"] = fix_type
        result["scheme_name"] = scheme.get("name", "")
        result["fix_type"]    = fix_type
        result["category"]    = scheme.get("category", "")
        result["engine_was"]  = audit_entry["engine"]
        result["gemini_said"] = {
            "verdict":          audit_entry["gemini"]["verdict"],
            "blocking_reason":  audit_entry["gemini"]["blocking_reason"],
            "confidence":       audit_entry["gemini"]["confidence"],
        }

        fixes.append(result)

        # Log summary of what was written
        n_cond = len(result.get("conditions", []))
        log.info(f"  → {n_cond} conditions written. Root cause: {result.get('root_cause','')[:80]}")

        # Checkpoint every 10
        if (i + 1) % 10 == 0:
            _write_json(fixes, errors, audit_report, total_agreed, fp_count, fn_count, error_count)
            log.info(f"  Checkpoint saved ({len(fixes)} fixed so far)")

    # ── Final outputs ─────────────────────────────────────────────────────────
    _write_json(fixes, errors, audit_report, total_agreed, fp_count, fn_count, error_count)
    _write_python(fixes)
    _write_summary(fixes, errors, audit_report, total_agreed, fp_count, fn_count, error_count)

    print(f"\n{'='*70}")
    print(f"  FIX CONDITIONS COMPLETE")
    print(f"  False Positives fixed:  {sum(1 for f in fixes if f.get('fix_type') == 'FALSE_POSITIVE')}")
    print(f"  False Negatives fixed:  {sum(1 for f in fixes if f.get('fix_type') == 'FALSE_NEGATIVE')}")
    print(f"  Engine Errors fixed:    {sum(1 for f in fixes if f.get('fix_type') == 'ENGINE_ERROR')}")
    print(f"  Could not fix:          {len(errors)}")
    print(f"  Skipped (agreed):       {total_agreed}")
    print(f"\n  Output files:")
    print(f"  → {OUT_JSON}      (structured conditions, patch into DB/adapter)")
    print(f"  → {OUT_PY}        (drop-in Python build_rule() cases)")
    print(f"  → {OUT_SUMMARY}   (human-readable report)")
    print(f"{'='*70}\n")


# ── Output writers ─────────────────────────────────────────────────────────────

def _write_json(fixes, errors, audit_report, total_agreed, fp_count, fn_count, error_count=0):
    out = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_fixed":     len(fixes),
            "false_positives": sum(1 for f in fixes if f.get("fix_type") == "FALSE_POSITIVE"),
            "false_negatives": sum(1 for f in fixes if f.get("fix_type") == "FALSE_NEGATIVE"),
            "engine_errors":   sum(1 for f in fixes if f.get("fix_type") == "ENGINE_ERROR"),
            "errors":          len(errors),
            "skipped_agreed":  total_agreed,
        },
        "fixes": fixes,
        "errors": errors,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


def _write_python(fixes):
    """Write a drop-in Python snippet with build_rule() cases for all fixed schemes."""
    lines = [
        '"""',
        'fixed_conditions.py',
        '====================',
        'Auto-generated by generate_fixed_conditions.py',
        f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
        '',
        'HOW TO USE:',
        '  Copy the cases below into your scheme_rule_adapter.py build_rule() function.',
        '  Place them BEFORE the generic/fallback rules so they take precedence.',
        '"""',
        '',
        '# ── Fixed conditions (paste into build_rule) ─────────────────────────────',
        'def build_rule_fixed(scheme):',
        '    """Drop-in replacements for disagreed schemes. Call this first in build_rule."""',
        '',
    ]

    for fix in sorted(fixes, key=lambda x: x.get("scheme_id", 0)):
        sid   = fix.get("scheme_id", 0)
        name  = fix.get("scheme_name", "")
        conds = fix.get("conditions", [])
        logic = fix.get("logic", "AND")
        ftype = fix.get("fix_type", "")
        cause = fix.get("root_cause", "")

        if not conds:
            # Institutional / no conditions — filter it out entirely
            lines.append(f"    # [{sid}] {name}")
            lines.append(f"    # Fix: {ftype} — {cause}")
            lines.append(f"    if scheme.id == {sid}:")
            lines.append(f"        return None  # Institutional scheme — filter out")
            lines.append("")
        else:
            lines.append(f"    # Fix type: {ftype}")
            lines.append(f"    # Root cause: {cause}")
            lines.append(conditions_to_python(sid, name, conds, logic))
            lines.append("")

    lines.append("    return None  # Not in fixed list — fall through to generic rules")

    with open(OUT_PY, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _write_summary(fixes, errors, audit_report, total_agreed, fp_count, fn_count, error_count=0):
    fp_fixes    = [f for f in fixes if f.get("fix_type") == "FALSE_POSITIVE"]
    fn_fixes    = [f for f in fixes if f.get("fix_type") == "FALSE_NEGATIVE"]
    error_fixes = [f for f in fixes if f.get("fix_type") == "ENGINE_ERROR"]

    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("  YOJANAMITRA — SCHEME CONDITIONS FIX REPORT\n")
        f.write(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 70 + "\n\n")

        f.write("WHAT THIS SCRIPT DID:\n")
        f.write("  Read audit_report.json and identified every scheme where the\n")
        f.write("  deterministic engine disagreed with Gemini, or crashed outright.\n")
        f.write("  For each case, Gemini was asked to write corrected conditions from\n")
        f.write("  the eligibility text. Schemes where both agreed were skipped.\n\n")

        f.write(f"TOTALS:\n")
        f.write(f"  Schemes agreed (skipped):       {total_agreed}\n")
        f.write(f"  FALSE POSITIVES fixed:          {len(fp_fixes)}\n")
        f.write(f"  FALSE NEGATIVES fixed:          {len(fn_fixes)}\n")
        f.write(f"  ENGINE ERRORS fixed:            {len(error_fixes)}\n")
        f.write(f"  Errors (could not fix):         {len(errors)}\n\n")

        if fp_fixes:
            f.write("─" * 70 + "\n")
            f.write(f"FALSE POSITIVES FIXED ({len(fp_fixes)}) — schemes that were wrongly shown:\n")
            f.write("─" * 70 + "\n\n")
            for fix in fp_fixes:
                sid   = fix['scheme_id']
                name  = fix['scheme_name']
                cause = fix.get('root_cause', '')
                conds = fix.get('conditions', [])
                f.write(f"  [{sid}] {name[:60]}\n")
                f.write(f"    Root cause:  {cause}\n")
                f.write(f"    Was blocked: {fix['gemini_said']['blocking_reason']}\n")
                f.write(f"    Conditions written ({len(conds)}):\n")
                for c in conds:
                    req = "REQUIRED" if c.get("required") else "preferred"
                    f.write(f"      [{req}] {c.get('label','')}\n")
                    f.write(f"               field={c['field']} {c['operator']} {c.get('value')}\n")
                f.write("\n")

        if fn_fixes:
            f.write("─" * 70 + "\n")
            f.write(f"FALSE NEGATIVES FIXED ({len(fn_fixes)}) — schemes that were wrongly hidden:\n")
            f.write("─" * 70 + "\n\n")
            for fix in fn_fixes:
                sid   = fix['scheme_id']
                name  = fix['scheme_name']
                cause = fix.get('root_cause', '')
                conds = fix.get('conditions', [])
                eng   = fix.get('engine_was', {})
                f.write(f"  [{sid}] {name[:60]}\n")
                f.write(f"    Root cause:  {cause}\n")
                f.write(f"    Engine said: {eng.get('class','')} — {eng.get('rejection','')[:60]}\n")
                f.write(f"    Conditions written ({len(conds)}):\n")
                for c in conds:
                    req = "REQUIRED" if c.get("required") else "preferred"
                    f.write(f"      [{req}] {c.get('label','')}\n")
                    f.write(f"               field={c['field']} {c['operator']} {c.get('value')}\n")
                f.write("\n")

        if error_fixes:
            f.write("─" * 70 + "\n")
            f.write(f"ENGINE ERRORS FIXED ({len(error_fixes)}) — schemes the engine crashed on:\n")
            f.write("─" * 70 + "\n\n")
            for fix in error_fixes:
                sid   = fix['scheme_id']
                name  = fix['scheme_name']
                cause = fix.get('root_cause', '')
                conds = fix.get('conditions', [])
                eng   = fix.get('engine_was', {})
                gem   = fix.get('gemini_said', {})
                f.write(f"  [{sid}] {name[:60]}\n")
                f.write(f"    Engine error: {eng.get('rejection','')[:80]}\n")
                f.write(f"    Gemini verdict: {gem.get('verdict','')} (confidence {gem.get('confidence',0):.0%})\n")
                f.write(f"    Root cause:  {cause}\n")
                f.write(f"    Conditions written from scratch ({len(conds)}):\n")
                for c in conds:
                    req = "REQUIRED" if c.get("required") else "preferred"
                    f.write(f"      [{req}] {c.get('label','')}\n")
                    f.write(f"               field={c['field']} {c['operator']} {c.get('value')}\n")
                f.write("\n")

        if errors:
            f.write("─" * 70 + "\n")
            f.write(f"ERRORS — could not generate conditions for {len(errors)} schemes:\n")
            f.write("─" * 70 + "\n\n")
            for e in errors:
                f.write(f"  [{e.get('scheme_id','')}] {e.get('scheme_name','')}\n")
                f.write(f"    Error: {e.get('error','')}\n\n")

        f.write("─" * 70 + "\n")
        f.write("NEXT STEPS:\n")
        f.write("  1. Review fixed_conditions.json — verify the conditions look right\n")
        f.write("  2. Paste the cases from fixed_conditions.py into build_rule() in\n")
        f.write("     scheme_rule_adapter.py, BEFORE the generic fallback rules\n")
        f.write("  3. Re-run the audit (profile_vs_gemini_audit.py) to confirm FP rate drops\n")
        f.write("─" * 70 + "\n")


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate corrected scheme conditions for all engine/Gemini disagreements"
    )
    parser.add_argument("--audit",     default=AUDIT_JSON,   help="Path to audit_report.json")
    parser.add_argument("--schemes",   default=SCHEMES_JSON, help="Path to all_schemes_export.json")
    parser.add_argument("--scheme-id", type=int, default=None, help="Fix a single scheme by ID (debug)")
    parser.add_argument("--only-fp",      action="store_true",  help="Only fix FALSE_POSITIVE schemes")
    parser.add_argument("--only-fn",      action="store_true",  help="Only fix FALSE_NEGATIVE schemes")
    parser.add_argument("--only-errors",  action="store_true",  help="Only fix ENGINE_ERROR schemes")
    parser.add_argument("--resume",       action="store_true",  help="Skip already-fixed schemes")
    args = parser.parse_args()

    run(
        audit_file=args.audit,
        schemes_file=args.schemes,
        only_fp=args.only_fp,
        only_fn=args.only_fn,
        only_errors=args.only_errors,
        scheme_id=args.scheme_id,
        resume=args.resume,
    )

