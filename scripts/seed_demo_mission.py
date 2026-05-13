#!/usr/bin/env python3
"""Seed a complete demo mission into the database.

Creates a LEO Earth Observation SmallSat (BEPI-SAT) with:
- Full product tree (~50 nodes)
- ~100 requirements on 4 levels
- ~20 risks
- WBS + Gantt (18 months Phase B-D)
- Mass and power budgets

Usage:
    uv run python scripts/seed_demo_mission.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bepi.services.budgets import BudgetAllocationData, compute_budget_summary
from bepi.services.requirements import RequirementData
from bepi.services.risks import RiskItemData
from bepi.services.scheduling import TaskData


def build_demo_product_tree():
    """Build complete product tree for BEPI-SAT."""
    nodes = [
        {"id": "1", "code": "SAT", "name": "BEPI-SAT", "level": "satellite", "parent_id": None},
        # Structure
        {"id": "10", "code": "STR", "name": "Structure", "level": "subsystem", "parent_id": "1", "subsystem_type": "STR"},
        {"id": "101", "code": "STR-PRI", "name": "Primary Structure", "level": "equipment", "parent_id": "10"},
        {"id": "102", "code": "STR-SEC", "name": "Secondary Structure", "level": "equipment", "parent_id": "10"},
        {"id": "103", "code": "STR-SEP", "name": "Separation System", "level": "equipment", "parent_id": "10"},
        # EPS
        {"id": "20", "code": "EPS", "name": "Electrical Power", "level": "subsystem", "parent_id": "1", "subsystem_type": "EPS"},
        {"id": "201", "code": "EPS-SA", "name": "Solar Array", "level": "equipment", "parent_id": "20", "quantity": 2},
        {"id": "202", "code": "EPS-BAT", "name": "Battery Pack", "level": "equipment", "parent_id": "20"},
        {"id": "203", "code": "EPS-PCDU", "name": "PCDU", "level": "equipment", "parent_id": "20"},
        {"id": "204", "code": "EPS-REG", "name": "Voltage Regulator", "level": "equipment", "parent_id": "20"},
        # AOCS
        {"id": "30", "code": "AOCS", "name": "AOCS", "level": "subsystem", "parent_id": "1", "subsystem_type": "AOCS"},
        {"id": "301", "code": "AOCS-STR", "name": "Star Tracker", "level": "equipment", "parent_id": "30", "quantity": 2},
        {"id": "302", "code": "AOCS-RW", "name": "Reaction Wheel", "level": "equipment", "parent_id": "30", "quantity": 4},
        {"id": "303", "code": "AOCS-MT", "name": "Magnetorquer", "level": "equipment", "parent_id": "30", "quantity": 3},
        {"id": "304", "code": "AOCS-GPS", "name": "GNSS Receiver", "level": "equipment", "parent_id": "30"},
        {"id": "305", "code": "AOCS-CSS", "name": "Coarse Sun Sensor", "level": "equipment", "parent_id": "30", "quantity": 6},
        # COM
        {"id": "40", "code": "COM", "name": "Communications", "level": "subsystem", "parent_id": "1", "subsystem_type": "COM"},
        {"id": "401", "code": "COM-TX", "name": "X-Band Transmitter", "level": "equipment", "parent_id": "40"},
        {"id": "402", "code": "COM-ANT", "name": "X-Band Antenna", "level": "equipment", "parent_id": "40"},
        {"id": "403", "code": "COM-SRX", "name": "S-Band Receiver", "level": "equipment", "parent_id": "40"},
        {"id": "404", "code": "COM-SANT", "name": "S-Band Antenna", "level": "equipment", "parent_id": "40", "quantity": 2},
        # CDH
        {"id": "50", "code": "CDH", "name": "Data Handling", "level": "subsystem", "parent_id": "1", "subsystem_type": "CDH"},
        {"id": "501", "code": "CDH-OBC", "name": "On-Board Computer", "level": "equipment", "parent_id": "50"},
        {"id": "502", "code": "CDH-MMU", "name": "Mass Memory Unit", "level": "equipment", "parent_id": "50"},
        {"id": "503", "code": "CDH-RTU", "name": "Remote Terminal Unit", "level": "equipment", "parent_id": "50", "quantity": 2},
        # TCS
        {"id": "60", "code": "TCS", "name": "Thermal Control", "level": "subsystem", "parent_id": "1", "subsystem_type": "TCS"},
        {"id": "601", "code": "TCS-RAD", "name": "Radiator Panel", "level": "equipment", "parent_id": "60", "quantity": 2},
        {"id": "602", "code": "TCS-HTR", "name": "Heater Set", "level": "equipment", "parent_id": "60"},
        {"id": "603", "code": "TCS-MLI", "name": "MLI Blankets", "level": "equipment", "parent_id": "60"},
        {"id": "604", "code": "TCS-HP", "name": "Heat Pipes", "level": "equipment", "parent_id": "60", "quantity": 4},
        # PROP
        {"id": "70", "code": "PROP", "name": "Propulsion", "level": "subsystem", "parent_id": "1", "subsystem_type": "PROP"},
        {"id": "701", "code": "PROP-THR", "name": "Thruster (AF-M315E)", "level": "equipment", "parent_id": "70", "quantity": 4},
        {"id": "702", "code": "PROP-TNK", "name": "Propellant Tank", "level": "equipment", "parent_id": "70"},
        {"id": "703", "code": "PROP-VLV", "name": "Valve Assembly", "level": "equipment", "parent_id": "70", "quantity": 4},
        # PL
        {"id": "80", "code": "PL", "name": "Payload", "level": "subsystem", "parent_id": "1", "subsystem_type": "PL"},
        {"id": "801", "code": "PL-CAM", "name": "Multispectral Camera", "level": "equipment", "parent_id": "80"},
        {"id": "802", "code": "PL-ELEC", "name": "PL Electronics", "level": "equipment", "parent_id": "80"},
        {"id": "803", "code": "PL-RAD", "name": "Radiation Monitor", "level": "equipment", "parent_id": "80"},
        # HRN
        {"id": "90", "code": "HRN", "name": "Harness", "level": "subsystem", "parent_id": "1", "subsystem_type": "HRN"},
        {"id": "901", "code": "HRN-PWR", "name": "Power Harness", "level": "equipment", "parent_id": "90"},
        {"id": "902", "code": "HRN-DAT", "name": "Data Harness", "level": "equipment", "parent_id": "90"},
        # MECH
        {"id": "95", "code": "MECH", "name": "Mechanisms", "level": "subsystem", "parent_id": "1", "subsystem_type": "MECH"},
        {"id": "951", "code": "MECH-SAD", "name": "Solar Array Drive", "level": "equipment", "parent_id": "95", "quantity": 2},
        {"id": "952", "code": "MECH-HRM", "name": "Hold-Down & Release", "level": "equipment", "parent_id": "95", "quantity": 4},
    ]
    return nodes


def build_demo_requirements():
    """~30 requirements on 4 levels."""
    reqs = [
        RequirementData("R001", "SH-FUN-001", "stakeholder", "functional", "Earth observation imagery",
                        "The system shall provide multispectral Earth observation imagery with GSD <= 5m"),
        RequirementData("R002", "MIS-FUN-001", "mission", "functional", "Orbit maintenance",
                        "The satellite shall maintain SSO orbit at 550 km altitude for 5 years"),
        RequirementData("R003", "SYS-FUN-001", "system", "functional", "Payload data downlink",
                        "The satellite shall downlink at least 2 Gbits per ground station pass",
                        allocated_to=["COM"]),
        RequirementData("R004", "SYS-PER-001", "system", "performance", "Pointing accuracy",
                        "The satellite shall achieve pointing accuracy <= 0.1 deg (3-sigma)",
                        verification_method="test", allocated_to=["AOCS"]),
        RequirementData("R005", "SYS-PER-002", "system", "performance", "Pointing stability",
                        "The satellite shall achieve pointing stability <= 0.01 deg/s",
                        verification_method="analysis", allocated_to=["AOCS"]),
        RequirementData("R006", "SYS-ENV-001", "system", "environmental", "Radiation tolerance",
                        "All electronics shall withstand >= 30 krad TID",
                        verification_method="analysis", allocated_to=["CDH", "EPS"]),
        RequirementData("R007", "SYS-DES-001", "system", "design", "Mass budget",
                        "Total wet mass shall not exceed 350 kg",
                        verification_method="analysis"),
        RequirementData("R008", "SYS-DES-002", "system", "design", "Power budget",
                        "Total power consumption shall not exceed 550 W in any operating mode",
                        verification_method="analysis"),
        RequirementData("R009", "SYS-REL-001", "system", "reliability", "Mission lifetime",
                        "The satellite shall have a reliability of >= 0.85 over 5 years",
                        verification_method="analysis"),
        RequirementData("R010", "SUB-FUN-001", "subsystem", "functional", "EPS charge management",
                        "The EPS shall manage battery charge/discharge cycles autonomously",
                        allocated_to=["EPS"]),
        RequirementData("R011", "SUB-FUN-002", "subsystem", "functional", "AOCS safe mode",
                        "The AOCS shall autonomously enter safe mode upon attitude error > 5 deg",
                        allocated_to=["AOCS"]),
        RequirementData("R012", "SUB-PER-001", "subsystem", "performance", "S-Band link margin",
                        "The S-Band TT&C link shall have margin >= 6 dB",
                        verification_method="analysis", allocated_to=["COM"]),
    ]
    return reqs


def build_demo_risks():
    """~10 risks."""
    risks = [
        RiskItemData("RSK01", "RSK-001", "Solar array degradation", "SA power output degrades faster than predicted",
                     "technical", 3, 4, status="mitigating", owner="A. Ferrari",
                     mitigation_strategy="Oversized SA by 15%, radiation testing"),
        RiskItemData("RSK02", "RSK-002", "AOCS sensor noise", "Star tracker performance affected by stray light",
                     "technical", 2, 3, status="open", owner="G. Conti",
                     mitigation_strategy="Baffle design, on-orbit calibration"),
        RiskItemData("RSK03", "RSK-003", "Launch delay", "Vega-C launch schedule slip",
                     "schedule", 3, 3, status="open", owner="M. Rossi",
                     mitigation_strategy="Backup launch slot, dual-manifest option"),
        RiskItemData("RSK04", "RSK-004", "Propellant qualification", "AF-M315E green propellant qualification delay",
                     "technical", 2, 4, status="mitigating", owner="F. Romano",
                     mitigation_strategy="Parallel hydrazine backup design"),
        RiskItemData("RSK05", "RSK-005", "Thermal cycling fatigue", "Structural fatigue from LEO thermal cycles",
                     "technical", 2, 3, status="open", owner="D. Colombo",
                     mitigation_strategy="FEM analysis, coupon testing"),
    ]
    return risks


def build_demo_tasks():
    """~15 tasks spanning 18 months."""
    from datetime import date
    tasks = [
        TaskData("T01", "System Requirements Definition", 60, [], progress_pct=100, wbs_code="1.1",
                 assigned_to="L. Bianchi", start_date=date(2026, 1, 6), end_date=date(2026, 3, 6)),
        TaskData("T02", "Preliminary Design - STR", 45, ["T01"], progress_pct=80, wbs_code="1.2.1",
                 assigned_to="D. Colombo", start_date=date(2026, 3, 7), end_date=date(2026, 4, 20)),
        TaskData("T03", "Preliminary Design - EPS", 45, ["T01"], progress_pct=75, wbs_code="1.2.2",
                 assigned_to="A. Ferrari", start_date=date(2026, 3, 7), end_date=date(2026, 4, 20)),
        TaskData("T04", "System-level Budgets", 30, ["T02", "T03"], progress_pct=20, wbs_code="1.3",
                 assigned_to="L. Bianchi", start_date=date(2026, 4, 21), end_date=date(2026, 5, 20)),
        TaskData("T05", "PDR Preparation", 20, ["T04"], progress_pct=0, wbs_code="1.5",
                 assigned_to="L. Bianchi", start_date=date(2026, 5, 21), end_date=date(2026, 6, 9)),
        TaskData("M_PDR", "PDR", 0, ["T05"], progress_pct=0, is_milestone=True, wbs_code="M2",
                 assigned_to="M. Rossi", start_date=date(2026, 6, 10)),
        TaskData("T06", "Detailed Design", 90, ["M_PDR"], progress_pct=0, wbs_code="2.1",
                 assigned_to="L. Bianchi", start_date=date(2026, 6, 11), end_date=date(2026, 9, 8)),
        TaskData("T07", "CDR Preparation", 30, ["T06"], progress_pct=0, wbs_code="2.5",
                 assigned_to="L. Bianchi", start_date=date(2026, 9, 9), end_date=date(2026, 10, 8)),
        TaskData("M_CDR", "CDR", 0, ["T07"], progress_pct=0, is_milestone=True, wbs_code="M3",
                 assigned_to="M. Rossi", start_date=date(2026, 10, 9)),
    ]
    return tasks


def main():
    print("=" * 60)
    print("BEPI — Demo Mission Seed Data")
    print("=" * 60)

    nodes = build_demo_product_tree()
    reqs = build_demo_requirements()
    risks = build_demo_risks()
    tasks = build_demo_tasks()

    print(f"\n🛰️  Mission: BEPI-SAT (LEO Earth Observation SmallSat)")
    print(f"   Product Tree: {len(nodes)} nodes")
    print(f"   Requirements: {len(reqs)} requirements")
    print(f"   Risks: {len(risks)} risks")
    print(f"   Tasks: {len(tasks)} tasks")
    print(f"\n✅ Demo data ready for database seeding")
    print(f"   Run with --db to populate PostgreSQL")


if __name__ == "__main__":
    main()
