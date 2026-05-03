"""
YojanaMitra — Gemini Question Generator
=========================================
Reads every scheme from all_schemes_export.json and uses Gemini
to generate eligibility questions in the EXACT same format as
myscheme.gov.in's Check Eligibility feature:

  { "key": "Age", "title": "Does your age lie between 18-70?",
    "positive": "Yes", "negative": "No", "required": true }

This matches the output of the Notte function you already tested.

USAGE:
    pip install google-generativeai tqdm
    set GEMINI_API_KEY=your_key         (Windows)
    export GEMINI_API_KEY=your_key      (Mac/Linux)

    python generate_eligibility_questions.py
    python generate_eligibility_questions.py --start 0 --end 500
    python generate_eligibility_questions.py --resume   (continue interrupted run)

OUTPUT:
    all_questions_by_scheme.json        — { scheme_id: [questions] } lookup
    schemes_with_questions.json         — full merged output (use this in app)
    question_gen_progress.json          — checkpoint for resume
    question_gen_failed.json            — schemes that failed after retries
"""

import os, sys, json, time, re, argparse, logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

try:
    import google.generativeai as genai
    from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
    print("ERROR: Run: pip install google-generativeai")
    sys.exit(1)

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("question_gen")

# ─── CONFIG ──────────────────────────────────────────────────────────────────
INPUT_FILE       = "all_schemes_export.json"
OUTPUT_QUESTIONS = "all_questions_by_scheme.json"   # { scheme_id: [questions] }
OUTPUT_MERGED    = "schemes_with_questions.json"    # full schemes + eligibilityQuestions
PROGRESS_FILE    = "question_gen_progress.json"
FAILED_FILE      = "question_gen_failed.json"
MODEL_NAME       = "gemini-flash-latest"
BATCH_SIZE       = 1      # 1 scheme per call (questions need per-scheme focus)
WORKERS          = 3      # parallel Gemini calls
DELAY_BETWEEN    = 1.0    # seconds between calls per worker
RETRY_LIMIT      = 3
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_INSTRUCTION = """You are an expert at converting Indian government scheme eligibility 
criteria into structured yes/no questions — exactly like the Check Eligibility feature on 
myscheme.gov.in. You output ONLY valid JSON arrays. No markdown, no prose, no explanation."""

PROMPT_TEMPLATE = """Generate eligibility questions for this Indian government scheme.

SCHEME NAME: {name}
CATEGORY: {category}
ELIGIBILITY TEXT: {eligibility}
DESCRIPTION: {description}
EXCLUSIONS: {exclusions}
MIN AGE: {min_age}
MAX AGE: {max_age}
MAX INCOME: {max_income}
ALLOWED GENDERS: {allowed_genders}
ALLOWED CASTES: {allowed_castes}
ALLOWED STATES: {allowed_states}
ALLOWED OCCUPATIONS: {allowed_occupations}
DISABILITY REQUIREMENT: {disability_requirement}
RESIDENCE REQUIREMENT: {residence_requirement}

YOUR TASK:
Convert the eligibility criteria into a list of YES/NO questions, exactly like the 
"Check Eligibility" button on myscheme.gov.in does.

RULES:
1. Each condition becomes ONE question
2. Questions must be answerable with Yes or No
3. Order: most important/disqualifying conditions FIRST (citizenship, age, income, then specifics)
4. Do NOT create duplicate or redundant questions
5. Keep question titles natural and concise (like a real government portal would phrase them)
6. The "key" field must be a camelCase identifier (e.g. "Age", "AnnualIncome", "IsWidow")
7. "required" is true for hard eligibility criteria, false for optional/preference criteria
8. Generate between 2 and 12 questions — no more, no less
9. If min_age and max_age both exist, combine into ONE age range question
10. If allowed_genders is only one gender, make a gender question

OUTPUT FORMAT — return ONLY this JSON array, nothing else:
[
  {{
    "key": "CamelCaseKey",
    "title": "Natural question text ending with ?",
    "positive": "Yes",
    "negative": "No",
    "required": true
  }}
]

EXAMPLES of good questions:
  {{"key": "Age", "title": "Does your age lie between 18 and 70 years?", "positive": "Yes", "negative": "No", "required": true}}
  {{"key": "AadharLinkedSavingsAccount", "title": "Do you have an Aadhaar linked bank or post office savings account?", "positive": "Yes", "negative": "No", "required": true}}
  {{"key": "AnnualIncome", "title": "Is your annual family income below ₹1,00,000?", "positive": "Yes", "negative": "No", "required": true}}
  {{"key": "IsCitizen", "title": "Are you a citizen of India?", "positive": "Yes", "negative": "No", "required": true}}
  {{"key": "IsDisabled", "title": "Do you have a disability of 40% or more?", "positive": "Yes", "negative": "No", "required": true}}
  {{"key": "ResidenceState", "title": "Are you a resident of Karnataka?", "positive": "Yes", "negative": "No", "required": true}}
  {{"key": "Caste", "title": "Do you belong to SC/ST/OBC category?", "positive": "Yes", "negative": "No", "required": true}}
  {{"key": "IsWidow", "title": "Are you a widow?", "positive": "Yes", "negative": "No", "required": true}}
  {{"key": "HasBankAccount", "title": "Do you have an active bank account?", "positive": "Yes", "negative": "No", "required": true}}

Return ONLY the JSON array. No markdown. No explanation."""


