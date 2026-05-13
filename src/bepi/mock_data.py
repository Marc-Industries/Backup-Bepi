from datetime import date, timedelta

from pydantic import BaseModel


class _PositionalModel(BaseModel):
    def __init__(self, *args, **data):
        field_names = list(getattr(self.__class__, "model_fields", getattr(self.__class__, "__fields__", {})))
        if len(args) > len(field_names):
            raise TypeError(f"{self.__class__.__name__} expected at most {len(field_names)} positional arguments")
        for name, value in zip(field_names, args):
            if name in data:
                raise TypeError(f"{self.__class__.__name__} got multiple values for argument {name!r}")
            data[name] = value
        super().__init__(**data)


class RequirementData(_PositionalModel):
    id: str
    req_id: str
    level: str
    category: str
    title: str
    text: str
    parent_id: str | None = None
    priority: str = "mandatory"
    verification_method: str = "analysis"
    verification_status: str = "not_started"
    allocated_to: list[str] = []


class RiskItemData(_PositionalModel):
    id: str
    risk_id: str
    title: str
    description: str
    category: str
    likelihood: int
    consequence: int
    status: str
    owner: str = ""
    mitigation: str = ""
    severity: int = 0
    occurrence: int = 0
    
    @property
    def risk_level(self) -> str:
        score = self.likelihood * self.consequence
        if score >= 15:
            return "critical"
        elif score >= 8:
            return "high"
        elif score >= 4:
            return "medium"
        return "low"


class FMECAEntryData(_PositionalModel):
    id: str
    node_id: str
    failure_mode: str
    failure_cause: str
    local_effect: str
    system_effect: str
    severity: int
    occurrence: int
    detection: int
    mitigation: str
    criticality: int = 0


class TaskData(_PositionalModel):
    task_id: str
    name: str
    duration_days: int
    predecessor_ids: list[str]
    progress_pct: int = 0
    wbs_code: str = ""
    assigned_to: str = ""
    start_date: date | None = None
    end_date: date | None = None
    status: str = "pending"
    is_milestone: bool = False
    notes: str = ""


