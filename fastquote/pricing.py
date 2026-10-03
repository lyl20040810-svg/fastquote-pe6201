"""Deterministic packaging conversion and quotation calculation."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


MONEY = Decimal("0.01")


def money(value: Decimal) -> float:
    return float(value.quantize(MONEY, rounding=ROUND_HALF_UP))


def calculate_quote(row: dict[str, Any], quantity: int, unit: str) -> dict[str, Any]:
    if not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("Quantity must be a positive whole number.")

    pieces_per_box = int(row["pieces_per_box"])
    boxes_per_carton = int(row["boxes_per_carton"])
    pieces_per_carton = pieces_per_box * boxes_per_carton
    normalized_unit = unit.lower()

    multipliers = {
        "piece": 1,
        "box": pieces_per_box,
        "carton": pieces_per_carton,
    }
    if normalized_unit not in multipliers:
        raise ValueError("Unit must be piece, box, or carton.")

    total_pieces = quantity * multipliers[normalized_unit]
    carton_equivalent = Decimal(total_pieces) / Decimal(pieces_per_carton)
    if carton_equivalent >= Decimal("10"):
        discount_rate = Decimal("0.15")
    elif carton_equivalent >= Decimal("5"):
        discount_rate = Decimal("0.10")
    elif carton_equivalent >= Decimal("1"):
        discount_rate = Decimal("0.05")
    else:
        discount_rate = Decimal("0")

    list_price_per_thousand = Decimal(str(row["list_price_per_thousand_cny"]))
    list_unit_price = list_price_per_thousand / Decimal("1000")
    cost_before_surcharge = list_unit_price * Decimal("0.4") * Decimal(total_pieces)
    surcharge = Decimal("5") if total_pieces < pieces_per_box else Decimal("0")
    total_cost = cost_before_surcharge + surcharge
    base_revenue = list_unit_price * Decimal("0.5") * Decimal(total_pieces)
    revenue = base_revenue * (Decimal("1") - discount_rate)
    if revenue <= 0:
        raise ValueError("Revenue must be positive.")
    gross_margin = (revenue - total_cost) / revenue * Decimal("100")
    status = "manager_approval" if gross_margin < Decimal("10") else "normal"

    return {
        "total_pieces": total_pieces,
        "pieces_per_box": pieces_per_box,
        "boxes_per_carton": boxes_per_carton,
        "pieces_per_carton": pieces_per_carton,
        "carton_equivalent": float(carton_equivalent.quantize(Decimal("0.0001"))),
        "list_price_per_thousand_cny": money(list_price_per_thousand),
        "cost_rate": 0.4,
        "base_selling_rate": 0.5,
        "discount_rate": float(discount_rate),
        "small_order_surcharge_cny": money(surcharge),
        "total_cost_cny": money(total_cost),
        "revenue_cny": money(revenue),
        "gross_profit_cny": money(revenue - total_cost),
        "gross_margin_percent": float(gross_margin.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "approval_status": status,
    }

