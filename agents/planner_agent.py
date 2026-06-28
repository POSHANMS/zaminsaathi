import os
import sys
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List
import dotenv

dotenv.load_dotenv()

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

MODEL = "gemini-2.5-flash-lite"

def _get_client():
    return genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# =====================================================================
# 1. Pydantic Schema
# =====================================================================
class PlannerOutput(BaseModel):
    status: str
    summary: str
    action_steps: List[str]
    offices_to_visit: List[str]
    portals_to_use: List[str]
    documents_to_carry: List[str]
    legal_disclaimer: str

# =====================================================================
# 2. Main Planner Function
# =====================================================================
def generate_plan(detector_result: dict) -> dict:
    """Generates an actionable next-steps plan based on detected discrepancies."""
    prompt = f"""You are the Action Planner Agent for ZaminSaathi.

Generate a concrete, actionable next-steps plan for a rural Karnataka family based on the discrepancy detection results below.

DETECTION RESULT:
{json.dumps(detector_result, indent=2)}

RULES:
- If cross_check_passed is true (no discrepancies): status = "clear", give reassuring message and simple maintenance tips
- If cross_check_passed is false (discrepancies found): status = "action_required" with:
  - Specific government office to visit (Tahsildar office, local revenue office)
  - Karnataka government portals (Bhoomi: https://landrecords.karnataka.gov.in/ for RTC/mutation issues)
  - Documents to carry (originals + photocopies)
  - Simple script of what to tell the officer
- legal_disclaimer MUST be exactly: "This is guidance only. Consult a qualified lawyer before taking legal action."

Return ONLY a JSON object:
{{
  "status": "clear or action_required",
  "summary": "One paragraph plain English summary for a rural family",
  "action_steps": ["1. First step", "2. Second step", "..."],
  "offices_to_visit": ["Office name — what to do and say there"],
  "portals_to_use": ["Portal name (https://url) — what to do there"],
  "documents_to_carry": ["Document name"],
  "legal_disclaimer": "This is guidance only. Consult a qualified lawyer before taking legal action."
}}"""

    import time
    client = _get_client()
    response = None
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            break
        except Exception as e:
            err_msg = str(e)
            is_transient = any(term in err_msg.upper() for term in ["503", "429", "UNAVAILABLE", "EXHAUSTED", "DEMAND"])
            if is_transient and attempt < max_attempts - 1:
                wait_time = (attempt + 1) * 2
                print(f"[Model Busy] planner_agent received transient error: {err_msg[:120]}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise e
    text = response.text.strip()
    parsed = json.loads(text)
    return PlannerOutput.model_validate(parsed).model_dump()


# =====================================================================
# 3. Standalone test
# =====================================================================
if __name__ == "__main__":
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    sample = {
        "document_id": "RTC-KA-HAS-2024-001",
        "permission_granted": True,
        "discrepancies_found": [{
            "field_name": "survey_number",
            "expected_value": "142/3",
            "actual_value": "142/4",
            "severity": "HIGH",
            "plain_english_explanation": "Survey number mismatch between RTC and Mutation documents."
        }],
        "cross_check_passed": False
    }
    result = generate_plan(sample)
    print(json.dumps(result, indent=2, ensure_ascii=False))
