const fs = require('fs');

// Check the exact structure
const conditionsData = JSON.parse(fs.readFileSync('C:/yojanamitra_complete/scheme_conditions.json', 'utf8'));
const schemesData = JSON.parse(fs.readFileSync('C:/yojanamitra_complete/all_schemes_export.json', 'utf8'));

console.log('=== FILE STRUCTURE CHECK ===');
console.log(`Schemes: ${schemesData.length} entries`);
console.log(`Conditions: ${Object.keys(conditionsData).length} entries`);

// Get min and max IDs from conditions
const conditionIds = Object.keys(conditionsData).map(Number).sort((a,b) => a-b);
console.log(`Condition IDs range: ${Math.min(...conditionIds)} to ${Math.max(...conditionIds)}`);

// Get first few and last few scheme IDs
const schemeIds = schemesData.map(s => s.id).sort((a,b) => a-b);
console.log(`Scheme IDs range: ${Math.min(...schemeIds)} to ${Math.max(...schemeIds)}`);

// Sample IDs
console.log('\nFirst 10 condition IDs:', conditionIds.slice(0, 10));
console.log('Last 10 condition IDs:', conditionIds.slice(-10));

console.log('\nFirst 10 scheme IDs:', schemeIds.slice(0, 10));
console.log('Last 10 scheme IDs:', schemeIds.slice(-10));

// Check if IDs match
const matching = conditionIds.filter(id => schemeIds.includes(id));
console.log(`\nMatching IDs: ${matching.length}`);