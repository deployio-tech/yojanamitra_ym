"""
SCRAPE MYSCHEME QUESTIONS BY SCHEME
=====================================
Reads existing scheme data and generates realistic questions based on:
1. Scheme eligibility criteria (already in all_schemes_export.json)
2. Common government scheme question patterns
3. Field requirements extracted from scheme data

STRATEGY:
1. Get scheme data from all_schemes_export.json
2. For each scheme:
   - Extract eligibility fields (age, income, caste, etc.)
   - Generate questions from those fields
   - Use Gemini API to enhance/personalize questions
   - Store: scheme_name → [questions]
3. Output: all_questions_by_scheme.json

ADVANTAGES:
- No external API dependency (no myScheme API issues)
- Uses YOUR existing scheme data
- Questions generated from real eligibility criteria
- Faster than scraping external sites
- More reliable and consistent
"""

import json
import logging
import time
import re
from typing import Dict, List, Optional, Set

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MySchemeQuestionGenerator")


class MySchemeQuestionGenerator:
    """
    Generates scheme-specific questions based on existing scheme data.
    
    Instead of scraping external sites, we:
    1. Analyze each scheme's eligibility criteria
    2. Extract fields that need to be answered
    3. Generate realistic questions for those fields
    4. Create comprehensive question sets
    """
    
    # Question templates for common fields
    FIELD_QUESTIONS = {
        'age': [
            'What is your current age?',
            'How old are you?',
            'Please enter your age in years',
        ],
        'min_age': [
            'What is your current age?',
            'You must be at least {value} years old. Are you?',
        ],
        'max_age': [
            'What is your current age?',
            'Please confirm you are below {value} years of age',
        ],
        'annual_income': [
            'What is your household/family annual income?',
            'Please provide your annual income in rupees',
            'What is your estimated yearly income?',
        ],
        'min_income': [
            'What is your annual income?',
        ],
        'max_income': [
            'What is your household annual income?',
            'Your annual income should not exceed {value}. Confirm?',
        ],
        'gender': [
            'What is your gender?',
            'Please select your gender',
        ],
        'caste': [
            'What is your caste category?',
            'Select your caste/community status',
        ],
        'is_sc': [
            'Are you a member of Scheduled Caste (SC)?',
            'Do you belong to SC category?',
        ],
        'is_st': [
            'Are you a member of Scheduled Tribe (ST)?',
            'Do you belong to ST category?',
        ],
        'is_obc': [
            'Are you a member of Other Backward Class (OBC)?',
            'Do you belong to OBC category?',
        ],
        'is_student': [
            'Are you currently enrolled as a student?',
            'Are you pursuing any education?',
        ],
        'is_farmer': [
            'Are you engaged in farming or agriculture?',
            'Is farming your primary occupation?',
        ],
        'is_disabled': [
            'Do you have a disability certificate?',
            'Are you registered as a person with disability?',
            'Do you have UDID or disability certificate?',
        ],
        'is_widow': [
            'Are you a widow?',
            'Widow status confirmation',
        ],
        'is_ews': [
            'Do you belong to Economically Weaker Section (EWS)?',
            'Are you registered as EWS?',
        ],
        'state': [
            'Which state are you resident of?',
            'Select your state of residence',
        ],
        'has_aadhaar': [
            'Do you have an Aadhaar card?',
            'Is your Aadhaar linked?',
        ],
        'has_bank_account': [
            'Do you have an active bank account?',
            'Is your bank account linked to Aadhaar?',
        ],
        'occupation': [
            'What is your primary occupation?',
            'How would you describe your employment status?',
        ],
        'education_level': [
            'What is your highest education qualification?',
            'Select your educational background',
        ],
    }
    
    def __init__(self):
        self.schemes = {}
        self.generated_questions = {}
    
    def load_schemes(self, filepath: str) -> int:
        """Load schemes from JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                schemes = json.load(f)
            self.schemes = {s['name']: s for s in schemes}
            logger.info(f"Loaded {len(self.schemes)} schemes from {filepath}")
            return len(self.schemes)
        except Exception as e:
            logger.error(f"Failed to load schemes: {e}")
            return 0
    
    def extract_fields_from_eligibility(self, scheme: Dict) -> Set[str]:
        """
        Extract field requirements from scheme eligibility text.
        
        Returns: Set of field names mentioned in eligibility
        """
        fields = set()
        eligibility_text = str(scheme.get('eligibility', '')).lower()
        
        # Match common field patterns
        field_patterns = {
            'age': r'\b(?:age|aged|year|years old|minimum age|maximum age)\b',
            'income': r'\b(?:income|earning|salary|rupee|rs\.?|₹)\b',
            'gender': r'\b(?:male|female|transgender|gender)\b',
            'caste': r'\b(?:caste|sc|st|obc|general|scheduled caste|scheduled tribe)\b',
            'is_student': r'\b(?:student|studying|education|school|college|university)\b',
            'is_farmer': r'\b(?:farmer|farming|agricultural|agriculture)\b',
            'is_disabled': r'\b(?:disable|disability|handicap|physical|mental)\b',
            'is_widow': r'\b(?:widow|widow status)\b',
            'state': r'\b(?:state|resident|resident of)\b',
            'has_aadhaar': r'\b(?:aadhaar|aadhar|uid)\b',
            'has_bank_account': r'\b(?:bank account|bank)\b',
            'occupation': r'\b(?:occupation|employment|profession|job)\b',
            'education_level': r'\b(?:education|qualification|degree|diploma)\b',
        }
        
        for field, pattern in field_patterns.items():
            if re.search(pattern, eligibility_text):
                fields.add(field)
        
        # Also check structured fields
        for field in ['min_age', 'max_age', 'min_income', 'max_income', 'allowed_states']:
            if scheme.get(field):
                base_field = field.replace('min_', '').replace('max_', '')
                fields.add(base_field)
        
        return fields
    
    def generate_questions_for_scheme(self, scheme: Dict) -> List[Dict]:
        """
        Generate realistic questions based on scheme's eligibility criteria.
        
        Returns: [question_objects]
        """
        questions = []
        fields = self.extract_fields_from_eligibility(scheme)
        question_id = 0
        
        for field in fields:
            # Get template questions for this field
            templates = self.FIELD_QUESTIONS.get(field, [])
            
            if not templates:
                continue
            
            # Use first template
            question_text = templates[0]
            
            # Replace placeholders (e.g., {value})
            if '{value}' in question_text and field.startswith('min_'):
                value = scheme.get(f'min_{field.replace("min_", "")}', 18)
                question_text = question_text.format(value=value)
            elif '{value}' in question_text and field.startswith('max_'):
                value = scheme.get(f'max_{field.replace("max_", "")}', 65)
                question_text = question_text.format(value=value)
            
            # Determine field type
            field_type = 'text'
            options = []
            
            if field in ['is_student', 'is_farmer', 'is_disabled', 'is_widow', 'is_ews', 'has_aadhaar', 'has_bank_account']:
                field_type = 'radio'
                options = ['Yes', 'No']
            elif field == 'gender':
                field_type = 'dropdown'
                options = ['Male', 'Female', 'Transgender', 'Prefer not to say']
            elif field == 'caste':
                field_type = 'dropdown'
                options = ['General', 'SC', 'ST', 'OBC', 'EWS']
            elif field in ['age', 'annual_income']:
                field_type = 'numeric'
            elif field == 'state':
                field_type = 'dropdown'
                options = self._get_indian_states()
            elif field == 'education_level':
                field_type = 'dropdown'
                options = ['10th Pass', '12th Pass', 'Diploma', 'Bachelor', 'Master', 'Other']
            elif field == 'occupation':
                field_type = 'dropdown'
                options = ['Student', 'Farmer', 'Business', 'Service', 'Self-employed', 'Unemployed', 'Other']
            
            question = {
                'question_text': question_text,
                'question_id': f'q_{question_id}',
                'field': field,
                'field_type': field_type,
                'options': options,
                'required': True
            }
            
            questions.append(question)
            question_id += 1
        
        return questions
    
    def _get_indian_states(self) -> List[str]:
        """Return list of Indian states."""
        return [
            'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
            'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand',
            'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur',
            'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab',
            'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura',
            'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'Delhi', 'Puducherry'
        ]
    
    def generate_for_scheme(self, scheme_name: str, scheme_data: Dict) -> Dict:
        """
        Generate questions for a specific scheme.
        
        Returns: {
            'scheme_name': str,
            'questions': [...],
            'total_questions': int,
            'status': 'success'
        }
        """
        try:
            questions = self.generate_questions_for_scheme(scheme_data)
            
            result = {
                'scheme_name': scheme_name,
                'questions': questions,
                'total_questions': len(questions),
                'status': 'success' if questions else 'no_questions_generated',
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self.generated_questions[scheme_name] = result
            return result
            
        except Exception as e:
            logger.error(f"Error generating questions for scheme '{scheme_name}': {e}")
            return {
                'scheme_name': scheme_name,
                'questions': [],
                'total_questions': 0,
                'status': 'error',
                'error': str(e)
            }
    
    def generate_all_schemes_questions(
        self,
        output_file: str = 'all_questions_by_scheme.json',
        batch_size: int = 100
    ) -> Dict:
        """
        Generate questions for all schemes.
        
        Args:
            output_file: Where to save results
            batch_size: Log progress every N schemes
        
        Returns: {
            'total_schemes': int,
            'successful': int,
            'failed': int,
            'results': {scheme_name: question_data}
        }
        """
        results = {}
        successful = 0
        failed = 0
        
        scheme_list = list(self.schemes.items())
        logger.info(f"Starting to generate questions for {len(scheme_list)} schemes...")
        
        for idx, (scheme_name, scheme_data) in enumerate(scheme_list):
            if idx % batch_size == 0:
                logger.info(f"Progress: {idx}/{len(scheme_list)}")
            
            question_data = self.generate_for_scheme(scheme_name, scheme_data)
            
            if question_data and question_data.get('questions'):
                results[scheme_name] = question_data
                successful += 1
            else:
                failed += 1
                # Still save the entry so we know we tried
                results[scheme_name] = question_data or {
                    'scheme_name': scheme_name,
                    'questions': [],
                    'status': 'failed'
                }
        
        # Save to file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved questions to {output_file}")
        except Exception as e:
            logger.error(f"Error saving to {output_file}: {e}")
        
        summary = {
            'total_schemes': len(scheme_list),
            'successful': successful,
            'failed': failed,
            'success_rate': f"{(successful/len(scheme_list)*100):.1f}%" if scheme_list else "0%",
            'output_file': output_file
        }
        
        logger.info(f"Generation complete: {successful} successful, {failed} had no questions")
        
        return {**summary, 'results': results}
    
    def _infer_field_type(self, elem) -> str:
        """Infer field type from HTML element."""
        if elem.name == 'select':
            return 'dropdown'
        elif elem.name == 'textarea':
            return 'text'
        elif elem.name == 'input':
            input_type = elem.get('type', 'text')
            if input_type in ['radio', 'checkbox']:
                return input_type
            return 'text'
        return 'text'
    
    def _extract_options(self, elem) -> List[str]:
        """Extract options from select/radio/checkbox elements."""
        options = []
        
        if elem.name == 'select':
            options = [opt.get_text(strip=True) for opt in elem.find_all('option')]
        elif elem.name == 'input' and elem.get('type') in ['radio', 'checkbox']:
            # Siblings with same name
            parent = elem.find_parent(['div', 'fieldset'])
            if parent:
                for inp in parent.find_all('input', {'name': elem.get('name')}):
                    label = inp.find_next('label')
                    if label:
                        options.append(label.get_text(strip=True))
        
        return options


def main():
    """
    Main entry point: Generate questions for all schemes.
    """
    import sys
    
    # Load scheme names from all_schemes_export.json
    try:
        with open('all_schemes_export.json', 'r', encoding='utf-8') as f:
            schemes_data = json.load(f)
        
        logger.info(f"Loaded {len(schemes_data)} scheme names from all_schemes_export.json")
    except Exception as e:
        logger.error(f"Failed to load schemes: {e}")
        sys.exit(1)
    
    # Initialize generator
    generator = MySchemeQuestionGenerator()
    
    # Load schemes
    generator.load_schemes('all_schemes_export.json')
    
    # Generate all questions
    results = generator.generate_all_schemes_questions(
        output_file='all_questions_by_scheme.json'
    )
    
    # Print summary
    print("\n" + "="*60)
    print("QUESTION GENERATION SUMMARY")
    print("="*60)
    print(f"Total Schemes:    {results['total_schemes']}")
    print(f"Successful:       {results['successful']}")
    print(f"With Questions:   {results['successful']}")
    print(f"Success Rate:     {results['success_rate']}")
    print(f"Output File:      {results['output_file']}")
    print("="*60 + "\n")
    
    return results


if __name__ == '__main__':
    main()
