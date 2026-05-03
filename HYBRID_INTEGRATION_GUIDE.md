# HYBRID SYSTEM INTEGRATION GUIDE

**Purpose:** Step-by-step instructions for integrating the three new hybrid system modules into the existing Yojana Mitra codebase.

**Files to Integrate:**
1. `semantic_eligibility_extractor.py` ← Semantic extraction
2. `hybrid_eligibility_matcher.py` ← Three-layer orchestration
3. `hybrid_validation_suite.py` ← Testing & field analysis

---

## STEP 1: Add New Imports to app.py

At the top of `app.py`, add:

```python
# Hybrid Eligibility System
from semantic_eligibility_extractor import SemanticExtractor
from hybrid_eligibility_matcher import HybridEligibilityMatcher
from hybrid_validation_suite import ProfileFieldAnalyzer

# Initialize hybrid components (at app startup)
semantic_extractor = SemanticExtractor()
hybrid_matcher = HybridEligibilityMatcher(semantic_extractor)
field_analyzer = ProfileFieldAnalyzer()
```

---

## STEP 2: Create New API Endpoint

Add this endpoint to `app.py`:

```python
@app.route('/api/schemes/eligible/hybrid', methods=['POST'])
def eligible_schemes_hybrid():
    """
    NEW: Hybrid three-layer eligibility check with semantic understanding
    
    Query Parameters:
      - include_ai: bool (default: False) - Include AI validation on top schemes
      - limit: int (default: 100) - Maximum schemes to return
    
    Request Body:
      {
        "user_id": str,
        "age": int,
        "gender": str,
        "state": str,
        "income": float,
        "occupations": list,
        "caste_category": str,
        "is_widow": bool,
        "is_disabled": bool,
        "is_senior_citizen": bool,
        "education_level": str (NEW),
        "marital_status": str (NEW),
        "economic_status": str (NEW),
        "owns_agricultural_land": bool (NEW)
      }
    
    Returns:
      {
        "status": "success",
        "user_id": str,
        "eligible_count": int,
        "schemes": [
          {
            "scheme_id": str,
            "scheme_name": str,
            "eligibility_class": str,
            "confidence_score": int,
            "layers": {...},
            "rejection_reason": str
          }
        ],
        "profile_gaps": {
          "missing_fields": [...],
          "profile_completeness": float,
          "recommended_improvements": [...]
        }
      }
    """
    try:
        user_data = request.get_json()
        limit = request.args.get('limit', 100, type=int)
        include_ai = request.args.get('include_ai', 'false').lower() == 'true'
        
        # Validate user data
        required_fields = ['age', 'gender', 'state']
        if not all(field in user_data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Convert JSON to UserProfile object
        from sqlalchemy import and_
        user_profile = UserProfile(
            user_id=user_data.get('user_id', 'ANON'),
            age=user_data['age'],
            gender=user_data['gender'],
            state=user_data['state'],
            annual_income=user_data.get('income'),
            occupations=user_data.get('occupations', []),
            caste_category=user_data.get('caste_category', 'General'),
            is_widow=user_data.get('is_widow', False),
            is_disabled=user_data.get('is_disabled', False),
            is_senior_citizen=user_data.get('is_senior_citizen', False),
            is_minority=user_data.get('is_minority', False),
            # NEW FIELDS
            education_level=user_data.get('education_level'),
            marital_status=user_data.get('marital_status'),
            economic_status=user_data.get('economic_status'),
            owns_agricultural_land=user_data.get('owns_agricultural_land'),
        )
        
        # Get all schemes from database
        all_schemes = db.session.query(Scheme).all()
        
        # Run hybrid matching
        results = []
        for scheme in all_schemes:
            # Convert Scheme model to dict
            scheme_dict = {
                'id': scheme.id,
                'name': scheme.name,
                'min_age': scheme.min_age,
                'max_age': scheme.max_age,
                'allowed_states': scheme.allowed_states or [],
                'allowed_genders': scheme.allowed_genders or ['M', 'F', 'Other'],
                'allowed_castes': scheme.allowed_castes or [],
                'description': scheme.description,
                'eligibility_criteria': scheme.eligibility_criteria,
                'notes': scheme.notes,
                'require_widow': scheme.require_widow or False,
                'require_disabled': scheme.require_disabled or False,
                'require_senior': scheme.require_senior or False,
            }
            
            # Run hybrid matcher
            result = hybrid_matcher.match(user_profile, scheme_dict)
            results.append(result)
        
        # Sort by confidence score (descending)
        results.sort(key=lambda x: x['confidence_score'], reverse=True)
        
        # Limit results
        results = results[:limit]
        
        # Identify profile gaps
        profile_gaps = field_analyzer.identify_profile_gaps(
            user_profile, 
            [r for r in results if r['final_eligibility'] == 'FULLY_ELIGIBLE']
        )
        
        return jsonify({
            'status': 'success',
            'user_id': user_profile.user_id,
            'eligible_count': sum(1 for r in results if r['final_eligibility'] == 'FULLY_ELIGIBLE'),
            'possibly_eligible_count': sum(1 for r in results if r['final_eligibility'] == 'POSSIBLY_ELIGIBLE'),
            'schemes': results,
            'profile_gaps': profile_gaps
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

---

## STEP 3: Update User Profile Model

Modify the `User` or `UserProfile` model in `app.py` to add new fields:

```python
class User(db.Model):
    # ... existing fields ...
    
    # NEW: Priority 1 fields for hybrid system
    education_level = db.Column(
        db.String(50),
        comment="Class I-XII, UG, PG, Diploma, ITI, No formal education"
    )
    marital_status = db.Column(
        db.String(30),
        comment="Single, Married, Widow, Divorced, Separated"
    )
    economic_status = db.Column(
        db.String(30),
        comment="BPL, APL, EWS, LIG, MIG, HIG"
    )
    owns_agricultural_land = db.Column(
        db.Boolean,
        default=False,
        comment="For farmer schemes"
    )
    land_size_acres = db.Column(
        db.Float,
        comment="Agricultural land size in acres"
    )
    
    # NEW: Priority 2 fields (optional, for Phase 2)
    disability_type = db.Column(
        db.String(100),
        comment="Visual, Hearing, Mobility, Mental, Multiple, Other"
    )
    employment_type = db.Column(
        db.String(50),
        comment="Formal, Informal, Self-employed, Unemployed"
    )