def mock_product_tree_flat():
    nodes = [
        {"id": "1", "code": "SAT", "name": "BEPI-SAT", "level": "satellite", "parent_id": None},
        {"id": "10", "code": "STR", "name": "Structure", "level": "subsystem", "parent_id": "1", "subsystem_type": "STR"},
        {"id": "20", "code": "EPS", "name": "Electrical Power", "level": "subsystem", "parent_id": "1", "subsystem_type": "EPS"},
        {"id": "30", "code": "AOCS", "name": "Attitude & Orbit Control", "level": "subsystem", "parent_id": "1", "subsystem_type": "AOCS"},
        {"id": "40", "code": "COM", "name": "Communications", "level": "subsystem", "parent_id": "1", "subsystem_type": "COM"},
        {"id": "50", "code": "CDH", "name": "Command & Data Handling", "level": "subsystem", "parent_id": "1", "subsystem_type": "CDH"},
        {"id": "60", "code": "TCS", "name": "Thermal Control", "level": "subsystem", "parent_id": "1", "subsystem_type": "TCS"},
        {"id": "70", "code": "PROP", "name": "Propulsion", "level": "subsystem", "parent_id": "1", "subsystem_type": "PROP"},
        {"id": "80", "code": "PL", "name": "Payload", "level": "subsystem", "parent_id": "1", "subsystem_type": "PL"},
        {"id": "90", "code": "HRN", "name": "Harness", "level": "subsystem", "parent_id": "1", "subsystem_type": "HRN"},
        {"id": "101", "code": "STR-PRI", "name": "Primary Structure", "level": "equipment", "parent_id": "10"},
        {"id": "102", "code": "STR-SEC", "name": "Secondary Structure", "level": "equipment", "parent_id": "10"},
        {"id": "103", "code": "STR-IFR", "name": "Interface Ring", "level": "equipment", "parent_id": "10"},
        {"id": "201", "code": "EPS-SA", "name": "Solar Array (6U)", "level": "equipment", "parent_id": "20"},
        {"id": "202", "code": "EPS-BAT", "name": "Li-ion Battery Pack", "level": "equipment", "parent_id": "20"},
        {"id": "203", "code": "EPS-PCDU", "name": "PCDU", "level": "equipment", "parent_id": "20"},
        {"id": "301", "code": "AOCS-STR", "name": "Star Tracker", "level": "equipment", "parent_id": "30"},
        {"id": "302", "code": "AOCS-SS", "name": "Sun Sensor", "level": "equipment", "parent_id": "30"},
        {"id": "303", "code": "AOCS-RW", "name": "Reaction Wheel", "level": "equipment", "parent_id": "30"},
        {"id": "304", "code": "AOCS-MT", "name": "Magnetorquer", "level": "equipment", "parent_id": "30"},
        {"id": "401", "code": "COM-SBT", "name": "S-Band Transponder (nom.)", "level": "equipment", "parent_id": "40"},
        {"id": "405", "code": "COM-SBR", "name": "S-Band Transponder (red.)", "level": "equipment", "parent_id": "40"},
        {"id": "402", "code": "COM-SBA", "name": "S-Band Antenna", "level": "equipment", "parent_id": "40"},
        {"id": "403", "code": "COM-XBT", "name": "X-Band Transmitter", "level": "equipment", "parent_id": "40"},
        {"id": "404", "code": "COM-XBA", "name": "X-Band Antenna", "level": "equipment", "parent_id": "40"},
        {"id": "501", "code": "CDH-OBC", "name": "On-Board Computer", "level": "equipment", "parent_id": "50"},
        {"id": "502", "code": "CDH-MMU", "name": "Mass Memory Unit", "level": "equipment", "parent_id": "50"},
        {"id": "503", "code": "CDH-RTU", "name": "Remote Terminal Unit", "level": "equipment", "parent_id": "50"},
        {"id": "601", "code": "TCS-MLI", "name": "MLI Blankets", "level": "equipment", "parent_id": "60"},
        {"id": "602", "code": "TCS-HTR", "name": "Heater Lines", "level": "equipment", "parent_id": "60"},
        {"id": "603", "code": "TCS-RAD", "name": "Radiator Panel", "level": "equipment", "parent_id": "60"},
        {"id": "604", "code": "TCS-HP", "name": "Heat Pipe", "level": "equipment", "parent_id": "60"},
        {"id": "701", "code": "PROP-THR", "name": "Thruster", "level": "equipment", "parent_id": "70"},
        {"id": "702", "code": "PROP-TNK", "name": "Propellant Tank", "level": "equipment", "parent_id": "70"},
        {"id": "703", "code": "PROP-PR", "name": "Pressure Regulator", "level": "equipment", "parent_id": "70"},
        {"id": "704", "code": "PROP-FDV", "name": "Fill & Drain Valve", "level": "equipment", "parent_id": "70"},
        {"id": "801", "code": "PL-OPT", "name": "Optical Instrument", "level": "equipment", "parent_id": "80"},
        {"id": "802", "code": "PL-ELEC", "name": "Payload Electronics", "level": "equipment", "parent_id": "80"},
        {"id": "901", "code": "HRN-ELC", "name": "Electrical Harness", "level": "equipment", "parent_id": "90"},
    ]
    return nodes


def _compute_criticality(severity: int, occurrence: int) -> int:
    return severity * occurrence


