from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict, Tuple

import pandas as pd

from .filter import KEEP_COLUMNS

REQUIRED_COLUMNS = ["Item#", "Item name", "Age", "Opening qty", "Closing qty"]
NUMERIC_COLUMNS = ["Age", "Opening qty", "Closing qty", "Opening val", "Closing val"]


def _safe_to_str(value: object) -> object:
    if pd.isna(value):
        return pd.NA
    return str(value).strip()


def load(uploaded_file) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Load .xls/.xlsx, normalize headers, and validate required columns."""
    if uploaded_file is None:
        raise ValueError("No file provided")

    filename = getattr(uploaded_file, "name", "uploaded_file")
    extension = Path(filename).suffix.lower()
    if extension not in {".xls", ".xlsx"}:
        raise ValueError(f"Unsupported file type: {extension}")

    engine = "xlrd" if extension == ".xls" else "openpyxl"
    file_obj = uploaded_file
    if isinstance(uploaded_file, (bytes, bytearray)):
        file_obj = io.BytesIO(uploaded_file)

    df = pd.read_excel(file_obj, engine=engine, converters={"Item#": _safe_to_str})
    if df.empty:
        raise ValueError("File contains no data")

    df.columns = [col.strip() if isinstance(col, str) else col for col in df.columns]

    original_rows = len(df)
    df = df.dropna(how="all")
    skipped_rows = original_rows - len(df)
    if df.empty:
        raise ValueError("File contains no data")

    missing_required = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_required:
        missing_text = ", ".join(missing_required)
        raise ValueError(f"Missing required columns: {missing_text}")

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Item#"] = df["Item#"].astype("string")

    if df["Opening qty"].isna().all() and df["Closing qty"].isna().all():
        raise ValueError("Could not parse numeric data")

    optional_columns = [col for col in KEEP_COLUMNS if col not in REQUIRED_COLUMNS]
    missing_optional_cols = [col for col in optional_columns if col not in df.columns]
    for col in missing_optional_cols:
        df[col] = pd.NA

    meta = {
        "filename": filename,
        "total_rows": len(df),
        "skipped_rows": skipped_rows,
        "missing_optional_cols": missing_optional_cols,
    }

    return df, meta
