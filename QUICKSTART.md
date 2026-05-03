# Yojanamitra: Quick Start Guide

## 5-Minute Setup & First Run

### 1. Prerequisites Check

```bash
# Verify Python 3.8+
python --version

# Verify required files exist
ls -la all_schemes_final.json
ls -la all_schemes_eligibility.json
ls -la all_questions_by_scheme.json
```

### 2. Run the System

```python
# Simple one-liner execution
python workflow_orchestrator.py
```

**Expected Output:**
```
============================================================
STARTING ELIGIBILITY WORKFLOW
============================================================
2024-01-15 10:30:45 - WorkflowOrchestrator - INFO - Loading data files...
2024-01-15 10:30:47 - WorkflowOrchestrator - INFO - Loaded 4226 schemes
...
============================================================
WORKFLOW COMPLETED
Results: 45 verified matches out of 87 candidates
============================================================

WORKFLOW SUMMARY
============================================================
Total Schemes Analyzed: 4226
Matching Schemes Found: 87
Verified Matches: 45
Status: success

Top Matching Schemes:
  1. Pradhan Mantri Jan Dhan Yojana (Score: 0.92)
  2. State Scholarship for SC/ST (Score: 0.88)
  3. Women Entrepreneur Scheme (Score: 0.85)
```

---

## Common Usage Patterns

### Pattern 1: Single User Analysis

```python
from workflow_orchestrator import WorkflowOrchestrator
import json

# Create orchestrator
orchestrator = WorkflowOrchestrator()

# Define user profile
user_profile = {
    'age': 25,
    'gender': 'Male',
    'state': 'Karnataka',
    'annual_income': 200000,
    'education': 'Bachelor',
    'occupation': 'Software Engineer',
    'is_student': False,
    'is_disabled': False
}

# Run analysis
results = orchestrator.run_full_workflow(user_profile)

# Print top 10 matches
print("\n📋 ELIGIBILITY RESULTS\n")
print(f"✅ Found {len(results['verified_matches'])} eligible schemes\n")

for i, scheme in enumerate(results['verified_matches'][:10], 1):
    score = scheme.get('verification_score', 0)
    status = "✓" if score > 0.8 else "○"
    print(f"{status} {i}. {scheme['scheme_name']}")
    print(f"   Score: {score:.1%}")
    if 'answerable_questions' in scheme:
        print(f"   Q&A: {scheme['answerable_questions']}/{scheme['total_questions']} answerable\n")

# Save results
orchestrator.save_results('my_results.json')
```

**Output:**
```
📋 ELIGIBILITY RESULTS

✅ Found 45 eligible schemes

✓ 1. Pradhan Mantri Jan Dhan Yojana (PMJDY)
   Score: 92.0%
   Q&A: 2/2 answerable

✓ 2. State Scholarship for General Category
   Score: 88.5%
   Q&A: 1/1 answerable

✓ 3. Stree Shakti Scheme
   Score: 85.2%
   Q&A: 3/3 answerable
```

### Pattern 2: Batch Processing

```python
import pandas as pd
import json
from workflow_orchestrator import WorkflowOrchestrator

# Load user data
users_df = pd.read_csv('users_to_analyze.csv')
orchestrator = WorkflowOrchestrator()

# Process each user
results_list = []

for idx, user_row in users_df.iterrows():
    print(f"Processing user {idx + 1}/{len(users_df)}...", end=' ')
    
    # Convert row to profile dict
    profile = user_row.to_dict()
    
    # Run analysis
    results = orchestrator.run_full_workflow(profile)
    
    # Extract summary
    summary = {
        'user_id': user_row.get('id', idx),
        'age': user_row['age'],
        'state': user_row['state'],
        'matches_found': len(results['verified_matches']),
        'top_scheme': results['verified_matches'][0]['scheme_name'] if results['verified_matches'] else 'None',
        'top_score': results['verified_matches'][0].get('verification_score', 0) if results['verified_matches'] else 0
    }
    
    results_list.append(summary)
    print("✓")

# Save batch results
results_df = pd.DataFrame(results_list)
results_df.to_csv('batch_analysis_results.csv', index=False)

# Print summary statistics
print(f"\n📊 BATCH PROCESSING SUMMARY")
print(f"Users processed: {len(results_df)}")
print(f"Average schemes found: {results_df['matches_found'].mean():.1f}")
print(f"Users with 0 matches: {(results_df['matches_found'] == 0).sum()}")
print(f"Average top score: {results_df['top_score'].mean():.1%}")
```

### Pattern 3: Interactive CLI