def mock_requirements():
    return [
        RequirementData("1", "SH-FUN-001", "stakeholder", "functional", "Earth observation imagery", "System shall provide optical imagery at 5 m GSD", verification_method="review", verification_status="passed"),
        RequirementData("2", "MIS-FUN-001", "mission", "functional", "Orbit maintenance", "Satellite shall maintain SSO at 550 km +/- 10 km", parent_id="1", verification_method="analysis", verification_status="passed"),
        RequirementData("3", "SYS-FUN-001", "system", "functional", "Payload data downlink", "System shall downlink 2 Gbit/orbit via X-band", parent_id="2", verification_method="test", verification_status="in_progress", allocated_to=["COM"]),
        RequirementData("4", "SYS-PER-001", "system", "performance", "Pointing accuracy", "System pointing accuracy shall be < 0.1 deg (3-sigma)", parent_id="1", verification_method="test", verification_status="in_progress", allocated_to=["AOCS"]),
        RequirementData("5", "SYS-PER-002", "system", "performance", "Pointing stability", "System shall provide < 5 arcsec jitter over 1 s integration", parent_id="4", verification_method="analysis", verification_status="not_started", allocated_to=["AOCS"]),
        RequirementData("6", "SYS-ENV-001", "system", "environmental", "Radiation tolerance", "All electronics shall withstand 20 krad TID", parent_id="1", verification_method="analysis", verification_status="not_started", allocated_to=["CDH", "EPS"]),
        RequirementData("7", "SYS-DES-001", "system", "design", "Mass budget", "Total wet mass shall not exceed 350 kg", parent_id="1", verification_method="analysis", verification_status="passed"),
        RequirementData("8", "SYS-DES-002", "system", "design", "Power budget", "Average power consumption shall not exceed 500 W", parent_id="1", verification_method="analysis", verification_status="passed", allocated_to=["EPS"]),
        RequirementData("9", "SYS-REL-001", "system", "reliability", "Mission lifetime", "Mission lifetime shall be >= 5 years", parent_id="1", verification_method="analysis", verification_status="in_progress"),
        RequirementData("10", "SUB-FUN-001", "subsystem", "functional", "EPS charge management", "EPS shall maintain battery SoC > 30%", parent_id="8", verification_method="test", verification_status="not_started", allocated_to=["EPS"]),
        RequirementData("11", "SUB-FUN-002", "subsystem", "functional", "AOCS safe mode", "AOCS shall transition to safe mode within 10 s of anomaly", parent_id="4", verification_method="demonstration", verification_status="passed", allocated_to=["AOCS"]),
        RequirementData("12", "SUB-PER-001", "subsystem", "performance", "S-Band link margin", "TTC link margin shall be >= 6 dB", parent_id="3", verification_method="analysis", verification_status="passed", allocated_to=["COM"]),
        RequirementData("13", "SUB-IFC-001", "subsystem", "interface", "SpaceWire bus", "CDH shall provide SpaceWire interface at 200 Mbps", parent_id="1", verification_method="test", verification_status="in_progress", allocated_to=["CDH"]),
        RequirementData("14", "EQP-DES-001", "equipment", "design", "Star tracker FOV", "Star tracker FOV shall be >= 20 x 20 deg", parent_id="4", verification_method="inspection", verification_status="passed", allocated_to=["AOCS-STR"]),
        RequirementData("15", "SYS-SAF-001", "system", "safety", "Passivation", "Satellite shall passivate all energy sources at EOL", parent_id="1", verification_method="review", verification_status="not_started"),
    ]


def mock_risks():
    return [
        RiskItemData("1", "RSK-001", "Solar array deployment failure", "Single-point failure on SA hinge mechanism", "technical", 2, 5, "open", "EPS Lead", "Redundant hinge + deployment test", 1, 4),
        RiskItemData("2", "RSK-002", "Radiation-induced latchup", "SEL on OBC FPGA in SAA region", "technical", 3, 4, "mitigating", "CDH Lead", "Rad-hard FPGA + watchdog", 2, 3),
        RiskItemData("3", "RSK-003", "Launch delay", "Launcher manifest slip > 6 months", "schedule", 3, 3, "open", "PM", "Backup launch slot reserved"),
        RiskItemData("4", "RSK-004", "Propulsion leak", "Propellant leak at fill/drain valve", "technical", 2, 5, "mitigating", "PROP Lead", "Redundant seals + leak test", 1, 4),
        RiskItemData("5", "RSK-005", "Star tracker blinding", "Sun intrusion in STR FOV during manoeuvre", "technical", 3, 3, "open", "AOCS Lead", "Sun exclusion angle + gyro propagation"),
        RiskItemData("6", "RSK-006", "Budget overrun", "Component cost increase > 15%", "cost", 2, 3, "accepted", "PM", "Cost contingency 20%"),
        RiskItemData("7", "RSK-007", "Thermal runaway in battery", "Li-ion cell thermal runaway", "technical", 1, 5, "mitigating", "EPS Lead", "Cell-level fuses + TCS monitoring", 1, 3),
        RiskItemData("8", "RSK-008", "Ground station unavailability", "Primary GS downtime > 24 h", "external", 2, 2, "open", "OPS Lead", "Backup GS agreement"),
    ]


