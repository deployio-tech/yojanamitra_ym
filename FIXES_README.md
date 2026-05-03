# YojanaMitra — Final Fix Package

## Validation Results (after all fixes)

| Harness | Profiles | Matches | FP | FP% | FN (sampled) |
|---------|----------|---------|-----|-----|--------------|
| 200-profile | 200 | 8,837 | **0** | 0.0% | 257 (LOW_CONFIDENCE) |
| 1000-profile | 1,000 | 42,705 | **0** | 0.0% | 1,351 (LOW_CONFIDENCE) |

---

## Root Cause Trace

### Why dashboard showed 0 matched schemes

The engine was correct all along. Four compounding issues hid the results:

1. **Gender false rejection** — `any()` should be `all()` for trans-only check. Schemes
   listing `['Male','Female','Transgender']` rejected all male/female users.

2. **DB state pollution** — Scraper defaulted `allowed_states=['Karnataka']` for 4,020
   schemes. `_resolve_true_state()` correctly overrides this from text — but 2,855 schemes
   genuinely belong to other states (Bihar, Rajasthan, etc.). These get STATE_MISMATCH for
   Karnataka users. Fix: run `fix_states_migration.py` once to correct the DB.

3. **Institutional schemes leaking through** — 16 new keyword phrases added to
   `INSTITUTIONAL_ELIG_SIGNALS` to filter B2B/export/infrastructure schemes that had
   0 individual-beneficiary conditions.

4. **Dashboard threshold too high** — `MATCH_THRESHOLD = 70` was above the engine's max
   achievable score (~66-69%) for sparse-condition schemes. Lowered to 60.

### Why harness showed 0 FPs (when it shouldn't have)

Three harness bugs, all fixed:

| Bug | File | Effect |
|-----|------|--------|
| Premature `return []` in `is_false_positive()` | both harnesses | Entire Layer 1 + Layer 2 audit was unreachable dead code |
| `evaluator.evaluate()` → method doesn't exist | both harnesses | `AttributeError` silently swallowed by `except Exception`, Layer 1 never caught mandatory condition failures |
| `"men only" in text` substring match | 1000 harness | Matched inside `"women only"`, flagging female users on mixed-gender schemes as FPs |

### The 3 FPs in the 1000-profile run

All came from scheme `[2237] Establishment of Goat Unit (10+1)`.
- **DB bug**: `allowed_genders=['Female']` — wrong. The scheme is open to SC/General (all genders). Only the ST sub-category is women-only.
- **Harness bug**: `"men only" in text` substring-matched `"wo**men only**"` in the eligibility text, flagging correctly-matched female users as FPs.
- **Engine fix**: `_detect_women_only()` now has a caste-qualifier guard that prevents `"ST – Women only"` from triggering whole-scheme female-only classification.
- **DB fix needed**: `UPDATE schemes SET allowed_genders='["Male","Female","Transgender"]' WHERE id=2237`

---

## Complete Change List

### `yojanamitra_eligibility_engine_v2.py` — 2 lines changed
- Line 781: `any(g in TRANS_VARIANTS ...)` → `all(...)` (Stage 1B gender check)
- Line 987: same fix (safety check copy)

### `scheme_rule_adapter.py` — 2 blocks changed
- `INSTITUTIONAL_ELIG_SIGNALS`: 16 new B2B/export keyword strings appended
- `_detect_women_only()`: added caste-qualifier guard so `"ST – Women only"` doesn't trigger whole-scheme female classification

### `dashboard.html` — 2 numbers changed
- Line 4097: `MATCH_THRESHOLD = 70` → `60`
- Line 4254: same

### `test_harness_200.py` — 3 fixes
- Removed premature `return []` that made Layer 1 + Layer 2 dead code
- `evaluator.evaluate(cond, profile)` → `evaluator.evaluate_condition(cond, profile).passed`
- `any()` → `all()` for trans-only check (×2) to mirror engine fix

### `test_harness_1000.py` — 4 fixes
- Same 3 as above
- `"men only" in text` → `re.search(r'\bmen only\b', text)` word-boundary fix

### `fix_states_migration.py` — new file
- Run once to correct `allowed_states` for 2,855 wrongly-tagged schemes in DB

---

## DB fixes (run manually)

```sql
-- Fix scheme 2237: open to all genders (SC/General), not female-only
UPDATE schemes SET allowed_genders='["Male","Female","Transgender"]' WHERE id=2237;
```

---

## Deployment Steps

1. Replace `yojanamitra_eligibility_engine_v2.py`
2. Replace `scheme_rule_adapter.py`
3. Replace `dashboard.html`
4. Replace `test_harness_200.py` and `test_harness_1000.py`
5. Run once: `python fix_states_migration.py`
6. Run once: SQL fix for scheme 2237
7. Restart server
8. Verify: `python test_harness_200.py --standalone` → FP=0, FN all LOW_CONFIDENCE
