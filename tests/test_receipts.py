"""Pytest suite for the Donation Receipt Generator core logic."""

import io
import zipfile

import pandas as pd
import pytest

from receipts import (
    create_receipt_pdf,
    create_receipts_zip,
    receipt_number,
    validate_donations,
)


def make_df(rows):
    return pd.DataFrame(rows, columns=["donor_name", "email", "amount", "date"])


GOOD_ROW = {
    "donor_name": "Ayesha Khan",
    "email": "ayesha@example.com",
    "amount": 5000,
    "date": "2026-10-01",
}


# ---------- validation ----------


def test_valid_csv_passes():
    df = make_df([GOOD_ROW, {**GOOD_ROW, "donor_name": "Bilal Ahmed"}])
    valid, errors = validate_donations(df)
    assert errors == []
    assert len(valid) == 2
    assert valid[0]["amount"] == 5000.0


def test_missing_column_reported():
    df = pd.DataFrame([{"donor_name": "X", "email": "x@y.z", "amount": 10}])
    valid, errors = validate_donations(df)
    assert valid == []
    assert any("date" in e for e in errors)


def test_empty_donor_name_flagged():
    df = make_df([{**GOOD_ROW, "donor_name": "   "}])
    valid, errors = validate_donations(df)
    assert valid == []
    assert any("donor_name" in e for e in errors)


def test_invalid_email_flagged():
    df = make_df([{**GOOD_ROW, "email": "not-an-email"}])
    valid, errors = validate_donations(df)
    assert valid == []
    assert any("email" in e for e in errors)


def test_non_numeric_amount_flagged():
    df = make_df([{**GOOD_ROW, "amount": "lots"}])
    valid, errors = validate_donations(df)
    assert valid == []
    assert any("amount" in e for e in errors)


def test_negative_amount_flagged():
    df = make_df([{**GOOD_ROW, "amount": -100}])
    valid, errors = validate_donations(df)
    assert valid == []
    assert any("greater than 0" in e for e in errors)


def test_bad_date_format_flagged():
    df = make_df([{**GOOD_ROW, "date": "01-10-2026"}])
    valid, errors = validate_donations(df)
    assert valid == []
    assert any("YYYY-MM-DD" in e for e in errors)


def test_mixed_rows_keep_good_skip_bad():
    df = make_df([GOOD_ROW, {**GOOD_ROW, "email": "bad"}])
    valid, errors = validate_donations(df)
    assert len(valid) == 1
    assert len(errors) == 1
    assert "Row 3" in errors[0]


# ---------- receipt numbering ----------


def test_receipt_number_format():
    assert receipt_number(0, year=2026) == "TAF-2026-0001"
    assert receipt_number(9, year=2026) == "TAF-2026-0010"
    assert receipt_number(123, year=2026) == "TAF-2026-0124"


def test_receipt_numbers_unique():
    nums = [receipt_number(i, year=2026) for i in range(50)]
    assert len(set(nums)) == 50


# ---------- PDF generation ----------


def test_receipt_pdf_is_valid_pdf():
    pdf = create_receipt_pdf(
        {"donor_name": "Ayesha Khan", "email": "a@b.co", "amount": 5000.0, "date": "2026-10-01"},
        "TAF-2026-0001",
    )
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 1000


def test_receipt_pdf_contains_donor_details():
    pdf = create_receipt_pdf(
        {"donor_name": "Zara Unique", "email": "z@b.co", "amount": 7777.0, "date": "2026-10-02"},
        "TAF-2026-0042",
        compress=False,
    )
    text = pdf.decode("latin-1")
    assert "Zara Unique" in text
    assert "TAF-2026-0042" in text
    assert "7,777.00" in text


# ---------- ZIP creation ----------


def test_zip_contains_one_pdf_per_donor():
    donors = [
        {"donor_name": "A", "email": "a@b.co", "amount": 10.0, "date": "2026-10-01"},
        {"donor_name": "B", "email": "b@b.co", "amount": 20.0, "date": "2026-10-02"},
    ]
    zbytes = create_receipts_zip(donors, year=2026)
    with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
        names = zf.namelist()
    assert len(names) == 2
    assert all(n.endswith(".pdf") for n in names)
    assert any(n.startswith("TAF-2026-0001") for n in names)
    assert any(n.startswith("TAF-2026-0002") for n in names)


def test_zip_filenames_unique_for_duplicate_names():
    donors = [
        {"donor_name": "Same Name", "email": "a@b.co", "amount": 10.0, "date": "2026-10-01"},
        {"donor_name": "Same Name", "email": "b@b.co", "amount": 20.0, "date": "2026-10-02"},
    ]
    zbytes = create_receipts_zip(donors, year=2026)
    with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
        names = zf.namelist()
    assert len(names) == len(set(names)) == 2
