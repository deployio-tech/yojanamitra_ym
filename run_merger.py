import sys
sys.path.insert(0, 'C:/yojanamitra_complete')
from app.engine.concept_merger import merge_concepts

# Run with lower threshold to catch more
result = merge_concepts(dry_run=True, threshold=0.6)

print('\n=== MERGE RESULT (threshold=0.6) ===')
print('Status:', result.get('status'))
print('Merge groups:', len(result.get('merges', [])))

if result.get('merges'):
    print('\n=== MERGE SUGGESTIONS ===')
    for m in result['merges']:
        canonical = m['canonical']
        merged = m['merged']
        print('Keep:', canonical)
        print('  Merge:', merged)