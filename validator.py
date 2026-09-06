"""
Basic content validator. No Bedrock calls — pure Python checks, same
logic verified standalone in step 6.
"""

REQUIRED_FIELDS = ["claim_number", "policy_number", "date_of_loss", "claimant_name"]


class ValidationResult:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {"is_valid": self.is_valid, "errors": self.errors, "warnings": self.warnings}


class ContentValidator:
    def validate_extraction(self, fields: dict) -> ValidationResult:
        result = ValidationResult()
        for field in REQUIRED_FIELDS:
            if not fields.get(field):
                result.errors.append(f"missing required field: {field}")

        amount = fields.get("claim_amount")
        if amount is not None:
            try:
                if float(amount) <= 0:
                    result.warnings.append("claim_amount is zero or negative")
            except (TypeError, ValueError):
                result.errors.append("claim_amount is not numeric")

        return result

    def validate_summary(self, summary: str, extracted_fields: dict) -> ValidationResult:
        result = ValidationResult()
        if not summary or len(summary.strip()) < 20:
            result.errors.append("summary is empty or too short")

        claim_number = extracted_fields.get("claim_number")
        if claim_number and claim_number not in summary:
            result.warnings.append("claim_number not referenced in summary — check grounding")

        return result