```

---

## STEP 4: Create Database Migration

Create a new migration file (Flask-Migrate):

```bash
flask db migrate -m "Add hybrid system fields to user profile"
flask db upgrade
```

Or manually (if not using Flask-Migrate):

```sql
-- c:\ymf\yojana-mitra-backend\migrations\add_hybrid_fields.sql

ALTER TABLE user ADD COLUMN education_level VARCHAR(50);
ALTER TABLE user ADD COLUMN marital_status VARCHAR(30);
ALTER TABLE user ADD COLUMN economic_status VARCHAR(30);
ALTER TABLE user ADD COLUMN owns_agricultural_land BOOLEAN DEFAULT FALSE;
ALTER TABLE user ADD COLUMN land_size_acres FLOAT;
ALTER TABLE user ADD COLUMN disability_type VARCHAR(100);
ALTER TABLE user ADD COLUMN employment_type VARCHAR(50);

CREATE INDEX idx_hybrid_fields ON user(
    education_level,
    marital_status,
    economic_status
);
```

Run migration:
```bash
# Using sqlite3
sqlite3 c:\ymf\yojana-mitra-backend\instance\yojana_mitra.db < migrations\add_hybrid_fields.sql

# Or with psql (if PostgreSQL)
psql -U postgres -d yojana_mitra -f migrations\add_hybrid_fields.sql
```

---

## STEP 5: Add Semantic Profile Caching

Create cache table to store extracted semantic conditions:

```python
class SchemeSemanticProfile(db.Model):
    """Cache of extracted semantic conditions for each scheme"""
    id = db.Column(db.Integer, primary_key=True)
    scheme_id = db.Column(db.Integer, db.ForeignKey('scheme.id'), unique=True)
    
    # Extracted conditions (stored as JSON)
    education_conditions = db.Column(db.JSON)  # [{"keyword": "UG", "confidence": 0.92}, ...]
    occupation_conditions = db.Column(db.JSON)
    economic_conditions = db.Column(db.JSON)
    beneficiary_conditions = db.Column(db.JSON)
    
    # Metadata
    extraction_date = db.Column(db.DateTime, default=datetime.utcnow)
    extraction_confidence = db.Column(db.Float)  # Overall confidence 0.0-1.0
    
    __tablename__ = 'scheme_semantic_profile'
