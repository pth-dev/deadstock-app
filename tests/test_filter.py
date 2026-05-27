from __future__ import annotations

import io
import unittest

import pandas as pd

from logic import filter as filter_logic
from logic import reader


class UploadedBytes(io.BytesIO):
	def __init__(self, data: bytes, name: str) -> None:
		super().__init__(data)
		self.name = name


class ReaderTests(unittest.TestCase):
	def _make_upload(self, df: pd.DataFrame, name: str) -> UploadedBytes:
		buffer = io.BytesIO()
		df.to_excel(buffer, index=False, engine="openpyxl")
		return UploadedBytes(buffer.getvalue(), name)

	def _make_upload_with_header_offset(self, headers: list, rows: list, name: str) -> UploadedBytes:
		from openpyxl import Workbook

		workbook = Workbook()
		worksheet = workbook.active
		worksheet.append(["Report title"])
		worksheet.append(headers)
		for row in rows:
			worksheet.append(row)
		buffer = io.BytesIO()
		workbook.save(buffer)
		return UploadedBytes(buffer.getvalue(), name)

	def test_load_trims_headers_and_adds_missing_optional(self) -> None:
		df = pd.DataFrame(
			{
				" Item# ": ["A001"],
				"Item name": ["Item A"],
				"Age": [400],
				"Opening qty ": [10],
				"Closing qty": [10],
			}
		)
		upload = self._make_upload(df, "sample.xlsx")

		df_out, meta = reader.load(upload)

		self.assertIn("Item#", df_out.columns)
		self.assertIn("Warehouse", df_out.columns)
		self.assertTrue(df_out["Warehouse"].isna().all())
		self.assertEqual(meta.get("skipped_rows"), 0)

	def test_load_missing_required_raises(self) -> None:
		df = pd.DataFrame({"Item name": ["Item A"], "Age": [100]})
		upload = self._make_upload(df, "bad.xlsx")

		with self.assertRaises(ValueError):
			reader.load(upload)

	def test_load_header_on_second_row(self) -> None:
		headers = ["Item#", "Item name", "Age", "Opening qty", "Closing qty"]
		rows = [["A001", "Item A", 400, 10, 10]]
		upload = self._make_upload_with_header_offset(headers, rows, "offset.xlsx")

		df_out, _ = reader.load(upload)
		self.assertIn("Item#", df_out.columns)
		self.assertEqual(len(df_out), 1)


class FilterTests(unittest.TestCase):
	def test_apply_breakdown_counts(self) -> None:
		df = pd.DataFrame(
			{
				"Item#": ["A", "", "C", "D", "E", "F"],
				"Age": [400, 400, "x", 100, 400, 400],
				"Opening qty": [10, 10, 10, 10, 0, 10],
				"Closing qty": [10, 10, 10, 10, 0, 5],
				"Closing val": [100, 100, 100, 100, 0, 50],
			}
		)

		df_result, breakdown = filter_logic.apply(df)

		self.assertEqual(breakdown["total_rows"], 6)
		self.assertEqual(breakdown["blank_rows"], 1)
		self.assertEqual(breakdown["invalid_rows"], 1)
		self.assertEqual(breakdown["rejected_age"], 1)
		self.assertEqual(breakdown["rejected_zero"], 1)
		self.assertEqual(breakdown["rejected_moved"], 1)
		self.assertEqual(breakdown["passed"], 1)

		self.assertEqual(len(df_result), 1)
		self.assertEqual(df_result.iloc[0]["Item#"], "A")

	def test_apply_missing_required_raises(self) -> None:
		df = pd.DataFrame({"Item#": ["A"], "Age": [400], "Opening qty": [1]})

		with self.assertRaises(ValueError):
			filter_logic.apply(df)


if __name__ == "__main__":
	unittest.main()
