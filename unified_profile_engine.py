"""
UNIFIED PROFILE ENGINE
=======================
Solves the myScheme Problem: "No cross-scheme intelligence"

What myScheme Does (Current Problem):
- User applies to Scheme A → answers Q1, Q2, Q3
- User applies to Scheme B → answers Q1, Q2, Q3 AGAIN
- No profile continuity
- No answer reuse
- Friction: Users must repeat same info

What Unified Profile Does (Innovation):
- User builds UNIFIED PROFILE once (age, income, caste, etc.)
- User applies to any scheme → auto-fill from unified profile
- Only ask NEW questions not in their profile
- Recommendation: "You might also qualify for Schemes X, Y, Z"
- Cross-scheme optimization: Which documents cover multiple schemes
- Smart batching: Ask one question that helps multiple schemes

FEATURES:
1. ProfileNormalizer: Standardize all answer formats
2. UnifiedProfileBuilder: Accumulate answers across sessions
3. SmartQuestionReuse: Avoid asking same question twice
4. SchemeRecommender: Suggest best schemes for their profile
5. DocumentOptimizer: Show which documents unlock multiple schemes
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UnifiedProfileEngine")


@dataclass
class ProfileAnswer:
    """Single answer in the unified profile."""
    field: str
    value: any
    source: str  # 'user_input', 'inferred', 'document', 'third_party'
    confidence: float = 1.0  # 0-1, how certain we are
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    schemes_used_in: List[str] = field(default_factory=list)  # Which schemes used this answer
    

@dataclass
class UnifiedProfile:
    """User's unified profile across all schemes."""
    user_id: str
    answers: Dict[str, ProfileAnswer] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    total_schemes_applied: int = 0
    matched_schemes: List[str] = field(default_factory=list)
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'answers': {k: asdict(v) for k, v in self.answers.items()},
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'total_schemes_applied': self.total_schemes_applied,
            'matched_schemes': self.matched_schemes
        }


class ProfileNormalizer:
    """Standardize answer formats across all possible variations."""
    
    # Standard field types and their normalizers
    NORMALIZERS = {
        'age': lambda x: int(x) if isinstance(x, (int, str)) and str(x).isdigit() else None,
        'annual_income': lambda x: int(float(str(x).replace(',', ''))) if x else None,
        'gender': lambda x: x.lower().strip() if x else None,
        'caste': lambda x: x.upper().strip() if x else None,
        'state': lambda x: x.upper().strip() if x else None,
        'is_student': lambda x: x.lower() in ['yes', 'true', '1', True] if x else None,
        'is_farmer': lambda x: x.lower() in ['yes', 'true', '1', True] if x else None,
        'is_disabled': lambda x: x.lower() in ['yes', 'true', '1', True] if x else None,
        'is_widow': lambda x: x.lower() in ['yes', 'true', '1', True] if x else None,
        'is_ews': lambda x: x.lower() in ['yes', 'true', '1', True] if x else None,
    }
    
    @staticmethod
    def normalize(field: str, value: any) -> Tuple[any, bool]:
        """
        Normalize a field value.
        
        Returns: (normalized_value, is_valid)
        """
        if not value:
            return None, False
        
        normalizer = ProfileNormalizer.NORMALIZERS.get(field, lambda x: x)
        
        try:
            normalized = normalizer(value)
            return normalized, normalized is not None
        except Exception as e:
            logger.warning(f"Failed to normalize {field}={value}: {e}")
            return value, False