```

Run batch extraction (one-time operation):

```python
# In a management command or script
def cache_all_semantic_profiles():
    """Extract and cache semantic profiles for all schemes"""
    all_schemes = db.session.query(Scheme).all()
    
    for scheme in all_schemes:
        scheme_dict = {
            'id': scheme.id,
            'name': scheme.name,
            'description': scheme.description,
            'eligibility_criteria': scheme.eligibility_criteria,
            'notes': scheme.notes,
        }
        
        # Extract semantic conditions
        conditions = semantic_extractor.extract_from_scheme(scheme_dict)
        
        # Store in cache
        cache_entry = SchemeSemanticProfile(
            scheme_id=scheme.id,
            education_conditions=conditions['education'],
            occupation_conditions=conditions['occupation'],
            economic_conditions=conditions['economic_status'],
            beneficiary_conditions=conditions['beneficiary_type'],
            extraction_confidence=0.90,  # Average confidence
        )
        db.session.add(cache_entry)
    
    db.session.commit()
    print(f"Cached semantic profiles for {len(all_schemes)} schemes")
```

Run cache:
```bash
python -c "from app import app, cache_all_semantic_profiles; app.app_context().push(); cache_all_semantic_profiles()"
```

---

## STEP 6: Testing Integration

Test the new endpoint:

```bash
# Test with curl
curl -X POST http://localhost:5000/api/schemes/eligible/hybrid \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "TEST123",
    "age": 28,
    "gender": "M",
    "state": "Karnataka",
    "income": 500000,
    "occupations": ["IT Professional"],
    "caste_category": "General",
    "education_level": "UG",
    "marital_status": "Single",
    "economic_status": "HIG"
  }'
