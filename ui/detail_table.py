from __future__ import annotations

import pandas as pd
import streamlit as st


def render_detail_table(df: pd.DataFrame) -> None:
    """Render detail table with sorting and scroll."""
    if df is None or df.empty:
        st.info("No rows matched the filter.")
        return

    formatters = _build_formatters(df)
    styled = df.style.format(formatters, na_rep="")
    if "Age" in df.columns:
        styled = styled.applymap(_age_style, subset=["Age"])

    st.dataframe(styled, height=600, use_container_width=True, hide_index=True)


def _age_style(value: object) -> str:
    if pd.isna(value):
        return ""
    try:
        age_value = float(value)
    except (TypeError, ValueError):
        return ""

    if age_value > 540:
        return "background-color: #FFE0E0"
    if 361 <= age_value <= 540:
        return "background-color: #FFF2CC"
    return ""


def _build_formatters(df: pd.DataFrame) -> dict:
    int_columns = {"Age", "reference order number"}
    qty_columns = {
        "Opening qty",
        "Closing qty",
        "361-540 days qty",
        ">540 days qty",
    }
    val_columns = {
        "Opening val",
        "Closing val",
        "361-540 days val",
        ">540 days val",
    }

    formatters = {}
    for col in df.columns:
        if col in int_columns:
            formatters[col] = _format_int
        elif col in qty_columns:
            formatters[col] = _format_qty
        elif col in val_columns:
            formatters[col] = _format_money

    return formatters


def _format_int(value: object) -> str:
    if pd.isna(value):
        return ""
    try:
        return f"{int(float(value)):,}"
    except (TypeError, ValueError):
        return ""


def _format_qty(value: object) -> str:
    if pd.isna(value):
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""

    formatted = f"{number:,.3f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


def _format_money(value: object) -> str:
    if pd.isna(value):
        return ""
    try:
        return f"{float(value):,.0f} VND"
    except (TypeError, ValueError):
        return ""
