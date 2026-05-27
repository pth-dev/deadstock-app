from __future__ import annotations

import streamlit as st


def render_summary_cards(summary: dict) -> None:
    """Render summary metric cards."""
    if not summary:
        st.info("No summary data available.")
        return

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Immobile Items", _format_count(summary.get("immobile_items")))
    col2.metric("Age 361-540 Items", _format_count(summary.get("age_361_540_count")))
    col3.metric("361-540 days val (VND)", _format_money(summary.get("age_361_540_val")))
    col4.metric("Age > 540 Items", _format_count(summary.get("age_540_count")))
    col5.metric(">540 days val (VND)", _format_money(summary.get("age_540_val")))


def _format_count(value: object) -> str:
    try:
        return f"{int(float(value)):,}"
    except (TypeError, ValueError):
        return "0"


def _format_qty(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "0"

    formatted = f"{number:,.3f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


def _format_money(value: object) -> str:
    try:
        return f"{float(value):,.0f} VND"
    except (TypeError, ValueError):
        return "0 VND"
