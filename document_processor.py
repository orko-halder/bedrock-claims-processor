"""
ClaimProcessor — orchestrates extraction, S3-backed RAG retrieval, and
grounded summary generation, using the standardized components
(model_invoker, prompt_manager, validator, rag) rather than calling
Bedrock directly. This is the file that should now be fully legible —
every method here was built and verified independently earlier in the
session before being assembled here.
"""

import json

import boto3

import config
from extraction_schema import EXTRACTION_TOOL
from model_invoker import ModelInvoker
from prompt_manager import PromptTemplateManager
from rag import PolicyRAG
from validator import ContentValidator


class ClaimProcessor:
    def __init__(self):
        self.invoker = ModelInvoker(region=config.AWS_REGION)
        self.prompts = PromptTemplateManager()
        self.validator = ContentValidator()

        s3_client = boto3.client("s3", region_name=config.AWS_REGION)
        self.rag = PolicyRAG(self.invoker, s3_client)

    def extract_fields(self, document_text: str, model_id: str = config.MODEL_EXTRACTION) -> dict:
        prompt = self.prompts.render("extraction", document_text=document_text)
        response = self.invoker.invoke(
            model_id=model_id,
            messages=[{"role": "user", "content": prompt}],
            tools=[EXTRACTION_TOOL],
            max_tokens=500,
        )
        return self.invoker.extract_tool_input(response, "record_claim_fields") or {}

    def summarize(
        self, extracted_fields: dict, model_id: str = config.MODEL_SUMMARY
    ) -> tuple[str, str]:
        doc_type = extracted_fields.get("document_type", "")
        incident = extracted_fields.get("incident_description", "")
        query = f"{doc_type} {incident}"
        policy_chunks = self.rag.retrieve(query, top_k=1)
        policy_context = policy_chunks[0] if policy_chunks else "No relevant policy context found."

        prompt = self.prompts.render(
            "summary",
            extracted_fields=json.dumps(extracted_fields, indent=2),
            policy_context=policy_context,
        )
        response = self.invoker.invoke(
            model_id=model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
        )
        return self.invoker.extract_text(response), policy_context

    def process(self, raw_text: str, model_overrides: dict | None = None) -> dict:
        """
        model_overrides lets the evaluate.py comparison swap models per
        step without touching this method, e.g.
        {"extraction": config.MODEL_EXTRACTION_CHEAP}
        """
        overrides = model_overrides or {}

        fields = self.extract_fields(raw_text, overrides.get("extraction", config.MODEL_EXTRACTION))
        extraction_result = self.validator.validate_extraction(fields)

        summary, policy_context = self.summarize(
            fields, overrides.get("summary", config.MODEL_SUMMARY)
        )
        summary_result = self.validator.validate_summary(summary, fields)

        return {
            "extracted_fields": fields,
            "extraction_validation": extraction_result.to_dict(),
            "policy_context": policy_context,
            "summary": summary,
            "summary_validation": summary_result.to_dict(),
        }