```

Expected response:
```json
{
  "status": "success",
  "user_id": "TEST123",
  "eligible_count": 45,
  "possibly_eligible_count": 12,
  "schemes": [
    {
      "scheme_id": "S123",
      "scheme_name": "Udyam MSME Registration",
      "eligibility_class": "FULLY_ELIGIBLE",
      "confidence_score": 98,
      ...
    }
  ],
  "profile_gaps": {...}
}
```

---

## STEP 7: Update Frontend Forms

**File:** `templates/profile_form.html` or `static/js/profile.vue`

Add new form fields:

```html
<!-- Education Level (Priority 1) -->
<div class="form-group">
  <label for="education_level">Education Level *</label>
  <select id="education_level" name="education_level" class="form-control" required>
    <option value="">-- Select Education Level --</option>
    <optgroup label="School Education">
      <option value="class_i">Class I</option>
      <option value="class_v">Class V</option>
      <option value="class_viii">Class VIII</option>
      <option value="class_x">Class X (10th Board)</option>
      <option value="class_xii">Class XII (12th Board)</option>
    </optgroup>
    <optgroup label="Higher Education">
      <option value="ug">UG (Bachelor's Degree)</option>
      <option value="pg">PG (Master's Degree/PhD)</option>
    </optgroup>
    <optgroup label="Vocational">
      <option value="diploma">Diploma</option>
      <option value="iti">ITI/Technical Training</option>
    </optgroup>
    <optgroup label="Other">
      <option value="no_formal">No Formal Education</option>
    </optgroup>
  </select>
  <small class="form-text text-muted">
    Helps match education-specific schemes like scholarships
  </small>
</div>

<!-- Marital Status (Priority 1) -->
<div class="form-group">
  <label for="marital_status">Marital Status *</label>
  <select id="marital_status" name="marital_status" class="form-control" required>
    <option value="">-- Select Marital Status --</option>
    <option value="single">Single</option>
    <option value="married">Married</option>
    <option value="widow">Widow</option>
    <option value="divorced">Divorced</option>
    <option value="separated">Separated</option>
  </select>
  <small class="form-text text-muted">
    Required for widow pensions and family schemes
  </small>
</div>

<!-- Economic Status (Priority 1) -->
<div class="form-group">
  <label for="economic_status">Economic Status *</label>
  <select id="economic_status" name="economic_status" class="form-control" required>
    <option value="">-- Select Economic Status --</option>
    <option value="bpl">BPL (Below Poverty Line)</option>
    <option value="apl">APL (Above Poverty Line)</option>
    <option value="ews">EWS (Economically Weaker Section)</option>
    <option value="lig">LIG (Low Income Group)</option>
    <option value="mig">MIG (Middle Income Group)</option>
    <option value="hig">HIG (High Income Group)</option>
  </select>
  <small class="form-text text-muted">
    Determines eligibility for welfare schemes
  </small>
</div>

<!-- Agricultural Land Ownership (Priority 1 - Conditional) -->
<div class="form-group" id="land_ownership_group" style="display:none;">
  <label>
    <input type="checkbox" id="owns_agricultural_land" name="owns_agricultural_land">
    I own agricultural land
  </label>
  <input type="number" 
         id="land_size_acres" 
         name="land_size_acres" 
         placeholder="Land size in acres" 
         class="form-control"
         step="0.5"
         min="0"
         max="1000">
  <small class="form-text text-muted">
    Required for farmer schemes like PM-KISAN
  </small>
</div>

<script>
// Show land ownership only if occupation contains "Farmer"
document.getElementById('occupations').addEventListener('change', function() {
  const occupations = Array.from(this.selectedOptions).map(opt => opt.value);
  const isFarmer = occupations.some(occ => occ.toLowerCase().includes('farmer'));
  document.getElementById('land_ownership_group').style.display = isFarmer ? 'block' : 'none';
});
</script>
```

Add update endpoint to handle form submission:

```python
@app.route('/api/user/profile/update', methods=['POST'])
@login_required
def update_user_profile():
    """Update user profile with new hybrid fields"""
    data = request.get_json()
    
    user = User.query.get(current_user.id)
    
    # Update new fields
    if 'education_level' in data:
        user.education_level = data['education_level']
    if 'marital_status' in data:
        user.marital_status = data['marital_status']
    if 'economic_status' in data:
        user.economic_status = data['economic_status']
    if 'owns_agricultural_land' in data:
        user.owns_agricultural_land = data.get('owns_agricultural_land', False)
        user.land_size_acres = data.get('land_size_acres')
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Profile updated successfully',
        'profile_completeness': calculate_profile_completeness(user)
    })
```

---

## STEP 8: Feature Flag Setup

Add feature flag for gradual rollout:

```python
# In config.py or settings
HYBRID_SYSTEM_ENABLED = os.getenv('HYBRID_SYSTEM_ENABLED', 'false').lower() == 'true'
HYBRID_SYSTEM_ROLLOUT_PERCENTAGE = int(os.getenv('HYBRID_SYSTEM_ROLLOUT_PERCENTAGE', 0))

# In app.py
@app.route('/api/schemes/eligible', methods=['POST'])
def eligible_schemes():
    """Original endpoint - route to hybrid or rule-based based on flag"""
    import random
    
    should_use_hybrid = (
        current_app.config['HYBRID_SYSTEM_ENABLED'] and 
        random.random() * 100 < current_app.config['HYBRID_SYSTEM_ROLLOUT_PERCENTAGE']
    )
    
    if should_use_hybrid:
        return eligible_schemes_hybrid()  # New hybrid implementation
    else:
        return eligible_schemes_strict()  # Original rule-based
```

Environment variables for deployment:
```bash
# Start with 0%
export HYBRID_SYSTEM_ENABLED=true
export HYBRID_SYSTEM_ROLLOUT_PERCENTAGE=0

