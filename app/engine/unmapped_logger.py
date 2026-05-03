"""
Unmapped field logger for safety detection.
Logs fields that are not mapped in field_to_concept for batch review.
Each field is a separate entry for easy Gemini processing.
"""
import json
import os
from datetime import datetime

LOG_FILE = 'unmapped_fields.log'


def log_unmapped_fields(fields, scheme_id=None):
    """
    Log unmapped fields to file for batch review.
    Creates ONE entry per field (not batch) for Gemini compatibility.

    Args:
        fields: List of unmapped field names (will be deduplicated)
        scheme_id: Optional scheme ID for tracking
    
    Example:
        log_unmapped_fields(['has_goat_farming_license', 'is_fisherman'], scheme_id=42)
    
    Output format (one entry per field):
        [
          {"field": "has_goat_farming_license", "scheme_id": 42, "timestamp": "..."},
          {"field": "is_fisherman", "scheme_id": 42, "timestamp": "..."}
        ]
    """
    if not fields:
        return
    
    # Deduplicate fields
    unique_fields = list(set(fields))
    
    # Read existing logs
    existing = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            existing = []
    
    # Add ONE entry per field (not one entry per batch)
    timestamp = datetime.now().isoformat()
    for field in unique_fields:
        entry = {
            'field': field,
            'scheme_id': scheme_id,
            'timestamp': timestamp
        }
        existing.append(entry)
    
    # Write back
    with open(LOG_FILE, 'w') as f:
        json.dump(existing, f, indent=2)
    
    print(f"[UNMAPPED] Logged {len(unique_fields)} fields for scheme {scheme_id}")


def get_unmapped_summary():
    """
    Get summary of all unmapped fields for review.
    
    Returns:
        dict with total_entries, unique_fields, entries
    """
    if not os.path.exists(LOG_FILE):
        return {
            'total_entries': 0,
            'unique_fields': [],
            'entries': []
        }
    
    try:
        with open(LOG_FILE, 'r') as f:
            logs = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {
            'total_entries': 0,
            'unique_fields': [],
            'entries': []
        }
    
    # Aggregate unique fields
    all_fields = set()
    for entry in logs:
        all_fields.add(entry.get('field', ''))
    
    return {
        'total_entries': len(logs),
        'unique_fields': sorted(all_fields),
        'entries': logs  # Full entries for Gemini processing
    }


def get_unmapped_fields_for_gemini(batch_size=50, offset=0):
    """
    Get unmapped fields in batches for Gemini processing.
    
    Args:
        batch_size: Number of fields per batch
        offset: Starting index
    
    Returns:
        List of field entries for Gemini
    """
    summary = get_unmapped_summary()
    entries = summary.get('entries', [])
    return entries[offset:offset + batch_size]


def clear_unmapped_logs():
    """Clear all unmapped field logs (for testing/reset)."""
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    print("[UNMAPPED] Logs cleared")


if __name__ == "__main__":
    # Test the new format
    print("Testing unmapped logger (new format)...")
    log_unmapped_fields(['test_field_1', 'test_field_2', 'test_field_3'], scheme_id=999)
    
    # Show the format
    summary = get_unmapped_summary()
    print(f"\nTotal entries: {summary['total_entries']}")
    print(f"Unique fields: {summary['unique_fields']}")
    print(f"\nFirst 2 entries:")
    for entry in summary['entries'][:2]:
        print(f"  {entry}")
    
    clear_unmapped_logs()
    print("\nTest complete")