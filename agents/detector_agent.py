import os
import sys
import json
import asyncio
import dotenv
from pydantic import BaseModel, Field
from typing import List

# Load environment variables from a .env file if present
dotenv.load_dotenv()

# Add the project root to the Python path to ensure clean imports of security and mcp_server
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# Import ADK modules
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner

# Import local project modules
from security.permissions import check_permission
from security.audit_log import log_flag
from mcp_server.server import query_land_record

# =====================================================================
# 1. Define Pydantic Schema for Local LLM Response Validation
# =====================================================================
class Discrepancy(BaseModel):
    field_name: str = Field(
        description="The name of the field with the discrepancy (e.g. 'survey_number', 'owner_name')"
    )
    expected_value: str = Field(
        description="The expected value based on the official database records or other uploaded documents"
    )
    actual_value: str = Field(
        description="The actual value found in the current document being checked"
    )
    severity: str = Field(
        description="The severity level: 'HIGH', 'MEDIUM', or 'LOW'"
    )
    plain_english_explanation: str = Field(
        description="A clear explanation of the discrepancy and why it matters, in simple terms a rural farmer can understand."
    )

class DetectorOutput(BaseModel):
    discrepancies_found: List[Discrepancy] = Field(
        description="A list of all detected discrepancies. Empty list if none."
    )

# =====================================================================
# 2. Main Discrepancy Detector Function
# =====================================================================
def detect_discrepancies(parsed_doc: dict, all_uploaded_docs: List[dict]) -> dict:
    """
    Cross-checks the parsed document against other family documents and the
    official government database to detect discrepancies.
    
    Parameters:
    - parsed_doc (dict): Output from Agent 1 (parsed document result).
    - all_uploaded_docs (List[dict]): List of all raw uploaded document JSONs.
    
    Returns:
    - dict: Structured results containing the checked document's ID, permission status,
            any discrepancies found, and whether the cross-check passed.
    """
    document_id = parsed_doc.get("document_id")
    document_type = parsed_doc.get("document_type")
    
    # -----------------------------------------------------------------
    # Step A: Perform Permission Check (Access Control Layer)
    # -----------------------------------------------------------------
    permission_result = check_permission(document_type, "flag")
    if not permission_result["allowed"]:
        return {
            "document_id": document_id,
            "permission_granted": False,
            "discrepancies_found": [],
            "cross_check_passed": False,
            "denial_reason": permission_result["reason"]
        }
        
    # Find the raw document matching the parsed document's ID
    raw_doc = None
    for doc in all_uploaded_docs:
        if doc.get("document_id") == document_id:
            raw_doc = doc
            break
    if not raw_doc:
        # Fallback to the parsed document itself if raw doc not found in the list
        raw_doc = parsed_doc

    survey_number = raw_doc.get("survey_number", "")
    village = raw_doc.get("village", "")

    # -----------------------------------------------------------------
    # Step B: Query the MCP Server Database
    # -----------------------------------------------------------------
    db_record = None
    try:
        db_response_str = query_land_record(survey_number, village)
        db_response = json.loads(db_response_str)
        if db_response.get("status") == "success":
            db_record = db_response.get("record")
    except Exception as e:
        print(f"[Warning] Failed to query MCP database for survey_number={survey_number}: {e}")

    # -----------------------------------------------------------------
    # Step C: Run Detector Agent (LLM Reasoning Layer)
    # -----------------------------------------------------------------
    system_instruction = f"""
You are the Discrepancy Detector Agent, a specialized component of the ZaminSaathi system.
Your job is to cross-check a land document against other uploaded family documents and the official government database record.

You will be provided with:
1. The Current Document being checked.
2. The Agent 1 Parser Output for this document.
3. All Uploaded Documents for this family.
4. The Official Land Record from the government database (MCP Server).

Cross-check these three things:
1. Does the survey_number in the current document match the survey_number in ALL other uploaded documents?
   - For example, if the current document says 142/4, but other uploaded documents for the same family plots say 142/3, flag this mismatch.
2. Does the survey_number match what the official database record says?
3. Does the owner_name match across documents where it should match?
   - Note: In RTC, it is `owner_name`. In Mutation, it can be `previous_owner` or `new_owner`. In official records, it is `registered_owner`. Check for continuity and mismatches in ownership.

For any mismatch, explain it in simple, jargon-free English so a rural farmer can understand what the discrepancy is and why it is a problem.
You MUST return your output as a valid JSON object matching the JSON schema below. Do not include any explanatory text or markdown outside the JSON.

Expected JSON format:
{{
  "discrepancies_found": [
    {{
      "field_name": "Name of the mismatched field (e.g. survey_number, owner_name)",
      "expected_value": "The value that should be there (from official record or matching documents)",
      "actual_value": "The incorrect value found in the current document",
      "severity": "HIGH, MEDIUM, or LOW",
      "plain_english_explanation": "Explanation of the mismatch and why it matters."
    }}
  ]
}}
"""

    detector_agent = Agent(
        name="detector_agent",
        model="gemini-2.5-flash",
        instruction=system_instruction
    )

    runner = InMemoryRunner(agent=detector_agent)

    # Compile all relevant context to pass to the agent
    context_to_send = {
        "current_document": raw_doc,
        "parser_output": parsed_doc,
        "all_uploaded_documents": all_uploaded_docs,
        "official_database_record": db_record
    }

    input_str = json.dumps(context_to_send, indent=2)

    # Run agent in async execution wrapper
    import time
    max_attempts = 5
    events = None
    for attempt in range(max_attempts):
        try:
            events = asyncio.run(runner.run_debug(input_str))
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

    # Extract text output
    text_response = ""
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    text_response += part.text

    if not text_response:
        raise RuntimeError("No output generated by the Detector Agent.")

    # -----------------------------------------------------------------
    # Step D: Process Results & Write Audit Logs (Audit Logging Layer)
    # -----------------------------------------------------------------
    discrepancies = []
    try:
        clean_text = text_response.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()
        
        parsed_dict = json.loads(clean_text)
        validated_output = DetectorOutput.model_validate(parsed_dict)
        discrepancies = [d.model_dump() for d in validated_output.discrepancies_found]
    except Exception as e:
        raise ValueError(f"Failed to parse or validate detector agent response. Response: {text_response}. Error: {str(e)}")

    # Log each discrepancy in the audit log (after the agent acts)
    action_permitted = permission_result["allowed"]
    for discrepancy in discrepancies:
        flag_raised = (
            f"Discrepancy in '{discrepancy['field_name']}': "
            f"Expected '{discrepancy['expected_value']}', Actual '{discrepancy['actual_value']}'. "
            f"Reason: {discrepancy['plain_english_explanation']}"
        )
        log_flag(
            document_id=document_id,
            document_type=document_type,
            flag_raised=flag_raised,
            action_permitted=action_permitted
        )

    # Determine if cross-check passed
    cross_check_passed = len(discrepancies) == 0

    return {
        "document_id": document_id,
        "permission_granted": action_permitted,
        "discrepancies_found": discrepancies,
        "cross_check_passed": cross_check_passed
    }

