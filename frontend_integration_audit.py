"""
FRONTEND INTEGRATION AUDIT
===========================
1. Extract all API endpoints called by dashboard.html
2. Check if they're defined in app.py
3. Identify old/broken endpoints
4. Check for questions form in "possibly eligible" tab
"""

import re
from pathlib import Path

print("\n" + "=" * 160)
print("FRONTEND INTEGRATION AUDIT - Dashboard vs Backend")
print("=" * 160)

# ========================================
# STEP 1: Extract endpoints from dashboard.html
# ========================================
print("\n🔍 STEP 1: Extracting API endpoints from dashboard.html...")
print("-" * 160)

dashboard_path = Path(r"c:\yojanamitra_complete\static\dashboard.html")
dashboard_content = dashboard_path.read_text(encoding='utf-8', errors='ignore')

# Find all fetch calls
fetch_pattern = r"fetch\s*\(\s*['\"]([^'\"]+)['\"]"
dashboard_endpoints = set()

for match in re.finditer(fetch_pattern, dashboard_content):
    endpoint = match.group(1)
    # Normalize dynamic paths
    endpoint = re.sub(r'/\d+', '/{id}', endpoint)
    endpoint = re.sub(r'/[a-f0-9]{8}-[a-f0-9]{4}', '/{uuid}', endpoint)
    dashboard_endpoints.add(endpoint)

print(f"\nFound {len(dashboard_endpoints)} unique endpoints called by dashboard:")
for i, ep in enumerate(sorted(dashboard_endpoints), 1):
    print(f"  {i:2d}. {ep}")

# ========================================
# STEP 2: Extract endpoints defined in app.py
# ========================================
print("\n" + "-" * 160)
print("🔍 STEP 2: Extracting defined routes from app.py...")
print("-" * 160)

app_path = Path(r"c:\yojanamitra_complete\app.py")
app_content = app_path.read_text(encoding='utf-8', errors='ignore')

# Find all route definitions
route_pattern = r"@app\.route\s*\(\s*['\"]([^'\"]+)['\"]"
app_endpoints = set()

for match in re.finditer(route_pattern, app_content):
    endpoint = match.group(1)
    # Normalize dynamic paths
    endpoint = re.sub(r'<\w+>', '{id}', endpoint)
    endpoint = re.sub(r'<int:\w+>', '{id}', endpoint)
    endpoint = re.sub(r'<path:\w+>', '/{path}', endpoint)
    app_endpoints.add(endpoint)

print(f"\nFound {len(app_endpoints)} unique routes defined in app.py:")
for i, ep in enumerate(sorted(app_endpoints), 1):
    print(f"  {i:2d}. {ep}")

# ========================================
# STEP 3: Find mismatches
# ========================================
print("\n" + "=" * 160)
print("ENDPOINT ANALYSIS")
print("=" * 160)

# Normalize for comparison
def normalize_endpoint(ep):
    """Normalize endpoint for comparison"""
    ep = ep.lower()
    ep = re.sub(r'/\{[^}]+\}', '/{id}', ep)
    return ep

dashboard_norm = {normalize_endpoint(ep): ep for ep in dashboard_endpoints}
app_norm = {normalize_endpoint(ep): ep for ep in app_endpoints}

missing_in_app = []
found_in_app = []

for norm, original in dashboard_norm.items():
    if norm in app_norm:
        found_in_app.append((original, app_norm[norm]))
    else:
        missing_in_app.append(original)

print(f"\n✅ ENDPOINTS FOUND (Dashboard calls exist in app.py): {len(found_in_app)}")
for original, defined in sorted(found_in_app):
    print(f"   ✓ {original:<40} → {defined}")

if missing_in_app:
    print(f"\n❌ ENDPOINTS MISSING/BROKEN: {len(missing_in_app)}")
    print(f"   These endpoints are called by dashboard but NOT defined in app.py:")
    for ep in sorted(missing_in_app):
        print(f"   ✗ {ep:<40}")
else:
    print(f"\n✅ NO MISSING ENDPOINTS - All dashboard calls are properly handled!")

# ========================================
# STEP 4: Check for questions form in dashboard
# ========================================
print("\n" + "=" * 160)
print("QUESTIONS FORM INTEGRATION CHECK")
print("=" * 160)

