"""
test_pdf_report.py — Unit tests for the pdf_report module.

Uses a temporary SQLite database (via monkeypatch on ``database.DB_PATH``)
so the real ``safarsync.db`` is never touched.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import database as db
import pdf_report


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> int:
    """
    Create an isolated temporary database, initialise it, add a vehicle,
    and return the vehicle id.
    """
    db_file = str(tmp_path / "test_safarsync.db")
    monkeypatch.setattr(db, "DB_PATH", db_file)
    db.init_db()
    vid = db.add_vehicle("Test Car", "TEST-0001")
    return vid  # type: ignore[return-value]


@pytest.fixture()
def tmp_db_with_records(tmp_db: int) -> int:
    """Add a few records to the test vehicle and return its id."""
    vid = tmp_db
    db.add_record(vid, "fuel", "2026-01-01", amount_pkr=5000, liters=20.0,
                  odometer_km=10000, description="Petrol fill-up", vendor_name="Shell")
    db.add_record(vid, "fuel", "2026-01-15", amount_pkr=6000, liters=25.0,
                  odometer_km=10500, description="Petrol fill-up", vendor_name="PSO")
    db.add_record(vid, "maintenance", "2026-02-01", amount_pkr=12000,
                  description="Oil change", vendor_name="AutoCare")
    return vid


# ===================================================================
# TestGeneratePDF — Normal generation → file exists and is non-empty
# ===================================================================
class TestGeneratePDF:

    def test_pdf_file_created(self, tmp_db_with_records: int, tmp_path: Path) -> None:
        vid = tmp_db_with_records
        output = str(tmp_path / "report.pdf")
        result_path = pdf_report.generate_logbook_pdf(vid, output)

        assert Path(result_path).exists()
        assert Path(result_path).stat().st_size > 0

    def test_pdf_starts_with_pdf_header(self, tmp_db_with_records: int, tmp_path: Path) -> None:
        vid = tmp_db_with_records
        output = str(tmp_path / "report.pdf")
        result_path = pdf_report.generate_logbook_pdf(vid, output)

        with open(result_path, "rb") as f:
            header = f.read(5)
        assert header == b"%PDF-"


# ===================================================================
# TestGeneratePDFBytes — returns non-empty bytes starting with %PDF
# ===================================================================
class TestGeneratePDFBytes:

    def test_bytes_non_empty(self, tmp_db_with_records: int) -> None:
        vid = tmp_db_with_records
        pdf_bytes = pdf_report.generate_logbook_pdf_bytes(vid)
        assert len(pdf_bytes) > 0

    def test_bytes_start_with_pdf_header(self, tmp_db_with_records: int) -> None:
        vid = tmp_db_with_records
        pdf_bytes = pdf_report.generate_logbook_pdf_bytes(vid)
        assert pdf_bytes[:5] == b"%PDF-"


# ===================================================================
# TestEmptyRecords — Vehicle with no records → PDF still generates
# ===================================================================
class TestEmptyRecords:

    def test_empty_vehicle_pdf_file(self, tmp_db: int, tmp_path: Path) -> None:
        """A vehicle with no records still produces a valid PDF."""
        vid = tmp_db
        output = str(tmp_path / "empty_report.pdf")
        result_path = pdf_report.generate_logbook_pdf(vid, output)

        assert Path(result_path).exists()
        assert Path(result_path).stat().st_size > 0

    def test_empty_vehicle_pdf_bytes(self, tmp_db: int) -> None:
        """A vehicle with no records still produces valid PDF bytes."""
        vid = tmp_db
        pdf_bytes = pdf_report.generate_logbook_pdf_bytes(vid)
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"


# ===================================================================
# TestInvalidVehicle — Non-existent vehicle_id → raises ValueError
# ===================================================================
class TestInvalidVehicle:

    def test_invalid_vehicle_pdf_file(self, tmp_db: int, tmp_path: Path) -> None:
        vid = tmp_db
        output = str(tmp_path / "bad.pdf")
        with pytest.raises(ValueError, match="Vehicle with id .* not found"):
            pdf_report.generate_logbook_pdf(99999, output)

    def test_invalid_vehicle_pdf_bytes(self, tmp_db: int) -> None:
        with pytest.raises(ValueError, match="Vehicle with id .* not found"):
            pdf_report.generate_logbook_pdf_bytes(99999)


# ===================================================================
# TestInvalidPath — Invalid output path → raises ValueError or RuntimeError
# ===================================================================
class TestInvalidPath:

    def test_empty_path_raises(self, tmp_db_with_records: int) -> None:
        vid = tmp_db_with_records
        with pytest.raises((ValueError, RuntimeError)):
            pdf_report.generate_logbook_pdf(vid, "")

    def test_whitespace_path_raises(self, tmp_db_with_records: int) -> None:
        vid = tmp_db_with_records
        with pytest.raises((ValueError, RuntimeError)):
            pdf_report.generate_logbook_pdf(vid, "   ")


# ===================================================================
# TestPDFContent — Generated PDF bytes are valid (start with %PDF)
# ===================================================================
class TestPDFContent:

    def test_pdf_bytes_valid(self, tmp_db_with_records: int) -> None:
        vid = tmp_db_with_records
        pdf_bytes = pdf_report.generate_logbook_pdf_bytes(vid)
        # Valid PDFs always start with %PDF-
        assert pdf_bytes.startswith(b"%PDF-")
        # PDFs should end with %%EOF (possibly with trailing whitespace)
        stripped = pdf_bytes.rstrip()
        assert stripped.endswith(b"%%EOF")