class UnifiedProfileBuilder:
    """Build and maintain unified profiles across schemes."""
    
    def __init__(self, schemes_data: List[Dict]):
        """
        Initialize with scheme data.
        
        Args:
            schemes_data: List of schemes with questions
        """
        self.schemes_data = {s['name']: s for s in schemes_data}
        self.profiles = {}  # user_id → UnifiedProfile
        self.normalizer = ProfileNormalizer()
        self.field_to_schemes = self._build_field_scheme_map()
    
    def _build_field_scheme_map(self) -> Dict[str, Set[str]]:
        """Build mapping of field → schemes that use it."""
        mapping = defaultdict(set)
        
        for scheme_name, scheme in self.schemes_data.items():
            for q in scheme.get('questions', []):
                field = q.get('normalized_field')
                if field:
                    mapping[field].add(scheme_name)
        
        return dict(mapping)
    
    def create_profile(self, user_id: str) -> UnifiedProfile:
        """Create a new unified profile for a user."""
        if user_id in self.profiles:
            logger.warning(f"Profile already exists for user {user_id}")
            return self.profiles[user_id]
        
        profile = UnifiedProfile(user_id=user_id)
        self.profiles[user_id] = profile
        logger.info(f"Created unified profile for user {user_id}")
        
        return profile
    
    def add_answer(
        self,
        user_id: str,
        field: str,
        value: any,
        source: str = 'user_input',
        schemes_used_in: List[str] = None
    ) -> bool:
        """
        Add an answer to the unified profile.
        
        Returns: True if successful
        """
        if user_id not in self.profiles:
            self.create_profile(user_id)
        
        normalized_value, is_valid = self.normalizer.normalize(field, value)
        
        if not is_valid:
            logger.warning(f"Could not normalize {field}={value}")
        
        profile = self.profiles[user_id]
        
        # Check if we already have an answer for this field
        if field in profile.answers:
            old_answer = profile.answers[field]
            logger.info(f"Updating answer for {field}: {old_answer.value} → {normalized_value}")
        
        profile.answers[field] = ProfileAnswer(
            field=field,
            value=normalized_value,
            source=source,
            schemes_used_in=schemes_used_in or []
        )
        
        profile.updated_at = datetime.now().isoformat()
        
        return True
    
    def add_answers_batch(
        self,
        user_id: str,
        answers: Dict[str, any],
        source: str = 'user_input'
    ) -> Dict[str, bool]:
        """
        Add multiple answers at once.
        
        Args:
            user_id: User ID
            answers: Dict of field → value
            source: Source of answers
        
        Returns: Dict of field → success
        """
        results = {}
        for field, value in answers.items():
            results[field] = self.add_answer(user_id, field, value, source)
        
        logger.info(f"Added {sum(results.values())}/{len(results)} answers for user {user_id}")
        return results
    
    def get_profile(self, user_id: str) -> Optional[UnifiedProfile]:
        """Get a user's unified profile."""
        return self.profiles.get(user_id)
    
    def get_profile_as_dict(self, user_id: str) -> Dict:
        """Get profile as dictionary for API/storage."""
        profile = self.get_profile(user_id)
        if not profile:
            return {}
        
        return profile.to_dict()
    
    def get_profile_completeness(self, user_id: str) -> Dict:
        """
        Get how complete a profile is.
        
        Returns: {
            'total_fields': int,
            'filled_fields': int,
            'completeness_percentage': float,
            'missing_critical_fields': [field_names]
        }
        """
        profile = self.get_profile(user_id)
        if not profile:
            return {}
        
        # Critical fields that schemes often use
        critical_fields = {
            'age', 'gender', 'annual_income', 'caste', 'state', 
            'is_student', 'is_farmer', 'is_disabled'
        }
        
        filled = len(profile.answers)
        total = len(self.field_to_schemes)
        
        filled_critical = {f for f in critical_fields if f in profile.answers}
        missing_critical = critical_fields - filled_critical
        
        return {
            'total_fields': total,
            'filled_fields': filled,
            'completeness_percentage': (filled / total * 100) if total > 0 else 0,
            'critical_fields_filled': len(filled_critical),
            'critical_fields_missing': len(missing_critical),
            'missing_critical_fields': list(missing_critical)
        }