# Gradually increase
# Day 1-2: 5%
export HYBRID_SYSTEM_ROLLOUT_PERCENTAGE=5

# Day 3-4: 25%
export HYBRID_SYSTEM_ROLLOUT_PERCENTAGE=25

# Day 5-6: 50%
export HYBRID_SYSTEM_ROLLOUT_PERCENTAGE=50

# Day 7+: 100% (if metrics OK)
export HYBRID_SYSTEM_ROLLOUT_PERCENTAGE=100
```

---

## STEP 9: Monitoring & Metrics

Add metrics tracking:

```python
from prometheus_client import Counter, Histogram

# Metrics
hybrid_scheme_matches = Counter(
    'hybrid_scheme_matches_total',
    'Total hybrid scheme matches',
    ['eligibility_class']
)

hybrid_layer_execution_time = Histogram(
    'hybrid_layer_execution_seconds',
    'Execution time per layer',
    ['layer']
)

@app.route('/api/schemes/eligible/hybrid', methods=['POST'])
def eligible_schemes_hybrid():
    start = time.time()
    
    # ... existing code ...
    
    # Track metrics
    hybrid_scheme_matches.labels(eligibility_class='FULLY_ELIGIBLE').inc(
        sum(1 for r in results if r['final_eligibility'] == 'FULLY_ELIGIBLE')
    )
    
    execution_time = time.time() - start
    hybrid_layer_execution_time.labels(layer='all').observe(execution_time)
    
    return jsonify({...})
```

---

## STEP 10: Validation & Testing

Run comprehensive tests:

```bash
# Run unit tests
python -m pytest tests/test_hybrid_system.py -v

# Run integration tests
python -m pytest tests/test_api_integration.py::test_eligible_schemes_hybrid -v

# Load testing (1000 concurrent requests)
ab -n 1000 -c 100 http://localhost:5000/api/schemes/eligible/hybrid

# Validation suite
python hybrid_validation_suite.py --schemes-count 4324 --profiles-count 20
```

---

## Troubleshooting

### Issue: Semantic extractor not finding conditions

**Solution:** Verify regex patterns match your scheme data:
```python
# Debug regex patterns
from semantic_eligibility_extractor import SemanticExtractor
extractor = SemanticExtractor()

test_scheme = {
    'description': 'Only for farmers aged 18-60',
    'eligibility_criteria': 'BPL families',
}
conditions = extractor.extract_from_scheme(test_scheme)
print(conditions)  # Should show extracted conditions
```

### Issue: API timeout (>5 seconds)

**Solution:** 
1. Enable caching: `SchemeSemanticProfile` table
2. Reduce schemes evaluated: add `limit` parameter
3. Disable AI validation: set `include_ai=false`

### Issue: False positives still occurring

**Solution:**
1. Review rejected reasons in results
2. Update semantic extraction patterns if needed
3. Ensure new user profile fields are being collected
4. Run validation suite to identify specific problem cases

---

## Deployment Checklist

- [ ] Push code to GitHub (3 new Python files + this integration guide)
- [ ] Create database migration
- [ ] Run migration in staging
- [ ] Update User model with new fields
- [ ] Cache semantic profiles (one-time batch job)
- [ ] Update frontend forms
- [ ] Create/update API endpoint
- [ ] Add feature flag configuration
- [ ] Add monitoring/metrics
- [ ] Write unit tests
- [ ] Conduct integration testing
- [ ] Prepare rollout plan (5% → 25% → 50% → 100%)
- [ ] Train support team on new system
- [ ] Deploy to staging (1-2 weeks)
- [ ] Validate with real users
- [ ] Deploy to production with feature flag at 0%
- [ ] Gradual rollout over 1 week
- [ ] Monitor metrics and user feedback
- [ ] Full rollout when metrics confirm success

---

**Questions?** Refer to `HYBRID_SYSTEM_DESIGN_REPORT.md` for architectural details or `HYBRID_SYSTEM_EXECUTIVE_SUMMARY.md` for business justification.
