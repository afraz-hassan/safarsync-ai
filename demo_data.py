"""
demo_data.py — Sample/demo data seeding for SafarSync AI development and testing.

Creates a single demo vehicle with realistic expense records spanning
several months, designed to exercise every feature of the application:

* **Fuel records** (11) — realistic Pakistani petrol prices (~PKR 270/L)
  with increasing odometer readings and one deliberate efficiency drop.
* **Maintenance records** (6) — oil change plus five generic service entries
  including a costly engine tune-up that triggers a cost anomaly.
* **Insurance record** (1) — annual comprehensive insurance.

Guaranteed triggers when the data is analysed:

* At least one **overdue** maintenance item (oil change > 5 000 km interval).
* At least one **fuel-efficiency decline** (km/L drops sharply on record 11).
* At least one **anomaly** in fuel amount, maintenance cost, and efficiency.

Idempotent — calling :func:`seed_demo_data` multiple times will not create
duplicate vehicles or records.

Public API::

    from demo_data import seed_demo_data

    count = seed_demo_data()   # returns number of records created (0 if exists)
"""

from __future__ import annotations

import logging
from typing import Any

import database as db

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# Unique name prefix used to detect an already-seeded demo vehicle.
_DEMO_VEHICLE_NAME: str = "SafarSync Demo \u2014 Toyota Corolla"
_DEMO_REGISTRATION: str = "DEMO-2026"


# ---------------------------------------------------------------------------
# Record data — ordered chronologically (oldest first).
# ---------------------------------------------------------------------------

# Fuel records (11 entries, Feb–Aug 2026).
#
# Columns: date, amount_pkr, liters, odometer_km, description, vendor
# Fuel price ~PKR 270/L (Pakistan mid-2026).  Normal efficiency ~13 km/L.
# Record 11 has only 400 km on 50 L → 8 km/L (efficiency-decline trigger).
_FUEL_RECORDS: list[dict[str, Any]] = [
    #  1  baseline
    {"date": "2026-02-10", "amount_pkr": 9500,  "liters": 35.2, "odometer_km": 45000,
     "description": "Petrol fill-up",         "vendor_name": "PSO Faisalabad"},
    #  2  550 km / 40 L = 13.75 km/L
    {"date": "2026-02-25", "amount_pkr": 10800, "liters": 40.0, "odometer_km": 45550,
     "description": "Full tank",              "vendor_name": "Shell Lahore"},
    #  3  500 km / 38 L = 13.16 km/L
    {"date": "2026-03-12", "amount_pkr": 10260, "liters": 38.0, "odometer_km": 46050,
     "description": "Petrol fill-up",         "vendor_name": "Total Multan"},
    #  4  480 km / 37 L = 12.97 km/L
    {"date": "2026-03-28", "amount_pkr": 9990,  "liters": 37.0, "odometer_km": 46530,
     "description": "Weekly fill",            "vendor_name": "PSO Islamabad"},
    #  5  520 km / 40 L = 13.00 km/L
    {"date": "2026-04-14", "amount_pkr": 10800, "liters": 40.0, "odometer_km": 47050,
     "description": "Full tank",              "vendor_name": "Shell Rawalpindi"},
    #  6  550 km / 42 L = 13.10 km/L
    {"date": "2026-04-30", "amount_pkr": 11340, "liters": 42.0, "odometer_km": 47600,
     "description": "Petrol fill-up",         "vendor_name": "Attock Karachi"},
    #  7  500 km / 38 L = 13.16 km/L
    {"date": "2026-05-15", "amount_pkr": 10260, "liters": 38.0, "odometer_km": 48100,
     "description": "Regular fill",           "vendor_name": "PSO Hyderabad"},
    #  8  530 km / 41 L = 12.93 km/L
    {"date": "2026-06-01", "amount_pkr": 11070, "liters": 41.0, "odometer_km": 48630,
     "description": "Full tank",              "vendor_name": "Total Sukkur"},
    #  9  500 km / 39 L = 12.82 km/L
    {"date": "2026-06-18", "amount_pkr": 10530, "liters": 39.0, "odometer_km": 49130,
     "description": "Petrol",                 "vendor_name": "Shell Quetta"},
    # 10  500 km / 38 L = 13.16 km/L
    {"date": "2026-07-05", "amount_pkr": 10260, "liters": 38.0, "odometer_km": 49630,
     "description": "Highway fill-up",        "vendor_name": "PSO Peshawar"},
    # 11  ANOMALY: 400 km / 50 L = 8.00 km/L  (sharp efficiency decline)
    #     amount 16 000 > 1.5× avg (~10 445) → fuel_amount anomaly
    #     liters 50    > 1.5× avg (~37.7)    → fuel_liters anomaly
    {"date": "2026-07-25", "amount_pkr": 16000, "liters": 50.0, "odometer_km": 50030,
     "description": "Suspiciously large fill-up", "vendor_name": "Unknown station"},
]

