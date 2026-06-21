import os
import json
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from pydantic import BaseModel, Field
from typing import Dict, List
import dotenv

# Load environment variables from a .env file if present
dotenv.load_dotenv()

# =====================================================================
# 1. Define the Structured Output Schema using Pydantic
# =====================================================================
class ParserOutput(BaseModel):
    document_type: str = Field(
        description="The detected type of document: 'RTC', 'MUTATION', or 'SURVEY'"
    )
    document_id: str = Field(
        description="The unique ID of the document (e.g. RTC-KA-HAS-2024-001)"
    )
    summary: str = Field(
        description="One paragraph plain English summary of the document, explaining it simply like to a farmer who has never seen a legal document before. No jargon, simple sentences."
    )
    fields_explained: Dict[str, str] = Field(
        description="A dictionary mapping each field name to its plain English explanation of what it means and what the value says, based on the provided skill guidelines."
    )
    warnings: List[str] = Field(
        description="A list of warnings for any fields that look unusual, missing, older than recommended (e.g. RTC older than 3 years, Survey older than 10 years), or mismatched. Empty list if none."
    )

# =====================================================================
# 2. Main Parser Function
# =====================================================================
def parse_document(doc: dict) -> dict:
    """
    Parses a land document python dict, auto-detects its type, loads the correct
    skill context dynamically, and uses the Parser Agent to generate a structured explanation.
    
    Parameters:
    - doc (dict): The land document fields.
    
    Returns:
    - dict: The structured dictionary conforming to ParserOutput schema.
    """
    # Auto-detect document type
    doc_type = doc.get("document_type", "").upper().strip()
    if not doc_type:
        # Fallback heuristics based on unique fields
        if "previous_owner" in doc or "new_owner" in doc:
            doc_type = "MUTATION"
        elif "boundaries" in doc or "surveyor_name" in doc:
            doc_type = "SURVEY"
        else:
            doc_type = "RTC"

    # Map document type to the skill subdirectory name
    skill_mapping = {
        "RTC": "rtc-skill",
        "MUTATION": "mutation-skill",
        "SURVEY": "survey-skill"
    }

    skill_folder = skill_mapping.get(doc_type)
    if not skill_folder:
        raise ValueError(f"Unsupported or unrecognized document type: {doc_type}")

    # Load the skill context from the skills folder relative to project root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    skill_file_path = os.path.join(project_root, "skills", skill_folder, "SKILL.md")

    if not os.path.exists(skill_file_path):
        raise FileNotFoundError(f"Expected skill file not found at {skill_file_path}")

    with open(skill_file_path, "r", encoding="utf-8") as f:
        skill_content = f.read()

    # Define instructions for the Parser Agent, embedding the loaded skill context
    system_instruction = f"""
You are the Parser Agent, a specialized component of the ZaminSaathi system.
Your job is to read a land document and explain every field in plain English for a rural Karnataka family.

Follow these strict rules:
1. Explain everything like you are talking to a farmer who has never seen a legal document before. No jargon, use simple sentences.
2. Use the provided Skill Context below to guide your explanations of specific fields.
3. Check for the warnings specified in the Skill Context (e.g., check dates, missing fields, or suspicious values) and list them.
4. You MUST return your output as a valid JSON object matching the JSON schema below. Do not include any explanatory text or markdown outside the JSON.

Expected JSON format:
{{
  "document_type": "{doc_type}",
  "document_id": "Document unique ID string",
  "summary": "One paragraph plain English summary for a rural farmer.",
  "fields_explained": {{
    "field_name_1": "Plain English explanation of what field_name_1 means and what its value indicates.",
    "field_name_2": "..."
  }},
  "warnings": [
    "Warning messages if any, otherwise empty list"
  ]
}}

---
SKILL CONTEXT FOR {doc_type}:
{skill_content}
---
"""

    # Instantiate the Google ADK Agent
    # Note: We do not pass output_schema to the Agent constructor to avoid
    # additionalProperties API validation errors in Google Developer API mode.
    # Instead, we validate the output locally using Pydantic.
    parser_agent = Agent(
        name="parser_agent",
        model="gemini-2.5-flash",
        instruction=system_instruction
    )

    # Use InMemoryRunner to execute the agent
    runner = InMemoryRunner(agent=parser_agent)

    # Pass the document as a formatted JSON string
    input_str = json.dumps(doc, indent=2)

    import asyncio
    # Run the agent in debug mode (synchronous execution wrapper)
    events = asyncio.run(runner.run_debug(input_str))

    # Extract the response text from the events list
    text_response = ""
    for event in events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    text_response += part.text

    if not text_response:
        raise RuntimeError("No output generated by the Parser Agent.")

    try:
        # Clean possible markdown code block wrappers
        clean_text = text_response.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()
        
        parsed_dict = json.loads(clean_text)
        
        # Local validation using Pydantic schema to ensure structure correctness
        validated_output = ParserOutput.model_validate(parsed_dict)
        return validated_output.model_dump()
    except Exception as e:
        raise ValueError(f"Failed to parse or validate agent response. Response: {text_response}. Error: {str(e)}")

# =====================================================================
# 3. Test Runner
# =====================================================================
if __name__ == "__main__":
    print("Starting Parser Agent test...")

    # Load rtc_001.json
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    sample_file_path = os.path.join(project_root, "sample_docs", "rtc_001.json")

    if not os.path.exists(sample_file_path):
        print(f"Error: Sample file not found at {sample_file_path}")
        exit(1)

    with open(sample_file_path, "r", encoding="utf-8") as f:
        doc_data = json.load(f)

    # Check for API key in environment
    if "GEMINI_API_KEY" not in os.environ and "GOOGLE_API_KEY" not in os.environ:
        print("\n[WARNING] Neither GEMINI_API_KEY nor GOOGLE_API_KEY found in environment variables.")
        print("Please export GEMINI_API_KEY=<your_key> before running this script.")
        print("Test file contents loaded successfully:")
        print(json.dumps(doc_data, indent=2))
    else:
        try:
            print(f"Parsing document: {doc_data['document_id']}...")
            result = parse_document(doc_data)
            print("\nParser Agent Result:")
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"\nExecution failed: {str(e)}")
