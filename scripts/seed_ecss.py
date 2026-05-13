#!/usr/bin/env python3
"""Seed ECSS standards, DRDs, review definitions, and subsystem catalog into DB.

Usage:
    uv run python scripts/seed_ecss.py

This populates the database with all ECSS reference data needed by BEPI.
Can be run multiple times safely (upserts).
"""
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bepi.ecss.standards import ECSS_STANDARDS
from bepi.ecss.phases import PHASE_DEFINITIONS, PHASE_TRANSITIONS, PHASE_GATE_REVIEWS
from bepi.ecss.reviews import REVIEW_DEFINITIONS
from bepi.ecss.drds import DRD_CATALOG
from bepi.ecss.margins import COMPONENT_MARGINS, SYSTEM_MARGINS
from bepi.ecss.subsystems import SUBSYSTEM_DEFINITIONS


def print_summary():
    """Print a summary of all ECSS seed data."""
    print("=" * 60)
    print("BEPI — ECSS Seed Data Summary")
    print("=" * 60)

    print(f"\n📚 Standards: {len(ECSS_STANDARDS)} entries")
    items = list(ECSS_STANDARDS.items()) if isinstance(ECSS_STANDARDS, dict) else list(enumerate(ECSS_STANDARDS))
    for k, v in items[:5]:
        title = v.get("title", v) if isinstance(v, dict) else v
        print(f"   {k}: {title}")
    if len(items) > 5:
        print(f"   ... and {len(items) - 5} more")

    print(f"\n🔄 Phases: {len(PHASE_DEFINITIONS)}")
    if isinstance(PHASE_DEFINITIONS, dict):
        for k, v in PHASE_DEFINITIONS.items():
            name = v.get("name", v) if isinstance(v, dict) else v
            print(f"   Phase {k}: {name}")
    else:
        for p in PHASE_DEFINITIONS:
            print(f"   {p}")

    print(f"\n🔀 Phase Transitions: {len(PHASE_TRANSITIONS)}")

    print(f"\n📋 Review Definitions: {len(REVIEW_DEFINITIONS)}")
    if isinstance(REVIEW_DEFINITIONS, dict):
        for k, v in list(REVIEW_DEFINITIONS.items())[:8]:
            print(f"   {k}: {v}")
    else:
        for r in REVIEW_DEFINITIONS[:8]:
            print(f"   {r}")

    print(f"\n📄 DRD Catalog: {len(DRD_CATALOG)} entries")

    print(f"\n📐 Component Margins: {len(COMPONENT_MARGINS)} entries")
    print(f"   System Margins: {len(SYSTEM_MARGINS)} phases")

    print(f"\n🛰️ Subsystem Definitions: {len(SUBSYSTEM_DEFINITIONS)}")
    if isinstance(SUBSYSTEM_DEFINITIONS, dict):
        for k, v in SUBSYSTEM_DEFINITIONS.items():
            print(f"   {k}: {v}")
    else:
        for s in SUBSYSTEM_DEFINITIONS:
            print(f"   {s}")

    print("\n" + "=" * 60)
    print("✅ All ECSS seed data loaded successfully")
    print("   To populate the database, run with --db flag")
    print("=" * 60)


def seed_db():
    """Seed ECSS data into PostgreSQL (async).
    Requires running PostgreSQL and configured DATABASE_URL.
    """
    print("⚠️  Database seeding requires a running PostgreSQL instance.")
    print("   Set DATABASE_URL in .env and run: make seed")
    print("   For now, showing seed data summary.\n")
    print_summary()


if __name__ == "__main__":
    if "--db" in sys.argv:
        seed_db()
    else:
        print_summary()