# ─── THREAD-SAFE WRITE LOCK ───────────────────────────────────────────────────
_write_lock = threading.Lock()

def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"done": {}, "failed": {}}

def save_progress(progress):
    with _write_lock:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

def write_outputs(schemes, progress):
    """Write all_questions_by_scheme.json and schemes_with_questions.json."""
    questions_map = progress["done"]  # { str(scheme_id): [questions] }

    # all_questions_by_scheme.json
    with _write_lock:
        with open(OUTPUT_QUESTIONS, "w", encoding="utf-8") as f:
            json.dump(questions_map, f, ensure_ascii=False, indent=2)

    # schemes_with_questions.json
    merged = []
    for scheme in schemes:
        sid = str(scheme["id"])
        questions = questions_map.get(sid, [])
        merged.append({**scheme, "eligibilityQuestions": questions})

    with _write_lock:
        with open(OUTPUT_MERGED, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

    # question_gen_failed.json
    failed_schemes = [
        {"id": sid, "error": err}
        for sid, err in progress["failed"].items()
    ]
    with _write_lock:
        with open(FAILED_FILE, "w", encoding="utf-8") as f:
            json.dump(failed_schemes, f, ensure_ascii=False, indent=2)


def clean_json_response(text: str) -> str:
    """Strip markdown fences if Gemini wraps in ```json ... ```."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def generate_questions_for_scheme(scheme, model) -> list:
    """Call Gemini and return list of question dicts."""
    prompt = PROMPT_TEMPLATE.format(
        name=scheme.get("name", ""),
        category=scheme.get("category", ""),
        eligibility=scheme.get("eligibility", "") or "",
        description=scheme.get("description", "") or "",
        exclusions=scheme.get("exclusions", "") or "",
        min_age=scheme.get("min_age") or "Not specified",
        max_age=scheme.get("max_age") or "Not specified",
        max_income=scheme.get("max_income") or "Not specified",
        allowed_genders=scheme.get("allowed_genders") or "All",
        allowed_castes=scheme.get("allowed_castes") or "All",
        allowed_states=scheme.get("allowed_states") or "All India",
        allowed_occupations=scheme.get("allowed_occupations") or "All",
        disability_requirement=scheme.get("disability_requirement") or "None",
        residence_requirement=scheme.get("residence_requirement") or "None",
    )

    for attempt in range(1, RETRY_LIMIT + 2):
        try:
            response = model.generate_content(prompt)
            raw = response.text
            cleaned = clean_json_response(raw)
            questions = json.loads(cleaned)

            # Validate shape
            if not isinstance(questions, list):
                raise ValueError("Response is not a list")
            for q in questions:
                if not all(k in q for k in ("key", "title", "positive", "negative")):
                    raise ValueError(f"Question missing fields: {q}")
                if "required" not in q:
                    q["required"] = True  # default

            return questions

        except ResourceExhausted:
            wait = 30 * attempt
            log.warning(f"Rate limited — waiting {wait}s (attempt {attempt})")
            time.sleep(wait)
        except ServiceUnavailable:
            time.sleep(10 * attempt)
        except json.JSONDecodeError as e:
            log.warning(f"JSON parse error for scheme {scheme['id']}: {e}")
            if attempt > RETRY_LIMIT:
                raise
            time.sleep(3)
        except Exception as e:
            log.warning(f"Error for scheme {scheme['id']} attempt {attempt}: {e}")
            if attempt > RETRY_LIMIT:
                raise
            time.sleep(3 * attempt)

    raise RuntimeError("Max retries exceeded")


def process_scheme(scheme, model, progress, pbar=None):
    """Process one scheme — generate questions and update progress."""
    sid = str(scheme["id"])

    try:
        questions = generate_questions_for_scheme(scheme, model)
        with _write_lock:
            progress["done"][sid] = questions
            progress["failed"].pop(sid, None)

        if pbar:
            pbar.set_postfix({"last": scheme["name"][:30], "q": len(questions)})
            pbar.update(1)
        else:
            log.info(f"  ✓ [{sid}] {scheme['name'][:50]} — {len(questions)} questions")

        time.sleep(DELAY_BETWEEN)
        return True

    except Exception as e:
        err = str(e)[:200]
        with _write_lock:
            progress["failed"][sid] = err
        if pbar:
            pbar.update(1)
        else:
            log.error(f"  ✗ [{sid}] {scheme['name'][:50]} — {err}")
        return False


def run(start=0, end=None, workers=WORKERS, resume=True):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        log.error("Set GEMINI_API_KEY environment variable first.")
        sys.exit(1)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    # Load schemes
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        all_schemes = json.load(f)

    slice_end = end or len(all_schemes)
    schemes = all_schemes[start:slice_end]
    log.info(f"Loaded {len(schemes)} schemes (index {start}–{slice_end})")

    # Load or reset progress
    progress = load_progress() if resume else {"done": {}, "failed": {}}
    already_done = set(progress["done"].keys())
    todo = [s for s in schemes if str(s["id"]) not in already_done]

    log.info(f"Already done: {len(already_done)} | To process: {len(todo)}")

    if not todo:
        log.info("Nothing to do — all schemes already processed!")
        write_outputs(all_schemes, progress)
        return

    # Process
    pbar = tqdm(total=len(todo), desc="Generating questions") if HAS_TQDM else None

    if workers == 1:
        # Single-threaded (safer for rate limits)
        for scheme in todo:
            process_scheme(scheme, model, progress, pbar)
            # Save + write every 10 schemes
            if int(scheme["id"]) % 10 == 0:
                save_progress(progress)
                write_outputs(all_schemes, progress)
    else:
        # Multi-threaded
        # Each thread gets its own model instance to avoid sharing
        def make_model():
            return genai.GenerativeModel(
                model_name=MODEL_NAME,
                system_instruction=SYSTEM_INSTRUCTION,
            )

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(process_scheme, s, make_model(), progress, pbar): s
                for s in todo
            }
            completed = 0
            for future in as_completed(futures):
                future.result()  # surface exceptions
                completed += 1
                if completed % 10 == 0:
                    save_progress(progress)
                    write_outputs(all_schemes, progress)

    if pbar:
        pbar.close()

    # Final save
    save_progress(progress)
    write_outputs(all_schemes, progress)

    # Summary
    done_count   = len(progress["done"])
    failed_count = len(progress["failed"])
    total_q      = sum(len(v) for v in progress["done"].values())

    log.info(f"""
╔══════════════════════════════════════════════╗
║  DONE!
║  ✓ Schemes with questions : {done_count}
║  ✗ Failed                 : {failed_count}
║  ∑ Total questions        : {total_q}
║  Avg per scheme           : {total_q / max(done_count, 1):.1f}
║
║  Output files:
║    {OUTPUT_MERGED}   ← use in Yojana Mitra
║    {OUTPUT_QUESTIONS}  ← lookup table
║    {FAILED_FILE}     ← retry these
╚══════════════════════════════════════════════╝
""")


def main():
    parser = argparse.ArgumentParser(description="YojanaMitra — Gemini Question Generator")
    parser.add_argument("--input",   default=INPUT_FILE,  help="Input schemes JSON file")
    parser.add_argument("--start",   type=int, default=0, help="Start index")
    parser.add_argument("--end",     type=int, default=None, help="End index")
    parser.add_argument("--workers", type=int, default=WORKERS, help="Parallel workers (1 = safe)")
    parser.add_argument("--model",   default=MODEL_NAME,  help="Gemini model name")
    parser.add_argument("--delay",   type=float, default=DELAY_BETWEEN, help="Delay between calls")
    parser.add_argument("--resume",  action="store_true", default=True, help="Resume from checkpoint")
    parser.add_argument("--fresh",   action="store_true", help="Start fresh (ignore checkpoint)")
    args = parser.parse_args()

    global INPUT_FILE, MODEL_NAME, DELAY_BETWEEN
    INPUT_FILE     = args.input
    MODEL_NAME     = args.model
    DELAY_BETWEEN  = args.delay

    run(
        start=args.start,
        end=args.end,
        workers=args.workers,
        resume=(args.resume and not args.fresh),
    )


if __name__ == "__main__":
    main()
