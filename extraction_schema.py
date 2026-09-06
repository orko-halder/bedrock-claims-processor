EXTRACTION_TOOL = {
    "name": "record_claim_fields",
    "description": "Records structured fields extracted from a claim document.",
    "input_schema": {
        "type": "object",
        "properties": {
            "claim_number": {"type": ["string", "null"]},
            "policy_number": {"type": ["string", "null"]},
            "date_of_loss": {"type": ["string", "null"]},
            "claimant_name": {"type": ["string", "null"]},
            "claim_amount": {"type": ["number", "null"]},
            "incident_description": {"type": ["string", "null"]},
            "document_type": {"type": ["string", "null"]},
        },
        "required": [
            "claim_number",
            "policy_number",
            "date_of_loss",
            "claimant_name",
            "claim_amount",
            "incident_description",
            "document_type",
        ],
    },
}
