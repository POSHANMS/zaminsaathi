import os
import sys
import json
import asyncio
import dotenv
from pydantic import BaseModel, Field
from typing import List

# Load environment variables from a .env file if present
dotenv.load_dotenv()

# Add the project root to the Python path to ensure clean imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# Import ADK modules
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner

# =====================================================================
# 1. Define Pydantic Schema for Local LLM Response Validation
# =====================================================================
class PlannerOutput(BaseModel):
    status: str = Field(
        description="Must be 'clear' if no discrepancies were found, or 'action_required' if discrepancies were found"
    )
    summary: str = Field(
        description="One paragraph explaining the situation simply to a rural family. No technical jargon, simple words."
    )
    action_steps: List[str] = Field(
        description="Numbered list of concrete, actionable next steps for the family."
    )
    offices_to_visit: List[str] = Field(
        description="List of specific government offices to visit and what to do there (e.g. Tahsildar office for Hassan taluk)."
    )
    portals_to_use: List[str] = Field(
        description="List of Karnataka government portal names and their URLs (Bhoomi: https://landrecords.karnataka.gov.in/, Kaveri: https://kaverionline.karnataka.gov.in/)."
    )
    documents_to_carry: List[str] = Field(
        description="List of specific land documents, applications, and ID proofs the family should bring."
    )
    legal_disclaimer: str = Field(
        description="Must be exactly: 'This is guidance only. Consult a qualified lawyer before taking legal action.'"
    )

# =====================================================================
# 2. Main Action Planner Function
# =====================================================================
def generate_plan(detector_result: dict) -> dict:
    """
    Generates a concrete, actionable next-steps plan for a rural family
    based on the discrepancies found in their land documents.
    
    Parameters:
    - detector_result (dict): The output from Agent 2 (discrepancy detection result).
    
    Returns:
    - dict: Action plan conforming to the PlannerOutput schema.
    """
    # Define instructions for the Planner Agent
    system_instruction = """
You are the Action Planner Agent, a specialized component of the ZaminSaathi system.
Your job is to generate a concrete, actionable next-steps plan for rural Karnataka families based on the discrepancies found in their land documents.

You will be provided with:
1. The Discrepancy Detection Result from Agent 2.

Follow these strict rules:
1. If the discrepancy result indicates no discrepancies were found ('cross_check_passed' is true), return status 'clear'. In your summary and action_steps, give a reassuring message and simple maintenance tips (e.g., check land documents every year, don't share OTPs, keep copies safe).
2. If discrepancies were found ('cross_check_passed' is false), return status 'action_required'. Generate a numbered action plan containing:
   - Which specific government office to visit (e.g. Tahsildar office for Hassan taluk if the document mentions Hassan, or the local sub-registrar office).
   - Which Karnataka government portal to use (e.g., Bhoomi portal at https://landrecords.karnataka.gov.in/ for RTC issues, Kaveri portal at https://kaverionline.karnataka.gov.in/ for registration/deed issues).
   - What documents to carry (e.g. original RTC, mutation copy, survey sketch, Aadhaar card, application letters).
   - What to say to the officer — provide a simple, polite script in plain English.
   - Estimated timeline for resolution (e.g. 15-30 days).
3. The legal_disclaimer MUST be exactly: 'This is guidance only. Consult a qualified lawyer before taking legal action.'
4. You MUST return your output as a valid JSON object matching the JSON schema below. Do not include any explanatory text or markdown outside the JSON.

Expected JSON format:
{
  "status": "clear or action_required",
  "summary": "One paragraph plain English summary of the situation.",
  "action_steps": [
     "Numbered action steps (e.g. '1. Visit...', '2. Submit...')"
  ],
  "offices_to_visit": [
     "Office name — what to do there"
  ],
  "portals_to_use": [
     "Portal name (URL) — what to do there"
  ],
  "documents_to_carry": [
     "Document name"
  ],
  "legal_disclaimer": "This is guidance only. Consult a qualified lawyer before taking legal action."
}
"""

    planner_agent = Agent(
        name="planner_agent",
        model="gemini-2.5-flash",
        instruction=system_instruction
    )

    runner = InMemoryRunner(agent=planner_agent)

    input_str = json.dumps(detector_result, indent=2)

    # Run the agent in debug mode (async wrapper)
    events = asyncio.run(runner.run_debug(input_str))

    # Extract response text
    text_response = ""
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    text_response += part.text

    if not text_response:
        raise RuntimeError("No output generated by the Planner Agent.")

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
        
        # Local validation using Pydantic schema
        validated_output = PlannerOutput.model_validate(parsed_dict)
        return validated_output.model_dump()
    except Exception as e:
        raise ValueError(f"Failed to parse or validate planner agent response. Response: {text_response}. Error: {str(e)}")

# =====================================================================
# 3. Test Runner
# =====================================================================
if __name__ == "__main__":
    # Force standard output to use UTF-8 to prevent encoding crashes on Windows
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

    print("Starting Planner Agent test...")

    # Check for API key
    if "GEMINI_API_KEY" not in os.environ and "GOOGLE_API_KEY" not in os.environ:
        print("\n[WARNING] Neither GEMINI_API_KEY nor GOOGLE_API_KEY found in environment variables.")
        print("Please export GEMINI_API_KEY=<your_key> before running this test.")
        exit(1)

    # Import parser and detector agents
    from agents.parser_agent import parse_document
    from agents.detector_agent import detect_discrepancies
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

    # Load the sample documents
    sample_files = ["rtc_001.json", "mutation_001.json"]
    all_raw_docs = []
    
    for filename in sample_files:
        path = os.path.join(project_root, "sample_docs", filename)
        if not os.path.exists(path):
            print(f"Error: Required sample file not found at {path}")
            exit(1)
        with open(path, "r", encoding="utf-8") as f:
            all_raw_docs.append(json.load(f))

    print("\nRunning Parser Agent on raw documents...")
    # Parse rtc_001
    print("Parsing rtc_001.json...")
    parsed_rtc = run_with_retry(parse_document, all_raw_docs[0])
    time.sleep(1.5)
    
    # Parse mutation_001
    print("Parsing mutation_001.json...")
    parsed_mutation = run_with_retry(parse_document, all_raw_docs[1])
    time.sleep(1.5)

    print("\nRunning Detector Agent on mutation document...")
    # Detect discrepancies on the mutation document (where we planted the mismatch)
    detector_result = run_with_retry(detect_discrepancies, parsed_mutation, all_raw_docs)
    print("\nDiscrepancy Check Output:")
    print(json.dumps(detector_result, indent=2))
    time.sleep(1.5)

    print("\nRunning Planner Agent to generate action plan...")
    # Generate action plan based on the detector results
    plan_result = run_with_retry(generate_plan, detector_result)
    print("\nPlanner Agent Result:")
    print(json.dumps(plan_result, indent=2))