# =====================================================================
# 3. Test Runner
# =====================================================================
if __name__ == "__main__":
    print("Starting Detector Agent test...")

    # Load all 4 sample documents
    sample_files = ["rtc_001.json", "mutation_001.json", "survey_001.json", "rtc_002.json"]
    all_raw_docs = []
    
    for filename in sample_files:
        path = os.path.join(project_root, "sample_docs", filename)
        if not os.path.exists(path):
            print(f"Error: Required sample file not found at {path}")
            exit(1)
        with open(path, "r", encoding="utf-8") as f:
            all_raw_docs.append(json.load(f))

    # Check for API key
    if "GEMINI_API_KEY" not in os.environ and "GOOGLE_API_KEY" not in os.environ:
        print("\n[WARNING] Neither GEMINI_API_KEY nor GOOGLE_API_KEY found in environment variables.")
        print("Please export GEMINI_API_KEY=<your_key> before running this test.")
        exit(1)

    # Import parser agent to parse each document first
    from agents.parser_agent import parse_document

    import time
    from google.genai.errors import ServerError

    def run_with_retry(func, *args, **kwargs):
        """Helper to retry model requests with exponential backoff on transient 503 errors."""
        max_attempts = 4
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except (ServerError, Exception) as e:
                err_msg = str(e)
                is_transient = "503" in err_msg or "UNAVAILABLE" in err_msg or "demand" in err_msg
                if is_transient and attempt < max_attempts - 1:
                    wait_time = (attempt + 1) * 3
                    print(f"  [Model Busy] 503 error received: {err_msg[:120]}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise e

    parsed_docs = []
    print("\nRunning Parser Agent on all sample documents...")
    for raw_doc in all_raw_docs:
        print(f"Parsing {raw_doc['document_id']}...")
        parsed_doc = run_with_retry(parse_document, raw_doc)
        parsed_docs.append(parsed_doc)
        time.sleep(1.5)  # Let the API breathe between documents

    print("\nRunning Detector Agent to check for discrepancies...")
    for parsed_doc in parsed_docs:
        print(f"\nChecking {parsed_doc['document_id']}...")
        result = run_with_retry(detect_discrepancies, parsed_doc, all_raw_docs)
        print(json.dumps(result, indent=2))
        time.sleep(1.5)  # Let the API breathe between checks
