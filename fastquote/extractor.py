"""Customer-request extraction using OpenRouter or a deterministic fallback."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from typing import Any


ALLOWED_UNITS = {"piece", "box", "carton"}
PLACEHOLDERS = {
    "{{SPEC}}",
    "{{QUANTITY}}",
    "{{UNIT}}",
    "{{TOTAL_PIECES}}",
    "{{TOTAL_PRICE}}",
    "{{DISCOUNT_PERCENT}}",
}


@dataclass
class Extraction:
    standard: str | None
    diameter: str | None
    length_mm: int | None
    quantity: int | None
    unit: str | None
    needs_clarification: bool
    clarification_reason: str
    reply_template: str
    extraction_method: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_unit(raw: str) -> str | None:
    value = raw.lower().strip()
    mapping = {
        "支": "piece",
        "个": "piece",
        "pc": "piece",
        "pcs": "piece",
        "piece": "piece",
        "pieces": "piece",
        "盒": "box",
        "box": "box",
        "boxes": "box",
        "箱": "carton",
        "carton": "carton",
        "cartons": "carton",
        "ctn": "carton",
        "ctns": "carton",
    }
    return mapping.get(value)


def extract_with_rules(text: str) -> Extraction:
    normalized = text.upper().replace("×", "X").replace("*", "X")
    sku_match = re.search(r"(?<![A-Z0-9])(M\s*\d{1,2})\s*[-X]\s*(\d{2,3})(?!\d)", normalized)
    diameter = re.sub(r"\s+", "", sku_match.group(1)) if sku_match else None
    length_mm = int(sku_match.group(2)) if sku_match else None

    standard_match = re.search(r"\bDIN\s*933\b", normalized)
    standard = "DIN933" if standard_match or sku_match else None

    quantity_match = re.search(
        r"(?<!M)(\d+)\s*(CARTONS?|CTNS?|BOX(?:ES)?|PIECES?|PCS?|PC|箱|盒|支|个)",
        normalized,
        re.IGNORECASE,
    )
    quantity = int(quantity_match.group(1)) if quantity_match else None
    unit = _normalize_unit(quantity_match.group(2)) if quantity_match else None

    missing = []
    if not diameter or length_mm is None:
        missing.append("an exact diameter and length, such as M16x50")
    if quantity is None or unit is None:
        missing.append("a quantity with unit: pieces, boxes, or cartons")
    needs_clarification = bool(missing)
    reason = "Please provide " + " and ".join(missing) + "." if missing else ""

    return Extraction(
        standard=standard,
        diameter=diameter,
        length_mm=length_mm,
        quantity=quantity,
        unit=unit,
        needs_clarification=needs_clarification,
        clarification_reason=reason,
        reply_template=(
            "Thank you for your enquiry. We can offer {{SPEC}} for {{QUANTITY}} {{UNIT}} "
            "({{TOTAL_PIECES}} pieces) at a total of CNY {{TOTAL_PRICE}} after a "
            "{{DISCOUNT_PERCENT}}% discount. Please let us know if you would like to proceed."
        ),
        extraction_method="rules",
    )


def extract_with_openrouter(
    text: str,
    allowed_skus: list[str],
    api_key: str,
    model: str,
    timeout_seconds: int = 45,
) -> Extraction:
    schema = {
        "name": "fastquote_extraction",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "standard": {"type": ["string", "null"]},
                "diameter": {"type": ["string", "null"]},
                "length_mm": {"type": ["integer", "null"]},
                "quantity": {"type": ["integer", "null"]},
                "unit": {"type": ["string", "null"], "enum": ["piece", "box", "carton", None]},
                "needs_clarification": {"type": "boolean"},
                "clarification_reason": {"type": "string"},
                "reply_template": {"type": "string"},
            },
            "required": [
                "standard", "diameter", "length_mm", "quantity", "unit",
                "needs_clarification", "clarification_reason", "reply_template"
            ],
            "additionalProperties": False,
        },
    }
    system_prompt = (
        "You extract a fastener quotation request. Do not calculate or invent any price. "
        "The application uses one internal DIN933 A2 catalog. Customers are not expected to "
        "state DIN933 or A2. When an exact listed diameter and length such as M16x50 is present, "
        "set standard to DIN933 and do not ask the customer for the standard or material. "
        "Only use piece, box, or carton as unit. Set needs_clarification=true when product, "
        "length, quantity, or unit is missing or ambiguous. The reply_template must be concise "
        "business English and may use only these placeholders: " + ", ".join(sorted(PLACEHOLDERS)) + ". "
        "Never put a numeric price in the template. Never mention gross margin, the 10% threshold, "
        "manager approval, or any internal approval result. Available SKUs: " + ", ".join(allowed_skus)
    )
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        "response_format": {"type": "json_schema", "json_schema": schema},
    }
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://127.0.0.1:8765",
            "X-Title": "FastQuote PE6201 Demo",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter returned HTTP {exc.code}: {detail[:300]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenRouter connection failed: {exc.reason}") from exc

    try:
        parsed = json.loads(body["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("OpenRouter returned an invalid structured response.") from exc

    unit = parsed.get("unit")
    if unit is not None and unit not in ALLOWED_UNITS:
        parsed["needs_clarification"] = True
        parsed["clarification_reason"] = "The quantity unit could not be verified."
        parsed["unit"] = None

    template = parsed.get("reply_template", "")
    used_placeholders = set(re.findall(r"\{\{[A-Z_]+\}\}", template))
    exposes_internal_rules = re.search(r"\b(?:margin|approval)\b|10\s*%", template, re.IGNORECASE)
    if (
        used_placeholders - PLACEHOLDERS
        or re.search(r"(?:CNY|RMB|¥)\s*\d", template, re.IGNORECASE)
        or exposes_internal_rules
    ):
        template = extract_with_rules(text).reply_template

    diameter = parsed.get("diameter")
    length_mm = parsed.get("length_mm")
    quantity = parsed.get("quantity")
    standard = parsed.get("standard")
    if not standard and diameter and length_mm is not None:
        standard = "DIN933"

    needs_clarification = bool(parsed.get("needs_clarification"))
    clarification_reason = str(parsed.get("clarification_reason", ""))
    if diameter and length_mm is not None and quantity is not None and parsed.get("unit"):
        needs_clarification = False
        clarification_reason = ""

    return Extraction(
        standard=standard,
        diameter=diameter,
        length_mm=length_mm,
        quantity=quantity,
        unit=parsed.get("unit"),
        needs_clarification=needs_clarification,
        clarification_reason=clarification_reason,
        reply_template=template,
        extraction_method=f"openrouter:{model}",
    )

