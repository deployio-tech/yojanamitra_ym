"""
MERGE QUESTIONS WITH SCHEMES
=============================
Takes:
- all_schemes_export.json (4000+ schemes)
- all_questions_by_scheme.json (questions for each scheme)

Outputs:
- all_schemes_with_questions.json (merged)

STRATEGY:
1. For each scheme in all_schemes_export.json
2. Look up questions from all_questions_by_scheme.json
3. Add questions array to scheme
4. Normalize/standardize question field mappings
5. Deduplicate questions across schemes (for unified profile)
"""

import json
import logging
from typing import Dict, List, Any
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SchemeQuestionMerger")


class SchemeQuestionMerger:
    """
    Merges scheme data with question data to create unified JSON.
    """
    
    def __init__(self):
        self.schemes = {}
        self.questions_by_scheme = {}
        self.all_questions = {}
        self.field_to_schemes = defaultdict(list)
    
    def load_schemes(self, filepath: str) -> int:
        """Load schemes from JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.schemes = {s['name']: s for s in data}
            logger.info(f"Loaded {len(self.schemes)} schemes from {filepath}")
            return len(self.schemes)
        
        except Exception as e:
            logger.error(f"Failed to load schemes from {filepath}: {e}")
            return 0
    
    def load_questions(self, filepath: str) -> int:
        """Load questions by scheme."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.questions_by_scheme = data
            logger.info(f"Loaded questions for {len(data)} schemes from {filepath}")
            return len(data)
        
        except Exception as e:
            logger.error(f"Failed to load questions from {filepath}: {e}")
            return 0
    
    def normalize_question_field(self, field: str, question_text: str = '') -> Dict[str, str]:
        """
        Map question field to canonical field names used in the system.
        
        Returns: {
            'normalized_field': canonical name,
            'category': broad category,
            'type': field type hint
        }
        """
        
        # Mapping of common question fields to canonical form
        field_mappings = {
            # Age-related
            'age': 'age',
            'date_of_birth': 'date_of_birth',
            'dob': 'date_of_birth',
            
            # Income-related
            'annual_income': 'annual_income',
            'income': 'annual_income',
            'family_income': 'annual_income',
            'household_income': 'annual_income',
            
            # Age/Education
            'student': 'is_student',
            'is_student': 'is_student',
            'currently_studying': 'is_student',
            'education_level': 'education_level',
            'highest_education': 'education_level',
            
            # Caste
            'caste': 'caste',
            'caste_category': 'caste',
            'sc': 'is_sc',
            'st': 'is_st',
            'obc': 'is_obc',
            'general': 'caste',
            
            # Employment
            'occupation': 'occupation',
            'employment_status': 'employment_status',
            'farmer': 'is_farmer',
            'self_employed': 'is_self_employed',
            'worker': 'is_construction_worker',
            
            # Disability
            'disability': 'is_disabled',
            'disabled': 'is_disabled',
            'disability_percentage': 'disability_percentage',
            'disability_certificate': 'is_disabled',
            
            # Gender
            'gender': 'gender',
            'sex': 'gender',
            'transgender': 'is_transgender',
            
            # Residency
            'state': 'state',
            'residence_state': 'state',
            'domicile': 'has_domicile',
            'urban_rural': 'is_urban',
            'rural': 'is_rural',
            'urban': 'is_urban',
            
            # Documents
            'aadhaar': 'has_aadhaar',
            'bank_account': 'has_bank_account',
            'aadhar': 'has_aadhaar',
            
            # Other
            'widow': 'is_widow',
            'pregnant': 'is_pregnant',
            'minority': 'is_minority',
            'ews': 'is_ews',
            'bpl': 'is_bpl',
        }
        
        # Try exact match first
        normalized = field_mappings.get(field.lower().strip())
        
        if not normalized:
            # Try to infer from question text
            text_lower = question_text.lower()
            
            if any(word in text_lower for word in ['age', 'year', 'born', 'dob']):
                normalized = 'age'
            elif any(word in text_lower for word in ['income', 'earning', 'salary', 'rupee']):
                normalized = 'annual_income'
            elif any(word in text_lower for word in ['student', 'studying', 'education', 'school', 'college']):
                normalized = 'is_student'
            elif any(word in text_lower for word in ['farmer', 'agricultural', 'farming']):
                normalized = 'is_farmer'
            elif any(word in text_lower for word in ['disable', 'disability', 'handicap']):
                normalized = 'is_disabled'
            elif any(word in text_lower for word in ['caste', 'sc', 'st', 'obc']):
                normalized = 'caste'
            elif any(word in text_lower for word in ['gender', 'sex', 'transgender']):
                normalized = 'gender'
            else:
                normalized = field or 'unknown'
        
        # Categorize
        if normalized.startswith('is_'):
            category = 'boolean'
        elif normalized in ['age', 'annual_income', 'disability_percentage']:
            category = 'numeric'
        elif normalized in ['caste', 'education_level', 'occupation', 'gender', 'state']:
            category = 'categorical'
        else:
            category = 'other'
        
        return {
            'normalized_field': normalized,
            'category': category,
            'original_field': field
        }
    
    def merge_scheme_questions(self, scheme_name: str, scheme_data: Dict) -> Dict:
        """
        Merge questions into a single scheme.
        
        Returns modified scheme_data with questions added.
        """
        result = scheme_data.copy()
        
        # Get questions for this scheme
        scheme_questions_data = self.questions_by_scheme.get(scheme_name, {})
        
        if not scheme_questions_data or scheme_questions_data.get('status') != 'success':
            result['questions'] = []
            result['original_question_count'] = 0
            logger.debug(f"No questions found for scheme: {scheme_name}")
            return result
        
        raw_questions = scheme_questions_data.get('questions', [])
        
        # Normalize and enrich questions
        normalized_questions = []
        for q in raw_questions:
            field_info = self.normalize_question_field(
                q.get('field', ''),
                q.get('question_text', '')
            )
            
            normalized_q = {
                'original_question': q.get('question_text', q.get('label', '')),
                'normalized_field': field_info['normalized_field'],
                'field_category': field_info['category'],
                'field_type': q.get('field_type', 'text'),
                'options': q.get('options', []),
                'required': q.get('required', True),
                'question_id': q.get('question_id', ''),
            }
            
            normalized_questions.append(normalized_q)
            
            # Track field usage across schemes
            self.field_to_schemes[field_info['normalized_field']].append(scheme_name)
            
            # Track all unique questions
            all_q_key = f"{field_info['normalized_field']}_{normalized_q['original_question'][:50]}"
            self.all_questions[all_q_key] = normalized_q
        
        result['questions'] = normalized_questions
        result['original_question_count'] = len(raw_questions)
        result['normalized_question_count'] = len(normalized_questions)
        
        return result
    
    def merge_all_schemes(self) -> List[Dict]:
        """
        Merge questions into all schemes.
        
        Returns: List of enhanced scheme objects
        """
        merged_schemes = []
        
        logger.info(f"Merging questions into {len(self.schemes)} schemes...")
        
        for scheme_name, scheme_data in self.schemes.items():
            merged = self.merge_scheme_questions(scheme_name, scheme_data)
            merged_schemes.append(merged)
        
        logger.info(f"Merged {len(merged_schemes)} schemes")
        return merged_schemes
    
    def save_merged_schemes(self, schemes: List[Dict], output_file: str) -> bool:
        """Save merged schemes to JSON file."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(schemes, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(schemes)} merged schemes to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save to {output_file}: {e}")
            return False
    
    def generate_cross_scheme_mapping(self) -> Dict[str, Any]:
        """
        Generate mapping of shared fields across schemes.
        
        Returns: {
            'field_name': {
                'total_schemes': int,
                'schemes': [names],
                'variations': [question variations]
            }
        }
        """
        mapping = {}
        
        for field, schemes in self.field_to_schemes.items():
            if len(schemes) > 1:  # Only include fields used in multiple schemes
                mapping[field] = {
                    'total_schemes': len(schemes),
                    'schemes': list(set(schemes)),
                    'percentage': f"{(len(set(schemes))/len(self.schemes)*100):.1f}%"
                }
        
        return mapping
    
    def generate_statistics(self, merged_schemes: List[Dict]) -> Dict:
        """Generate statistics about the merged data."""
        total_questions = 0
        schemes_with_questions = 0
        field_frequency = defaultdict(int)
        
        for scheme in merged_schemes:
            questions = scheme.get('questions', [])
            if questions:
                schemes_with_questions += 1
                total_questions += len(questions)
                
                for q in questions:
                    field_frequency[q['normalized_field']] += 1
        
        return {
            'total_schemes': len(merged_schemes),
            'schemes_with_questions': schemes_with_questions,
            'schemes_without_questions': len(merged_schemes) - schemes_with_questions,
            'total_questions_across_all_schemes': total_questions,
            'average_questions_per_scheme': f"{(total_questions/len(merged_schemes) if merged_schemes else 0):.1f}",
            'unique_fields': len(field_frequency),
            'top_fields': dict(sorted(
                field_frequency.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10])
        }


def main():
    """Main entry point: Load, merge, and save."""
    import sys
    
    logger.info("="*60)
    logger.info("SCHEME-QUESTION MERGER")
    logger.info("="*60)
    
    merger = SchemeQuestionMerger()
    
    # Load data
    schemes_loaded = merger.load_schemes('all_schemes_export.json')
    questions_loaded = merger.load_questions('all_questions_by_scheme.json')
    
    if not schemes_loaded or not questions_loaded:
        logger.error("Failed to load required data files")
        sys.exit(1)
    
    # Merge
    merged_schemes = merger.merge_all_schemes()
    
    # Generate statistics
    stats = merger.generate_statistics(merged_schemes)
    
    # Generate cross-scheme mapping
    cross_scheme_mapping = merger.generate_cross_scheme_mapping()
    
    # Save
    merger.save_merged_schemes(merged_schemes, 'all_schemes_with_questions.json')
    
    # Save cross-scheme mapping
    try:
        with open('cross_scheme_field_mapping.json', 'w', encoding='utf-8') as f:
            json.dump(cross_scheme_mapping, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved cross-scheme mapping with {len(cross_scheme_mapping)} shared fields")
    except Exception as e:
        logger.error(f"Failed to save cross-scheme mapping: {e}")
    
    # Print statistics
    print("\n" + "="*60)
    print("MERGE STATISTICS")
    print("="*60)
    print(f"Total Schemes:                    {stats['total_schemes']}")
    print(f"Schemes with Questions:           {stats['schemes_with_questions']}")
    print(f"Schemes without Questions:        {stats['schemes_without_questions']}")
    print(f"Total Questions:                  {stats['total_questions_across_all_schemes']}")
    print(f"Avg Questions per Scheme:         {stats['average_questions_per_scheme']}")
    print(f"Unique Question Fields:           {stats['unique_fields']}")
    print(f"\nTop 10 Most Common Fields:")
    for field, count in stats['top_fields'].items():
        print(f"  - {field}: {count} schemes")
    print(f"\nCross-Scheme Shared Fields:       {len(cross_scheme_mapping)}")
    print("="*60 + "\n")
    
    return {
        'schemes': merged_schemes,
        'statistics': stats,
        'cross_scheme_mapping': cross_scheme_mapping
    }


if __name__ == '__main__':
    main()
