# TechAbout Foundation — Donation Receipt Generator

A Streamlit web app that turns a CSV of donations into individual PDF receipts and bundles them into a single ZIP download. Built for the TechAbout Foundation's donor-management workflow.

Built for [BlogReach.com](https://blogreach.com) — guest-posting marketplace.

## What it does

1. **CSV upload with validation** — Upload a donations CSV. Required columns: `donor_name`, `email`, `amount`, `date` (YYYY-MM-DD). Every row is validated; bad rows are listed with clear per-row error messages (e.g. "Row 4: email 'x' is not valid") while good rows are kept.
2. **One PDF receipt per donor** — Each receipt has a unique receipt number (`TAF-2026-0001`, …), donor name, email, date, amount, and a thank-you message. Generated with fpdf2.
3. **Download all as ZIP** — One button builds an in-memory ZIP containing every receipt PDF, with unique filenames even for duplicate donor names.
4. **Privacy by design** — Donor data lives only in Streamlit session-state memory. Nothing is written to disk or a database. A "Clear all data" button wipes the session; closing the tab does the same.

## Setup

```bash
git clone https://github.com/Bilal175-gif/donation-receipt-generator.git
cd donation-receipt-generator
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL Streamlit prints (usually http://localhost:8501).

A sample file is included: `mock_donations.csv` (8 donors) for a quick end-to-end try.

## How I tested it

- **Automated tests:** 14 pytest tests in `tests/test_receipts.py` covering CSV validation (missing columns, empty names, bad emails, non-numeric/negative amounts, bad dates, mixed good+bad rows), receipt-number format and uniqueness, PDF generation (valid `%PDF-` header, donor details embedded), and ZIP creation (one PDF per donor, unique filenames for duplicate names). Run with `pytest tests/ -v` — all 14 pass.
- **Full flow test:** loaded `mock_donations.csv` (8 donors) → validation returned 8 valid / 0 errors → ZIP contained 8 valid PDFs.
- **Local run:** `streamlit run app.py` serves the app with HTTP 200 and zero errors in the server log; the upload → validate → generate → ZIP-download flow works in the UI.

## Limitations

- Amounts are formatted as PKR; multi-currency is not supported.
- Receipts are generated on demand — there is no database, donor history, or re-print lookup.
- Email validation is format-only (regex), not deliverability-checked.
- Very large CSVs (tens of thousands of rows) will be slow since every PDF is rendered in memory.
- The app is single-user per browser session; concurrent sessions do not share state.
- No authentication — do not expose it publicly with real donor data.

## Project structure

```
app.py                Streamlit UI
receipts.py           Core logic: validation, PDF, ZIP (no Streamlit, fully tested)
mock_donations.csv    8 sample donors for testing
tests/                pytest suite (14 tests)
requirements.txt      Pinned dependencies
.env.example          Config convention (no secrets needed)
```
