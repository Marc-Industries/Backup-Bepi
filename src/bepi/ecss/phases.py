PHASE_DEFINITIONS = {
    "0": {"name": "Mission Analysis / Needs Identification", "typical_duration_months": 6, "key_activity": "Feasibility study, mission concept"},
    "A": {"name": "Feasibility", "typical_duration_months": 12, "key_activity": "System requirements, concept selection"},
    "B1": {"name": "Preliminary Definition", "typical_duration_months": 12, "key_activity": "Preliminary design, technology development"},
    "B2": {"name": "Detailed Definition", "typical_duration_months": 12, "key_activity": "Detailed design baseline"},
    "C": {"name": "Detailed Definition", "typical_duration_months": 18, "key_activity": "Detailed design completion, start QM procurement"},
    "D": {"name": "Qualification & Production", "typical_duration_months": 18, "key_activity": "QM/FM manufacturing, integration, qualification testing"},
    "E1": {"name": "Utilization - Commissioning", "typical_duration_months": 3, "key_activity": "Launch, LEOP, commissioning"},
    "E2": {"name": "Utilization - Operations", "typical_duration_months": 60, "key_activity": "Routine operations"},
    "F": {"name": "Disposal", "typical_duration_months": 6, "key_activity": "Decommissioning, passivation, deorbit"},
}

PHASE_TRANSITIONS = {
    "0": ["A"],
    "A": ["B1"],
    "B1": ["B2"],
    "B2": ["C"],
    "C": ["D"],
    "D": ["E1"],
    "E1": ["E2"],
    "E2": ["F"],
    "F": [],
}

PHASE_GATE_REVIEWS = {
    ("0", "A"): "MDR",
    ("A", "B1"): "PRR",
    ("B1", "B2"): "SRR",
    ("B2", "C"): "PDR",
    ("C", "D"): "CDR",
    ("D", "E1"): "QR",
    ("E1", "E2"): "ORR",
    ("E2", "F"): "ELR",
}

# ---------------------------------------------------------------------------
# NASA Phase Framework (NPR 7120.5)
# ---------------------------------------------------------------------------

NASA_PHASE_DEFINITIONS = {
    "Pre-A": {"name": "Concept Studies", "typical_duration_months": 12, "key_activity": "Mission concept exploration, feasibility assessment"},
    "A": {"name": "Concept & Technology Development", "typical_duration_months": 18, "key_activity": "Concept refinement, technology identification, SRR"},
    "B": {"name": "Preliminary Design & Technology Completion", "typical_duration_months": 24, "key_activity": "Preliminary design, PDR, technology maturation"},
    "C": {"name": "Final Design & Fabrication", "typical_duration_months": 24, "key_activity": "Detailed design, CDR, fabrication, component testing"},
    "D": {"name": "System Assembly, Integration & Test, Launch", "typical_duration_months": 18, "key_activity": "System integration, qualification, launch"},
    "E": {"name": "Operations & Sustainment", "typical_duration_months": 60, "key_activity": "Mission operations, data collection"},
    "F": {"name": "Closeout", "typical_duration_months": 6, "key_activity": "Disposal, data archival, lessons learned"},
}

NASA_PHASE_TRANSITIONS = {
    "Pre-A": ["A"],
    "A": ["B"],
    "B": ["C"],
    "C": ["D"],
    "D": ["E"],
    "E": ["F"],
    "F": [],
}

NASA_PHASE_GATE_REVIEWS = {
    ("Pre-A", "A"): "MCR",    # Mission Concept Review
    ("A", "B"): "SRR/MDR",    # System Requirements Review / Mission Definition Review
    ("B", "C"): "PDR",        # Preliminary Design Review
    ("C", "D"): "CDR",        # Critical Design Review
    ("D", "E"): "ORR/FRR",    # Operational/Flight Readiness Review
    ("E", "F"): "DR",         # Decommissioning Review
}

# ---------------------------------------------------------------------------
# TRL targets per project phase
# ---------------------------------------------------------------------------

