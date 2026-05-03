const fs = require('fs');

console.log('Loading scheme data files...');

// Load both files
const schemesData = JSON.parse(fs.readFileSync('C:/yojanamitra_complete/all_schemes_export.json', 'utf8'));
const conditionsData = JSON.parse(fs.readFileSync('C:/yojanamitra_complete/scheme_conditions.json', 'utf8'));

console.log(`Loaded ${schemesData.length} schemes`);
console.log(`Loaded ${Object.keys(conditionsData).length} condition entries`);

// Define all possible condition fields that could be extracted
const ALL_CONDITION_FIELDS = [
  'age_min', 'age_max', 'annual_family_income_max', 'income_annual_max',
  'gender', 'caste_category', 'state', 'residence',
  'education_level_min', 'education_level_max', 'disability_percentage_min',
  'land_owned_max_acres', 'land_owned_min_acres', 'religion',
  'is_student', 'is_disabled', 'is_farmer', 'is_bpl', 'is_bocw_registered',
  'is_tribal', 'is_widow', 'is_senior_citizen', 'is_minority', 'is_orphan',
  'is_self_employed', 'is_landless', 'is_migrant_worker', 'is_school_dropout',
  'is_acid_attack_survivor', 'is_first_gen_student', 'is_single_woman',
  'is_abandoned_woman', 'is_pensioner', 'is_woman_entrepreneur',
  'has_pucca_house_disqualifies', 'is_govt_employee_disqualifies',
  'is_income_taxpayer_disqualifies', 'is_citizen', 'is_nri', 'is_indian_citizen'
];

// Keywords to search in text for each condition
const CONDITION_KEYWORDS = {
  'age_min': ['minimum age', 'age between', 'aged', 'years and above', 'years of age', 'below', 'above'],
  'age_max': ['maximum age', 'age limit', 'years and below', 'up to', 'not exceeding', 'attained age'],
  'gender': ['male', 'female', 'woman', 'man', 'transgender', 'gender'],
  'caste_category': ['sc', 'st', 'obc', 'general', 'reserved category', '-backward', 'scheduled caste', 'scheduled tribe', 'other backward'],
  'state': ['state', 'resident of', 'domicile', 'located in'],
  'residence': ['rural', 'urban', 'semi-urban', 'metropolitan'],
  'religion': ['hindu', 'muslim', 'sikh', 'christian', 'jain', 'parsi', 'religion', 'faith'],
  'education_level_min': ['education', 'qualification', 'passed', 'completed', 'degree', 'diploma', 'matriculation', 'literate'],
  'is_bpl': ['bpl', 'below poverty line', 'poor family', 'economically weaker'],
  'is_student': ['student', 'studying', 'enrolled', 'pursuing'],
  'is_farmer': ['farmer', 'agriculturist', 'cultivator', 'farming'],
  'is_disabled': ['disabled', 'handicap', 'divyang', 'differently abled', 'physically challenged'],
  'is_senior_citizen': ['senior citizen', 'elderly', 'aged person', 'old age'],
  'is_widow': ['widow', 'widowed'],
  'is_orphan': ['orphan', 'abandoned child'],
  'is_minority': ['minority', 'minority community'],
  'is_tribal': ['tribal', 'tribe', 'scheduled tribe'],
  'is_minor': ['minor', 'below 18', 'under 18', 'guardian'],
  'is_citizen': ['citizen of india', 'indian citizen', 'citizen', 'nationality'],
  'is_nri': ['nri', 'non-resident', 'non resident', 'foreigner', 'foreign national'],
  'is_woman_entrepreneur': ['woman entrepreneur', 'women entrepreneur', 'female entrepreneur'],
  'is_single_woman': ['single woman', 'unmarried woman'],
  'is_abandoned_woman': ['abandoned woman', 'deserted woman'],
  'is_landless': ['landless', 'no land', 'without agricultural land'],
  'is_self_employed': ['self-employed', 'self employed', 'business', 'enterprise'],
  'is_defaulter': ['defaulter', 'defaulted', ' loan default', 'poor credit', 'cibil'],
  'is_govt_employee': ['government employee', 'govt employee', 'public servant'],
  'is_pensioner': ['pensioner', 'pension holder', 'receiving pension'],
  'has_bank_account': ['bank account', 'savings account', 'banking'],
  'is_epf_member': ['epf', 'provident fund', 'employees provident fund'],
  'income_annual_max': ['income limit', 'annual income', 'income threshold', 'maximum income'],
  'land_owned': ['land holding', 'acre', 'agricultural land'],
  'disability_percentage': ['percentage of disability', 'disability percentage'],
  'is_insured': ['insurance', 'insured', 'cover'],
  'is_employed': ['employed', 'unemployed', 'employment'],
  'is_migrant_worker': ['migrant worker', 'migrant labour'],
  'is_first_gen_student': ['first generation', 'first learner', 'first graduate']
};

