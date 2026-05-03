const fs = require('fs');

console.log('=== COMPREHENSIVE SCHEME CONDITIONS COMPARISON ===');
console.log('Analyzing all schemes and deduplicating questions...\n');

// Load both data files
const schemesData = JSON.parse(fs.readFileSync('C:/yojanamitra_complete/all_schemes_export.json', 'utf8'));
const conditionsData = JSON.parse(fs.readFileSync('C:/yojanamitra_complete/scheme_conditions.json', 'utf8'));

// Map conditions by scheme ID
const conditionsById = {};
for (const [key, val] of Object.entries(conditionsData)) {
  conditionsById[parseInt(key)] = val;
}

console.log(`Total schemes in export: ${schemesData.length}`);
console.log(`Total condition entries: ${Object.keys(conditionsById).length}\n`);

// Comprehensive keyword patterns for conditions
const CONDITION_PATTERNS = {
  // Age
  age: /\b(age|years?|yrs?)\b/i,
  minor: /\b(minor|below\s+18|under\s+18|guardian|parent)\b/i,
  senior: /\b(senior\s+citizen|elderly|60\s*\+|65\s*\+)\b/i,
  
  // Identity
  citizen: /\b(citizen\s+of\s+india|indian\s+citizen|national)\b/i,
  nri: /\b(nri|non-resident|non\s+resident|foreigner)\b/i,
  gender: /\b(male|female|woman|men|transgender)\b/i,
  caste: /\b(sc|st|obc|general|scheduled\s+(caste|tribe)|backward|reserved)\b/i,
  
  // Location
  state: /\b(state|domicile|resident\s+of)\b/i,
  residence: /\b(rural|urban|village|city|town)\b/i,
  
  // Religion
  religion: /\b(hindu|muslim|sikh|christian|jain|parsi|faith)\b/i,
  
  // Education
  education: /\b(education|qualification|degree|diploma|passed|graduate|literate|illiterate)\b/i,
  
  // Income
  income: /\b(income|salary|earnings)\b/i,
  bpl: /\b(bpl|below\s+poverty|poor|weaker)\b/i,
  
  // Occupation
  student: /\b(student|studying|enrolled|pursuing|college|school)\b/i,
  farmer: /\b(farmer|agriculturist|cultivator|farming|agriculture)\b/i,
  employed: /\b(employee|employed|unemployed|job|work)\b/i,
  self_employed: /\b(self[-\s]employed|business|enterprise|entrepreneur)\b/i,
  government_employee: /\b(government\s+employee|govt\s+employee|public\s+servant)\b/i,
  
  // Status
  disabled: /\b(disabled|divyang|differently\s+abled|handicapped)\b/i,
  widow: /\b(widow|widowed)\b/i,
  orphan: /\b(orphan|abandoned\s+child)\b/i,
  minority: /\b(minority)\b/i,
  tribal: /\b(tribal|tribe)\b/i,
  
  // Special categories
  pensioner: /\b(pensioner|pension)\b/i,
  veteran: /\b(veteran|ex[-\s]serviceman|ex\s+army)\b/i,
  migrant: /\b(migrant)\b/i,
  bpl_card: /\b(bpl\s+card)\b/i,
  defaulter: /\b(default|defaulter|loan\s+default|cibil)\b/i,
  bank_account: /\b(bank\s+account|savings\s+account)\b/i,
  epf: /\b(epf|provident\s+fund)\b/i,
  land: /\b(land|acre|agricultural)\b/i,
  aadhaar: /\b(aadhaar|aadhar)\b/i,
  pan: /\b(pan\s+card)\b/i,
  tax: /\b(tax\s+payer|income\s+tax)\b/i,
  insurance: /\b(insurance|insured)\b/i,
  artisan: /\b(artisan|craft|handloom|handicraft)\b/i
};

