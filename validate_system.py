"""
Yojanamitra System Validation & Testing
========================================

Comprehensive validation suite to ensure the eligibility determination
system is working correctly with real data.
"""

import json
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SystemValidator:
    """Validate Yojanamitra system integrity and functionality."""
    
    def __init__(self):
        self.validation_results = {
            'timestamp': datetime.now().isoformat(),
            'data_files': {},
            'data_quality': {},
            'workflow_tests': {},
            'overall_status': 'unknown'
        }
        self.test_profiles = self._create_test_profiles()
    
    def _create_test_profiles(self) -> List[Dict[str, Any]]:
        """Create diverse test user profiles."""
        return [
            {
                'name': 'Young Female Student',
                'profile': {
                    'age': 22,
                    'gender': 'Female',
                    'state': 'Karnataka',
                    'annual_income': 0,
                    'education': '12th Pass',
                    'is_student': True,
                    'is_disabled': False
                }
            },
            {
                'name': 'Middle-aged SC Male',
                'profile': {
                    'age': 42,
                    'gender': 'Male',
                    'state': 'Rajasthan',
                    'annual_income': 250000,
                    'education': 'Bachelor',
                    'is_sc_st': True,
                    'is_disabled': False
                }
            },
            {
                'name': 'Elderly Woman',
                'profile': {
                    'age': 68,
                    'gender': 'Female',
                    'state': 'Maharashtra',
                    'annual_income': 100000,
                    'education': '10th Pass',
                    'is_disabled': True
                }
            },
            {
                'name': 'Unemployed Youth',
                'profile': {
                    'age': 25,
                    'gender': 'Male',
                    'state': 'Uttar Pradesh',
                    'annual_income': 50000,
                    'education': 'Graduate',
                    'occupation': 'Unemployed'
                }
            },
            {
                'name': 'Business Owner',
                'profile': {
                    'age': 35,
                    'gender': 'Female',
                    'state': 'Gujarat',
                    'annual_income': 500000,
                    'education': 'Postgraduate',
                    'occupation': 'Entrepreneur'
                }
            }
        ]
    
    def validate_data_files(self) -> Dict[str, Any]:
        """Validate existence and integrity of data files."""
        logger.info("=" * 60)
        logger.info("VALIDATING DATA FILES")
        logger.info("=" * 60)
        
        files_to_check = {
            'schemes': 'all_schemes_final.json',
            'eligibility': 'all_schemes_eligibility.json',
            'questions': 'all_questions_by_scheme.json'
        }
        
        results = {}
        
        for key, filename in files_to_check.items():
            logger.info(f"\n📄 Checking {key}: {filename}")
            
            if not os.path.exists(filename):
                logger.error(f"   ❌ FILE NOT FOUND: {filename}")
                results[key] = {
                    'status': 'missing',
                    'error': 'File not found'
                }
                continue
            
            try:
                file_size = os.path.getsize(filename)
                logger.info(f"   ✓ File size: {file_size / 1024 / 1024:.1f} MB")
                
                # Load and validate JSON
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                record_count = len(data)
                logger.info(f"   ✓ Records: {record_count:,}")
                
                # Sample validation
                if record_count > 0:
                    first_key = list(data.keys())[0]
                    first_record = data[first_key]
                    
                    if isinstance(first_record, dict):
                        field_count = len(first_record)
                        logger.info(f"   ✓ Fields per record: {field_count}")
                
                results[key] = {
                    'status': 'valid',
                    'file_size_mb': file_size / 1024 / 1024,
                    'record_count': record_count,
                    'first_key': first_key if record_count > 0 else None
                }
                
                logger.info(f"   ✅ VALID")
            
            except json.JSONDecodeError as e:
                logger.error(f"   ❌ JSON ERROR: {e}")
                results[key] = {
                    'status': 'corrupt',
                    'error': str(e)
                }
            except Exception as e:
                logger.error(f"   ❌ ERROR: {e}")
                results[key] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        self.validation_results['data_files'] = results
        return results
    
    def validate_data_quality(self) -> Dict[str, Any]:
        """Validate data quality and consistency."""
        logger.info("\n" + "=" * 60)
        logger.info("VALIDATING DATA QUALITY")
        logger.info("=" * 60)
        
        results = {}
        
        try:
            # Load data
            with open('all_schemes_final.json', 'r', encoding='utf-8') as f:
                schemes = json.load(f)
            
            with open('all_schemes_eligibility.json', 'r', encoding='utf-8') as f:
                eligibility = json.load(f)
            
            with open('all_questions_by_scheme.json', 'r', encoding='utf-8') as f:
                questions = json.load(f)
            
            # Check coverage
            logger.info(f"\n📊 Coverage Analysis:")
            
            schemes_count = len(schemes)
            eligibility_count = len(eligibility)
            questions_count = len(questions)
            
            logger.info(f"   Total schemes: {schemes_count:,}")
            logger.info(f"   With eligibility data: {eligibility_count:,}")
            logger.info(f"   With Q&A data: {questions_count:,}")
            
            eligibility_coverage = (eligibility_count / schemes_count * 100) if schemes_count > 0 else 0
            questions_coverage = (questions_count / schemes_count * 100) if schemes_count > 0 else 0
            
            logger.info(f"   Eligibility coverage: {eligibility_coverage:.1f}%")
            logger.info(f"   Q&A coverage: {questions_coverage:.1f}%")
            
            # Check data consistency
            logger.info(f"\n🔗 Data Consistency:")
            
            missing_schemes = []
            for sch_id in eligibility.keys():
                if sch_id not in schemes:
                    missing_schemes.append(sch_id)
            
            if missing_schemes:
                logger.warning(f"   ⚠️ {len(missing_schemes)} schemes in eligibility but not in schemes")
            else:
                logger.info(f"   ✓ All eligibility schemes reference valid schemes")
            
            # Check eligibility structure
            logger.info(f"\n✓ Eligibility Data Sample:")
            if eligibility:
                sample_id = list(eligibility.keys())[0]
                sample_elig = eligibility[sample_id]
                
                required_fields = ['age_range', 'applicable_states', 'income_criteria']
                found_fields = [f for f in required_fields if f in sample_elig]
                
                logger.info(f"   Scheme: {schemes[sample_id].get('scheme_name', 'Unknown')}")
                logger.info(f"   Fields: {list(sample_elig.keys())}")
                logger.info(f"   Has {len(found_fields)}/{len(required_fields)} required fields")
            
            # Check question structure
            logger.info(f"\n✓ Questions Data Sample:")
            if questions:
                sample_id = list(questions.keys())[0]
                sample_q = questions[sample_id]
                
                if 'questions' in sample_q:
                    q_count = len(sample_q['questions'])
                    logger.info(f"   Scheme: {sample_q.get('scheme_name', 'Unknown')}")
                    logger.info(f"   Questions: {q_count}")
                    
                    if q_count > 0:
                        first_q = sample_q['questions'][0]
                        logger.info(f"   Sample Q: {first_q.get('question_text', 'N/A')[:60]}...")
            
            results = {
                'status': 'valid',
                'schemes_count': schemes_count,
                'eligibility_coverage': f"{eligibility_coverage:.1f}%",
                'questions_coverage': f"{questions_coverage:.1f}%",
                'missing_schemes': len(missing_schemes)
            }
            
        except Exception as e:
            logger.error(f"❌ Quality check failed: {e}")
            results = {
                'status': 'error',
                'error': str(e)
            }
        
        self.validation_results['data_quality'] = results
        return results
    
    def test_workflow(self) -> Dict[str, Any]:
        """Test the workflow orchestrator with test profiles."""
        logger.info("\n" + "=" * 60)
        logger.info("TESTING WORKFLOW")
        logger.info("=" * 60)
        
        results = {}
        
        try:
            from workflow_orchestrator import WorkflowOrchestrator
            
            orchestrator = WorkflowOrchestrator()
            
            # Run tests with different profiles
            test_results = []
            
            for test in self.test_profiles:
                logger.info(f"\n🧪 Testing: {test['name']}")
                
                try:
                    # Run workflow
                    result = orchestrator.run_full_workflow(test['profile'])
                    
                    matches_found = len(result.get('verified_matches', []))
                    verified_count = len(result.get('verified_matches', []))
                    
                    logger.info(f"   ✓ Matches found: {matches_found}")
                    logger.info(f"   ✓ Verified matches: {verified_count}")
                    
                    if verified_count > 0:
                        top_scheme = result['verified_matches'][0]
                        logger.info(f"   ✓ Top scheme: {top_scheme['scheme_name']}")
                        logger.info(f"   ✓ Score: {top_scheme.get('verification_score', 0):.1%}")
                    
                    test_results.append({
                        'test': test['name'],
                        'status': 'passed',
                        'matches': verified_count
                    })
                
                except Exception as e:
                    logger.error(f"   ❌ Test failed: {e}")
                    test_results.append({
                        'test': test['name'],
                        'status': 'failed',
                        'error': str(e)
                    })
            
            results = {
                'status': 'completed',
                'tests_run': len(test_results),
                'tests_passed': len([t for t in test_results if t['status'] == 'passed']),
                'results': test_results
            }
            
        except ImportError:
            logger.error("❌ Cannot import WorkflowOrchestrator")
            results = {
                'status': 'import_error',
                'error': 'WorkflowOrchestrator not found'
            }
        except Exception as e:
            logger.error(f"❌ Workflow test failed: {e}")
            results = {
                'status': 'error',
                'error': str(e)
            }
        
        self.validation_results['workflow_tests'] = results
        return results
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate final validation report."""
        logger.info("\n" + "=" * 60)
        logger.info("VALIDATION REPORT")
        logger.info("=" * 60)
        
        # Determine overall status
        data_files_ok = all(
            v.get('status') == 'valid' 
            for v in self.validation_results['data_files'].values()
        )
        
        data_quality_ok = self.validation_results['data_quality'].get('status') == 'valid'
        
        workflow_ok = (
            self.validation_results['workflow_tests'].get('status') == 'completed' and
            self.validation_results['workflow_tests'].get('tests_passed', 0) > 0
        )
        
        overall_status = 'PASS' if (data_files_ok and data_quality_ok and workflow_ok) else 'FAIL'
        self.validation_results['overall_status'] = overall_status
        
        # Print summary
        print("\n📋 VALIDATION SUMMARY\n")
        print(f"Data Files:        {'✅ PASS' if data_files_ok else '❌ FAIL'}")
        print(f"Data Quality:      {'✅ PASS' if data_quality_ok else '❌ FAIL'}")
        print(f"Workflow Tests:    {'✅ PASS' if workflow_ok else '❌ FAIL'}")
        print(f"\nOverall Status:    {'🎉 PASS' if overall_status == 'PASS' else '⚠️ FAIL'}")
        
        # Print details
        if self.validation_results['data_quality']:
            quality = self.validation_results['data_quality']
            print(f"\nData Coverage:")
            print(f"  - Schemes: {quality.get('schemes_count', 'N/A'):,}")
            print(f"  - Eligibility: {quality.get('eligibility_coverage', 'N/A')}")
            print(f"  - Questions: {quality.get('questions_coverage', 'N/A')}")
        
        if self.validation_results['workflow_tests'].get('tests_passed'):
            tests = self.validation_results['workflow_tests']
            print(f"\nWorkflow Tests:")
            print(f"  - Passed: {tests['tests_passed']}/{tests.get('tests_run', 0)}")
        
        return self.validation_results
    
    def save_report(self, filename: str = 'validation_report.json') -> bool:
        """Save validation report to file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.validation_results, f, indent=2, ensure_ascii=False)
            logger.info(f"\n✓ Report saved to: {filename}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save report: {e}")
            return False
    
    def run_full_validation(self) -> bool:
        """Run complete validation suite."""
        logger.info("\n🚀 STARTING SYSTEM VALIDATION\n")
        
        # Run all validation steps
        self.validate_data_files()
        self.validate_data_quality()
        self.test_workflow()
        
        # Generate and save report
        report = self.generate_report()
        self.save_report()
        
        return report['overall_status'] == 'PASS'


def main():
    """Run validation."""
    validator = SystemValidator()
    success = validator.run_full_validation()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
