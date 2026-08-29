"""
pdf_report.py — PDF logbook report generation for SafarSync AI.

Generates a professional, bordered PDF logbook for a vehicle using
*fpdf2*.  The report contains vehicle metadata, spending summary,
and a complete records table sorted newest-first.

Public API::

    from pdf_report import generate_logbook_pdf

    path = generate_logbook_pdf(vehicle_id=1, output_path="report.pdf")

Edge cases handled:
    • Empty records   → valid PDF with a "No records" notice (never blank).
    • Long text       → truncated before layout so cells never overflow.
    • Invalid path    → ``ValueError`` raised *before* any PDF work begins.
    • Unknown vehicle → ``ValueError`` with a clear message.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from fpdf import FPDF

import database as db

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Layout constants (millimetres — fpdf2 default unit)
# ---------------------------------------------------------------------------
_PAGE_MARGIN: float = 12.0

# Table column spec: (header_label, width_mm)
_TABLE_COLS: list[tuple[str, float]] = [
    ("Date", 20),
    ("Type", 20),
    ("Amount (PKR)", 26),
    ("Odometer (km)", 24),
    ("Description", 56),
    ("Vendor", 30),
]
_TABLE_WIDTH: float = sum(w for _, w in _TABLE_COLS)
_ROW_HEIGHT: float = 7.0        # single-line row height
_HEADER_HEIGHT: float = 8.0     # table-header row height

# Maximum character limits per column — prevents cell overflow on the page.
_DESC_LIMIT: int = 55
_VENDOR_LIMIT: int = 28


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _find_vehicle(vehicle_id: int) -> dict[str, Any]:
    """Return the vehicle dict for *vehicle_id*, or raise ``ValueError``."""
    for v in db.get_vehicles():
        if v["id"] == vehicle_id:
            return v
    raise ValueError(f"Vehicle with id {vehicle_id} not found.")


def _validate_output_path(output_path: str) -> str:
    """Ensure the parent directory of *output_path* exists and is writable.

    Creates intermediate directories if they don't exist.  Raises
    ``ValueError`` when the path is unusable.
    """
    if not output_path or not output_path.strip():
        raise ValueError("output_path must be a non-empty string.")

    output_path = os.path.abspath(output_path)
    parent: str = os.path.dirname(output_path)

    try:
        os.makedirs(parent, exist_ok=True)
    except OSError as exc:
        raise ValueError(
            f"Cannot create directory '{parent}': {exc}"
        ) from exc

    if not os.access(parent, os.W_OK):
        raise ValueError(
            f"Output directory is not writable: '{parent}'"
        )

    return output_path


def _fmt_amount(value: Any) -> str:
    """Format a monetary value as ``"12,345"`` or ``"—"``."""
    if value is None:
        return "\u2014"  # em dash
    try:
        return f"{float(value):,.0f}"
    except (ValueError, TypeError):
        return "\u2014"


def _fmt_int(value: Any) -> str:
    """Format an integer value or ``"—"``."""
    if value is None:
        return "\u2014"
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return "\u2014"


def _safe_str(value: Any, limit: int = 0) -> str:
    """Coerce to string, truncate if *limit* > 0."""
    text: str = str(value) if value is not None else ""
    if limit and len(text) > limit:
        text = text[: limit - 1] + "\u2026"  # ellipsis
    return text


# ---------------------------------------------------------------------------
# PDF document class
# ---------------------------------------------------------------------------
class _LogbookPDF(FPDF):
    """Minimal ``FPDF`` subclass that injects page footers."""

    def footer(self) -> None:  # noqa: D102  (override)
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(160, 160, 160)
        self.cell(
            0, 10,
            f"SafarSync AI  |  Page {self.page_no()}/{{nb}}",
            align="C",
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_logbook_pdf(vehicle_id: int, output_path: str) -> str:
    """Generate a vehicle logbook PDF.

    The resulting document contains:

    1. **Header** — vehicle name, registration number, generation date.
    2. **Summary** — total spending, record count, date range.
    3. **Records table** — every record for the vehicle, sorted
       newest-first, with columns: Date, Type, Amount (PKR),
       Odometer (km), Description, Vendor.

    The function **never** produces a blank or corrupt PDF:

    * **Empty records** → a valid one-page PDF with a "No records" notice.
    * **Invalid output path** → ``ValueError`` before any PDF work begins.
    * **Unknown vehicle** → ``ValueError`` with a clear message.

    Parameters
    ----------
    vehicle_id : int
        The vehicle whose logbook to generate.
    output_path : str
        Filesystem path where the PDF will be written.  Parent directories
        are created automatically.

    Returns
    -------
    str
        The absolute path of the generated PDF.

    Raises
    ------
    ValueError
        If the vehicle does not exist or the output path is invalid.
    """
    try:
        return _generate(vehicle_id, output_path)
    except ValueError:
        raise  # propagate expected validation errors unchanged
    except Exception as exc:
        logger.exception("PDF generation failed for vehicle %s", vehicle_id)
        raise RuntimeError(
            f"Failed to generate PDF: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Generation engine (private)
# ---------------------------------------------------------------------------
def _generate(vehicle_id: int, output_path: str) -> str:
    # ── Validate inputs ───────────────────────────────────────────────
    vehicle: dict[str, Any] = _find_vehicle(vehicle_id)
    output_path = _validate_output_path(output_path)

    # ── Fetch records (newest-first from DB) ──────────────────────────
    records: list[dict[str, Any]] = db.get_records(vehicle_id)

    # ── Compute summary ───────────────────────────────────────────────
    record_count: int = len(records)
    total_spend: float = sum(r.get("amount_pkr") or 0.0 for r in records)

    dates: list[str] = [r["date"] for r in records if r.get("date")]
    date_range: str = (
        f"{min(dates)}  \u2192  {max(dates)}" if dates else "N/A"
    )
    gen_date: str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # ── Build the PDF ─────────────────────────────────────────────────
    pdf = _LogbookPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(_PAGE_MARGIN, _PAGE_MARGIN, _PAGE_MARGIN)
    pdf.add_page()

    _draw_header(pdf, vehicle, gen_date)
    _draw_summary(pdf, total_spend, record_count, date_range)

    if record_count == 0:
        _draw_empty_notice(pdf)
    else:
        _draw_table(pdf, records)

    # ── Write to disk ─────────────────────────────────────────────────
    try:
        pdf.output(output_path)
    except Exception as exc:
        raise ValueError(
            f"Failed to write PDF to '{output_path}': {exc}"
        ) from exc

    return output_path


# ---------------------------------------------------------------------------
# Section renderers (private helpers)
# ---------------------------------------------------------------------------
def _draw_header(
    pdf: _LogbookPDF,
    vehicle: dict[str, Any],
    gen_date: str,
) -> None:
    """Draw the report title and vehicle identification block."""
    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(25, 25, 112)
    pdf.cell(0, 12, "Vehicle Logbook", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(2)

    # Vehicle info block
    pdf.set_fill_color(240, 240, 245)
    block_h: float = 26.0
    x0: float = pdf.get_x()
    y0: float = pdf.get_y()
    usable_w: float = pdf.w - 2 * _PAGE_MARGIN

    pdf.rect(x0, y0, usable_w, block_h, style="F")

    pdf.set_x(x0 + 5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(usable_w - 10, 8, _safe_str(vehicle.get("name", "Vehicle")),
             new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(x0 + 5)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    reg = vehicle.get("registration_number") or "N/A"
    pdf.cell(usable_w - 10, 7, f"Registration: {reg}",
             new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(x0 + 5)
    pdf.cell(usable_w - 10, 7, f"Generated: {gen_date}",
             new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(y0 + block_h + 6)


def _draw_summary(
    pdf: _LogbookPDF,
    total_spend: float,
    record_count: int,
    date_range: str,
) -> None:
    """Draw the spending / count / date-range summary strip."""
    pdf.set_fill_color(230, 240, 250)
    strip_h: float = 18.0
    x0: float = pdf.get_x()
    y0: float = pdf.get_y()
    usable_w: float = pdf.w - 2 * _PAGE_MARGIN

    pdf.rect(x0, y0, usable_w, strip_h, style="F")

    col_w: float = usable_w / 3
    items: list[tuple[str, str]] = [
        ("Total Spending", f"PKR {total_spend:,.0f}"),
        ("Records", f"{record_count}"),
        ("Date Range", date_range),
    ]

    for i, (label, value) in enumerate(items):
        cx: float = x0 + i * col_w

        pdf.set_xy(cx + 2, y0 + 1)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(col_w - 4, 5, label.upper())

        pdf.set_xy(cx + 2, y0 + 7)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(col_w - 4, 8, value)

    pdf.set_y(y0 + strip_h + 8)


def _draw_empty_notice(pdf: _LogbookPDF) -> None:
    """Draw a centred notice when there are no records."""
    pdf.ln(20)
    pdf.set_font("Helvetica", "I", 13)
    pdf.set_text_color(140, 140, 140)
    pdf.cell(0, 10, "No records found for this vehicle.", align="C")


def _draw_table(
    pdf: _LogbookPDF,
    records: list[dict[str, Any]],
) -> None:
    """Draw the records table with header and data rows."""
    # ── Table header ──────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(50, 50, 70)
    pdf.set_text_color(255, 255, 255)

    for header, width in _TABLE_COLS:
        pdf.cell(width, _HEADER_HEIGHT, header, border=1, fill=True)
    pdf.ln()

    # ── Data rows ─────────────────────────────────────────────────────
    fill: bool = False
    for rec in records:
        row_data: list[str] = [
            _safe_str(rec.get("date", "")),
            _safe_str(rec.get("record_type", "")).capitalize(),
            _fmt_amount(rec.get("amount_pkr")),
            _fmt_int(rec.get("odometer_km")),
            _safe_str(rec.get("description"), limit=_DESC_LIMIT),
            _safe_str(rec.get("vendor_name"), limit=_VENDOR_LIMIT),
        ]

        # Pre-calculate row height: count wrapped lines per cell.
        max_lines: int = 1
        for i, (_, col_w) in enumerate(_TABLE_COLS):
            text_w: float = pdf.get_string_width(row_data[i])
            inner_w: float = col_w - 2  # 1 mm padding each side
            if inner_w > 0:
                n: int = max(1, int(text_w / inner_w) + 1)
                max_lines = max(max_lines, n)

        row_h: float = _ROW_HEIGHT * max_lines

        # Page-break guard: start a fresh page if this row won't fit.
        if pdf.get_y() + row_h > pdf.h - 22:
            pdf.add_page()

        # Alternating row background
        if fill:
            pdf.set_fill_color(248, 248, 252)
        else:
            pdf.set_fill_color(255, 255, 255)

        y_start: float = pdf.get_y()
        x_start: float = pdf.get_x()

        for i, (_, col_w) in enumerate(_TABLE_COLS):
            cx: float = x_start + sum(w for _, w in _TABLE_COLS[:i])

            # Cell background + border
            pdf.rect(cx, y_start, col_w, row_h, style="DF")

            # Text
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(40, 40, 40)

            # Centre numeric columns (Date, Amount, Odometer)
            align: str = "C" if i in (0, 2, 3) else "L"

            n_lines: int = max(1, int(row_h / _ROW_HEIGHT))
            text_y: float = y_start + 1

            # Vertical-centre multi-line text
            if n_lines > 1:
                text_y = y_start + (row_h - n_lines * _ROW_HEIGHT) / 2

            pdf.set_xy(cx + 1, text_y)
            pdf.multi_cell(
                col_w - 2,
                _ROW_HEIGHT,
                row_data[i],
                align=align,
            )

        pdf.set_y(y_start + row_h)
        fill = not fill
