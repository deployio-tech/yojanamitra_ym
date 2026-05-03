# QUESTIONS FORM INTEGRATION GUIDE
## For YojanaMitra Dashboard

### 📋 Overview
The `questions_form_component.html` contains a complete questions form system that integrates into the "Possibly Eligible" tab of the dashboard.

**What it does:**
- ✅ Fetches unanswered questions from `/api/recommendations`
- ✅ Displays them with proper answer options (radio, checkbox, number, text)
- ✅ Tracks progress (X of Y questions answered)
- ✅ Submits answers to `/api/user/answer` endpoint
- ✅ Auto-refreshes scheme recommendations after answers
- ✅ Shows which questions affect how many schemes

---

## 🔧 INTEGRATION STEPS

### Step 1: Add Questions Form HTML to Dashboard
In `static/dashboard.html`, find the "Possibly Eligible Tab" section (around line 2940), and add this BEFORE the schemes grid:

```html
<!-- Import Questions Form Component -->
<div id="questions-form-placeholder" style="margin-bottom:24px;"></div>
<script src="/static/questions_form_component.js"></script>
```

### Step 2: Create JavaScript Module
Create `static/js/questions-form.js` with the questions form logic (extracted from the HTML component).

### Step 3: Update Backend - /api/recommendations Endpoint
The endpoint MUST return `missing_questions` field in response.

**Current structure expected:**
```json
{
  "recommendations": [...schemes...],
  "possibly_eligible": [...schemes...],
  "missing_questions": [
    {
      "question_id": "q_category",
      "field": "category",
      "concept": "category",
      "text": "What is your category/caste?",
      "field_type": "select",
      "options": ["SC", "ST", "OBC", "General"],
      "schemes_affected": [1, 2, 3, ...],
      "impact_score": 3.5
    },
    ...
  ]
}
```

### Step 4: Verify Backend Endpoints
These endpoints must be working:
- ✅ `/api/user` - GET current user & their question answers
- ✅ `/api/recommendations` - GET schemes & missing questions
- ✅ `/api/user/answer` - POST to submit question answers
- ✅ `/api/profile` - POST to save profile updates

---

## 📊 Current Status

### ✅ What's Working
- Endpoint `/api/recommendations` exists in app.py
- Endpoint `/api/user` exists and returns user profile
- Endpoint `/api/user/answer` exists to submit answers
- "Possibly Eligible" tab exists in dashboard.html
- Backend questions engine works (can fetch & sort up to 40 questions)

### ❌ What's Missing
1. **`/api/recommendations` missing `missing_questions` field**
   - Currently returns only schemes
   - Need to include missing questions in response
   
2. **No questions form HTML in dashboard**
   - "Possibly Eligible" tab shows only schemes
   - No form for users to answer questions
   
3. **No form rendering JavaScript**
   - Dashboard doesn't call `/api/user/answer`
   - Questions don't auto-refresh schemes

---

## 🔄 RECOMMENDED FIX ORDER

### 1️⃣ Fix Backend `/api/recommendations` (HIGH PRIORITY)
**File:** `app.py` - Find the `/api/recommendations` route

**What to change:**
```python
@app.route('/api/recommendations')
def get_recommendations():
    # ... existing code ...
    
    # ADD THIS SECTION:
    # Get missing questions
    missing_questions = []
    try:
        engine = EligibilityEngine()
        qengine = QuestionEngine()
        
        # Get possible schemes
        possible_schemes = [
            (scheme, engine.evaluate(scheme, user_profile))
            for scheme in suggested_schemes
            if engine.evaluate(scheme, user_profile).result.lower() == 'possible'
        ]
        
        # Get questions
        questions = qengine.select_questions(possible_schemes, user_profile)
        missing_questions = [q.to_dict() for q in questions]
    except Exception as e:
        print(f"Error getting questions: {e}")
    
    # Return WITH missing_questions
    return jsonify({
        'recommendations': ...,
        'possibly_eligible': ...,
        'missing_questions': missing_questions,  # ADD THIS
        'user_answers': user.question_answers or {}  # ADD THIS
    })
```

### 2️⃣ Add Questions Form to Dashboard (MEDIUM PRIORITY)
**File:** `static/dashboard.html`

**What to add:**
- Include the questions form before the schemes grid in "Possibly Eligible" tab
- Add JavaScript to render questions
- Connect answer submission to backend

### 3️⃣ Test Integration
1. Go to dashboard
2. Click "Possibly Eligible" tab
3. Should see question form at the top
4. Answer a question
5. Click "Update Results"
6. Schemes should refresh based on new information

---

## 🧪 TESTING CHECKLIST

- [ ] `/api/recommendations` returns `missing_questions` field
- [ ] Questions form appears in "Possibly Eligible" tab
- [ ] Can select answer options (radio, checkbox, etc.)
- [ ] Progress bar updates when answering
- [ ] "Update Results" button works
- [ ] New answers go to `/api/user/answer`
- [ ] Schemes update after answering
- [ ] "Skip for Now" button hides form
- [ ] No profile fields are asked as questions ✅ (FIXED)
- [ ] Max 40 questions shown ✅ (FIXED)

---

## 📝 MODIFICATION CHECKLIST

- [ ] Copy `questions_form_component.html` content to dashboard
- [ ] Create `static/js/questions-form.js` module
- [ ] Update `/api/recommendations` endpoint to include `missing_questions`
- [ ] Test all endpoints work correctly
- [ ] Test frontend form displays properly
- [ ] Test question answers are submitted correctly
- [ ] Test schemes update after answering

---

## 🔗 Related Files
- Backend engine: `app/engine/questions.py` ✅ (Fixed)
- Dashboard: `static/dashboard.html` (Needs integration)
- Questions form: `questions_form_component.html` (New)
- API routes: `app.py` (Needs modification)

---

## ⚠️ IMPORTANT NOTES

1. **No Duplication**: Questions NEVER ask for 67 profile fields ✅ (Already excluded)
2. **Max 40 Questions**: Questions capped at 40 for scalability ✅ (Already set)
3. **Auto-refresh**: Recommendations should refresh when user answers
4. **Progress Tracking**: Show X of Y questions answered
5. **Skip Option**: Let users skip if they don't want to answer

---

## 📞 SUPPORT

If you have issues:
1. Check browser console for JavaScript errors
2. Verify `/api/recommendations` returns `missing_questions`
3. Ensure `/api/user/answer` endpoint is working
4. Check that question form HTML is properly included
5. Verify all endpoints are returning correct JSON structure
