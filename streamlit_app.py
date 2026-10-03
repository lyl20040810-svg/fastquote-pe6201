"""Publicly reachable FastQuote review UI for Streamlit Community Cloud."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from fastquote.service import QuoteService


ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="FastQuote", layout="wide")

try:
    cloud_secrets = st.secrets
    for name in ("OPENROUTER_API_KEY", "OPENROUTER_MODEL"):
        value = cloud_secrets.get(name, "")
        if value:
            os.environ[name] = str(value)
except FileNotFoundError:
    pass


@st.cache_resource
def get_service() -> QuoteService:
    return QuoteService(ROOT)


st.title("FastQuote")
st.caption("Fastener quotation review")

with st.form("quotation_request"):
    request = st.text_area(
        "Customer request",
        value="Please quote M16x50, 2 cartons.",
        height=100,
    )
    mode = st.selectbox("Extraction mode", ("Auto", "Rules", "OpenRouter"))
    submitted = st.form_submit_button("Generate quotation", type="primary")

if submitted:
    try:
        st.session_state["quote_result"] = get_service().quote(request, mode.lower())
    except (RuntimeError, ValueError) as exc:
        st.session_state["quote_result"] = None
        st.error(str(exc))

result = st.session_state.get("quote_result")
if result:
    if result["processing_status"] == "flagged":
        st.warning(result.get("message", "This request needs manual review."))
    elif result["processing_status"] == "quoted":
        pricing = result["pricing"]
        row = result["catalog_match"]
        approval = result["manager_approval_required"]

        if approval:
            st.error("NEED MANAGER APPROVAL")
        else:
            st.success("READY FOR REVIEW")

        first, second, third, fourth = st.columns(4)
        first.metric("Product", row["sku"])
        second.metric("Total pieces", f"{pricing['total_pieces']:,}")
        third.metric("Quoted total", f"CNY {pricing['revenue_cny']:,.2f}")
        fourth.metric("Need Approval", "YES" if approval else "NO")

        st.subheader("Calculation")
        st.table({
            "Field": [
                "Discount", "Total cost", "Small-order cost", "Gross margin"
            ],
            "Value": [
                f"{pricing['discount_rate'] * 100:.0f}%",
                f"CNY {pricing['total_cost_cny']:,.2f}",
                f"CNY {pricing['small_order_surcharge_cny']:,.2f}",
                f"{pricing['gross_margin_percent']:.2f}%",
            ],
        })

        st.subheader("Customer reply draft")
        st.code(result["customer_reply_draft"], language=None)
        st.caption("A salesperson must review the quotation before sending it.")

        with st.expander("Calculation details"):
            st.json(result)
