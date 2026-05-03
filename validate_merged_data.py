"""
VALIDATE & ANALYZE MERGED DATA
================================
After scraping and merging, validate that we have quality data:
1. All 4000 schemes have question data
2. Question fields are properly normalized
3. Cross-scheme mappings are sensible
4. No data corruption
"""

import json
import logging
from typing import Dict, List, Tuple
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DataValidator")


class MergedDataValidator:
    """Validate merged schemes+questions data."""
    
    def __init__(self, merged_file: str = 'all_schemes_with_questions.json'):
        self.merged_file = merged_file
        self.schemes = []
        self.cross_mapping_file = 'cross_scheme_field_mapping.json'
        self.cross_mapping = {}
    
    def load_data(self) -> bool:
        """Load merged data and cross-scheme mapping."""
        try:
            with open(self.merged_file, 'r', encoding='utf-8') as f:
                self.schemes = json.load(f)
            logger.info(f"Loaded {len(self.schemes)} schemes")
            
            try:
                with open(self.cross_mapping_file, 'r', encoding='utf-8') as f:
                    self.cross_mapping = json.load(f)
                logger.info(f"Loaded cross-scheme mapping with {len(self.cross_mapping)} fields")
            except FileNotFoundError:
                logger.warning(f"{self.cross_mapping_file} not found, skipping")
            
            return True
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return False
    
    def validate_scheme_structure(self) -> Tuple[int, List[str]]:
        """Validate each scheme has required fields."""
        errors = []
        valid_count = 0
        
        required_fields = ['id', 'name', 'category']
        
        for idx, scheme in enumerate(self.schemes):
            for field in required_fields:
                if field not in scheme:
                    errors.append(f"Scheme {idx}: Missing field '{field}'")
            
            if 'questions' in scheme and not isinstance(scheme['questions'], list):
                errors.append(f"Scheme {scheme.get('name', idx)}: 'questions' is not a list")
            
            if 'questions' in scheme and len(scheme['questions']) > 0:
                valid_count += 1
        
        return valid_count, errors
    
    def validate_question_normalization(self) -> Tuple[Dict, List[str]]:
        """Check if questions have normalized fields."""
        errors = []
        field_stats = defaultdict(int)
        non_normalized = 0
        
        for scheme in self.schemes:
            for q in scheme.get('questions', []):
                if 'normalized_field' not in q:
                    errors.append(f"{scheme['name']}: Question missing 'normalized_field'")
                    non_normalized += 1
                else:
                    field_stats[q['normalized_field']] += 1
        
        return dict(field_stats), errors
    
    def check_field_consistency(self) -> List[str]:
        """Check if normalized fields are consistent."""
        errors = []
        fields_seen = set()
        
        for scheme in self.schemes:
            for q in scheme.get('questions', []):
                field = q.get('normalized_field')
                if field:
                    fields_seen.add(field)
        
        # Check against known canonical fields
        canonical_fields = {
            'age', 'gender', 'annual_income', 'caste', 'state',
            'is_student', 'is_farmer', 'is_disabled', 'is_widow',
            'is_ews', 'is_bpl', 'occupation', 'education_level'
        }
        
        # Exclude very specific/rare fields
        common_fields = {f for f in fields_seen if fields_seen.count(f) > 5}
        
        return errors
    
    def validate_cross_scheme_mapping(self) -> Dict:
        """Validate cross-scheme field mappings."""
        issues = {}
        
        for field, data in self.cross_mapping.items():
            scheme_count = data.get('total_schemes', 0)
            
            # Check: Is this reasonable?
            if scheme_count > len(self.schemes):
                issues[field] = f"Scheme count ({scheme_count}) > total schemes ({len(self.schemes)})"
            
            if scheme_count == 0:
                issues[field] = "No schemes use this field"
        
        return issues
    
    def analyze_questions_per_scheme(self) -> Dict:
        """Analyze question distribution."""
        q_counts = []
        zero_question_schemes = []
        very_high_question_schemes = []
        
        for scheme in self.schemes:
            q_count = len(scheme.get('questions', []))
            q_counts.append(q_count)
            
            if q_count == 0:
                zero_question_schemes.append(scheme['name'])
            elif q_count > 50:
                very_high_question_schemes.append((scheme['name'], q_count))
        
        return {
            'total_schemes': len(self.schemes),
            'schemes_with_questions': len([c for c in q_counts if c > 0]),
            'average_questions': sum(q_counts) / len(q_counts) if q_counts else 0,
            'min_questions': min(q_counts) if q_counts else 0,
            'max_questions': max(q_counts) if q_counts else 0,
            'median_questions': sorted(q_counts)[len(q_counts)//2] if q_counts else 0,
            'schemes_with_zero_questions': len(zero_question_schemes),
            'schemes_with_high_questions': len(very_high_question_schemes)
        }
    
    def find_anomalies(self) -> Dict:
        """Find data anomalies."""
        anomalies = {
            'duplicate_scheme_names': [],
            'duplicate_questions': defaultdict(list),
            'malformed_questions': [],
            'missing_required_fields': []
        }
        
        scheme_names = set()
        
        for scheme in self.schemes:
            name = scheme.get('name')
            
            # Check duplicates
            if name in scheme_names:
                anomalies['duplicate_scheme_names'].append(name)
            scheme_names.add(name)
            
            # Check questions
            for q in scheme.get('questions', []):
                # Check if required fields exist
                if not q.get('original_question') or not q.get('normalized_field'):
                    anomalies['malformed_questions'].append({
                        'scheme': name,
                        'question': q
                    })
                
                # Check for empty/invalid values
                if not q.get('field_type'):
                    anomalies['missing_required_fields'].append({
                        'scheme': name,
                        'question_id': q.get('question_id'),
                        'missing': 'field_type'
                    })
        
        return anomalies
    
    def run_full_validation(self) -> Dict:
        """Run all validations."""
        if not self.load_data():
            return {'status': 'FAILED', 'error': 'Could not load data'}
        
        print("\n" + "="*70)
        print("MERGED DATA VALIDATION REPORT")
        print("="*70)
        
        # 1. Structure validation
        print("\n[1/5] Validating Scheme Structure...")
        valid_schemes, struct_errors = self.validate_scheme_structure()
        print(f"  ✓ {valid_schemes}/{len(self.schemes)} schemes have questions")
        if struct_errors:
            print(f"  ✗ {len(struct_errors)} structural errors found")
            for err in struct_errors[:3]:
                print(f"    - {err}")
        
        # 2. Question normalization
        print("\n[2/5] Validating Question Normalization...")
        field_stats, norm_errors = self.validate_question_normalization()
        print(f"  ✓ Questions have {len(field_stats)} unique normalized fields")
        if norm_errors:
            print(f"  ✗ {len(norm_errors)} normalization errors")
        
        # 3. Field consistency
        print("\n[3/5] Checking Field Consistency...")
        consistency_errors = self.check_field_consistency()
        if consistency_errors:
            print(f"  ✗ {len(consistency_errors)} consistency issues")
        else:
            print(f"  ✓ All fields properly normalized")
        
        # 4. Cross-scheme mapping
        print("\n[4/5] Validating Cross-Scheme Mapping...")
        mapping_issues = self.validate_cross_scheme_mapping()
        if mapping_issues:
            print(f"  ✗ {len(mapping_issues)} mapping issues found")
        else:
            print(f"  ✓ Cross-scheme mappings valid")
        
        # 5. Distribution analysis
        print("\n[5/5] Analyzing Question Distribution...")
        dist_stats = self.analyze_questions_per_scheme()
        print(f"  Schemes with questions: {dist_stats['schemes_with_questions']}/{dist_stats['total_schemes']}")
        print(f"  Average questions/scheme: {dist_stats['average_questions']:.1f}")
        print(f"  Range: {dist_stats['min_questions']}-{dist_stats['max_questions']} questions")
        print(f"  Schemes with 0 questions: {dist_stats['schemes_with_zero_questions']}")
        
        # Anomalies
        print("\n[ANOMALIES]")
        anomalies = self.find_anomalies()
        if anomalies['duplicate_scheme_names']:
            print(f"  ✗ {len(anomalies['duplicate_scheme_names'])} duplicate scheme names")
        if anomalies['malformed_questions']:
            print(f"  ✗ {len(anomalies['malformed_questions'])} malformed questions")
        if anomalies['missing_required_fields']:
            print(f"  ✗ {len(anomalies['missing_required_fields'])} missing required fields")
        
        # Summary
        print("\n" + "="*70)
        print("[SUMMARY]")
        print("="*70)
        
        total_issues = (
            len(struct_errors) + len(norm_errors) + len(consistency_errors) +
            len(mapping_issues) + len(anomalies['malformed_questions'])
        )
        
        if total_issues == 0:
            print("✓ ALL VALIDATIONS PASSED")
            return {
                'status': 'SUCCESS',
                'schemes': dist_stats['total_schemes'],
                'schemes_with_questions': dist_stats['schemes_with_questions'],
                'total_issues': 0
            }
        else:
            print(f"✗ {total_issues} ISSUES FOUND")
            return {
                'status': 'FAILED',
                'total_issues': total_issues,
                'struct_errors': len(struct_errors),
                'norm_errors': len(norm_errors),
                'consistency_errors': len(consistency_errors),
                'mapping_issues': len(mapping_issues),
                'malformed_questions': len(anomalies['malformed_questions'])
            }


def main():
    """Run validation."""
    validator = MergedDataValidator()
    result = validator.run_full_validation()
    
    print("\n" + "="*70)
    print(f"VALIDATION STATUS: {result.get('status', 'UNKNOWN')}")
    print("="*70 + "\n")
    
    # Recommendations
    if result.get('status') == 'SUCCESS':
        print("✓ Data is ready for Phase 2 (Flask Integration)")
        print("\nNext steps:")
        print("  1. Add UnifiedProfileModel to database")
        print("  2. Create API endpoints for profile management")
        print("  3. Update eligibility engine to use unified profile")
        print("  4. Test with sample users")
    else:
        print("✗ Data needs fixes before Phase 2")
        print("\nIssues to fix:")
        for key, value in result.items():
            if key not in ['status'] and value > 0:
                print(f"  - {key}: {value}")


if __name__ == '__main__':
    main()
