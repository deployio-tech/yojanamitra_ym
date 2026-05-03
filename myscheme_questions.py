"""
myscheme_questions.py
---------------------
Scrapes eligibility questions for ALL schemes on myscheme.gov.in.
Uses only Python stdlib — no pip installs required.

Output: scheme_questions.json
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Config ─────────────────────────────────────────────────────────────────────
SEARCH_API_KEY  = "tYTy5eEhlu9rFjyxuCr7ra7ACp4dv1RH8gWuHTDc"
SEARCH_BASE     = "https://api.myscheme.gov.in"
RULES_BASE      = "https://rules.myscheme.gov.in"
OUTPUT_FILE     = "scheme_questions.json"
PAGE_SIZE       = 100   # max the API accepts reliably
MAX_WORKERS     = 20    # concurrent requests for questions
REQUEST_TIMEOUT = 15    # seconds

# ── Step 1: Fetch all scheme slugs + names ─────────────────────────────────────
def fetch_schemes_page(size, frm):
    filters = []   # no filters = all schemes
    q = urllib.parse.quote(json.dumps(filters, separators=(",", ":")))
    url = (f"{SEARCH_BASE}/search/v6/schemes"
           f"?lang=en&q={q}&keyword=&sort=&from={frm}&size={size}")
    req = urllib.request.Request(url, headers={
        "x-api-key": SEARCH_API_KEY,
        "origin":    "https://www.myscheme.gov.in",
        "user-agent": "Mozilla/5.0",
    })
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
        data = json.loads(r.read())
    d = data.get("data")
    if not isinstance(d, dict):
        return [], 0
    hits = d.get("hits", {})
    items = hits.get("items", [])
    total = hits.get("page", {}).get("total", 0)
    return items, total

def fetch_all_schemes():
    print("Fetching scheme list...", flush=True)
    # first page gives us the total count
    items, total = fetch_schemes_page(PAGE_SIZE, 0)
    print(f"  Total schemes on site: {total}", flush=True)

    all_items = list(items)
    offset = PAGE_SIZE
    while offset < total:
        page_items, _ = fetch_schemes_page(PAGE_SIZE, offset)
        if not page_items:
            break
        all_items.extend(page_items)
        offset += PAGE_SIZE
        print(f"  Fetched {len(all_items)}/{total} schemes...", flush=True)

    schemes = [
        {
            "slug": i["fields"]["slug"],
            "name": i["fields"]["schemeName"],
            "ministry": i["fields"].get("nodalMinistryName", ""),
            "category": i["fields"].get("schemeCategory", []),
            "level": i["fields"].get("level", ""),
            "state": i["fields"].get("beneficiaryState", []),
        }
        for i in all_items
        if i.get("fields", {}).get("slug")
    ]

    # deduplicate by slug
    seen, unique = set(), []
    for s in schemes:
        if s["slug"] not in seen:
            seen.add(s["slug"])
            unique.append(s)

    print(f"✓ {len(unique)} unique schemes collected\n", flush=True)
    return unique


# ── Step 2: Get the dynamic buildId from rules.myscheme.gov.in ─────────────────
def fetch_build_id():
    req = urllib.request.Request(RULES_BASE, headers={
        "user-agent": "Mozilla/5.0",
        "referer":    "https://www.myscheme.gov.in/",
    })
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
        html = r.read().decode("utf-8", errors="replace")
    m = re.search(r'"buildId":"([^"]+)"', html)
    if not m:
        raise RuntimeError("Could not extract buildId from rules.myscheme.gov.in")
    build_id = m.group(1)
    print(f"✓ buildId: {build_id}\n", flush=True)
    return build_id


# ── Step 3: Fetch eligibility questions for one scheme ─────────────────────────
def fetch_questions(slug, build_id):
    url = f"{RULES_BASE}/_next/data/{build_id}/en/check-eligibility/{slug}.json"
    try:
        req = urllib.request.Request(url, headers={
            "user-agent": "Mozilla/5.0",
            "referer":    "https://www.myscheme.gov.in/",
        })
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
            d = json.loads(r.read())

        props = (d.get("pageProps", {})
                  .get("questionData", {})
                  .get("data", {}))
        schema       = props.get("schema", {})
        properties   = schema.get("properties", {})
        required_set = set(schema.get("required", []))

        questions = [
            {
                "key":      k,
                "title":    v.get("title", k),
                "positive": v.get("positive", "Yes"),
                "negative": v.get("negative", "No"),
                "required": k in required_set,
            }
            for k, v in properties.items()
        ]
        return slug, questions, None

    except urllib.error.HTTPError as e:
        return slug, [], f"HTTP {e.code}"
    except Exception as e:
        return slug, [], str(e)


# ── Step 4: Concurrent scrape ──────────────────────────────────────────────────
def scrape_all_questions(schemes, build_id):
    print(f"Scraping questions for {len(schemes)} schemes "
          f"(concurrency={MAX_WORKERS})...\n", flush=True)

    results, errors, done = [], [], 0
    total = len(schemes)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_scheme = {
            executor.submit(fetch_questions, s["slug"], build_id): s
            for s in schemes
        }
        for future in as_completed(future_to_scheme):
            scheme = future_to_scheme[future]
            slug, questions, err = future.result()
            done += 1

            if err:
                errors.append({
                    "slug":        slug,
                    "scheme_name": scheme["name"],
                    "error":       err,
                })
                print(f"  [{done:4d}/{total}] ✗ {slug:50s} — {err}", flush=True)
            else:
                results.append({
                    "slug":           slug,
                    "scheme_name":    scheme["name"],
                    "ministry":       scheme["ministry"],
                    "category":       scheme["category"],
                    "level":          scheme["level"],
                    "state":          scheme["state"],
                    "question_count": len(questions),
                    "questions":      questions,
                })
                marker = "✓" if questions else "○"
                label  = f"{len(questions)}q" if questions else "no questions"
                print(f"  [{done:4d}/{total}] {marker} {slug:50s} {label}", flush=True)

    return results, errors


# ── Step 5: Save + print summary ───────────────────────────────────────────────
def save_and_summarise(results, errors):
    from collections import Counter

    total_q = sum(r["question_count"] for r in results)

    output = {
        "meta": {
            "total_schemes_attempted":    len(results) + len(errors),
            "schemes_with_questions":     len([r for r in results if r["question_count"] > 0]),
            "schemes_without_questions":  len([r for r in results if r["question_count"] == 0]),
            "schemes_failed_404":         len(errors),
            "total_questions_collected":  total_q,
        },
        "schemes": sorted(results, key=lambda x: x["scheme_name"].strip().lower()),
        "failed":  errors,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    dist = Counter(r["question_count"] for r in results)

    print(f"\n{'═'*54}")
    print(f"  Schemes attempted      : {output['meta']['total_schemes_attempted']}")
    print(f"  With questions         : {output['meta']['schemes_with_questions']}")
    print(f"  Without questions      : {output['meta']['schemes_without_questions']}")
    print(f"  Failed (no eligib. pg) : {output['meta']['schemes_failed_404']}")
    print(f"  Total questions        : {total_q}")
    print(f"\n  Question count distribution:")
    for k in sorted(dist):
        bar = "█" * dist[k]
        print(f"    {k:2d}q : {dist[k]:4d}  {bar[:60]}")
    print(f"\n  Saved → {OUTPUT_FILE}")
    print(f"{'═'*54}")


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    schemes  = fetch_all_schemes()
    build_id = fetch_build_id()
    results, errors = scrape_all_questions(schemes, build_id)
    save_and_summarise(results, errors)