"""TechAbout Foundation — Donation Receipt Generator (Streamlit UI).

Upload a CSV of donations, validate it, preview valid rows, generate one
PDF receipt per donor and download everything as a ZIP. All data lives in
memory only (Streamlit session state) and is wiped on "Clear data" or when
the session ends — nothing is stored on disk or in a database.
"""

import io
from datetime import datetime

import pandas as pd
import streamlit as st

from receipts import (
    REQUIRED_COLUMNS,
    create_receipt_pdf,
    create_receipts_zip,
    receipt_number,
    validate_donations,
)

st.set_page_config(page_title="Donation Receipt Generator", page_icon="🧾")
st.title("🧾 TechAbout Foundation — Donation Receipt Generator")
st.caption(
    "Upload a donations CSV → validate → generate PDF receipts → download a ZIP. "
    "Your data stays in memory only and is never saved anywhere."
)

with st.expander("CSV format help", expanded=False):
    st.markdown(
        "Your CSV **must** have these exact columns:\n\n"
        "- `donor_name` — full name of the donor\n"
        "- `email` — valid email address\n"
        "- `amount` — donation amount as a positive number (PKR)\n"
        "- `date` — donation date as `YYYY-MM-DD`\n\n"
        "Example:\n"
        "```csv\n"
        "donor_name,email,amount,date\n"
        "Ayesha Khan,ayesha@example.com,5000,2026-10-01\n"
        "```"
    )

uploaded = st.file_uploader("Upload donations CSV", type=["csv"])

if uploaded is not None:
    try:
        df = pd.read_csv(uploaded)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not read the CSV file: {exc}")
        st.stop()

    valid_rows, errors = validate_donations(df)

    if errors:
        st.warning(f"Found {len(errors)} problem(s) in the file:")
        for err in errors:
            st.error(err)

    if valid_rows:
        st.success(f"✅ {len(valid_rows)} valid donation(s) ready for receipts.")
        st.dataframe(
            pd.DataFrame(valid_rows)[["donor_name", "email", "amount", "date"]],
            use_container_width=True,
        )
        st.session_state["valid_rows"] = valid_rows
    else:
        st.info("No valid rows to process. Fix the errors above and re-upload.")
        st.session_state.pop("valid_rows", None)
        st.stop()

valid_rows = st.session_state.get("valid_rows")

if valid_rows:
    year = datetime.now().year
    st.subheader("Generate receipts")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧾 Generate all receipts", type="primary"):
            with st.spinner("Creating PDFs…"):
                zip_bytes = create_receipts_zip(valid_rows, year=year)
            st.session_state["zip_bytes"] = zip_bytes
            st.success(f"Generated {len(valid_rows)} receipts.")

    with col2:
        if st.button("🗑️ Clear all data"):
            for key in ("valid_rows", "zip_bytes"):
                st.session_state.pop(key, None)
            st.rerun()

    zip_bytes = st.session_state.get("zip_bytes")
    if zip_bytes:
        st.download_button(
            label=f"⬇️ Download all {len(valid_rows)} receipts (ZIP)",
            data=io.BytesIO(zip_bytes),
            file_name=f"donation_receipts_{year}.zip",
            mime="application/zip",
        )

        # Preview the first receipt
        with st.expander("Preview first receipt"):
            first_pdf = create_receipt_pdf(valid_rows[0], receipt_number(0, year=year))
            st.download_button(
                label="Download preview PDF",
                data=io.BytesIO(first_pdf),
                file_name=f"{receipt_number(0, year=year)}.pdf",
                mime="application/pdf",
            )

st.divider()
st.caption(
    "🔒 Privacy: donor data is held only in this browser session's memory. "
    "Use “Clear all data” or close the tab and it is gone — nothing is stored."
)
