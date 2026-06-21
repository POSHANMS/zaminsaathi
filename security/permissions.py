"""
Security Layer: Access Control
-------------------------------
This module is responsible ONLY for checking permissions BEFORE an agent acts.
It does NOT write logs or perform any auditing. That responsibility belongs 
exclusively to the audit log module (security/audit_log.py).
"""

def check_permission(document_type: str, action: str) -> dict:
    """
    Check if an agent is permitted to perform a specific action on a document type.
    
    Parameters:
    - document_type (str): The type of land document (e.g., "RTC", "MUTATION", "SURVEY").
    - action (str): The action being attempted (e.g., "flag").
    
    Returns:
    - dict: A dictionary containing:
        - "allowed" (bool): True if permitted, False otherwise.
        - "reason" (str): A message explaining the decision.
    """
    # Normalize inputs for consistency
    doc_type_upper = str(document_type).upper().strip()
    action_lower = str(action).lower().strip()
    
    # We only manage the "flag" action in this scope
    if action_lower != "flag":
        return {
            "allowed": False,
            "reason": f"Action '{action}' is not supported by the permissions check."
        }
    
    # Define allowed document types for flagging
    allowed_types = {"RTC", "MUTATION", "SURVEY"}
    
    if doc_type_upper in allowed_types:
        return {
            "allowed": True,
            "reason": f"Detector agent is permitted to perform '{action}' on '{doc_type_upper}' documents."
        }
    
    # Deny all unknown document types
    return {
        "allowed": False,
        "reason": f"Access denied. Document type '{document_type}' is unknown or not authorized for action '{action}'."
    }