def mock_fmeca():
    entries = [
        FMECAEntryData("1", "EPS-SA", "Cell string open circuit", "Micrometeorite impact", "Reduced power", "Degraded mission", 3, 2, 3, "String bypass diode"),
        FMECAEntryData("2", "EPS-BAT", "Cell thermal runaway", "Internal short", "Battery loss", "Mission loss (single battery)", 5, 1, 2, "Cell-level fuse, TCS monitoring"),
        FMECAEntryData("3", "AOCS-RW", "Bearing seizure", "Lubricant degradation", "Wheel loss", "Degraded pointing (3-wheel mode)", 3, 2, 4, "4th wheel redundancy"),
        FMECAEntryData("4", "COM-SBT", "Transponder failure", "Power amplifier burnout", "No TTC on nominal", "Switchover to COM-SBR", 4, 1, 3, "Redundant transponder (cold spare)"),
        FMECAEntryData("5", "CDH-OBC", "SEL latchup", "Heavy ion strike", "OBC reset", "Temporary loss of control", 4, 3, 2, "Watchdog + rad-hard design"),
        FMECAEntryData("6", "PROP-THR", "Valve stuck closed", "Contamination", "No thrust on 1 thruster", "Reduced delta-V capability", 3, 2, 3, "Quad redundancy"),
        FMECAEntryData("7", "TCS-HTR", "Heater line open", "Wire fatigue", "Cold spot", "Component below survival temp", 4, 2, 3, "Redundant heater circuit"),
        FMECAEntryData("8", "PL-OPT", "Detector degradation", "Radiation damage", "Noise increase", "Image quality degradation", 3, 3, 3, "Annealing cycle"),
        FMECAEntryData("9", "AOCS-STR", "Star tracker blinding", "Sun intrusion", "No attitude fix", "Safe mode entry", 3, 3, 2, "Sun exclusion + gyro backup"),
        FMECAEntryData("10", "EPS-PCDU", "MOSFET short", "Over-current", "Bus anomaly", "Partial power loss", 4, 2, 3, "Current limiters + redundant switches"),
    ]
    for e in entries:
        e.criticality = _compute_criticality(e.severity, e.occurrence)
    return entries


def mock_tasks():
    return [
        TaskData("T01", "System Requirements Definition", 60, [], progress_pct=100, wbs_code="1.1", assigned_to="L. Bianchi (SE)"),
        TaskData("T02", "Preliminary Design - STR", 45, ["T01"], progress_pct=80, wbs_code="1.2.1", assigned_to="D. Colombo (STR)"),
        TaskData("T03", "Preliminary Design - EPS", 45, ["T01"], progress_pct=75, wbs_code="1.2.2", assigned_to="A. Ferrari (EPS)"),
        TaskData("T04", "Preliminary Design - AOCS", 40, ["T01"], progress_pct=70, wbs_code="1.2.3", assigned_to="G. Conti (AOCS)"),
        TaskData("T05", "Preliminary Design - COM", 40, ["T01"], progress_pct=65, wbs_code="1.2.4", assigned_to="S. Moretti (COM)"),
        TaskData("T06", "Preliminary Design - CDH", 35, ["T01"], progress_pct=60, wbs_code="1.2.5", assigned_to="P. Russo (CDH)"),
        TaskData("T07", "Preliminary Design - PL", 50, ["T01"], progress_pct=55, wbs_code="1.2.6", assigned_to="C. Marino (PL)"),
        TaskData("T08", "System-level Budgets & Margins", 30, ["T02", "T03", "T04", "T05", "T06", "T07"], progress_pct=20, wbs_code="1.3", assigned_to="L. Bianchi (SE)"),
        TaskData("T09", "Verification Plan", 25, ["T08"], progress_pct=0, wbs_code="1.4", assigned_to="R. Greco (QA)"),
        TaskData("T10", "PDR Preparation", 20, ["T08", "T09"], progress_pct=0, wbs_code="1.5", assigned_to="L. Bianchi (SE)"),
        TaskData("M_SRR", "SRR", 0, ["T01"], progress_pct=100, is_milestone=True, wbs_code="M1", assigned_to="M. Rossi (PM)"),
        TaskData("M_PDR", "PDR", 0, ["T10"], progress_pct=0, is_milestone=True, wbs_code="M2", assigned_to="M. Rossi (PM)"),
        TaskData("T11", "Detailed Design", 60, ["M_PDR"], progress_pct=0, wbs_code="2.1", assigned_to="L. Bianchi (SE)"),
        TaskData("T12", "QM Procurement", 45, ["T11"], progress_pct=0, wbs_code="2.2", assigned_to="M. Rossi (PM)"),
        TaskData("T13", "CDR Preparation", 25, ["T11", "T12"], progress_pct=0, wbs_code="2.3", assigned_to="L. Bianchi (SE)"),
        TaskData("M_CDR", "CDR", 0, ["T13"], progress_pct=0, is_milestone=True, wbs_code="M3", assigned_to="M. Rossi (PM)"),
    ]


def _code_by_id(node_id: str) -> str:
    for n in mock_product_tree_flat():
        if n["id"] == node_id:
            return n["code"]
    return ""