// Question templates for each condition
const QUESTION_TEMPLATES = {
  'age_min': { question: 'What is your age?', type: 'numeric', derives: ['is_minor', 'is_senior_citizen'] },
  'age_max': { question: 'What is your age?', type: 'numeric', derives: ['is_minor', 'is_senior_citizen'] },
  'gender': { question: 'What is your gender?', type: 'select', options: ['Male', 'Female', 'Transgender', 'Other'] },
  'caste_category': { question: 'What is your caste category?', type: 'select', options: ['SC', 'ST', 'OBC', 'General', 'Other'] },
  'state': { question: 'Which state do you reside in?', type: 'text' },
  'residence': { question: 'What is your residence type?', type: 'select', options: ['Rural', 'Urban', 'Semi-Urban'] },
  'religion': { question: 'What is your religion?', type: 'select', options: ['Hindu', 'Muslim', 'Sikh', 'Christian', 'Jain', 'Parsi', 'Other'] },
  'education_level_min': { question: 'What is your highest education qualification?', type: 'select', options: ['Below 10th', '10th Pass', '12th Pass', 'Graduate', 'Post Graduate', 'None'] },
  'is_bpl': { question: 'Do you have a BPL card?', type: 'radio', options: ['Yes', 'No'] },
  'is_student': { question: 'Are you currently a student?', type: 'radio', options: ['Yes', 'No'] },
  'is_farmer': { question: 'Are you a farmer?', type: 'radio', options: ['Yes', 'No'] },
  'is_disabled': { question: 'Are you differently abled?', type: 'radio', options: ['Yes', 'No'] },
  'is_senior_citizen': { question: 'Are you a senior citizen (60+ years)?', type: 'radio', options: ['Yes', 'No'] },
  'is_widow': { question: 'Are you a widow?', type: 'radio', options: ['Yes', 'No'] },
  'is_orphan': { question: 'Are you an orphan?', type: 'radio', options: ['Yes', 'No'] },
  'is_minority': { question: 'Do you belong to a minority community?', type: 'radio', options: ['Yes', 'No'] },
  'is_tribal': { question: 'Are you a member of a scheduled tribe?', type: 'radio', options: ['Yes', 'No'] },
  'is_minor': { question: 'Are you below 18 years of age?', type: 'radio', options: ['Yes', 'No'] },
  'is_citizen': { question: 'Are you an Indian citizen?', type: 'radio', options: ['Yes', 'No'] },
  'is_nri': { question: 'Are you a Non-Resident Indian (NRI)?', type: 'radio', options: ['Yes', 'No'] },
  'is_woman_entrepreneur': { question: 'Are you a woman entrepreneur?', type: 'radio', options: ['Yes', 'No'] },
  'is_single_woman': { question: 'Are you a single/unmarried woman?', type: 'radio', options: ['Yes', 'No'] },
  'is_abandoned_woman': { question: 'Have you been abandoned?', type: 'radio', options: ['Yes', 'No'] },
  'is_landless': { question: 'Do you own agricultural land?', type: 'radio', options: ['Yes (Own Land)', 'No (Landless)'] },
  'is_self_employed': { question: 'Are you self-employed?', type: 'radio', options: ['Yes', 'No'] },
  'is_defaulter': { question: 'Have you ever defaulted on any loan?', type: 'radio', options: ['Yes', 'No'] },
  'is_govt_employee': { question: 'Are you a government employee?', type: 'radio', options: ['Yes', 'No'] },
  'is_pensioner': { question: 'Are you currently receiving a pension?', type: 'radio', options: ['Yes', 'No'] },
  'has_bank_account': { question: 'Do you have a bank account?', type: 'radio', options: ['Yes', 'No'] },
  'is_epf_member': { question: 'Are you a member of EPF?', type: 'radio', options: ['Yes', 'No'] },
  'income_annual_max': { question: 'What is your annual family income?', type: 'numeric' },
  'annual_family_income_max': { question: 'What is your annual family income?', type: 'numeric' },
  'is_migrant_worker': { question: 'Are you a migrant worker?', type: 'radio', options: ['Yes', 'No'] },
  'is_first_gen_student': { question: 'Are you a first generation learner?', type: 'radio', options: ['Yes', 'No'] },
  'is_school_dropout': { question: 'Have you dropped out of school?', type: 'radio', options: ['Yes', 'No'] },
  'land_owned': { question: 'How much agricultural land do you own?', type: 'select', options: ['Landless', 'Less than 1 acre', '1-5 acres', '5-10 acres', 'More than 10 acres'] },
  'disability_percentage': { question: 'What is your disability percentage?', type: 'numeric' },
  'is_acid_attack_survivor': { question: 'Are you an acid attack survivor?', type: 'radio', options: ['Yes', 'No'] }
};