ESA_TRL_TARGETS = {
    "0": {"min": 1, "target": 2, "description": "Basic principles observed"},
    "A": {"min": 2, "target": 3, "description": "Analytical/experimental proof of concept"},
    "B1": {"min": 3, "target": 4, "description": "Component validation in lab"},
    "B2": {"min": 4, "target": 5, "description": "Component validation in relevant environment"},
    "C": {"min": 5, "target": 6, "description": "Model demonstration in relevant environment"},
    "D": {"min": 6, "target": 8, "description": "Qualified & flight-proven"},
    "E1": {"min": 8, "target": 9, "description": "Flight-proven in operations"},
    "E2": {"min": 9, "target": 9, "description": "Flight-proven in operations"},
    "F": {"min": 9, "target": 9, "description": "End of life"},
}

NASA_TRL_TARGETS = {
    "Pre-A": {"min": 1, "target": 2, "description": "Basic principles observed"},
    "A": {"min": 2, "target": 3, "description": "Proof of concept"},
    "B": {"min": 4, "target": 5, "description": "Component validated in relevant environment"},
    "C": {"min": 5, "target": 6, "description": "System model demonstrated"},
    "D": {"min": 6, "target": 8, "description": "System qualified and flight-proven"},
    "E": {"min": 8, "target": 9, "description": "Flight-proven in operations"},
    "F": {"min": 9, "target": 9, "description": "End of life"},
}

# ---------------------------------------------------------------------------
# Activities expected per phase
# ---------------------------------------------------------------------------

ESA_PHASE_ACTIVITIES = {
    "0": ["Mission needs analysis", "Concept exploration", "Feasibility assessment", "Technology survey"],
    "A": ["System requirements definition", "Concept trade-offs", "Preliminary risk assessment", "Cost estimation"],
    "B1": ["Preliminary design", "Technology development plans", "Breadboard/EM procurement", "Test planning"],
    "B2": ["Design baseline freeze", "Interface definition", "EM testing", "Procurement specifications"],
    "C": ["Detailed design completion", "QM procurement", "Software development", "AIT planning"],
    "D": ["QM/FM manufacturing", "Qualification testing", "FM integration", "System validation"],
    "E1": ["Launch campaign", "LEOP", "In-orbit commissioning", "Performance verification"],
    "E2": ["Routine operations", "Payload data exploitation", "Orbit maintenance", "Anomaly handling"],
    "F": ["Passivation", "Deorbit/graveyard", "Data archival", "Lessons learned"],
}

NASA_PHASE_ACTIVITIES = {
    "Pre-A": ["Mission concept exploration", "Science objectives definition", "Feasibility studies", "Technology survey"],
    "A": ["Concept refinement", "System requirements", "Technology development", "Cost/schedule baseline"],
    "B": ["Preliminary design", "PDR preparation", "Technology maturation", "Prototype testing"],
    "C": ["Final design", "CDR", "Component fabrication", "Software development"],
    "D": ["System assembly", "Integration & test", "Launch preparation", "Flight readiness"],
    "E": ["Mission operations", "Data collection", "Orbit maintenance", "Extended mission planning"],
    "F": ["Disposal operations", "Data archival", "Final reporting", "Lessons learned"],
}

# ---------------------------------------------------------------------------
# MAIT status progression per phase
# ---------------------------------------------------------------------------

ESA_MAIT_STATUS = {
    "0": "N/A",
    "A": "N/A",
    "B1": "EM procurement",
    "B2": "EM testing",
    "C": "QM procurement & testing",
    "D": "FM manufacturing, AIT, qualification",
    "E1": "Launch campaign",
    "E2": "In-orbit operations",
    "F": "Decommissioning",
}

# ---------------------------------------------------------------------------
# Framework selector
# ---------------------------------------------------------------------------

FRAMEWORKS = {
    "ESA": {
        "phases": PHASE_DEFINITIONS,
        "transitions": PHASE_TRANSITIONS,
        "gate_reviews": PHASE_GATE_REVIEWS,
        "trl_targets": ESA_TRL_TARGETS,
        "activities": ESA_PHASE_ACTIVITIES,
    },
    "NASA": {
        "phases": NASA_PHASE_DEFINITIONS,
        "transitions": NASA_PHASE_TRANSITIONS,
        "gate_reviews": NASA_PHASE_GATE_REVIEWS,
        "trl_targets": NASA_TRL_TARGETS,
        "activities": NASA_PHASE_ACTIVITIES,
    },
}


def get_framework(name: str = "ESA") -> dict:
    return FRAMEWORKS.get(name, FRAMEWORKS["ESA"])
