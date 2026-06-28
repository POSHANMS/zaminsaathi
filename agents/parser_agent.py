import os
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import Dict, List
import dotenv

dotenv.load_dotenv()

# Use google.genai client (new SDK) — works with v1 API endpoint
# gemini-2.5-flash-lite: 500 req/day free tier (vs 20/day for gemini-2.5-flash)
MODEL = "gemini-2.5-flash-lite"

def _get_client():
    return genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# =====================================================================
# 1. Structured Output Schema
# =====================================================================
class ParserOutput(BaseModel):
    document_type: str
    document_id: str
    summary: str
    fields_explained: Dict[str, str]
    warnings: List[str]

# =====================================================================
# 2. Main Parser Function
# =====================================================================
def parse_document(doc: dict) -> dict:
    """Parses a land document and explains every field in plain English."""
    doc_type = doc.get("document_type", "").upper().strip()
    if not doc_type:
        if "previous_owner" in doc or "new_owner" in doc:
            doc_type = "MUTATION"
        elif "boundaries" in doc or "surveyor_name" in doc:
            doc_type = "SURVEY"
        else:
            doc_type = "RTC"

    skill_mapping = {"RTC": "rtc-skill", "MUTATION": "mutation-skill", "SURVEY": "survey-skill"}
    skill_folder = skill_mapping.get(doc_type, "rtc-skill")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    skill_file_path = os.path.join(project_root, "skills", skill_folder, "SKILL.md")

    skill_content = ""
    if os.path.exists(skill_file_path):
        with open(skill_file_path, "r", encoding="utf-8") as f:
            skill_content = f.read()[:2000]

    prompt = f"""You are the Parser Agent for ZaminSaathi. Read this Karnataka land document and explain every field in plain English for a rural farmer who has never seen a legal document before.

SKILL CONTEXT FOR {doc_type}:
{skill_content}

DOCUMENT TO PARSE:
{json.dumps(doc, indent=2)}

Return ONLY a JSON object with this exact structure:
{{
  "document_type": "{doc_type}",
  "document_id": "{doc.get('document_id', 'unknown')}",
  "summary": "One paragraph plain English summary for a farmer",
  "fields_explained": {{
    "each_field_name": "Plain English explanation of what it means and what its value indicates"
  }},
  "warnings": ["List any concerns, or empty list if none"]
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
                print(f"[Model Busy] parser_agent received transient error: {err_msg[:120]}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise e
    text = response.text.strip()
    parsed = json.loads(text)
    return ParserOutput.model_validate(parsed).model_dump()


# =====================================================================
# 3. Standalone test
# =====================================================================
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    with open(os.path.join(project_root, "sample_docs", "rtc_001.json")) as f:
        doc = json.load(f)
    print(f"Parsing {doc['document_id']}...")
    result = parse_document(doc)
    print(json.dumps(result, indent=2))
