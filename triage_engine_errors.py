"""
triage_engine_errors.py
========================
Before spending Gemini quota writing conditions for 3,450 engine errors,
this script tells you WHY they're crashing.

Most engine errors are caused by 2-3 root causes in build_rule / evaluate
(a missing field, a None check, a bad type cast). Fix those and the error
count collapses — then run generate_fixed_conditions.py on the remainder.

Output (all to stdout + triage_report.txt):
  - Error message frequency table  (what's crashing)
  - Stack trace samples per error type
  - List of scheme IDs per error bucket
  - Suggested one-line fixes

Usage:
  python triage_engine_errors.py
  python triage_engine_errors.py --audit audit_report.json --schemes all_schemes_export.json
  python triage_engine_errors.py --show-samples 5   # show 5 example schemes per error type
"""

import json
import re
import argparse
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

AUDIT_JSON   = "audit_report.json"
SCHEMES_JSON = "all_schemes_export.json"
OUT_TXT      = "triage_report.txt"


def classify_error(msg: str) -> str:
    """Bucket a raw error message into a short category label."""
    msg = msg.lower()

    buckets = [
        ("NoneType",              r"nonetype|'nonetype' object|none has no attribute"),
        ("KeyError",              r"keyerror"),
        ("AttributeError",        r"attributeerror|has no attribute"),
        ("TypeError",             r"typeerror|unsupported operand|can't compare|not subscriptable"),
        ("ValueError",            r"valueerror|invalid literal|could not convert"),
        ("IndexError",            r"indexerror|list index out of range"),
        ("build_rule returned None", r"build_rule filtered|rule is none"),
        ("ImportError",           r"importerror|modulenotfounderror|cannot import"),
        ("JSONDecodeError",       r"jsondecode|expecting value"),
        ("ZeroDivisionError",     r"zerodivision|division by zero"),
    ]

    for label, pattern in buckets:
        if re.search(pattern, msg):
            return label

    # Grab first meaningful word if nothing matched
    first = msg.strip().split(":")[0].strip()[:60]
    return first or "Unknown"


def extract_field_hint(msg: str) -> str:
    """Try to extract which field/attribute caused the error."""
    patterns = [
        r"'(\w+)' object has no attribute '(\w+)'",
        r"object has no attribute '(\w+)'",
        r"KeyError: '(\w+)'",
        r"'(\w+)'",
    ]
    for p in patterns:
        m = re.search(p, msg)
        if m:
            return m.group(0)
    return ""


