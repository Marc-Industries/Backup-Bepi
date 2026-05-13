import enum


class Phase(str, enum.Enum):
    ZERO = "0"
    A = "A"
    B1 = "B1"
    B2 = "B2"
    C = "C"
    D = "D"
    E1 = "E1"
    E2 = "E2"
    F = "F"


class ProductLevel(str, enum.Enum):
    MISSION = "mission"
    SATELLITE = "satellite"
    SUBSYSTEM = "subsystem"
    EQUIPMENT = "equipment"
    COMPONENT = "component"


class SubsystemType(str, enum.Enum):
    STR = "STR"
    TCS = "TCS"
    EPS = "EPS"
    AOCS = "AOCS"
    PROP = "PROP"
    COM = "COM"
    CDH = "CDH"
    MECH = "MECH"
    PL = "PL"
    HRN = "HRN"
    SW = "SW"


class BudgetType(str, enum.Enum):
    MASS_KG = "mass_kg"
    POWER_W = "power_w"
    POWER_PEAK_W = "power_peak_w"
    DISSIPATION_W = "dissipation_w"
    COST_EUR = "cost_eur"
    COST_NRE_EUR = "cost_nre_eur"
    DATA_RATE_KBPS = "data_rate_kbps"
    VOLUME_CM3 = "volume_cm3"
    DELTA_V_MS = "delta_v_ms"
    CUSTOM = "custom"


class Maturity(str, enum.Enum):
    ESTIMATE = "estimate"
    MEASURED = "measured"
    QUALIFIED = "qualified"


class MarginStatus(str, enum.Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class RequirementLevel(str, enum.Enum):
    STAKEHOLDER = "stakeholder"
    MISSION = "mission"
    SYSTEM = "system"
    SUBSYSTEM = "subsystem"
    EQUIPMENT = "equipment"


class RequirementCategory(str, enum.Enum):
    FUNCTIONAL = "functional"
    PERFORMANCE = "performance"
    INTERFACE = "interface"
    ENVIRONMENTAL = "environmental"
    DESIGN = "design"
    OPERATIONAL = "operational"
    RELIABILITY = "reliability"
    SAFETY = "safety"
    PA = "product_assurance"


class VerificationMethod(str, enum.Enum):
    T = "test"
    A = "analysis"
    I = "inspection"
    R = "review"
    D = "demonstration"


class VerificationStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    WAIVED = "waived"


class RequirementStatus(str, enum.Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DELETED = "deleted"


class Priority(str, enum.Enum):
    MANDATORY = "mandatory"
    DESIRABLE = "desirable"
    OPTIONAL = "optional"


class RiskCategory(str, enum.Enum):
    TECHNICAL = "technical"
    SCHEDULE = "schedule"
    COST = "cost"
    PROGRAMMATIC = "programmatic"
    EXTERNAL = "external"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskStatus(str, enum.Enum):
    OPEN = "open"
    MITIGATING = "mitigating"
    ACCEPTED = "accepted"
    CLOSED = "closed"
    RETIRED = "retired"


class Criticality(str, enum.Enum):
    CAT_1 = "cat_1"
    CAT_2 = "cat_2"
    CAT_3 = "cat_3"
    CAT_4 = "cat_4"


class FTGateType(str, enum.Enum):
    AND = "and"
    OR = "or"
    VOTE = "vote_k_of_n"


class TaskStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ON_HOLD = "on_hold"


class DependencyType(str, enum.Enum):
    FS = "finish_to_start"
    FF = "finish_to_finish"
    SS = "start_to_start"
    SF = "start_to_finish"


class MilestoneStatus(str, enum.Enum):
    PLANNED = "planned"
    ACHIEVED = "achieved"
    MISSED = "missed"
    REPLANNED = "replanned"


class ReviewType(str, enum.Enum):
    MDR = "MDR"
    PRR = "PRR"
    SRR = "SRR"
    PDR = "PDR"
    CDR = "CDR"
    QR = "QR"
    AR = "AR"
    ORR = "ORR"
    FRR = "FRR"
    LRR = "LRR"
    CRR = "CRR"
    ELR = "ELR"
    MCR = "MCR"


class ReviewStatus(str, enum.Enum):
    NOT_READY = "not_ready"
    IN_PREPARATION = "in_preparation"
    READY = "ready"
    PASSED = "passed"
    CONDITIONAL = "conditional"
    FAILED = "failed"


class DeliverableStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"


class ComponentStatus(str, enum.Enum):
    PROPOSED = "proposed"
    SELECTED = "selected"
    QUALIFIED = "qualified"
    FLIGHT = "flight"


class MatlabEngine(str, enum.Enum):
    MATLAB = "matlab"
    OCTAVE = "octave"
