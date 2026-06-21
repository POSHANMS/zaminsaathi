from mcp.server.fastmcp import FastMCP
import json
import os

# Initialize FastMCP server with a descriptive name
mcp = FastMCP("ZaminSaathi Land Records MCP Server")

# Resolve path to the synthetic land records database file relative to this script
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "land_records.json")

@mcp.tool()
def query_land_record(survey_number: str, village: str) -> str:
    """
    Query the official government land records database for a specific survey number and village.
    
    Parameters:
    - survey_number (str): The survey number of the land (e.g., "142/3").
    - village (str): The village where the land is located (e.g., "Kerehalli").
    
    Returns:
    - str: A JSON string containing the land record if found, or an error message.
    """
    try:
        # Check if the database file exists
        if not os.path.exists(DB_PATH):
            return json.dumps({
                "status": "error",
                "message": f"Database file not found at {DB_PATH}"
            })

        # Load the land records database
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        records = data.get("records", [])

        # Search for a matching record (case-insensitive for village)
        for record in records:
            if (record.get("survey_number", "").strip() == survey_number.strip() and
                record.get("village", "").strip().lower() == village.strip().lower()):
                return json.dumps({
                    "status": "success",
                    "record": record
                }, indent=2)

        # Return error if record is not found
        return json.dumps({
            "status": "error",
            "message": f"No record found for survey number '{survey_number}' in village '{village}'."
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"An error occurred while querying the database: {str(e)}"
        }, indent=2)

if __name__ == "__main__":
    # Start the FastMCP server using standard I/O (stdio) transport
    mcp.run()
