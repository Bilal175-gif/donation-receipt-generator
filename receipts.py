"""Core logic for the TechAbout Foundation Donation Receipt Generator.

Pure functions only (no Streamlit, no disk I/O) so the whole module is
unit-testable. All donor data stays in memory — nothing is ever written
to disk by this module.
"""

import io
import re
import zipfile
from datetime import datetime

from fpdf import FPDF

REQUIRED_COLUMNS = ["donor_name", "email", "amount", "date"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ORG_NAME = "TechAbout Foundation"


def validate_donations(df):
    """Validate an uploaded donations DataFrame.

    Returns (valid_rows, errors) where valid_rows is a list of dicts with
    keys donor_name, email, amount (float), date (str) and errors is a list
    of human-readable strings like "Row 3: ...".
    """
    errors = []
    valid_rows = []

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        errors.append(
            "Missing required column(s): " + ", ".join(missing)
            + ". Required columns: " + ", ".join(REQUIRED_COLUMNS)
        )
        return [], errors

    if df.empty:
        errors.append("The uploaded file has no data rows.")
        return [], errors

    for i, row in df.iterrows():
        row_no = i + 2  # +1 for 0-index header, +1 for 1-based rows
        name = str(row["donor_name"]).strip() if row["donor_name"] is not None else ""
        email = str(row["email"]).strip() if row["email"] is not None else ""
        raw_amount = row["amount"]
        date = str(row["date"]).strip() if row["date"] is not None else ""

        if not name or name.lower() == "nan":
            errors.append(f"Row {row_no}: donor_name is empty.")
            continue
        if not EMAIL_RE.match(email):
            errors.append(f"Row {row_no}: email '{email}' is not valid.")
            continue
        try:
            amount = float(raw_amount)
        except (TypeError, ValueError):
            errors.append(f"Row {row_no}: amount '{raw_amount}' is not a number.")
            continue
        if amount <= 0:
            errors.append(f"Row {row_no}: amount must be greater than 0 (got {amount}).")
            continue
        if not date or date.lower() == "nan":
            errors.append(f"Row {row_no}: date is empty.")
            continue
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            errors.append(f"Row {row_no}: date '{date}' must be YYYY-MM-DD.")
            continue

        valid_rows.append(
            {"donor_name": name, "email": email, "amount": amount, "date": date}
        )

    return valid_rows, errors


def receipt_number(index, year=None):
    """Unique receipt number like TAF-2026-0001 (1-based index)."""
    year = year or datetime.now().year
    return f"TAF-{year}-{index + 1:04d}"


def create_receipt_pdf(donor, receipt_no, compress=True):
    """Build one donation receipt PDF. Returns PDF bytes."""
    pdf = FPDF()
    pdf.set_compression(compress)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Header band
    pdf.set_fill_color(15, 76, 129)
    pdf.rect(0, 0, 210, 38, "F")
    pdf.set_xy(10, 10)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 10, ORG_NAME, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, "Official Donation Receipt", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(12)
    pdf.set_text_color(0, 0, 0)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, "Thank you for your generosity!", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0,
        6,
        "Dear " + donor["donor_name"] + ",\n\n"
        "Thank you for supporting the TechAbout Foundation. Your contribution "
        "helps us fund free tech education, open-source projects and community "
        "events across Pakistan. This receipt confirms your donation details below.",
    )
    pdf.ln(4)

    # Details table
    pdf.set_fill_color(240, 244, 248)
    rows = [
        ("Receipt No", receipt_no),
        ("Donor Name", donor["donor_name"]),
        ("Email", donor["email"]),
        ("Donation Date", donor["date"]),
        ("Amount", f"PKR {donor['amount']:,.2f}"),
    ]
    for label, value in rows:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(45, 9, " " + label, fill=True)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 9, " " + str(value), fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(
        0,
        6,
        "This is a computer-generated receipt and does not require a signature. "
        "For queries, contact donations@techabout.com.",
    )

    out = pdf.output()
    return bytes(out)


def create_receipts_zip(donors, year=None):
    """Create a ZIP (bytes) with one receipt PDF per donor.

    Filenames are unique even for duplicate donor names.
    """
    buf = io.BytesIO()
    seen = set()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, donor in enumerate(donors):
            rno = receipt_number(i, year=year)
            pdf_bytes = create_receipt_pdf(donor, rno)
            safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", donor["donor_name"]).strip("_")
            fname = f"{rno}_{safe_name}.pdf"
            j = 1
            while fname in seen:
                j += 1
                fname = f"{rno}_{safe_name}_{j}.pdf"
            seen.add(fname)
            zf.writestr(fname, pdf_bytes)
    buf.seek(0)
    return buf.getvalue()
