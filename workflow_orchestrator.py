"""
Yojanamitra Workflow Orchestrator
==================================

Coordinates the complete eligibility determination pipeline:
1. Load scheme data and pre-calculated eligibility
2. Load user profile
3. Process eligibility checks via eligibility engine
4. Present matching schemes with Q&A verification

This orchestrator manages the flow between components while providing
logging, error handling, and result compilation.
"""

import json
import os
import sys
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('workflow.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Main orchestrator for the eligibility determination pipeline."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the orchestrator with configuration."""
        self.config = config or self._load_config()
        self.schemes_data = {}
        self.eligibility_data = {}
        self.questions_data = {}
        self.user_profile = {}
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'user_profile': {},
            'matching_schemes': [],
            'verified_matches': [],
            'errors': []
        }
        logger.info("WorkflowOrchestrator initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or provide defaults."""
        config_file = 'workflow_config.json'
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return {
            'data_dir': '.',
            'schemes_file': 'all_schemes_final.json',
            'eligibility_file': 'all_schemes_eligibility.json',
            'questions_file': 'all_questions_by_scheme.json',
            'max_matches': 50,
            'confidence_threshold': 0.6,
            'enable_detailed_logging': True
        }
    
    def load_data(self) -> bool:
        """Load all required data files."""
        logger.info("Loading data files...")
        
        try:
            # Load schemes
            schemes_path = os.path.join(self.config['data_dir'], self.config['schemes_file'])
            if os.path.exists(schemes_path):
                with open(schemes_path, 'r', encoding='utf-8') as f:
                    self.schemes_data = json.load(f)
                logger.info(f"Loaded {len(self.schemes_data)} schemes")
            else:
                logger.warning(f"Schemes file not found: {schemes_path}")
            
            # Load eligibility data
            eligibility_path = os.path.join(self.config['data_dir'], 
                                           self.config['eligibility_file'])
            if os.path.exists(eligibility_path):
                with open(eligibility_path, 'r', encoding='utf-8') as f:
                    self.eligibility_data = json.load(f)
                logger.info(f"Loaded eligibility data for {len(self.eligibility_data)} schemes")
            else:
                logger.warning(f"Eligibility file not found: {eligibility_path}")
            
            # Load questions
            questions_path = os.path.join(self.config['data_dir'], 
                                         self.config['questions_file'])
            if os.path.exists(questions_path):
                with open(questions_path, 'r', encoding='utf-8') as f:
                    self.questions_data = json.load(f)
                logger.info(f"Loaded questions for {len(self.questions_data)} schemes")
            else:
                logger.warning(f"Questions file not found: {questions_path}")
            
            return bool(self.schemes_data and self.eligibility_data)
        
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            self.results['errors'].append(str(e))
            return False
    
    def load_user_profile(self, profile: Dict[str, Any]) -> bool:
        """Load and validate user profile."""
        logger.info("Loading user profile...")
        
        try:
            # Validate required fields
            required_fields = ['age', 'state', 'gender']
            missing_fields = [f for f in required_fields if f not in profile]
            
            if missing_fields:
                logger.warning(f"Missing fields in profile: {missing_fields}")
            
            self.user_profile = profile
            self.results['user_profile'] = {
                'timestamp': datetime.now().isoformat(),
                'fields_provided': len(profile),
                'required_fields_met': len(missing_fields) == 0
            }
            
            logger.info(f"Profile loaded with {len(profile)} fields")
            return True
        
        except Exception as e:
            logger.error(f"Error loading profile: {e}")
            self.results['errors'].append(str(e))
            return False
    
    def determine_matching_schemes(self) -> List[Dict[str, Any]]:
        """
        Determine schemes that user might be eligible for.
        
        Returns:
            List of matching schemes with eligibility scores.
        """
        logger.info("Determining matching schemes...")
        matches = []
        
        try:
            for scheme_id, eligibility_info in self.eligibility_data.items():
                if scheme_id not in self.schemes_data:
                    continue
                
                scheme = self.schemes_data[scheme_id]
                
                # Calculate eligibility score
                score = self._calculate_eligibility_score(
                    self.user_profile,
                    eligibility_info
                )
                
                if score > self.config.get('confidence_threshold', 0.6):
                    matches.append({
                        'scheme_id': scheme_id,
                        'scheme_name': scheme.get('scheme_name', 'Unknown'),
                        'score': score,
                        'eligibility_info': eligibility_info,
                        'scheme_details': scheme
                    })
            
            # Sort by score and limit results
            matches.sort(key=lambda x: x['score'], reverse=True)
            matches = matches[:self.config.get('max_matches', 50)]
            
            logger.info(f"Found {len(matches)} matching schemes")
            self.results['matching_schemes'] = [
                {
                    'scheme_name': m['scheme_name'],
                    'score': m['score']
                }
                for m in matches
            ]
            
            return matches
        
        except Exception as e:
            logger.error(f"Error determining matches: {e}")
            self.results['errors'].append(str(e))
            return []
    
    def _calculate_eligibility_score(self, profile: Dict[str, Any], 
                                     eligibility: Dict[str, Any]) -> float:
        """
        Calculate eligibility score for a scheme.
        
        Score algorithm:
        - Age match: 0-0.3 points
        - State match: 0-0.3 points
        - Gender match: 0-0.2 points
        - Income match: 0-0.2 points
        
        Args:
            profile: User profile data
            eligibility: Scheme eligibility requirements
        
        Returns:
            Eligibility score (0-1)
        """
        score = 0.0
        
        # Age eligibility (0-0.3)
        age_range = eligibility.get('age_range', {})
        if age_range and 'min_age' in age_range:
            user_age = profile.get('age', 0)
            min_age = age_range.get('min_age', 0)
            max_age = age_range.get('max_age', 150)
            
            if min_age <= user_age <= max_age:
                score += 0.3
            elif user_age >= max_age:
                score += 0  # Too old
            else:
                score += 0.1  # Close to minimum age
        
        # State eligibility (0-0.3)
        applicable_states = eligibility.get('applicable_states', [])
        user_state = profile.get('state', '').lower()
        
        if not applicable_states or any(s.lower() == user_state for s in applicable_states):
            score += 0.3
        
        # Gender eligibility (0-0.2)
        applicable_genders = eligibility.get('applicable_genders', [])
        user_gender = profile.get('gender', '').lower()
        
        if not applicable_genders or any(g.lower() == user_gender for g in applicable_genders):
            score += 0.2
        
        # Income eligibility (0-0.2)
        income_criteria = eligibility.get('income_criteria', {})
        if income_criteria and 'max_income' in income_criteria:
            user_income = profile.get('annual_income', float('inf'))
            max_income = income_criteria.get('max_income', 0)
            
            if user_income <= max_income:
                score += 0.2
            elif user_income <= max_income * 1.1:
                score += 0.1  # Slightly above limit
        
        return min(score, 1.0)
    
    def verify_with_questions(self, matching_schemes: List[Dict[str, Any]]
                             ) -> List[Dict[str, Any]]:
        """
        Verify matching schemes using Q&A verification.
        
        Args:
            matching_schemes: List of initially matched schemes
        
        Returns:
            List of verified matches with Q&A results.
        """
        logger.info(f"Verifying {len(matching_schemes)} schemes with Q&A...")
        verified = []
        
        try:
            for match in matching_schemes:
                scheme_id = match['scheme_id']
                scheme_questions = self.questions_data.get(scheme_id, {})
                
                if not scheme_questions.get('questions'):
                    # No questions to verify, keep initial eligibility
                    verified.append({
                        **match,
                        'verification_status': 'no_questions',
                        'verification_score': match['score']
                    })
                    continue
                
                # Score based on answer availability
                questions = scheme_questions.get('questions', [])
                answerable_count = len([q for q in questions 
                                       if self._can_answer_question(q, self.user_profile)])
                
                if questions:
                    answer_score = answerable_count / len(questions)
                    final_score = (match['score'] + answer_score) / 2
                    
                    verified.append({
                        **match,
                        'verification_status': 'verified',
                        'answerable_questions': answerable_count,
                        'total_questions': len(questions),
                        'answer_score': answer_score,
                        'verification_score': final_score
                    })
            
            # Sort by verification score
            verified.sort(key=lambda x: x.get('verification_score', 0), reverse=True)
            
            logger.info(f"Verified {len(verified)} schemes")
            self.results['verified_matches'] = [
                {
                    'scheme_name': v['scheme_name'],
                    'verification_score': v.get('verification_score', 0),
                    'status': v.get('verification_status')
                }
                for v in verified
            ]
            
            return verified
        
        except Exception as e:
            logger.error(f"Error verifying with questions: {e}")
            self.results['errors'].append(str(e))
            return matching_schemes
    
    def _can_answer_question(self, question: Dict[str, Any], 
                            profile: Dict[str, Any]) -> bool:
        """
        Check if user profile contains required information to answer question.
        
        Args:
            question: Question data
            profile: User profile
        
        Returns:
            True if question can be answered, False otherwise
        """
        question_text = question.get('question_text', '').lower()
        
        # Map common question patterns to profile fields
        patterns = {
            'age': ['age', 'years old'],
            'gender': ['gender', 'sex', 'male', 'female'],
            'state': ['state', 'location', 'resident'],
            'income': ['income', 'salary', 'earning'],
            'occupation': ['occupation', 'job', 'profession'],
            'education': ['education', 'qualified', 'degree'],
            'caste': ['caste', 'sc', 'st', 'obc'],
            'religion': ['religion', 'faith'],
            'family': ['family', 'member', 'dependent'],
            'disability': ['disability', 'disable', 'differently'],
            'student': ['student', 'studying', 'education'],
        }
        
        for field, keywords in patterns.items():
            if any(keyword in question_text for keyword in keywords):
                return field in profile or profile.get(field) is not None
        
        return True  # Assume answerable if no specific pattern matched
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive report of workflow results."""
        logger.info("Generating report...")
        
        report = {
            **self.results,
            'summary': {
                'total_schemes_analyzed': len(self.schemes_data),
                'matching_schemes_found': len(self.results['matching_schemes']),
                'verified_matches': len(self.results['verified_matches']),
                'workflow_status': 'success' if not self.results['errors'] else 'partial_success',
                'error_count': len(self.results['errors'])
            }
        }
        
        return report
    
    def save_results(self, output_file: str = 'workflow_results.json') -> bool:
        """Save workflow results to file."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            return False
    
    def run_full_workflow(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute complete eligibility determination workflow.
        
        Args:
            user_profile: User profile dictionary
        
        Returns:
            Workflow results including matching schemes and verification status.
        """
        logger.info("=" * 60)
        logger.info("STARTING ELIGIBILITY WORKFLOW")
        logger.info("=" * 60)
        
        # Step 1: Load data
        if not self.load_data():
            logger.error("Failed to load data")
            return self.results
        
        # Step 2: Load user profile
        if not self.load_user_profile(user_profile):
            logger.error("Failed to load user profile")
            return self.results
        
        # Step 3: Find matching schemes
        matches = self.determine_matching_schemes()
        if not matches:
            logger.warning("No matching schemes found")
            self.results['matches_warning'] = "No schemes matching the provided profile"
            return self.results
        
        # Step 4: Verify with Q&A
        verified = self.verify_with_questions(matches)
        
        # Step 5: Generate report
        report = self.generate_report()
        
        logger.info("=" * 60)
        logger.info("WORKFLOW COMPLETED")
        logger.info(f"Results: {len(verified)} verified matches out of {len(matches)} candidates")
        logger.info("=" * 60)
        
        return report


def main():
    """Example workflow execution."""
    # Create orchestrator
    orchestrator = WorkflowOrchestrator()
    
    # Example user profile (for testing)
    sample_profile = {
        'age': 28,
        'gender': 'Female',
        'state': 'Karnataka',
        'annual_income': 150000,
        'education': 'Bachelor',
        'occupation': 'Student',
        'is_student': True,
        'is_disabled': False
    }
    
    # Run workflow
    results = orchestrator.run_full_workflow(sample_profile)
    
    # Save results
    orchestrator.save_results()
    
    # Print summary
    print("\n" + "=" * 60)
    print("WORKFLOW SUMMARY")
    print("=" * 60)
    print(f"Total Schemes Analyzed: {results['summary']['total_schemes_analyzed']}")
    print(f"Matching Schemes Found: {results['summary']['matching_schemes_found']}")
    print(f"Verified Matches: {results['summary']['verified_matches']}")
    print(f"Status: {results['summary']['workflow_status']}")
    
    if results['verified_matches']:
        print("\nTop Matching Schemes:")
        for i, match in enumerate(results['verified_matches'][:5], 1):
            print(f"  {i}. {match['scheme_name']} "
                  f"(Score: {match['verification_score']:.2f})")
    
    if results['errors']:
        print(f"\nErrors Encountered ({len(results['errors'])}):")
        for error in results['errors'][:3]:
            print(f"  - {error}")


if __name__ == '__main__':
    main()
