"""
Security Layer: Audit Logger
----------------------------
This module is responsible ONLY for appending logs to the audit trail AFTER 
an agent has attempted or performed an action.
It does NOT check permissions or enforce access control. That responsibility 
belongs exclusively to the permissions module (security/permissions.py).
"""

import json
import os
from datetime import datetime, timezone

# Resolve the project root directory (one level up from security/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE_PATH = os.path.join(PROJECT_ROOT, "audit_log.jsonl")

def log_flag(document_id: str, document_type: str, flag_raised: str, action_permitted: bool) -> None:
    """
    Appends one JSON-formatted log entry to the audit log (audit_log.jsonl) in the project root.
    
    Parameters:
    - document_id (str): The ID of the document (e.g., "RTC-KA-HAS-2024-001").
    - document_type (str): The type of the document (e.g., "RTC").
    - flag_raised (str): A description of the discrepancy found by the detector agent.
    - action_permitted (bool): The permission check result from permissions.py.
    """
    # Create the log entry dictionary
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "document_id": document_id,
        "document_type": document_type,
        "flag_raised": flag_raised,
        "agent_name": "detector_agent",
        "action_permitted": action_permitted
    }
    
    # Append the JSON representation of the log entry as a single line to audit_log.jsonl
    with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")
