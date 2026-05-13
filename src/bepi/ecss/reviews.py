REVIEW_DEFINITIONS = {
    "MDR": {
        "full_name": "Mission Definition Review",
        "phase_before": "0",
        "phase_after": "A",
        "purpose": "Confirm mission need, objectives, and feasibility",
        "entry_criteria": [
            "Mission need identified and documented",
            "Preliminary mission concept defined",
            "Feasibility study completed",
        ],
        "exit_criteria": [
            "Mission objectives approved",
            "Phase A study scope defined",
            "Preliminary cost and schedule estimates available",
        ],
        "required_documents": [
            {"drd": "MRD", "title": "Mission Requirements Document"},
            {"drd": "MCD", "title": "Mission Concept Document"},
        ],
    },
    "PRR": {
        "full_name": "Preliminary Requirements Review",
        "phase_before": "A",
        "phase_after": "B1",
        "purpose": "Confirm system requirements baseline and selected concept",
        "entry_criteria": [
            "System requirements defined",
            "At least two mission concepts evaluated",
            "Preliminary risk assessment completed",
        ],
        "exit_criteria": [
            "System requirements baseline approved",
            "Preferred mission concept selected",
            "Phase B work plan approved",
        ],
        "required_documents": [
            {"drd": "SRD", "title": "System Requirements Document"},
            {"drd": "SEP", "title": "System Engineering Plan"},
            {"drd": "PMP", "title": "Project Management Plan"},
        ],
    },
    "SRR": {
        "full_name": "System Requirements Review",
        "phase_before": "B1",
        "phase_after": "B2",
        "purpose": "Confirm system requirements are complete and consistent",
        "entry_criteria": [
            "System requirements fully defined and traced",
            "Verification approach defined for all requirements",
            "Preliminary design concept established",
        ],
        "exit_criteria": [
            "All system requirements reviewed and approved",
            "Verification matrix complete",
            "Risk register updated",
        ],
        "required_documents": [
            {"drd": "SRD", "title": "System Requirements Document (updated)"},
            {"drd": "VCD", "title": "Verification Control Document"},
            {"drd": "ICD", "title": "Interface Control Documents"},
            {"drd": "RAR", "title": "Risk Assessment Report"},
        ],
    },
    "PDR": {
        "full_name": "Preliminary Design Review",
        "phase_before": "B2",
        "phase_after": "C",
        "purpose": "Confirm preliminary design meets requirements and is ready for detailed design",
        "entry_criteria": [
            "Preliminary design complete for all subsystems",
            "All budgets established (mass, power, link, thermal)",
            "Verification plan defined",
            "Technology readiness demonstrated (TRL >= 5 for critical items)",
        ],
        "exit_criteria": [
            "Preliminary design approved",
            "Budget margins acceptable",
            "Detailed design phase authorized",
            "Make-or-buy decisions taken",
        ],
        "required_documents": [
            {"drd": "DDF", "title": "Design Definition File"},
            {"drd": "BMR", "title": "Budget and Margin Report"},
            {"drd": "VP", "title": "Verification Plan"},
            {"drd": "PA-PLAN", "title": "Product Assurance Plan"},
            {"drd": "MAIT-PLAN", "title": "MAIT Plan"},
        ],
    },
    "CDR": {
        "full_name": "Critical Design Review",
        "phase_before": "C",
        "phase_after": "D",
        "purpose": "Confirm detailed design is complete and ready for manufacturing",
        "entry_criteria": [
            "Detailed design complete with manufacturing drawings",
            "All analyses completed (structural, thermal, EMC, etc.)",
            "Test specifications written",
            "All components identified and procurement started",
        ],
        "exit_criteria": [
            "Design baseline frozen",
            "Manufacturing authorized",
            "Test readiness confirmed",
            "All non-conformances resolved or waived",
        ],
        "required_documents": [
            {"drd": "DDF", "title": "Design Definition File (detailed)"},
            {"drd": "TS", "title": "Test Specifications"},
            {"drd": "AS-DOC", "title": "Analysis Summary Documents"},
            {"drd": "DJF", "title": "Design Justification File"},
            {"drd": "PPPL", "title": "Preferred Parts and Processes List"},
        ],
    },
    "QR": {
        "full_name": "Qualification Review",
        "phase_before": "D",
        "phase_after": "E1",
        "purpose": "Confirm product is qualified and flight model is ready for acceptance",
        "entry_criteria": [
            "Qualification testing completed successfully",
            "All NCRs closed or dispositioned",
            "Flight model manufactured and integrated",
        ],
        "exit_criteria": [
            "Qualification status approved",
            "FM acceptance testing authorized",
        ],
        "required_documents": [
            {"drd": "QSR", "title": "Qualification Status Report"},
            {"drd": "TR", "title": "Test Reports"},
            {"drd": "NCR-LOG", "title": "Non-Conformance Report Log"},
        ],
    },
    "AR": {
        "full_name": "Acceptance Review",
        "phase_before": "D",
        "phase_after": "E1",
        "purpose": "Confirm FM acceptance testing complete and product ready for delivery",
        "entry_criteria": [
            "FM acceptance testing completed",
            "All NCRs from acceptance testing resolved",
            "End-item data package complete",
        ],
        "exit_criteria": [
            "Product accepted",
            "Delivery to launch site authorized",
        ],
        "required_documents": [
            {"drd": "ATR", "title": "Acceptance Test Report"},
            {"drd": "EIDP", "title": "End-Item Data Package"},
        ],
    },
    "ORR": {
        "full_name": "Operational Readiness Review",
        "phase_before": "E1",
        "phase_after": "E2",
        "purpose": "Confirm ground segment and operations team ready",
        "entry_criteria": [
            "Operations procedures validated",
            "Ground segment tested end-to-end",
            "Operations team trained",
        ],
        "exit_criteria": [
            "Operational readiness confirmed",
            "Operations phase authorized",
        ],
        "required_documents": [
            {"drd": "OP", "title": "Operations Plan"},
            {"drd": "FOP", "title": "Flight Operations Procedures"},
        ],
    },
    "FRR": {
        "full_name": "Flight Readiness Review",
        "phase_before": "E1",
        "phase_after": "E1",
        "purpose": "Final go/no-go for launch",
        "entry_criteria": [
            "Spacecraft at launch site and fueled",
            "Launch vehicle integration complete",
            "All open items resolved",
            "Range safety approval obtained",
        ],
        "exit_criteria": [
            "Launch authorized",
        ],
        "required_documents": [
            {"drd": "FRR-DP", "title": "FRR Data Package"},
            {"drd": "RSOA", "title": "Range Safety Approval"},
        ],
    },
    "LRR": {
        "full_name": "Launch Readiness Review",
        "phase_before": "E1",
        "phase_after": "E1",
        "purpose": "Confirm all systems go for countdown",
        "entry_criteria": [
            "All countdown prerequisites met",
            "Weather constraints satisfied",
            "All teams in position",
        ],
        "exit_criteria": [
            "Countdown authorized",
        ],
        "required_documents": [],
    },
    "CRR": {
        "full_name": "Commissioning Result Review",
        "phase_before": "E1",
        "phase_after": "E2",
        "purpose": "Confirm satellite commissioned and ready for routine operations",
        "entry_criteria": [
            "In-orbit checkout completed",
            "All subsystems verified functional",
            "Payload calibrated",
        ],
        "exit_criteria": [
            "Routine operations authorized",
        ],
        "required_documents": [
            {"drd": "CRR-RP", "title": "Commissioning Results Report"},
        ],
    },
    "ELR": {
        "full_name": "End of Life Review",
        "phase_before": "E2",
        "phase_after": "F",
        "purpose": "Confirm disposal plan and authorize end-of-life operations",
        "entry_criteria": [
            "Mission objectives fulfilled or resources depleted",
            "Disposal plan updated with current status",
            "Passivation plan reviewed",
        ],
        "exit_criteria": [
            "Disposal operations authorized",
        ],
        "required_documents": [
            {"drd": "DP", "title": "Disposal Plan"},
        ],
    },
    "MCR": {
        "full_name": "Mission Close-out Review",
        "phase_before": "F",
        "phase_after": None,
        "purpose": "Close mission, capture lessons learned",
        "entry_criteria": [
            "Disposal operations completed",
            "All data archived",
        ],
        "exit_criteria": [
            "Mission officially closed",
            "Lessons learned documented",
        ],
        "required_documents": [
            {"drd": "MCR-RP", "title": "Mission Close-out Report"},
            {"drd": "LL", "title": "Lessons Learned Report"},
        ],
    },
}
