
import json
import os
from datetime import datetime

path = 'all_conditions.json'
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # If already in new format, skip
    if 'schemes' in data and 'version' in data:
        print("Already in new format. Skipping migration.")
    else:
        new_data = {
            "version": "1.0",
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "schemes": data
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=2)
        print(f"Migrated {len(data)} schemes to new format.")
else:
    # Create empty as requested
    new_data = {
        "version": "1.0",
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "schemes": {}
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, indent=2)
    print("Created new empty all_conditions.json.")