class SmartQuestionReuse:
    """
    Avoid asking the same question twice.
    
    LOGIC:
    1. User already answered "age"? Don't ask again for any scheme
    2. User answered "is_student"? Skip that question in all schemes
    3. Only ask questions user hasn't answered yet
    4. If answer exists in profile but low confidence: ask to verify
    """
    
    def __init__(self, profile_builder: UnifiedProfileBuilder):
        self.profile_builder = profile_builder
    
    def filter_scheme_questions(
        self,
        scheme_name: str,
        user_id: str,
        questions: List[Dict]
    ) -> List[Dict]:
        """
        Filter questions for a scheme based on unified profile.
        
        Returns: Questions to ask (filtered)
        """
        profile = self.profile_builder.get_profile(user_id)
        
        if not profile:
            # No profile yet, ask all questions
            return questions
        
        to_ask = []
        already_answered = set()
        
        for q in questions:
            field = q.get('normalized_field')
            
            if field in profile.answers:
                answer = profile.answers[field]
                
                # If we have high confidence, skip the question
                if answer.confidence >= 0.9:
                    already_answered.add(field)
                    continue
                
                # If confidence is low, ask to verify
                to_ask.append({**q, 'verify': True})
            else:
                to_ask.append(q)
        
        logger.info(
            f"Filtered {len(questions)} questions for {scheme_name}: "
            f"{len(to_ask)} to ask, {len(already_answered)} already answered"
        )
        
        return to_ask
    
    def get_reuse_stats(self, user_id: str, schemes: List[Dict]) -> Dict:
        """
        Get statistics on how many times each question is asked.
        
        Shows opportunities for unified profiles.
        """
        question_frequency = defaultdict(lambda: {'count': 0, 'schemes': []})
        
        for scheme in schemes:
            for q in scheme.get('questions', []):
                field = q.get('normalized_field')
                if field:
                    question_frequency[field]['count'] += 1
                    question_frequency[field]['schemes'].append(scheme['name'])
        
        # Sort by frequency
        sorted_questions = sorted(
            question_frequency.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        
        return {
            'question_reuse_map': dict(sorted_questions),
            'most_repeated_questions': [
                (field, data['count']) for field, data in sorted_questions[:10]
            ],
            'total_opportunities_for_reuse': sum(d['count'] - 1 for d in question_frequency.values() if d['count'] > 1)
        }


class SchemeRecommender:
    """
    Recommend schemes based on unified profile.
    
    LOGIC:
    1. Calculate match score for each scheme: (fields_answer / total_fields) * 100
    2. Rank by eligibility potential
    3. Show "You might qualify for these schemes"
    4. Highlight what's needed to become eligible
    """
    
    def __init__(self, schemes_data: List[Dict], profile_builder: UnifiedProfileBuilder):
        self.schemes_data = schemes_data
        self.profile_builder = profile_builder
    
    def calculate_match_score(self, scheme: Dict, profile: UnifiedProfile) -> float:
        """
        Calculate how well a user's profile matches a scheme's questions.
        
        Returns: 0-100% match
        """
        questions = scheme.get('questions', [])
        if not questions:
            return 0.0
        
        matched = 0
        for q in questions:
            field = q.get('normalized_field')
            if field in profile.answers:
                matched += 1
        
        return (matched / len(questions)) * 100 if questions else 0
    
    def recommend_schemes(
        self,
        user_id: str,
        top_n: int = 5
    ) -> Dict:
        """
        Recommend top schemes for a user.
        
        Returns: {
            'recommended_schemes': [
                {
                    'scheme_name': str,
                    'match_score': float,
                    'matched_questions': int,
                    'total_questions': int,
                    'missing_questions': List[str],
                    'why_recommended': str
                }
            ]
        }
        """
        profile = self.profile_builder.get_profile(user_id)
        
        if not profile:
            logger.warning(f"No profile found for user {user_id}")
            return {}
        
        scores = []
        
        for scheme in self.schemes_data:
            match_score = self.calculate_match_score(scheme, profile)
            
            questions = scheme.get('questions', [])
            matched_q = sum(1 for q in questions if q.get('normalized_field') in profile.answers)
            missing_q = [
                q.get('normalized_field') for q in questions 
                if q.get('normalized_field') not in profile.answers
            ]
            
            scores.append({
                'scheme_name': scheme['name'],
                'match_score': match_score,
                'matched_questions': matched_q,
                'total_questions': len(questions),
                'missing_questions': missing_q,
                'category': scheme.get('category', 'Unknown'),
                'benefits': scheme.get('benefits', '')[:100]  # Short preview
            })
        
        # Sort by match score
        scores.sort(key=lambda x: x['match_score'], reverse=True)
        
        return {
            'user_id': user_id,
            'total_schemes': len(self.schemes_data),
            'recommended_schemes': scores[:top_n],
            'profile_completeness': self.profile_builder.get_profile_completeness(user_id)
        }


class DocumentOptimizer:
    """
    Show which documents cover multiple schemes.
    
    LOGIC:
    If uploading income_certificate covers 50 schemes,
    user should upload it first rather than scheme-by-scheme docs.
    """
    
    def __init__(self, schemes_data: List[Dict]):
        self.schemes_data = schemes_data
        self.document_scheme_map = self._build_document_map()
    
    def _build_document_map(self) -> Dict[str, Set[str]]:
        """
        Build mapping: document_type → schemes that need it.
        """
        mapping = defaultdict(set)
        
        for scheme in self.schemes_data:
            docs = scheme.get('documents_required', '')
            if isinstance(docs, str):
                # Parse document types from text
                doc_types = self._extract_document_types(docs)
                for doc_type in doc_types:
                    mapping[doc_type].add(scheme['name'])
        
        return dict(mapping)
    
    def _extract_document_types(self, doc_text: str) -> Set[str]:
        """Extract canonical document types from text."""
        doc_types = set()
        
        keywords = {
            'aadhaar': ['aadhaar', 'aadhar'],
            'pan': ['pan card', 'pan'],
            'income_certificate': ['income certificate', 'income proof'],
            'caste_certificate': ['caste certificate'],
            'disability_certificate': ['disability certificate', 'udid'],
            'birth_certificate': ['birth certificate'],
            'domicile': ['domicile', 'domicile certificate'],
            'bank_account': ['bank account', 'bank statement'],
        }
        
        text_lower = doc_text.lower()
        
        for doc_type, keywords_list in keywords.items():
            if any(kw in text_lower for kw in keywords_list):
                doc_types.add(doc_type)
        
        return doc_types
    
    def get_optimization_report(self, user_id: str, target_schemes: List[str]) -> Dict:
        """
        Generate document optimization report.
        
        Shows: "Upload these X docs to unlock Y schemes"
        """
        doc_coverage = {}
        
        for doc_type, schemes in self.document_scheme_map.items():
            schemes_in_target = [s for s in schemes if s in set(target_schemes)]
            
            if schemes_in_target:
                doc_coverage[doc_type] = {
                    'schemes_covered': len(schemes_in_target),
                    'schemes': schemes_in_target
                }
        
        # Sort by coverage
        sorted_docs = sorted(
            doc_coverage.items(),
            key=lambda x: x[1]['schemes_covered'],
            reverse=True
        )
        
        return {
            'user_id': user_id,
            'target_schemes': len(target_schemes),
            'document_optimization': dict(sorted_docs),
            'recommendation': f"Upload documents in this order to maximize scheme coverage"
        }


def main():
    """Demo/test the unified profile engine."""
    
    # Load merged schemes
    try:
        with open('all_schemes_with_questions.json', 'r', encoding='utf-8') as f:
            schemes_data = json.load(f)
        logger.info(f"Loaded {len(schemes_data)} schemes")
    except Exception as e:
        logger.error(f"Failed to load schemes: {e}")
        return
    
    # Initialize engines
    profile_builder = UnifiedProfileBuilder(schemes_data)
    recommender = SchemeRecommender(schemes_data, profile_builder)
    question_reuse = SmartQuestionReuse(profile_builder)
    doc_optimizer = DocumentOptimizer(schemes_data)
    
    # Test user
    user_id = "test_user_001"
    
    # Create profile
    profile = profile_builder.create_profile(user_id)
    
    # Add some answers
    answers = {
        'age': 35,
        'gender': 'Male',
        'annual_income': 400000,
        'caste': 'OBC',
        'is_student': False,
        'is_farmer': True,
    }
    
    profile_builder.add_answers_batch(user_id, answers)
    
    # Get recommendations
    recommendations = recommender.recommend_schemes(user_id, top_n=5)
    
    # Get reuse stats
    reuse_stats = question_reuse.get_reuse_stats(user_id, schemes_data)
    
    # Get document optimization
    doc_report = doc_optimizer.get_optimization_report(user_id, [s['name'] for s in schemes_data[:20]])
    
    print("\n" + "="*70)
    print("UNIFIED PROFILE ENGINE - DEMO")
    print("="*70)
    
    print(f"\nProfile Completeness:")
    completeness = profile_builder.get_profile_completeness(user_id)
    print(f"  Filled: {completeness['filled_fields']}/{completeness['total_fields']} fields")
    print(f"  Completeness: {completeness['completeness_percentage']:.1f}%")
    print(f"  Missing Critical: {completeness['missing_critical_fields']}")
    
    print(f"\nTop Recommended Schemes:")
    for i, scheme in enumerate(recommendations['recommended_schemes'][:3], 1):
        print(f"  {i}. {scheme['scheme_name']}")
        print(f"     Match: {scheme['match_score']:.1f}%")
        print(f"     Missing: {len(scheme['missing_questions'])} fields")
    
    print(f"\nQuestion Reuse Opportunities:")
    print(f"  Total Reuse Opportunities: {reuse_stats['total_opportunities_for_reuse']}")
    print(f"  Top 3 Repeated Questions:")
    for field, count in reuse_stats['most_repeated_questions'][:3]:
        print(f"    - {field}: asked {count} times across schemes")
    
    print("\n" + "="*70)


if __name__ == '__main__':
    main()