def run(audit_file: str, schemes_file: str, show_samples: int = 3):

    print(f"Loading {audit_file}...")
    with open(audit_file, encoding="utf-8") as f:
        audit: dict = json.load(f)

    print(f"Loading {schemes_file}...")
    with open(schemes_file, encoding="utf-8") as f:
        all_schemes = json.load(f)
    schemes_by_id = {s["id"]: s for s in all_schemes}

    # ── Pull all engine error entries ─────────────────────────────────────────
    errors = {
        sid: entry for sid, entry in audit.items()
        if entry.get("engine", {}).get("class") == "ERROR"
    }

    total   = len(audit)
    n_err   = len(errors)
    n_ok    = total - n_err

    print(f"\nTotal schemes in audit:  {total}")
    print(f"Engine errors:           {n_err}  ({n_err/total*100:.1f}%)")
    print(f"Non-errors:              {n_ok}\n")

    if n_err == 0:
        print("No engine errors found. Nothing to triage.")
        return

    # ── Bucket errors by type ─────────────────────────────────────────────────
    buckets: dict[str, list] = defaultdict(list)   # label → list of (sid, entry)
    field_hints: dict[str, Counter] = defaultdict(Counter)

    for sid, entry in errors.items():
        raw_msg = entry.get("engine", {}).get("rejection", "")
        label   = classify_error(raw_msg)
        hint    = extract_field_hint(raw_msg)
        buckets[label].append((sid, entry, raw_msg))
        if hint:
            field_hints[label][hint] += 1

    # Sort buckets by frequency
    sorted_buckets = sorted(buckets.items(), key=lambda x: len(x[1]), reverse=True)

    # ── Build report ──────────────────────────────────────────────────────────
    lines = []
    lines.append("=" * 70)
    lines.append("  ENGINE ERROR TRIAGE REPORT")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 70)
    lines.append(f"\nTotal engine errors: {n_err} out of {total} schemes ({n_err/total*100:.1f}%)\n")
    lines.append("FIX THESE ROOT CAUSES FIRST — then re-run generate_fixed_conditions.py")
    lines.append("Most errors are caused by 2-3 patterns in build_rule / evaluate.\n")

    lines.append("─" * 70)
    lines.append("ERROR FREQUENCY TABLE:")
    lines.append("─" * 70)
    lines.append(f"  {'Count':>6}  {'%':>5}  Error type")
    lines.append(f"  {'─'*6}  {'─'*5}  {'─'*40}")
    for label, entries in sorted_buckets:
        pct = len(entries) / n_err * 100
        lines.append(f"  {len(entries):>6}  {pct:>4.1f}%  {label}")
    lines.append("")

    # ── Per-bucket detail ─────────────────────────────────────────────────────
    for label, entries in sorted_buckets:
        lines.append("─" * 70)
        lines.append(f"[{len(entries)} schemes] {label}")

        # Most common field hints
        if field_hints[label]:
            top_hints = field_hints[label].most_common(5)
            lines.append(f"  Common attributes/keys involved: {', '.join(h for h,_ in top_hints)}")

        # Unique raw messages (deduplicated)
        unique_msgs = list(dict.fromkeys(e[2] for e in entries))
        lines.append(f"  Unique error messages ({len(unique_msgs)}):")
        for msg in unique_msgs[:5]:
            lines.append(f"    • {msg[:120]}")
        if len(unique_msgs) > 5:
            lines.append(f"    ... and {len(unique_msgs)-5} more unique messages")

        # Sample scheme names
        lines.append(f"\n  Sample schemes ({min(show_samples, len(entries))}):")
        for sid, entry, _ in entries[:show_samples]:
            scheme = schemes_by_id.get(int(sid), {})
            name   = scheme.get("name", "?")[:60]
            cat    = scheme.get("category", "")
            lines.append(f"    [{sid}] {name}  ({cat})")

        # All scheme IDs in this bucket
        all_ids = [sid for sid, _, _ in entries]
        lines.append(f"\n  All {len(all_ids)} scheme IDs:")
        # Print in rows of 15
        for i in range(0, len(all_ids), 15):
            chunk = all_ids[i:i+15]
            lines.append("    " + ", ".join(chunk))

        # Suggested fix
        fix = _suggest_fix(label, field_hints.get(label, Counter()))
        if fix:
            lines.append(f"\n  SUGGESTED FIX:")
            for fline in fix:
                lines.append(f"    {fline}")

        lines.append("")

    # ── Quick re-run estimate ─────────────────────────────────────────────────
    top_label, top_entries = sorted_buckets[0]
    top_pct = len(top_entries) / n_err * 100
    lines.append("─" * 70)
    lines.append("IMPACT ESTIMATE:")
    lines.append(f"  Fixing just '{top_label}' eliminates {len(top_entries)} errors ({top_pct:.0f}% of all engine errors).")
    lines.append(f"  After fixing the top 2 error types, remaining errors likely < {sum(len(e) for _,e in sorted_buckets[2:])}")
    lines.append(f"  THEN run generate_fixed_conditions.py on the true remainder.")
    lines.append("─" * 70)

    report = "\n".join(lines)
    print(report)

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n→ Full report saved to {OUT_TXT}")

    # ── Also dump a JSON summary for programmatic use ─────────────────────────
    summary = {
        "generated_at": datetime.now().isoformat(),
        "total_in_audit": total,
        "engine_errors": n_err,
        "buckets": [
            {
                "error_type":     label,
                "count":          len(entries),
                "pct_of_errors":  round(len(entries) / n_err * 100, 1),
                "top_field_hints": [h for h, _ in field_hints[label].most_common(5)],
                "sample_messages": list(dict.fromkeys(e[2] for e in entries))[:5],
                "scheme_ids":      [int(sid) for sid, _, _ in entries],
            }
            for label, entries in sorted_buckets
        ]
    }
    with open("triage_report.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"→ Machine-readable summary saved to triage_report.json")


def _suggest_fix(label: str, hints: Counter) -> list[str]:
    """Return suggested code fix lines for common error types."""
    top_fields = [h for h, _ in hints.most_common(3)]

    if "NoneType" in label:
        return [
            "The engine is accessing an attribute on None — a scheme field is missing.",
            "In build_rule(), guard every optional field:",
            "  age_min = getattr(scheme, 'age_min', None)  # instead of scheme.age_min",
            "  if age_min is not None: conditions.append(...)",
            f"  Most likely culprits: {', '.join(top_fields) or 'unknown field'}",
        ]
    if "AttributeError" in label:
        return [
            "Scheme object is missing an attribute that build_rule expects.",
            "Use getattr(scheme, 'field_name', None) for every optional scheme field.",
            f"  Attributes involved: {', '.join(top_fields) or 'see messages above'}",
        ]
    if "KeyError" in label:
        return [
            "build_rule is using dict-style access (scheme['key']) on a missing key.",
            "Replace with: scheme.get('key') or getattr(scheme, 'key', None)",
            f"  Keys involved: {', '.join(top_fields) or 'see messages above'}",
        ]
    if "TypeError" in label:
        return [
            "Type mismatch — likely comparing int to None or str to int.",
            "Add None-guards before comparisons:",
            "  if scheme.age_min is not None and isinstance(scheme.age_min, (int, float)):",
            f"  Fields involved: {', '.join(top_fields) or 'see messages above'}",
        ]
    if "build_rule returned None" in label:
        return [
            "build_rule() is intentionally returning None for these schemes.",
            "These are either institutional schemes or unrecognised patterns.",
            "Inspect the scheme categories for these IDs — they may need a new rule template.",
        ]
    if "ImportError" in label:
        return [
            "A module used inside build_rule or the engine can't be imported.",
            "Check that scheme_rule_adapter.py and its dependencies are on sys.path.",
        ]
    return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Triage engine errors before fixing conditions")
    parser.add_argument("--audit",        default=AUDIT_JSON)
    parser.add_argument("--schemes",      default=SCHEMES_JSON)
    parser.add_argument("--show-samples", type=int, default=3,
                        help="Number of example schemes to show per error bucket")
    args = parser.parse_args()

    run(
        audit_file=args.audit,
        schemes_file=args.schemes,
        show_samples=args.show_samples,
    )
