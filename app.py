from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from logic import exporter, filter as filter_logic, reader
from ui.detail_table import render_detail_table
from ui.summary_card import render_summary_cards


def main() -> None:
    st.set_page_config(page_title="Warehouse 090 - Dead Stock Filter", layout="wide")
    st.title("Warehouse 090 - Dead Stock Filter")

    _init_state()

    uploaded_file = st.file_uploader(
        "Step 1: Upload file (.xls or .xlsx)",
        type=["xls", "xlsx"],
    )
    if uploaded_file is not None and getattr(uploaded_file, "size", 0) > 80 * 1024 * 1024:
        st.warning("File is larger than 80 MB and may exceed free-tier memory limits.")

    run_clicked = st.button("Run Analysis", disabled=uploaded_file is None)
    if run_clicked:
        if uploaded_file is None:
            st.warning("Please upload a file before running analysis.")
        else:
            _process_file(uploaded_file)

    if st.session_state.get("processed"):
        summary = st.session_state.get("summary")
        df_result = st.session_state.get("df_result")

        render_summary_cards(summary)
        _render_breakdown(summary)
        render_detail_table(df_result)

        excel_bytes = st.session_state.get("excel_bytes")
        if excel_bytes:
            st.download_button(
                label="Download Result (.xlsx)",
                data=excel_bytes,
                file_name=_build_output_filename(summary),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


def _init_state() -> None:
    if "processed" not in st.session_state:
        st.session_state["processed"] = False
        st.session_state["df_result"] = None
        st.session_state["summary"] = None
        st.session_state["excel_bytes"] = None


def _process_file(uploaded_file) -> None:
    try:
        with st.spinner("Processing..."):
            df, meta = reader.load(uploaded_file)
            df_result, breakdown = filter_logic.apply(df)
            summary = _build_summary(df_result, breakdown, meta)
            excel_bytes = exporter.export_to_xlsx(df_result, summary)

        st.session_state["df_result"] = df_result
        st.session_state["summary"] = summary
        st.session_state["excel_bytes"] = excel_bytes
        st.session_state["processed"] = True
    except Exception as exc:
        st.session_state["processed"] = False
        st.error(str(exc))


def _build_summary(
    df_result: pd.DataFrame,
    breakdown: dict,
    meta: dict,
) -> dict:
    now = datetime.now(timezone(timedelta(hours=7)))
    processed_at = now.strftime("%Y-%m-%d %H:%M")

    closing_qty_total = (
        float(df_result["Closing qty"].sum()) if "Closing qty" in df_result.columns else 0.0
    )
    closing_val_total = (
        float(df_result["Closing val"].sum()) if "Closing val" in df_result.columns else 0.0
    )

    if "Age" in df_result.columns:
        age_series = pd.to_numeric(df_result["Age"], errors="coerce")
        mask_361_540 = (age_series >= 361) & (age_series <= 540)
        mask_540 = age_series > 540
    else:
        mask_361_540 = pd.Series([False] * len(df_result), index=df_result.index)
        mask_540 = pd.Series([False] * len(df_result), index=df_result.index)

    age_361_540_count = int(mask_361_540.sum())
    age_540_count = int(mask_540.sum())

    if "361-540 days val" in df_result.columns:
        age_361_540_val = float(
            pd.to_numeric(df_result["361-540 days val"], errors="coerce").sum()
        )
    else:
        age_361_540_val = 0.0

    if ">540 days val" in df_result.columns:
        age_540_val = float(
            pd.to_numeric(df_result[">540 days val"], errors="coerce").sum()
        )
    else:
        age_540_val = 0.0

    return {
        "filename": meta.get("filename", ""),
        "processed_at": processed_at,
        "immobile_items": int(len(df_result)),
        "closing_qty_total": closing_qty_total,
        "closing_val_total": closing_val_total,
        "age_361_540_count": age_361_540_count,
        "age_361_540_val": age_361_540_val,
        "age_540_count": age_540_count,
        "age_540_val": age_540_val,
        "breakdown": breakdown,
        "meta": meta,
    }


def _render_breakdown(summary: dict) -> None:
    breakdown = (summary or {}).get("breakdown") or {}
    if not breakdown:
        return

    rows = [
        ("Total rows read", breakdown.get("total_rows", 0)),
        ("Blank rows skipped", breakdown.get("blank_rows", 0)),
        ("Invalid data skipped", breakdown.get("invalid_rows", 0)),
        ("Rejected age <= 360", breakdown.get("rejected_age", 0)),
        ("Rejected qty = 0", breakdown.get("rejected_zero", 0)),
        ("Rejected moved", breakdown.get("rejected_moved", 0)),
        ("Passed", breakdown.get("passed", 0)),
    ]
    breakdown_df = pd.DataFrame(rows, columns=["Metric", "Value"])

    with st.expander("Filter Breakdown", expanded=False):
        st.table(breakdown_df)


def _build_output_filename(summary: dict) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return f"deadstock_result_{timestamp}.xlsx"


if __name__ == "__main__":
    main()