# Check if dashboard has question form
questions_keywords = [
    "question", "answer", "submit_answer", "/api/user/answer",
    "possibly_eligible", "possibly eligible", "question form"
]

dashboard_lower = dashboard_content.lower()
questions_found = []

for keyword in questions_keywords:
    if keyword.lower() in dashboard_lower:
        questions_found.append(keyword)

print(f"\n📋 Checking for questions form integration...")

if not questions_found:
    print(f"   ⚠️  WARNING: No questions form keywords found in dashboard!")
else:
    print(f"   ✅ Found {len(questions_found)} question-related keywords:")
    for kw in sorted(set(questions_found)):
        print(f"      • {kw}")

# Check if /api/user/answer endpoint is defined
if "/api/user/answer" in app_endpoints or "/api/user/{id}" in app_endpoints:
    print(f"   ✅ /api/user/answer endpoint is properly defined")
else:
    print(f"   ❌ /api/user/answer endpoint is NOT defined!")

# Check for question rendering/display code
if "question" in dashboard_lower:
    question_lines = [
        i for i, line in enumerate(dashboard_content.split('\n'))
        if 'question' in line.lower()
    ]
    print(f"\n   Found {len(question_lines)} lines mentioning 'question' in dashboard.html")
    
    # Show a sample
    if question_lines:
        sample_line_num = question_lines[0]
        lines = dashboard_content.split('\n')
        start = max(0, sample_line_num - 2)
        end = min(len(lines), sample_line_num + 3)
        print(f"\n   Sample (line {sample_line_num}):")
        for i in range(start, end):
            prefix = "   >>> " if i == sample_line_num else "       "
            print(f"{prefix}{lines[i][:100]}")

# ========================================
# STEP 5: Check for dynamically loaded question form
# ========================================
print("\n" + "-" * 160)
print("🔍 STEP 3: Checking for question form HTML/component...")
print("-" * 160)

# Check for question form ID or class
form_patterns = [
    r'id\s*=\s*["\'].*question.*["\']',
    r'class\s*=\s*["\'].*question.*["\']',
    r'id\s*=\s*["\'].*answer.*["\']',
    r'data-questions'
]

form_elements = []
for pattern in form_patterns:
    for match in re.finditer(pattern, dashboard_content, re.IGNORECASE):
        form_elements.append(match.group(0)[:80])

if form_elements:
    print(f"\n✅ Found {len(set(form_elements))} question-related form elements:")
    for elem in sorted(set(form_elements)):
        print(f"   • {elem}")
else:
    print(f"\n⚠️  WARNING: No question form elements found (id/class with 'question' or 'answer')")

# Check for "possibly eligible" or "possible" section
if "possib" in dashboard_lower or "possible" in dashboard_lower:
    print(f"\n✅ Found reference to 'possible/possibly eligible' tab")
    
    # Count occurrences
    count = dashboard_lower.count("possib")
    print(f"   Total mentions: {count}")
else:
    print(f"\n❌ NO reference to 'possible/possibly eligible' section found!")

# ========================================
# FINAL SUMMARY
# ========================================
print("\n" + "=" * 160)
print("FINAL AUDIT SUMMARY")
print("=" * 160)

summary_status = "✅ PASS" if not missing_in_app else "❌ FAIL"

print(f"""
╔════════════════════════════════════════════════════╗
║          FRONTEND INTEGRATION STATUS               ║
╠════════════════════════════════════════════════════╣
║                                                    ║
║  Dashboard Endpoints:          {len(dashboard_endpoints):3d}
║  App Routes Defined:           {len(app_endpoints):3d}
║  ✓ Endpoints Found:            {len(found_in_app):3d}
║  ✗ Endpoints Missing:          {len(missing_in_app):3d}
║                                                    ║
║  Question Form Integration:    {"✅ Found" if questions_found else "❌ Missing"}
║  Possibly Eligible Tab:        {"✅ Found" if "possib" in dashboard_lower else "❌ Missing"}
║                                                    ║
║  Status: {summary_status}                          ║
║                                                    ║
╚════════════════════════════════════════════════════╝
""")

if missing_in_app:
    print(f"\n⚠️  ACTION REQUIRED:")
    print(f"   The following endpoints need to be implemented in app.py:")
    for ep in sorted(missing_in_app):
        print(f"   • {ep}")

print("\n" + "=" * 160)