```python
from workflow_orchestrator import WorkflowOrchestrator

def get_user_input():
    """Interactive profile collection."""
    print("\n🔍 YOJANAMITRA - ELIGIBILITY CHECKER\n")
    
    profile = {}
    
    # Age
    while True:
        try:
            profile['age'] = int(input("Enter your age: "))
            if 0 < profile['age'] < 150:
                break
            print("Please enter a valid age (1-149)")
        except ValueError:
            print("Please enter a number")
    
    # Gender
    gender_options = ['Male', 'Female', 'Other', 'Prefer not to say']
    print("\nGender:")
    for i, g in enumerate(gender_options, 1):
        print(f"  {i}. {g}")
    gender_choice = int(input("Select (1-4): "))
    profile['gender'] = gender_options[gender_choice - 1]
    
    # State
    profile['state'] = input("\nEnter your state: ")
    
    # Income
    while True:
        try:
            profile['annual_income'] = int(input("Annual income (₹): "))
            break
        except ValueError:
            print("Please enter a number")
    
    # Education
    education_options = ['Below 10th', '10th Pass', '12th Pass', 'Graduate', 'Postgraduate']
    print("\nEducation:")
    for i, e in enumerate(education_options, 1):
        print(f"  {i}. {e}")
    education_choice = int(input("Select (1-5): "))
    profile['education'] = education_options[education_choice - 1]
    
    # Special categories
    print("\nSpecial Categories (y/n):")
    profile['is_sc_st'] = input("Are you SC/ST? ").lower() == 'y'
    profile['is_obc'] = input("Are you OBC? ").lower() == 'y'
    profile['is_disabled'] = input("Are you disabled? ").lower() == 'y'
    profile['is_student'] = input("Are you a student? ").lower() == 'y'
    
    return profile

# Run interactive mode
orchestrator = WorkflowOrchestrator()
user_profile = get_user_input()

print("\n⏳ Analyzing schemes...")
results = orchestrator.run_full_workflow(user_profile)

# Display results
print(f"\n✅ RESULTS - Found {len(results['verified_matches'])} eligible schemes\n")

for i, scheme in enumerate(results['verified_matches'][:15], 1):
    score = scheme.get('verification_score', 0)
    indicator = "🎯" if score > 0.85 else "✓"
    print(f"{indicator} {i:2d}. {scheme['scheme_name']:50} ({score:5.1%})")

print(f"\n📄 Detailed results saved to: workflow_results.json")
```

---

## Understanding Results

### Result Structure

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "user_profile": {
    "fields_provided": 8,
    "required_fields_met": true
  },
  "summary": {
    "total_schemes_analyzed": 4226,
    "matching_schemes_found": 87,
    "verified_matches": 45,
    "workflow_status": "success",
    "error_count": 0
  },
  "verified_matches": [
    {
      "scheme_id": "pmjjby",
      "scheme_name": "Pradhan Mantri Jan Dhan Yojana",
      "verification_score": 0.92,
      "answerable_questions": 2,
      "total_questions": 2,
      "verification_status": "verified"
    }
  ]
}
```

### Interpreting Scores

| Score Range | Interpretation | Recommendation |
|-------------|-----------------|-----------------|
| 0.90 - 1.00 | Highly Eligible | ✅ Apply immediately |
| 0.80 - 0.89 | Very Likely Eligible | ✅ Prepare documents & apply |
| 0.70 - 0.79 | Likely Eligible | ⚠️ Review criteria carefully |
| 0.60 - 0.69 | Possibly Eligible | ℹ️ Verify with official source |
| < 0.60 | Not Likely Eligible | ❌ Below threshold |

---

## Troubleshooting

### Issue 1: "File not found" errors

**Problem:** Missing data files
```
FileNotFoundError: all_schemes_final.json not found
```

**Solution:**
```bash
# Verify files exist
ls -la *.json

# If missing, regenerate:
python standardize_scheme_data.py
python build_concept_registry_final.py
python generate_questions_final.py
```

### Issue 2: Encoding errors

**Problem:** Unicode/encoding issues
```
UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d
```

**Solution:**
```python
# Already handled in workflow_orchestrator.py
# Ensures UTF-8 encoding:
with open(file, 'r', encoding='utf-8') as f:
    data = json.load(f)
```

### Issue 3: Very few results

**Problem:** Getting < 10 eligible schemes

**Reasons & Solutions:**
1. **Income threshold too high**
   - Many schemes have income limits of ₹2-5 lakh
   - Reduce income in profile or adjust threshold in config

2. **State not applicable**
   - Verify your state spelling
   - Some schemes are national, some state-specific

3. **Age outside most ranges**
   - Most schemes target 18-65 age range
   - Change age in profile if testing

**Debug:**
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Or check specific scheme
scheme_id = 'pmjjby'
scheme_data = orchestrator.schemes_data.get(scheme_id)
eligibility = orchestrator.eligibility_data.get(scheme_id)
print(f"Scheme: {scheme_data['scheme_name']}")
print(f"Age Range: {eligibility.get('age_range')}")
print(f"States: {eligibility.get('applicable_states')}")
```

