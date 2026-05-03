import asyncio
import json
from google import genai
from google.genai import types

# Define the "Mental Models" for the Engine
INTENT_SCHEMA = {
    "poverty_support": "DBT, BPL, Ration, or direct financial aid for poor.",
    "manual_labour": "MGNREGA, e-Shram, Artisan, Weaver, Street Vendor.",
    "professional_growth": "Upskilling, Startup loans, Higher education for graduates.",
    "farming": "Agriculture, Land, Cattle, Seed subsidies.",
    "merit_scholarship": "Score-based education aid, non-poverty linked.",
    "disability_support": "Specifically for PwD (Divyangjan)."
}

SYSTEM_PROMPT = f"""
For the given Indian Govt Scheme, pick the SINGLE most accurate 'intent_category' from this list:
{json.dumps(INTENT_SCHEMA, indent=2)}

Return ONLY JSON: {{"scheme_id": "...", "intent_category": "..."}}
"""

async def tag_intent(client, scheme_id, name, desc):
    prompt = f"Scheme: {name}\nDescription: {desc}"
    try:
        response = await client.aio.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json"
            )
        )
        return scheme_id, json.loads(response.text)['intent_category']
    except:
        return scheme_id, "general"

# Logic to run this across your batch and save to a new 'schemes_with_intent.json'