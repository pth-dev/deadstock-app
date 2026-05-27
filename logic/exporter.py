from __future__ import annotations

import io
from typing import Dict, List, Tuple

import pandas as pd


def export_to_xlsx(df_result: pd.DataFrame, summary: Dict[str, object]) -> bytes:
    """Export detail and summary to an in-memory .xlsx."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_result.to_excel(writer, sheet_name="Detail", index=False)
        df_summary = _build_summary_df(summary)
        df_summary.to_excel(writer, sheet_name="Summary", index=False, header=False)

        workbook = writer.book
        detail_ws = writer.sheets["Detail"]
        summary_ws = writer.sheets["Summary"]

        header_fmt = workbook.add_format({"bold": True})
        for col_idx, col_name in enumerate(df_result.columns):
            detail_ws.write(0, col_idx, col_name, header_fmt)

        if len(df_result.columns) > 0:
            last_col = len(df_result.columns) - 1
            last_row = max(len(df_result), 1)
            detail_ws.freeze_panes(1, 0)
            detail_ws.autofilter(0, 0, last_row, last_col)

            if "Age" in df_result.columns:
                age_col = int(df_result.columns.get_loc("Age"))
                yellow_fmt = workbook.add_format({"bg_color": "#FFF2CC"})
                red_fmt = workbook.add_format({"bg_color": "#FFE0E0"})
                detail_ws.conditional_format(
                    1,
                    age_col,
                    last_row,
                    age_col,
                    {
                        "type": "cell",
                        "criteria": "between",
                        "minimum": 361,
                        "maximum": 540,
                        "format": yellow_fmt,
                    },
                )
                detail_ws.conditional_format(
                    1,
                    age_col,
                    last_row,
                    age_col,
                    {
                        "type": "cell",
                        "criteria": ">",
                        "value": 540,
                        "format": red_fmt,
                    },
                )

        summary_header_fmt = workbook.add_format({"bold": True})
        for row_idx in range(len(df_summary)):
            summary_ws.write(row_idx, 0, df_summary.iloc[row_idx, 0], summary_header_fmt)
            summary_ws.write(row_idx, 1, df_summary.iloc[row_idx, 1])

        summary_ws.set_column(0, 0, 36)
        summary_ws.set_column(1, 1, 24)

    output.seek(0)
    return output.getvalue()


def _build_summary_df(summary: Dict[str, object]) -> pd.DataFrame:
    breakdown = summary.get("breakdown") or {}

    rows: List[Tuple[str, object]] = [
        ("Source filename", summary.get("filename", "")),
        ("Processed at (UTC+7)", summary.get("processed_at", "")),
        ("Total immobile items", summary.get("immobile_items", 0)),
        ("Total Closing qty", summary.get("closing_qty_total", 0)),
        ("Total Closing val", summary.get("closing_val_total", 0)),
        ("Items age 361-540 (count)", summary.get("age_361_540_count", 0)),
        ("361-540 days val total", summary.get("age_361_540_val", 0)),
        ("Items age > 540 (count)", summary.get("age_540_count", 0)),
        (">540 days val total", summary.get("age_540_val", 0)),
    ]

    if breakdown:
        rows.extend(
            [
                ("Breakdown - total rows", breakdown.get("total_rows", 0)),
                ("Breakdown - blank rows", breakdown.get("blank_rows", 0)),
                ("Breakdown - invalid rows", breakdown.get("invalid_rows", 0)),
                ("Breakdown - rejected age", breakdown.get("rejected_age", 0)),
                ("Breakdown - rejected zero", breakdown.get("rejected_zero", 0)),
                ("Breakdown - rejected moved", breakdown.get("rejected_moved", 0)),
                ("Breakdown - passed", breakdown.get("passed", 0)),
            ]
        )

    return pd.DataFrame(rows, columns=["Metric", "Value"])