// Question templates (core questions that derive multiple conditions)
const CORE_QUESTIONS = {
  'What is your date of birth?': {
    field: 'dob',
    type: 'date',
    derives: ['age', 'age_category', 'is_minor', 'is_senior_citizen'],
    applicable_to: ['age', 'minor', 'senior']
  },
  'What is your gender?': {
    field: 'gender',
    type: 'select',
    options: ['Male', 'Female', 'Transgender', 'Other'],
    derives: [],
    applicable_to: ['gender']
  },
  'What is your caste category?': {
    field: 'caste_category',
    type: 'select',
    options: ['SC', 'ST', 'OBC', 'General', 'Other'],
    derives: [],
    applicable_to: ['caste']
  },
  'Which state do you reside in?': {
    field: 'state',
    type: 'select',
    options: ['Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Delhi', 'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'All India'],
    derives: [],
    applicable_to: ['state']
  },
  'What is your residence type?': {
    field: 'residence',
    type: 'select',
    options: ['Rural', 'Urban', 'Semi-Urban'],
    derives: [],
    applicable_to: ['residence']
  },
  'What is your religion?': {
    field: 'religion',
    type: 'select',
    options: ['Hindu', 'Muslim', 'Sikh', 'Christian', 'Jain', 'Parsi', 'Buddhist', 'Other'],
    derives: [],
    applicable_to: ['religion']
  },
  'What is your highest education qualification?': {
    field: 'education_level',
    type: 'select',
    options: ['Below 5th', '5th Pass', '8th Pass', '10th Pass', '12th Pass', 'Graduate', 'Post Graduate', 'None/Illiterate'],
    derives: [],
    applicable_to: ['education']
  },
  'What is your annual family income?': {
    field: 'annual_income',
    type: 'select',
    options: ['Below ₹1 Lakh', '₹1-2.5 Lakh', '₹2.5-5 Lakh', '₹5-10 Lakh', 'Above ₹10 Lakh', 'No Income Limit'],
    derives: [],
    applicable_to: ['income', 'bpl']
  },
  'Are you currently a student?': {
    field: 'is_student',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: [],
    applicable_to: ['student']
  },
  'Are you a farmer/agriculturist?': {
    field: 'is_farmer',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: [],
    applicable_to: ['farmer']
  },
  'Are you currently employed?': {
    field: 'employment_status',
    type: 'select',
    options: ['Employed (Government)', 'Employed (Private)', 'Self-Employed', 'Unemployed', 'Student', 'Homemaker'],
    derives: ['is_employed', 'is_self_employed'],
    applicable_to: ['employed', 'self_employed', 'government_employee']
  },
  'Are you an Indian citizen?': {
    field: 'is_indian_citizen',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: ['is_citizen', 'is_nri'],
    applicable_to: ['citizen', 'nri']
  },
  'Do you have a bank account?': {
    field: 'has_bank_account',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: [],
    applicable_to: ['bank_account']
  },
  'Are you differently abled?': {
    field: 'is_disabled',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: [],
    applicable_to: ['disabled']
  },
  'Are you a widow?': {
    field: 'is_widow',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: [],
    applicable_to: ['widow']
  },
  'Do you belong to a minority community?': {
    field: 'is_minority',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: [],
    applicable_to: ['minority']
  },
  'Are you a member of scheduled tribe?': {
    field: 'is_tribal',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: [],
    applicable_to: ['tribal']
  },
  'Are you currently receiving a pension?': {
    field: 'is_pensioner',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: [],
    applicable_to: ['pensioner']
  },
  'Have you ever defaulted on any loan?': {
    field: 'is_defaulter',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: [],
    applicable_to: ['defaulter']
  },
  'Are you a member of EPF?': {
    field: 'is_epf_member',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: [],
    applicable_to: ['epf']
  },
  'How much agricultural land do you own?': {
    field: 'land_owned',
    type: 'select',
    options: ['Landless', 'Less than 1 acre', '1-2.5 acres', '2.5-5 acres', '5-10 acres', 'Above 10 acres'],
    derives: ['is_landless'],
    applicable_to: ['land']
  },
  'Do you have an Aadhaar card?': {
    field: 'has_aadhaar',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: [],
    applicable_to: ['aadhaar']
  },
  'Do you have a PAN card?': {
    field: 'has_pan',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: [],
    applicable_to: ['pan']
  },
  'Are you an income tax payer?': {
    field: 'is_income_taxpayer',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: [],
    applicable_to: ['tax']
  },
  'Are you an ex-serviceman?': {
    field: 'is_ex_serviceman',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: [],
    applicable_to: ['veteran']
  },
  'Are you an artisan/craftsperson?': {
    field: 'is_artisan',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: [],
    applicable_to: ['artisan']
  },
  'Are you a migrant worker?': {
    field: 'is_migrant_worker',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: [],
    applicable_to: ['migrant']
  },
  'Do you have a BPL card?': {
    field: 'has_bpl_card',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: ['is_bpl'],
    applicable_to: ['bpl', 'bpl_card']
  },
  'Are you a first generation learner?': {
    field: 'is_first_gen_student',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: [],
    applicable_to: ['first_gen']
  },
  'Have you dropped out of school?': {
    field: 'is_school_dropout',
    type: 'radio',
    options: ['Yes', 'No'],
    derives: [],
    applicable_to: ['dropout']
  }
};

function findConditionsInText(text) {
  const found = new Set();
  const lowerText = text.toLowerCase();
  
  for (const [condition, pattern] of Object.entries(CONDITION_PATTERNS)) {
    if (pattern.test(lowerText)) {
      found.add(condition);
    }
  }
  return Array.from(found);
}

function getMissingConditions(schemeId, textConditions, extracted) {
  const missing = [];
  
  for (const condition of textConditions) {
    // Check if already extracted in conditions file
    const alreadyExtracted = extracted && Object.values(extracted).some(v => v !== null);
    
    if (!alreadyExtracted) {
      missing.push(condition);
    }
  }
  return missing;
}

function mapToCoreQuestion(condition) {
  // Map condition to core question
  for (const [question, info] of Object.entries(CORE_QUESTIONS)) {
    if (info.applicable_to.includes(condition)) {
      return { question, ...info };
    }
  }
  return null;
}

// Process all schemes
const allResults = {};
const questionDedupe = new Map();
const fieldCount = {};
let totalMissing = 0;
let processed = 0;

console.log('Processing each scheme...\n');

for (const scheme of schemesData) {
  const schemeId = scheme.id;
  
  // Combine all text
  const fullText = [
    scheme.eligibility || '',
    scheme.benefits || '',
    scheme.application_process || '',
    scheme.exclusions || '',
    scheme.description || ''
  ].join(' ');
  
  // Find conditions in text
  const textConditions = findConditionsInText(fullText);
  
  // Get extracted conditions
  const extracted = conditionsById[schemeId]?.conditions || {};
  
  // Find missing conditions
  const missing = textConditions.filter(cond => {
    // If nothing extracted, or no matching extracted field
    return true; // For now, add all since we want comprehensive
  });
  
  // Map missing conditions to questions
  const questionsToAsk = [];
  const seenQuestions = new Set();
  
  for (const cond of missing) {
    const mapped = mapToCoreQuestion(cond);
    if (mapped && !seenQuestions.has(mapped.question)) {
      questionsToAsk.push({
        question: mapped.question,
        field: mapped.field,
        type: mapped.type,
        options: mapped.options || [],
        derived_conditions: mapped.derives || []
      });
      seenQuestions.add(mapped.question);
      
      // Track for deduplication
      if (!questionDedupe.has(mapped.question)) {
        questionDedupe.set(mapped.question, {
          question: mapped.question,
          field: mapped.field,
          type: mapped.type,
          options: mapped.options || [],
          derived_conditions: mapped.derives || [],
          scheme_ids: []
        });
      }
      questionDedupe.get(mapped.question).scheme_ids.push(schemeId);
    }
    fieldCount[cond] = (fieldCount[cond] || 0) + 1;
  }
  
  // Store result
  allResults[schemeId] = {
    scheme_id: schemeId,
    scheme_name: scheme.name,
    category: scheme.category,
    eligibility_text: scheme.eligibility,
    benefits_text: scheme.benefits,
    application_process_text: scheme.application_process,
    exclusions_text: scheme.exclusions,
    extracted_conditions: Object.keys(extracted).length > 0 ? extracted : null,
    conditions_found_in_text: textConditions,
    missing_conditions: missing,
    questions_to_ask: questionsToAsk
  };
  
  totalMissing += missing.length;
  processed++;
  
  if (processed % 500 === 0) {
    console.log(`Processed ${processed}/${schemesData.length} schemes...`);
  }
}

// Create final output
const uniqueQuestions = Array.from(questionDedupe.values()).map(q => ({
  ...q,
  scheme_count: q.scheme_ids.length
})).sort((a, b) => b.scheme_count - a.scheme_count);

const output = {
  metadata: {
    total_schemes_analyzed: processed,
    total_schemes_with_extracted_conditions: Object.keys(conditionsById).length,
    total_conditions_found_in_text: totalMissing,
    total_unique_questions: uniqueQuestions.length,
    processed_at: new Date().toISOString()
  },
  unique_questions_deduplicated: uniqueQuestions,
  scheme_results: allResults
};

// Save
const outPath = 'C:/yojanamitra_complete/final_missing_conditions_analysis.json';
fs.writeFileSync(outPath, JSON.stringify(output, null, 2));
console.log(`\nSaved to: ${outPath}`);

// Summary
console.log('\n=== FINAL SUMMARY ===');
console.log(`Total schemes analyzed: ${processed}`);
console.log(`Total unique questions (deduplicated): ${uniqueQuestions.length}`);
console.log(`Total condition mentions in text: ${totalMissing}`);

console.log('\n=== TOP 20 CONDITIONS IN TEXT ===');
const sorted = Object.entries(fieldCount).sort((a, b) => b[1] - a[1]);
for (const [cond, count] of sorted.slice(0, 20)) {
  console.log(`${cond}: ${count}`);
}

console.log('\n=== UNIQUE QUESTIONS WITH SCHEME COUNTS ===');
for (const q of uniqueQuestions.slice(0, 30)) {
  console.log(`${q.question}: ${q.scheme_count} schemes`);
}