function extractTextFields(scheme) {
  // Combine all text fields
  const allText = [
    scheme.eligibility || '',
    scheme.benefits || '',
    scheme.application_process || '',
    scheme.exclusions || '',
    scheme.description || ''
  ].join(' ').toLowerCase();
  return allText;
}

function findMissingConditions(schemeText, extractedConditions) {
  const missing = [];
  
  for (const [field, keywords] of Object.entries(CONDITION_KEYWORDS)) {
    // Check if condition was extracted
    const wasExtracted = extractedConditions && 
      extractedConditions[field] !== null && 
      extractedConditions[field] !== undefined;
    
    if (!wasExtracted) {
      // Check if condition is mentioned in text
      const found = keywords.some(kw => schemeText.includes(kw));
      if (found) {
        missing.push({
          field: field,
          source: 'text_analysis',
          confidence: 0.7
        });
      }
    }
  }
  
  return missing;
}

// Process all schemes
const results = {};
const allQuestionsMap = new Map();
let schemesProcessed = 0;

for (const scheme of schemesData) {
  const schemeId = String(scheme.id);
  const extractedConditions = conditionsData[schemeId]?.conditions || {};
  
  // Get full text
  const fullText = extractTextFields(scheme);
  
  // Find missing conditions
  const missingConditions = findMissingConditions(fullText, extractedConditions);
  
  // Generate questions for missing conditions
  const questionsToAsk = [];
  for (const missing of missingConditions) {
    const template = QUESTION_TEMPLATES[missing.field];
    if (template) {
      questionsToAsk.push({
        field: missing.field,
        question: template.question,
        type: template.type,
        options: template.options || [],
        derives: template.derives || []
      });
    } else {
      questionsToAsk.push({
        field: missing.field,
        question: `What is your ${missing.field}?`,
        type: 'text'
      });
    }
  }
  
  // Store in results
  results[schemeId] = {
    scheme_id: scheme.id,
    scheme_name: scheme.name,
    category: scheme.category,
    full_eligibility: scheme.eligibility,
    full_benefits: scheme.benefits,
    full_application_process: scheme.application_process,
    full_exclusions: scheme.exclusions,
    extracted_conditions: extractedConditions,
    missing_conditions: missingConditions,
    questions_to_ask: questionsToAsk
  };
  
  // Add to global questions map (for deduplication later)
  for (const q of questionsToAsk) {
    const key = q.question.toLowerCase();
    if (!allQuestionsMap.has(key)) {
      allQuestionsMap.set(key, {
        question: q.question,
        type: q.type,
        options: q.options,
        field: q.field,
        derives: q.derives,
        schemes: []
      });
    }
    allQuestionsMap.get(key).schemes.push(scheme.id);
  }
  
  schemesProcessed++;
  if (schemesProcessed % 500 === 0) {
    console.log(`Processed ${schemesProcessed} schemes...`);
  }
}

console.log(`\nTotal schemes processed: ${schemesProcessed}`);
console.log(`Total unique questions found: ${allQuestionsMap.size}`);

// Create final output
const finalOutput = {
  summary: {
    total_schemes: schemesProcessed,
    total_unique_questions: allQuestionsMap.size,
    processing_time: new Date().toISOString()
  },
  unique_questions: Array.from(allQuestionsMap.values()),
  schemes: results
};

// Save results
const outputPath = 'C:/yojanamitra_complete/missing_conditions_comparison_full.json';
fs.writeFileSync(outputPath, JSON.stringify(finalOutput, null, 2));
console.log(`\nSaved to: ${outputPath}`);

console.log('\n=== TOP MISSING CONDITIONS ===');
const fieldCounts = {};
for (const [key, q] of allQuestionsMap) {
  fieldCounts[q.field] = (fieldCounts[q.field] || 0) + 1;
}
const sortedFields = Object.entries(fieldCounts).sort((a, b) => b[1] - a[1]);
for (const [field, count] of sortedFields.slice(0, 20)) {
  console.log(`${field}: ${count} schemes`);
}