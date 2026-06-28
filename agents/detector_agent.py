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

from security.permissions import check_permission
from security.audit_log import log_flag
from mcp_server.server import query_land_record

# =====================================================================
# 1. Pydantic Schema
# =====================================================================
class Discrepancy(BaseModel):
    field_name: str
    expected_value: str
    actual_value: str
    severity: str
    plain_english_explanation: str

class DetectorOutput(BaseModel):
    discrepancies_found: List[Discrepancy]

# =====================================================================
# 2. Main Detector Function
# =====================================================================
def detect_discrepancies(parsed_doc: dict, all_uploaded_docs: List[dict]) -> dict:
    """Cross-checks the parsed document against other docs and the MCP database."""
    document_id = parsed_doc.get("document_id")
    document_type = parsed_doc.get("document_type")

    # Permission check (access control — before agent acts)
    permission_result = check_permission(document_type, "flag")
    if not permission_result["allowed"]:
        return {
            "document_id": document_id,
            "permission_granted": False,
            "discrepancies_found": [],
            "cross_check_passed": False,
            "denial_reason": permission_result["reason"]
        }

    raw_doc = next(
        (d for d in all_uploaded_docs if d.get("document_id") == document_id),
        parsed_doc
    )

    # Query MCP Server (official government land records database)
    db_record = None
    try:
        db_response_str = query_land_record(raw_doc.get("survey_number", ""), raw_doc.get("village", ""))
        db_response = json.loads(db_response_str)
        if db_response.get("status") == "success":
            db_record = db_response.get("record")
    except Exception as e:
        print(f"[Warning] MCP query failed: {e}")

    prompt = f"""You are the Discrepancy Detector Agent for ZaminSaathi.

Cross-check this land document against other uploaded documents and the official government database. Find any mismatches in survey numbers, owner names, or other critical fields.

CURRENT DOCUMENT:
{json.dumps(raw_doc, indent=2)}

ALL UPLOADED DOCUMENTS (for this family):
{json.dumps(all_uploaded_docs, indent=2)}

OFFICIAL GOVERNMENT DATABASE RECORD (MCP Server):
{json.dumps(db_record, indent=2) if db_record else "Not found in database"}

Return ONLY a JSON object:
{{
  "discrepancies_found": [
    {{
      "field_name": "name of mismatched field",
      "expected_value": "what it should be based on official records or other documents",
      "actual_value": "what this document shows",
      "severity": "HIGH or MEDIUM or LOW",
      "plain_english_explanation": "simple explanation for a rural farmer about why this matters"
    }}
  ]
}}
If no discrepancies found, return: {{"discrepancies_found": []}}"""

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
                print(f"[Model Busy] detector_agent received transient error: {err_msg[:120]}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise e
    text = response.text.strip()
    parsed = json.loads(text)
    validated = DetectorOutput.model_validate(parsed)
    discrepancies = [d.model_dump() for d in validated.discrepancies_found]

    # Audit log (after agent acts — separate concern from permission check)
    for disc in discrepancies:
        log_flag(
            document_id=document_id,
            document_type=document_type,
            flag_raised=f"Discrepancy in '{disc['field_name']}': Expected '{disc['expected_value']}', Got '{disc['actual_value']}'",
            action_permitted=permission_result["allowed"]
        )

    return {
        "document_id": document_id,
        "permission_granted": permission_result["allowed"],
        "discrepancies_found": discrepancies,
        "cross_check_passed": len(discrepancies) == 0
    }


# =====================================================================
# 3. Standalone test
# =====================================================================
if __name__ == "__main__":
    all_raw = []
    for fname in ["rtc_001.json", "mutation_001.json"]:
        with open(os.path.join(project_root, "sample_docs", fname)) as f:
            all_raw.append(json.load(f))
    from agents.parser_agent import parse_document
    parsed = parse_document(all_raw[0])
    result = detect_discrepancies(parsed, all_raw)
    print(json.dumps(result, indent=2))