# Maintenance records (6 entries — 1 specific type + 5 generic "maintenance").
#
# The oil_change record (odo 45 000) ensures check_due_maintenance() flags
# oil_change as OVERDUE at the final odo of 51 500 km (6 500 km driven,
# interval is 5 000 km).
#
# The 5 generic "maintenance" records give anomaly.py enough history
# (>= 3 prior) to detect the expensive engine tune-up:
#   avg of prior 4 = (3 500+4 500+5 500+2 500)/4 = 4 000
#   22 000 / 4 000 = 5.5x  →  HIGH severity maintenance_cost anomaly.
_MAINTENANCE_RECORDS: list[dict[str, Any]] = [
    # oil_change → triggers overdue in check_due_maintenance
    {"date": "2026-02-15", "amount_pkr": 4500,  "odometer_km": 45000,
     "description": "Oil change and filter replacement",
     "vendor_name": "Toyota Downtown Lahore",  "record_type": "oil_change"},
    # Generic maintenance #1 (baseline)
    {"date": "2026-03-10", "amount_pkr": 3500,  "odometer_km": 45800,
     "description": "Tire rotation and wheel balancing",
     "vendor_name": "Tyre Shop Faisalabad",    "record_type": "maintenance"},
    # Generic maintenance #2 (baseline)
    {"date": "2026-04-20", "amount_pkr": 4500,  "odometer_km": 47200,
     "description": "Brake pad inspection and adjustment",
     "vendor_name": "AutoCare Multan",         "record_type": "maintenance"},
    # Generic maintenance #3 (baseline)
    {"date": "2026-05-25", "amount_pkr": 5500,  "odometer_km": 48500,
     "description": "Air filter and coolant flush",
     "vendor_name": "Quick Fix Islamabad",     "record_type": "maintenance"},
    # Generic maintenance #4 (baseline)
    {"date": "2026-06-20", "amount_pkr": 2500,  "odometer_km": 49800,
     "description": "Wiper blade and battery check",
     "vendor_name": "AutoPro Karachi",         "record_type": "maintenance"},
    # ANOMALY: 22 000 / avg(3 500,4 500,5 500,2 500 = 4 000) = 5.5x  → HIGH
    {"date": "2026-07-10", "amount_pkr": 22000, "odometer_km": 50500,
     "description": "Full engine tune-up and diagnostics",
     "vendor_name": "Toyota Downtown Lahore",  "record_type": "maintenance"},
]

# Insurance record (1 entry).
_INSURANCE_RECORD: dict[str, Any] = {
    "date": "2026-01-15",
    "amount_pkr": 45000,
    "description": "Annual comprehensive vehicle insurance",
    "vendor_name": "EFU General Insurance",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _demo_exists() -> bool:
    """Return ``True`` if a demo vehicle is already in the database."""
    for v in db.get_vehicles():
        if v.get("name", "").startswith("SafarSync Demo"):
            return True
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def seed_demo_data() -> int:
    """Seed the database with one demo vehicle and its expense records.

    Creates a Toyota Corolla with 11 fuel records, 6 maintenance records,
    and 1 insurance record — all tagged with ``source="demo"``.

    The data is designed to exercise every analytics feature:

    * Odometer readings increase logically from 45 000 → 51 500 km.
    * Fuel prices reflect realistic Pakistani market rates (~PKR 270/L).
    * The oil change (last at 45 000 km) is **overdue** at the final
      odometer reading of 51 500 km (interval: 5 000 km).
    * Record 11 has a sharp **fuel-efficiency decline** (8 km/L vs the
      ~13 km/L average of prior records).
    * The engine tune-up (PKR 22 000) triggers a **high-severity
      maintenance-cost anomaly** (> 5× the prior average).
    * The large fuel fill-up (PKR 16 000 / 50 L) triggers both a
      **fuel-amount** and **fuel-liters** anomaly.

    **Idempotent**: if a demo vehicle already exists the function returns
    ``0`` without creating any duplicates.

    Returns
    -------
    int
        The number of records created (18), or ``0`` if the demo vehicle
        already exists.
    """
    if _demo_exists():
        logger.info("Demo vehicle already exists — skipping seed.")
        return 0

    # Ensure schema is ready.
    db.init_db()

    # Create the vehicle.
    vehicle_id: int = db.add_vehicle(_DEMO_VEHICLE_NAME, _DEMO_REGISTRATION)

    created: int = 0

    # -- Fuel records --
    for r in _FUEL_RECORDS:
        db.add_record(
            vehicle_id=vehicle_id,
            record_type="fuel",
            date=r["date"],
            amount_pkr=r["amount_pkr"],
            liters=r["liters"],
            odometer_km=r["odometer_km"],
            description=r["description"],
            vendor_name=r["vendor_name"],
            source="demo",
        )
        created += 1

    # -- Maintenance records --
    for r in _MAINTENANCE_RECORDS:
        db.add_record(
            vehicle_id=vehicle_id,
            record_type=r["record_type"],
            date=r["date"],
            amount_pkr=r["amount_pkr"],
            odometer_km=r["odometer_km"],
            description=r["description"],
            vendor_name=r["vendor_name"],
            source="demo",
        )
        created += 1

    # -- Insurance record --
    r = _INSURANCE_RECORD
    db.add_record(
        vehicle_id=vehicle_id,
        record_type="insurance",
        date=r["date"],
        amount_pkr=r["amount_pkr"],
        description=r["description"],
        vendor_name=r["vendor_name"],
        source="demo",
    )
    created += 1

    logger.info("Seeded demo vehicle '%s' with %d records.", _DEMO_VEHICLE_NAME, created)
    return created