### Issue 4: High memory usage

**Problem:** System uses too much RAM (>2GB)

**Solution:**
```python
# Process schemes in batches instead of loading all
# Modify workflow_orchestrator.py:

max_schemes = 1000  # Limit schemes to process
for scheme_id in list(eligibility_data.keys())[:max_schemes]:
    # Process scheme...
```

---

## Configuration Options

### Basic Configuration

```json
{
  "data_dir": ".",
  "schemes_file": "all_schemes_final.json",
  "eligibility_file": "all_schemes_eligibility.json",
  "questions_file": "all_questions_by_scheme.json",
  "max_matches": 50,
  "confidence_threshold": 0.60,
  "enable_detailed_logging": true
}
```

### Advanced Configuration

```json
{
  "data_dir": ".",
  "schemes_file": "all_schemes_final.json",
  "eligibility_file": "all_schemes_eligibility.json",
  "questions_file": "all_questions_by_scheme.json",
  "max_matches": 50,
  "confidence_threshold": 0.60,
  "enable_detailed_logging": true,
  "scoring_weights": {
    "age": 0.3,
    "state": 0.3,
    "gender": 0.2,
    "income": 0.2
  },
  "answer_score_weight": 0.5,
  "enable_caching": false,
  "cache_ttl_seconds": 3600
}
```

---

## Performance Tips

### Optimization 1: Caching Results
```python
# Cache user results to avoid reprocessing
cache = {}

def get_schemes_cached(profile_key, profile_dict):
    if profile_key in cache:
        return cache[profile_key]
    
    results = orchestrator.run_full_workflow(profile_dict)
    cache[profile_key] = results
    return results
```

### Optimization 2: Limiting Schemes
```python
# Only analyze recent/popular schemes
config = {
    'schemes_filter': 'active',  # Only active schemes
    'max_schemes': 2000,          # Process top 2000
    'priority_states': ['Karnataka', 'Maharashtra']
}
orchestrator = WorkflowOrchestrator(config)
```

### Optimization 3: Parallel Processing
```python
from concurrent.futures import ThreadPoolExecutor
import json

users = json.load(open('users.json'))
orchestrator = WorkflowOrchestrator()

def process_user(user):
    return orchestrator.run_full_workflow(user)

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(process_user, users))
```

---

## API Reference

### WorkflowOrchestrator Class

#### `__init__(config: Dict = None)`
Initialize orchestrator with optional configuration

#### `load_data() -> bool`
Load all required data files
- Returns: True if all files loaded successfully

#### `load_user_profile(profile: Dict) -> bool`
Load and validate user profile
- Args: User profile dictionary
- Returns: True if valid

#### `determine_matching_schemes() -> List[Dict]`
Find matching schemes based on user profile
- Returns: List of matching schemes with scores

#### `verify_with_questions(matches: List) -> List[Dict]`
Verify matches using Q&A verification
- Args: List of matching schemes
- Returns: Verified matches with verification scores

#### `generate_report() -> Dict`
Generate comprehensive results report
- Returns: Dictionary with all results

#### `save_results(output_file: str) -> bool`
Save results to JSON file
- Args: Output file path
- Returns: True if saved successfully

#### `run_full_workflow(user_profile: Dict) -> Dict`
Execute complete workflow (main entry point)
- Args: User profile dictionary
- Returns: Complete workflow results

---

## Examples Directory Structure

```
project/
├── workflow_orchestrator.py          # Main orchestrator
├── workflow_config.json              # Configuration
├── all_schemes_final.json            # Scheme data (4.2GB)
├── all_schemes_eligibility.json      # Eligibility data
├── all_questions_by_scheme.json      # Q&A data
├── SYSTEM_ARCHITECTURE.md            # This guide
└── examples/
    ├── single_user.py                # Single user analysis
    ├── batch_processing.py           # Batch user processing
    ├── interactive_cli.py            # CLI application
    └── api_integration.py            # REST API integration
```

---

## Next Steps

1. **Run your first analysis:**
   ```bash
   python workflow_orchestrator.py
   ```

2. **Try with your own profile:**
   See Pattern 1 above

3. **Integrate with your application:**
   See Pattern 2-3 or SYSTEM_ARCHITECTURE.md

4. **Explore results:**
   Open `workflow_results.json` to see detailed results

5. **Customize scoring:**
   Edit configuration in `workflow_config.json`

---

## Support & Documentation

- **Architecture Details:** See [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md)
- **Navigation Guide:** See [00_NAVIGATION_GUIDE.md](00_NAVIGATION_GUIDE.md)
- **Data Analysis:** See `analyze_schemes_dataset.py`
- **Logs:** Check `workflow.log` for detailed execution logs

---

*Quick Start Guide - Yojanamitra v2.0*
*Ready for production use*
