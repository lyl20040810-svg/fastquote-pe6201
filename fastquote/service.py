"""End-to-end quotation orchestration and guardrails."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .catalog import Catalog
from .config import openrouter_settings
from .extractor import Extraction, extract_with_openrouter, extract_with_rules
from .pricing import calculate_quote


class QuoteService:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.catalog = Catalog(project_root / "data" / "price_list.json")

    def extract(self, request_text: str, mode: str = "auto") -> tuple[Extraction, str | None]:
        api_key, model = openrouter_settings(self.project_root)
        should_use_api = mode == "openrouter" or (mode == "auto" and api_key and model)
        if should_use_api:
            if not api_key or not model:
                if mode == "openrouter":
                    raise RuntimeError("OpenRouter mode requires OPENROUTER_API_KEY and OPENROUTER_MODEL.")
            else:
                try:
                    return extract_with_openrouter(
                        request_text, self.catalog.allowed_skus(), api_key, model
                    ), None
                except RuntimeError as exc:
                    if mode == "openrouter":
                        raise
                    return extract_with_rules(request_text), str(exc)
        return extract_with_rules(request_text), None

    def quote(self, request_text: str, mode: str = "auto") -> dict[str, Any]:
        if not request_text or not request_text.strip():
            return self._flag("empty_request", "Enter a customer quotation request.")

        extraction, fallback_warning = self.extract(request_text.strip(), mode)
        result: dict[str, Any] = {
            "request": request_text.strip(),
            "extraction": extraction.to_dict(),
            "processing_status": "flagged" if extraction.needs_clarification else "processing",
            "fallback_warning": fallback_warning,
        }
        if extraction.needs_clarification:
            result.update({
                "flag_reason": "ambiguous_or_incomplete",
                "message": extraction.clarification_reason,
                "human_confirmation_required": True,
            })
            return result

        if not all([
            extraction.standard,
            extraction.diameter,
            extraction.length_mm is not None,
            extraction.quantity is not None,
            extraction.unit,
        ]):
            return self._flag("invalid_extraction", "The extracted fields are incomplete.", extraction)

        row = self.catalog.find(
            extraction.standard, extraction.diameter, extraction.length_mm
        )
        if row is None:
            result.update({
                "processing_status": "flagged",
                "flag_reason": "no_exact_catalog_match",
                "message": "No exact verified price-list match was found. Check the specification manually.",
                "human_confirmation_required": True,
            })
            return result

        pricing = calculate_quote(row, extraction.quantity, extraction.unit)
        reply = self._fill_reply(extraction.reply_template, row, extraction, pricing)
        result.update({
            "processing_status": "quoted",
            "catalog_match": row,
            "pricing": pricing,
            "customer_reply_draft": reply,
            "human_confirmation_required": True,
            "manager_approval_required": pricing["approval_status"] == "manager_approval",
        })
        return result

    @staticmethod
    def _flag(reason: str, message: str, extraction: Extraction | None = None) -> dict[str, Any]:
        return {
            "processing_status": "flagged",
            "flag_reason": reason,
            "message": message,
            "extraction": extraction.to_dict() if extraction else None,
            "human_confirmation_required": True,
        }

    @staticmethod
    def _fill_reply(
        template: str,
        row: dict[str, Any],
        extraction: Extraction,
        pricing: dict[str, Any],
    ) -> str:
        spec = f'{row["diameter"]}x{row["length_mm"]}'
        unit = str(extraction.unit)
        unit_display = unit if extraction.quantity == 1 else {
            "piece": "pieces",
            "box": "boxes",
            "carton": "cartons",
        }.get(unit, unit)
        values = {
            "{{SPEC}}": spec,
            "{{SKU}}": spec,
            "{{QUANTITY}}": str(extraction.quantity),
            "{{UNIT}}": unit_display,
            "{{TOTAL_PIECES}}": str(pricing["total_pieces"]),
            "{{TOTAL_PRICE}}": f'{pricing["revenue_cny"]:,.2f}',
            "{{DISCOUNT_PERCENT}}": f'{pricing["discount_rate"] * 100:.0f}',
            "{{GROSS_MARGIN_PERCENT}}": "",
            "{{APPROVAL_NOTE}}": "",
        }
        reply = template
        for key, value in values.items():
            reply = reply.replace(key, value)
        reply = " ".join(reply.split())
        safe_reply = (
            f"Thank you for your enquiry. We can offer {spec} for {extraction.quantity} "
            f"{unit_display} ({pricing['total_pieces']} pieces) at a total of CNY "
            f"{pricing['revenue_cny']:,.2f} after a "
            f"{pricing['discount_rate'] * 100:.0f}% discount. "
            "Please let us know if you would like to proceed."
        )
        if re.search(r"\b(?:margin|approval)\b|10\s*%", reply, re.IGNORECASE):
            reply = safe_reply

        if pricing["approval_status"] == "manager_approval":
            reply = (
                f"Thank you for your enquiry. We can offer {spec} for {extraction.quantity} "
                f"{unit_display} ({pricing['total_pieces']} pieces) at a total of CNY "
                f"{pricing['revenue_cny']:,.2f} after a "
                f"{pricing['discount_rate'] * 100:.0f}% discount. "
                "Please note that this order must still receive internal manager approval "
                "before it can be accepted, and approval is not guaranteed. This quoted "
                "amount is therefore the lowest price we are able to offer. Please let us "
                "know if you would like to continue."
            )
        return reply

