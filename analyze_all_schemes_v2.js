const fs = require('fs');

console.log('=== SCHEME CONDITIONS COMPARISON ANALYZER ===');
console.log('Loading data...');

// Load both files
const schemesData = JSON.parse(fs.readFileSync('C:/yojanamitra_complete/all_schemes_export.json', 'utf8'));
const conditionsData = JSON.parse(fs.readFileSync('C:/yojanamitra_complete/scheme_conditions.json', 'utf8'));

console.log(`Schemes: ${schemesData.length}`);
console.log(`Condition entries: ${Object.keys(conditionsData).length}`);

// Map conditions by ID
const conditionsById = {};
for (const [key, val] of Object.entries(conditionsData)) {
  const id = parseInt(key);
  conditionsById[id] = val;
}

// Keywords that indicate conditions in text
const TEXT_KEYWORDS = {
  // Age related
  'age_min': /\b(minimum age|minimum\s+(?:is\s+)?(\d+)\s+(?:years?|yrs?)|aged?\s+(\d+)\s+(?:years?|yrs?)\s+(?:and\s+|above)|at\s+least\s+(\d+)\s+(?:years?|yrs?)|above\s+(\d+)\s+(?:years?|yrs?)\b/i,
  'age_max': /\b(maximum age|max\s+age|up\s+to\s+(\d+)\s+(?:years?|yrs?)|below\s+(\d+)\s+(?:years?|yrs?)|not\s+(?:exceeding|more\s+than)\s+(\d+)|(\d+)\s+(?:years?|yrs?)\s+(?:and\s+|or\s+)?below|attained\s+(\d+)\s+years)\b/i,
  
  // Gender
  'gender': /\b(male|female|woman|men|woman|transgender|gender)\b/i,
  
  // Caste
  'caste_category': /\b(sc|st|obc|general|scheduled\s+caste|scheduled\s+tribe|other\s+backward|reserved\s+category|backward\s+class)\b/i,
  
  // Residence
  'residence': /\b(rural|urban|semi-urban|metropolitan|city|town|village)\b/i,
  
  // Religion
  'religion': /\b(hindu|muslim|sikh|christian|jain|parsi|religion|faith)\b/i,
  
  // Education
  'education_level_min': /\b(education|qualification|passed|completed|degree|diploma|matriculation|literate|class\s+10|class\s+12|graduate|post\s+graduate|illiterate)\b/i,
  
  // Income
  'income_max': /\b(income\s+limit|annual\s+income|income\s+threshold|maximum\s+income|bpl|below\s+poverty|weaker\s+section|economically\s+weaker)\b/i,
  
  // Occupation/Status
  'is_student': /\b(student|studying|enrolled|pursuing|course|college|school|university)\b/i,
  'is_farmer': /\b(farmer|agriculturist|cultivator|farming|agriculture)\b/i,
  'is_disabled': /\b(disabled|handicapped|divyang|differently\s+abled|physically\s+challenged|special\s+ability)\b/i,
  'is_senior_citizen': /\b(senior\s+citizen|elderly|old\s+age|aged\s+(?:person|people))\b/i,
  'is_widow': /\b(widow|widowed)\b/i,
  'is_minority': /\b(minority|minority\s+community)\b/i,
  'is_tribal': /\b(tribal|tribe|scheduled\s+tribe)\b/i,
  'is_minor': /\b(minor|below\s+18|under\s+18|guardian|parent)\b/i,
  'is_citizen': /\b(citizen\s+of\s+india|indian\s+citizen|national)\b/i,
  'is_nri': /\b(nri|non-resident|non\s+resident|foreign\s+national|foreigner)\b/i,
  'is_bpl': /\b(bpl|below\s+poverty|poor|weaker)\b/i,
  'is_orphan': /\b(orphan|abandoned\s+child)\b/i,
  'is_self_employed': /\b(self-employed|self\s+employed|business|enterprise|entrepreneur)\b/i,
  'is_landless': /\b(landless|no\s+land|without\s+land)\b/i,
  'is_woman_entrepreneur': /\b(woman\s+entrepreneur|female\s+entrepreneur)\b/i,
  'is_single_woman': /\b(single\s+woman|unmarried\s+woman)\b/i,
  'is_abandoned_woman': /\b(abandoned\s+woman|deserted\s+woman)\b/i,
  'is_defaulter': /\b(defaulter|default|loan\s+default|poor\s+credit|cibil)\b/i,
  'is_govt_employee': /\b(government\s+employee|govt\s+employee|public\s+servant)\b/i,
  'is_pensioner': /\b(pensioner|pension\s+holder|receiving\s+pension)\b/i,
  'has_bank_account': /\b(bank\s+account|savings\s+account|banking)\b/i,
  'is_epf_member': /\b(epf|provident\s+fund|employees\s+provident)\b/i,
  'is_migrant_worker': /\b(migrant\s+worker|migrant\s+labour)\b/i,
  'is_first_gen_student': /\b(first\s+generation|first\s+learner|first\s+graduate)\b/i,
  'is_school_dropout': /\b(school\s+dropout|dropout)\b/i,
  'is_acid_attack_survivor': /\b(acid\s+attack|acid\s+survivor)\b/i,
  'land_owned': /\b(acre|agricultural\s+land|land\s+holding)\b/i,
  'disability_percentage': /\b(disability\s+percentage|percentage\s+disability)\b/i,
  'is_insured': /\b(insurance|insured|cover)\b/i,
  'state': /\b(state|resident\s+of|domicile)\b/i,
  
  // Exclusion keywords
  'excluded': /\b(excluded|not\s+eligible|disqualified|ineligible)\b/i,
  
  // Additional conditions
  'is_employed': /\b(employed|unemployed|employment)\b/i,
  'is_ex_serviceman': /\b(ex-serviceman|ex\s+serviceman|ex\s+army|ex\s+forces)\b/i,
  'is_artisan': /\b(artisan|artisan|craft|handloom|handicraft)\b/i,
  'is_veteran': /\b(veteran|war\s+injury)\b/i,
  'is_homemaker': /\b(homemaker|housewife|home\s+maker)\b/i,
  'is_child': /\b(child|children|infant)\b/i,
  'has_aadhaar': /\b(aadhaar|aadhar)\b/i,
  'has_pan': /\b(pan\s+card)\b/i,
  'income_taxpayer': /\b(income\s+tax|income-tax|tax\s+payer)\b/i
};

// Questions map
const QUESTIONS = {
  'age_min': { question: 'What is your date of birth?', type: 'date', derives: ['age', 'age_category', 'is_minor', 'is_senior_citizen'] },
  'age_max': { question: 'What is your date of birth?', type: 'date', derives: ['age', 'age_category', 'is_minor', 'is_senior_citizen'] },
  'gender': { question: 'What is your gender?', type: 'select', options: ['Male', 'Female', 'Transgender', 'Other'] },
  'caste_category': { question: 'What is your caste category?', type: 'select', options: ['SC', 'ST', 'OBC', 'General', 'Other'] },
  'state': { question: 'Which state do you reside in?', type: 'select', options: ['Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'Delhi', 'All States'] },
  'residence': { question: 'What is your residence type?', type: 'select', options: ['Rural', 'Urban', 'Semi-Urban'] },
  'religion': { question: 'What is your religion?', type: 'select', options: ['Hindu', 'Muslim', 'Sikh', 'Christian', 'Jain', 'Parsi', 'Buddhist', 'Other'] },
  'education_level_min': { question: 'What is your highest education qualification?', type: 'select', options: ['Below 5th', '5th Pass', '8th Pass', '10th Pass', '12th Pass', 'Graduate', 'Post Graduate', 'None/Illiterate'] },
  'income_max': { question: 'What is your annual family income?', type: 'select', options: ['Below ₹1 Lakh', '₹1-2.5 Lakh', '₹2.5-5 Lakh', '₹5-10 Lakh', 'Above ₹10 Lakh', 'No Income Limit'] },
  'is_bpl': { question: 'Do you have a BPL card?', type: 'radio', options: ['Yes', 'No'] },
  'is_student': { question: 'Are you currently a student?', type: 'radio', options: ['Yes', 'No'] },
  'is_farmer': { question: 'Are you a farmer/agriculturist?', type: 'radio', options: ['Yes', 'No'] },
  'is_disabled': { question: 'Are you differently abled?', type: 'radio', options: ['Yes', 'No'] },
  'is_senior_citizen': { question: 'Are you a senior citizen (60+ years)?', type: 'radio', options: ['Yes', 'No'] },
  'is_widow': { question: 'Are you a widow?', type: 'radio', options: ['Yes', 'No'] },
  'is_minority': { question: 'Do you belong to a minority community?', type: 'radio', options: ['Yes', 'No'] },
  'is_tribal': { question: 'Are you a member of a scheduled tribe?', type: 'radio', options: ['Yes', 'No'] },
  'is_minor': { question: 'Are you below 18 years of age?', type: 'radio', options: ['Yes', 'No'] },
  'is_citizen': { question: 'Are you an Indian citizen?', type: 'radio', options: ['Yes', 'No'] },
  'is_nri': { question: 'Are you a Non-Resident Indian (NRI)?', type: 'radio', options: ['Yes', 'No'] },
  'is_orphan': { question: 'Are you an orphan?', type: 'radio', options: ['Yes', 'No'] },
  'is_self_employed': { question: 'Are you self-employed?', type: 'radio', options: ['Yes', 'No'] },
  'is_landless': { question: 'Do you own agricultural land?', type: 'radio', options: ['Yes (Own Land)', 'No (Landless)'] },
  'is_woman_entrepreneur': { question: 'Are you a woman entrepreneur?', type: 'radio', options: ['Yes', 'No'] },
  'is_single_woman': { question: 'Are you a single/unmarried woman?', type: 'radio', options: ['Yes', 'No'] },
  'is_abandoned_woman': { question: 'Have you been abandoned?', type: 'radio', options: ['Yes', 'No'] },
  'is_defaulter': { question: 'Have you ever defaulted on any loan?', type: 'radio', options: ['Yes', 'No'] },
  'is_govt_employee': { question: 'Are you a government employee?', type: 'radio', options: ['Yes', 'No'] },
  'is_pensioner': { question: 'Are you currently receiving a pension?', type: 'radio', options: ['Yes', 'No'] },
  'has_bank_account': { question: 'Do you have a bank account?', type: 'radio', options: ['Yes', 'No'] },
  'is_epf_member': { question: 'Are you a member of EPF/Provident Fund?', type: 'radio', options: ['Yes', 'No'] },
  'is_migrant_worker': { question: 'Are you a migrant worker?', type: 'radio', options: ['Yes', 'No'] },
  'is_first_gen_student': { question: 'Are you a first generation learner?', type: 'radio', options: ['Yes', 'No'] },
  'is_school_dropout': { question: 'Have you dropped out of school?', type: 'radio', options: ['Yes', 'No'] },
  'is_acid_attack_survivor': { question: 'Are you an acid attack survivor?', type: 'radio', options: ['Yes', 'No'] },
  'land_owned': { question: 'How much agricultural land do you own?', type: 'select', options: ['Landless', 'Less than 1 acre', '1-2.5 acres', '2.5-5 acres', '5-10 acres', 'Above 10 acres'] },
  'disability_percentage': { question: 'What is your disability percentage?', type: 'numeric' },
  'is_insured': { question: 'Do you have any existing insurance?', type: 'radio', options: ['Yes', 'No'] },
  'is_employed': { question: 'Are you currently employed?', type: 'radio', options: ['Yes (Employed)', 'No (Unemployed)', 'Self-Employed'] },
  'is_ex_serviceman': { question: 'Are you an ex-serviceman?', type: 'radio', options: ['Yes', 'No'] },
  'is_artisan': { question: 'Are you an artisan/craftsperson?', type: 'radio', options: ['Yes', 'No'] },
  'is_veteran': { question: 'Are you a war veteran?', type: 'radio', options: ['Yes', 'No'] },
  'is_homemaker': { question: 'Are you a homemaker?', type: 'radio', options: ['Yes', 'No'] },
  'is_child': { question: 'Are you a child?', type: 'radio', options: ['Yes', 'No'] },
  'has_aadhaar': { question: 'Do you have an Aadhaar card?', type: 'radio', options: ['Yes', 'No'] },
  'has_pan': { question: 'Do you have a PAN card?', type: 'radio', options: ['Yes', 'No'] },
  'income_taxpayer': { question: 'Are you an income tax payer?', type: 'radio', options: ['Yes', 'No'] }
};

function extractConditionsFromText(text) {
  const found = [];
  const lowerText = text.toLowerCase();
  
  for (const [field, regex] of Object.entries(TEXT_KEYWORDS)) {
    if (regex.test(lowerText)) {
      found.push(field);
    }
  }
  return [...new Set(found)];
}

function getExtractedConditions(schemeId) {
  const cond = conditionsById[schemeId];
  if (!cond || !cond.conditions) return {};
  
  const extracted = {};
  for (const [key, val] of Object.entries(cond.conditions)) {
    if (val !== null && val !== undefined) {
      extracted[key] = val;
    }
  }
  return extracted;
}

// Process all schemes
const allSchemeResults = {};
const allQuestionsMap = new Map();
let schemesProcessed = 0;
let schemesWithConditions = 0;
let totalMissingConditions = 0;

console.log('\nProcessing schemes...');

for (const scheme of schemesData) {
  const schemeId = scheme.id;
  
  // Get full text
  const fullText = [
    scheme.eligibility || '',
    scheme.benefits || '',
    scheme.application_process || '',
    scheme.exclusions || '',
    scheme.description || ''
  ].join(' ');
  
  // Extract conditions from text
  const textConditions = extractConditionsFromText(fullText);
  
  // Get extracted conditions from conditions file
  const extractedConditions = getExtractedConditions(schemeId);
  
  if (Object.keys(extractedConditions).length > 0) {
    schemesWithConditions++;
  }
  
  // Find missing conditions (mentioned in text but not in extracted)
  const missingFields = textConditions.filter(field => {
    const extracted = extractedConditions[field];
    return extracted === null || extracted === undefined;
  });
  
  // Generate questions for missing conditions
  const questionsToAsk = [];
  for (const field of missingFields) {
    const qTemplate = QUESTIONS[field];
    if (qTemplate) {
      questionsToAsk.push({
        field: field,
        question: qTemplate.question,
        type: qTemplate.type,
        options: qTemplate.options || [],
        derives: qTemplate.derives || []
      });
    } else {
      questionsToAsk.push({
        field: field,
        question: `What is your ${field}?`,
        type: 'text'
      });
    }
  }
  
  // Store result
  allSchemeResults[schemeId] = {
    scheme_id: schemeId,
    scheme_name: scheme.name,
    category: scheme.category,
    description: scheme.description,
    eligibility: scheme.eligibility,
    benefits: scheme.benefits,
    application_process: scheme.application_process,
    exclusions: scheme.exclusions,
    extracted_conditions: extractedConditions,
    conditions_in_text: textConditions,
    missing_conditions: missingFields,
    questions_to_ask: questionsToAsk
  };
  
  // Add to global deduplication
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
    allQuestionsMap.get(key).schemes.push(schemeId);
  }
  
  totalMissingConditions += missingFields.length;
  schemesProcessed++;
  
  if (schemesProcessed % 500 === 0) {
    console.log(`Processed ${schemesProcessed}/${schemesData.length} schemes...`);
  }
}

console.log(`\n=== PROCESSING COMPLETE ===`);
console.log(`Total schemes: ${schemesProcessed}`);
console.log(`Schemes with extracted conditions: ${schemesWithConditions}`);
console.log(`Total missing condition mentions: ${totalMissingConditions}`);
console.log(`Unique questions after dedup: ${allQuestionsMap.size}`);

// Create output
const output = {
  metadata: {
    total_schemes_processed: schemesProcessed,
    schemes_with_extracted_conditions: schemesWithConditions,
    total_missing_conditions_found: totalMissingConditions,
    total_unique_questions: allQuestionsMap.size,
    processed_at: new Date().toISOString()
  },
  unique_questions: Array.from(allQuestionsMap.values()).map(q => ({
    ...q,
    scheme_count: q.schemes.length
  })),
  schemes: allSchemeResults
};

// Save
const outputPath = 'C:/yojanamitra_complete/missing_conditions_analysis_v2.json';
fs.writeFileSync(outputPath, JSON.stringify(output, null, 2));
console.log(`\nSaved to: ${outputPath}`);

// Show summary of top missing fields
const fieldCounts = {};
for (const schemeResult of Object.values(allSchemeResults)) {
  for (const field of schemeResult.missing_conditions) {
    fieldCounts[field] = (fieldCounts[field] || 0) + 1;
  }
}

console.log('\n=== TOP 20 MISSING CONDITIONS (by scheme count) ===');
const sorted = Object.entries(fieldCounts).sort((a, b) => b[1] - a[1]);
for (const [field, count] of sorted.slice(0, 20)) {
  console.log(`${field}: ${count} schemes`);
}