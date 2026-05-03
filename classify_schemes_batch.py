"""
classify_schemes_batch.py
Optimized Gemini pipeline for mass condition classification.
- Batching: 10 schemes per request
- Parallelism: 5 concurrent workers
- Retries and incremental saving
"""
import os, json, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import google.generativeai as genai
from tqdm import tqdm
from dotenv import load_dotenv

# --- CONFIGURATION ---
BATCH_SIZE = 10
MAX_WORKERS = 5  # Increased for faster throughput
MODEL_NAME = 'gemini-flash-latest'
INPUT_CONDITIONS = 'all_conditions.json'
INPUT_SCHEMES = 'all_schemes_fixed.json'
OUTPUT_FILE = 'all_conditions_classified.json'
# ---------------------

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)
model = genai.GenerativeModel(MODEL_NAME)

LOCK = threading.Lock()

PROMPT_TEMPLATE = """
Classify the eligibility conditions for the following {batch_size} schemes into CORE, PROOF, or SUPPORTING.

### SCHEMES DATA:
{schemes_context}

### STRICT RULES:
1. CORE (STRICT DISQUALIFIER): Mark as CORE if it defines WHO the scheme is for (age, gender, income, caste, state, occupation, category). If this fails, the user is NOT_ELIGIBLE.
2. PROOF (DOCUMENT / VERIFICATION): Mark as PROOF if it involves documents (Aadhaar, bank account, certificates, ID cards). If missing, user is POSSIBLY_ELIGIBLE.
3. SUPPORTING (DEFAULT SAFE CATEGORY): Mark as SUPPORTING if it is NOT a strict disqualifier (achievement certificates, timing, deadlines, self-declarations like health/willingness, vague wording). If missing/failed, user MUST NOT be rejected.

Return a JSON object with a "results" key containing a list of classification results for each scheme ID.
JSON FORMAT:
{{
  "results": [
    {{
      "scheme_id": "123",
      "classified_conditions": [
        {{
          "field": "...",
          "operator": "...",
          "value": "...",
          "classification": "core | proof | supporting",
          "reason": "..."
        }}
      ]
    }}
  ]
}}
"""

def load_data():
    with open(INPUT_CONDITIONS, 'r', encoding='utf-8') as f:
        conditions_data = json.load(f)["schemes"]
    with open(INPUT_SCHEMES, 'r', encoding='utf-8') as f:
        schemes_raw = json.load(f)
        schemes_map = {str(s['id']): s for s in schemes_raw}
    return conditions_data, schemes_map

def process_batch(batch_ids, conditions_data, schemes_map):
    schemes_context = []
    for sid in batch_ids:
        info = schemes_map.get(sid, {})
        conds = conditions_data[sid].get("conditions", [])
        schemes_context.append({
            "id": sid,
            "name": info.get('name'),
            "description": info.get('description', '')[:500], # Trucate for token limit
            "target": info.get('target_group_category', ''),
            "conditions": conds
        })

    prompt = PROMPT_TEMPLATE.format(
        batch_size=len(batch_ids),
        schemes_context=json.dumps(schemes_context, indent=2)
    )

    retries = 2
    for attempt in range(retries + 1):
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                )
            )
            data = json.loads(response.text)
            return data.get("results", [])
        except Exception as e:
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            print(f"Error processing batch {batch_ids[0]}...: {e}")
            return []

def main():
    conditions_data, schemes_map = load_data()
    
    results = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            results = json.load(f)

    processed_ids = set(results.keys())
    remaining_ids = [sid for sid in conditions_data.keys() if sid not in processed_ids]
    
    print(f"Total: {len(conditions_data)} | Processed: {len(processed_ids)} | Remaining: {len(remaining_ids)}")
    
    if not remaining_ids:
        print("Done!")
        return

    # Split into batches
    batches = [remaining_ids[i:i + BATCH_SIZE] for i in range(0, len(remaining_ids), BATCH_SIZE)]
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_batch = {executor.submit(process_batch, b, conditions_data, schemes_map): b for b in batches}
        
        with tqdm(total=len(batches), desc="Processing Batches") as pbar:
            for future in as_completed(future_to_batch):
                batch_results = future.result()
                
                with LOCK:
                    for item in batch_results:
                        sid = str(item.get("scheme_id"))
                        results[sid] = item
                    
                    # Save progress every batch
                    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2)
                
                pbar.update(1)
                time.sleep(0.5) # Gentle rate limiting

if __name__ == "__main__":
    main()
