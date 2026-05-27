from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd

KEEP_COLUMNS: List[str] = [
    "Warehouse",
    "Style#",
    "Item#",
    "Item name",
    "Unit",
    "Stock zone",
    "Business area",
    "Buyer",
    "Account control code",
    "Item type",
    "reference order number",
    "Opening qty",
    "Opening val",
    "Closing qty",
    "Closing val",
    "Receiving date",
    "Age",
    "361-540 days qty",
    "361-540 days val",
    ">540 days qty",
    ">540 days val",
    "Procument group",
    "Liability",
    "PO_Pretext",
]


def apply(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Filter immobile stock items and return result with breakdown."""
    required_cols = ["Item#", "Age", "Opening qty", "Closing qty"]
    missing_required = [col for col in required_cols if col not in df.columns]
    if missing_required:
        missing_text = ", ".join(missing_required)
        raise ValueError(f"Missing required columns: {missing_text}")

    total_rows = int(len(df))
    if total_rows == 0:
        breakdown = {
            "total_rows": 0,
            "blank_rows": 0,
            "invalid_rows": 0,
            "rejected_age": 0,
            "rejected_zero": 0,
            "rejected_moved": 0,
            "passed": 0,
        }
        return df.copy(), breakdown

    item_series = df["Item#"].astype("string")
    blank_mask = item_series.isna() | item_series.str.strip().eq("")
    blank_rows = int(blank_mask.sum())

    df_nonblank = df.loc[~blank_mask].copy()
    for col in ["Age", "Opening qty", "Closing qty"]:
        df_nonblank[col] = pd.to_numeric(df_nonblank[col], errors="coerce")

    numeric_mask = df_nonblank[["Age", "Opening qty", "Closing qty"]].notna().all(axis=1)
    invalid_rows = int((~numeric_mask).sum())
    df_valid = df_nonblank.loc[numeric_mask].copy()

    rejected_age_mask = df_valid["Age"] <= 360
    rejected_age = int(rejected_age_mask.sum())
    df_age = df_valid.loc[~rejected_age_mask].copy()

    rejected_zero_mask = df_age["Opening qty"] == 0
    rejected_zero = int(rejected_zero_mask.sum())
    df_qty = df_age.loc[~rejected_zero_mask].copy()

    rejected_moved_mask = df_qty["Opening qty"] != df_qty["Closing qty"]
    rejected_moved = int(rejected_moved_mask.sum())
    df_passed = df_qty.loc[~rejected_moved_mask].copy()

    keep_cols = [col for col in KEEP_COLUMNS if col in df_passed.columns]
    df_result = df_passed.loc[:, keep_cols].copy()

    breakdown = {
        "total_rows": total_rows,
        "blank_rows": blank_rows,
        "invalid_rows": invalid_rows,
        "rejected_age": rejected_age,
        "rejected_zero": rejected_zero,
        "rejected_moved": rejected_moved,
        "passed": int(len(df_passed)),
    }

    return df_result, breakdown
