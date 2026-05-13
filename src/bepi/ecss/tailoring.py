def create_default_tailoring(mission_type: str = "standard") -> dict:
    """Create default ECSS tailoring based on mission type.

    mission_type: "standard", "small_satellite", "cubesat", "technology_demo"
    Returns dict of {standard_id: "applicable" | "tailored_out" | "modified"}
    """
    from bepi.ecss.standards import ECSS_STANDARDS

    tailoring = {std_id: "applicable" for std_id in ECSS_STANDARDS}

    if mission_type == "cubesat":
        tailored_out = [
            "ECSS-E-ST-35C",       # No propulsion typically
            "ECSS-E-ST-33-01C",    # No complex mechanisms
            # "ECSS-E-ST-20-08C" moved to modified
            "ECSS-M-ST-60C",       # Simplified cost/schedule management
            "ECSS-Q-ST-30C",       # Simplified dependability analysis
            "ECSS-Q-ST-40C",       # Simplified safety analysis
            "ECSS-Q-ST-60C",       # COTS parts accepted
            "ECSS-Q-ST-70C",       # Simplified materials control
        ]
        modified = [
            "ECSS-E-ST-20-08C",    # Body-mounted cells, simplified requirements
            "ECSS-E-ST-10C",       # Simplified SE process
            "ECSS-E-ST-10-02C",    # Reduced verification rigor
            "ECSS-E-ST-10-03C",    # Reduced test campaign
            "ECSS-Q-ST-10C",       # Tailored PA programme
            "ECSS-Q-ST-20C",       # Simplified quality assurance
            "ECSS-Q-ST-80C",       # Software PA tailored
            "ECSS-E-ST-40C",       # Software lifecycle tailored
        ]
        for std in tailored_out:
            if std in tailoring:
                tailoring[std] = "tailored_out"
        for std in modified:
            if std in tailoring:
                tailoring[std] = "modified"

    elif mission_type == "small_satellite":
        tailored_out = [
            "ECSS-M-ST-60C",       # Simplified cost management
        ]
        modified = [
            "ECSS-E-ST-10C",       # Adapted SE process
            "ECSS-E-ST-10-02C",    # Reduced verification margins
            "ECSS-Q-ST-30C",       # Simplified dependability
            "ECSS-Q-ST-60C",       # Some COTS EEE accepted with screening
            "ECSS-Q-ST-80C",       # Software PA tailored
        ]
        for std in tailored_out:
            if std in tailoring:
                tailoring[std] = "tailored_out"
        for std in modified:
            if std in tailoring:
                tailoring[std] = "modified"

    elif mission_type == "technology_demo":
        tailored_out = [
            "ECSS-M-ST-60C",       # Simplified cost management
            "ECSS-Q-ST-40C",       # Reduced safety requirements
        ]
        modified = [
            "ECSS-E-ST-10C",       # Adapted SE process for demo missions
            "ECSS-E-ST-10-02C",    # Reduced verification requirements
            "ECSS-E-ST-10-03C",    # Reduced test requirements
            "ECSS-Q-ST-10C",       # Tailored PA
            "ECSS-Q-ST-20C",       # Simplified quality assurance
            "ECSS-Q-ST-30C",       # Simplified dependability
            "ECSS-Q-ST-60C",       # COTS EEE accepted with risk acceptance
        ]
        for std in tailored_out:
            if std in tailoring:
                tailoring[std] = "tailored_out"
        for std in modified:
            if std in tailoring:
                tailoring[std] = "modified"

    # "standard" keeps all applicable

    return tailoring
