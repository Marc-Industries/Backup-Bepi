"""Product tree operations."""
from dataclasses import dataclass, field


@dataclass
class ProductNodeData:
    """Lightweight product node for tree operations."""
    id: str
    code: str
    name: str
    level: str
    subsystem_type: str | None = None
    quantity: int = 1
    parent_id: str | None = None
    children: list["ProductNodeData"] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def build_tree(nodes: list[dict]) -> ProductNodeData | None:
    """Build tree from flat list of node dicts (e.g. from DB query).
    Each dict has: id, code, name, level, parent_id, subsystem_type, quantity.
    Returns root node with children populated recursively.
    """
    if not nodes:
        return None

    node_map: dict[str, ProductNodeData] = {}
    for n in nodes:
        node_map[str(n["id"])] = ProductNodeData(
            id=str(n["id"]),
            code=n["code"],
            name=n["name"],
            level=n["level"],
            subsystem_type=n.get("subsystem_type"),
            quantity=n.get("quantity", 1),
            parent_id=str(n["parent_id"]) if n.get("parent_id") is not None else None,
            metadata=n.get("metadata", {}),
        )

    roots = []
    for node in node_map.values():
        if node.parent_id is None:
            roots.append(node)
        else:
            parent = node_map.get(node.parent_id)
            if parent is not None:
                parent.children.append(node)

    if not roots:
        return None
    if len(roots) == 1:
        return roots[0]
    # Multiple roots → wrap in synthetic MISSION node
    mission = ProductNodeData(
        id="__mission__", code="MISSION", name="Mission System",
        level="mission", children=roots,
    )
    return mission


def flatten_tree(root: ProductNodeData) -> list[ProductNodeData]:
    """Flatten tree to list (depth-first)."""
    result = [root]
    for child in root.children:
        result.extend(flatten_tree(child))
    return result


def find_node(root: ProductNodeData, code: str) -> ProductNodeData | None:
    """Find node by code in tree (depth-first search)."""
    if root.code == code:
        return root
    for child in root.children:
        found = find_node(child, code)
        if found is not None:
            return found
    return None


def compute_wbs_codes(root: ProductNodeData, prefix: str = "1") -> dict[str, str]:
    """Generate WBS codes from product tree structure.
    Returns {node_id: wbs_code} mapping.
    E.g.: SAT→"1", STR→"1.1", EPS→"1.2", EPS-SA→"1.2.1"
    """
    result = {root.id: prefix}
    for i, child in enumerate(root.children, start=1):
        child_prefix = f"{prefix}.{i}"
        result.update(compute_wbs_codes(child, child_prefix))
    return result


def generate_node_code(parent_code: str, subsystem_type: str | None, index: int) -> str:
    """Generate a node code based on parent and subsystem type.
    E.g.: parent="SAT", subsystem="EPS" → "EPS"
          parent="EPS", subsystem=None, index=1 → "EPS-001"
    """
    if subsystem_type:
        return subsystem_type
    return f"{parent_code}-{index:03d}"


def get_subsystem_template(subsystem_type: str) -> list[dict]:
    """Return a template of typical equipment for a subsystem type.
    Uses ECSS subsystem definitions to suggest standard equipment.
    """
    templates = {
        "EPS": [
            {"name": "Solar Array", "code_suffix": "SA", "level": "equipment"},
            {"name": "Battery Pack", "code_suffix": "BAT", "level": "equipment"},
            {"name": "Power Control & Distribution Unit", "code_suffix": "PCDU", "level": "equipment"},
        ],
        "AOCS": [
            {"name": "Star Tracker", "code_suffix": "STR", "level": "equipment", "quantity": 2},
            {"name": "Sun Sensor", "code_suffix": "SS", "level": "equipment", "quantity": 4},
            {"name": "Reaction Wheel", "code_suffix": "RW", "level": "equipment", "quantity": 4},
            {"name": "Magnetorquer", "code_suffix": "MT", "level": "equipment", "quantity": 3},
            {"name": "Gyroscope", "code_suffix": "GYR", "level": "equipment"},
        ],
        "COM": [
            {"name": "S-Band Transponder", "code_suffix": "SBT", "level": "equipment"},
            {"name": "S-Band Antenna", "code_suffix": "SBA", "level": "equipment", "quantity": 2},
            {"name": "X-Band Transmitter", "code_suffix": "XBT", "level": "equipment"},
            {"name": "X-Band Antenna", "code_suffix": "XBA", "level": "equipment"},
        ],
        "CDH": [
            {"name": "On-Board Computer", "code_suffix": "OBC", "level": "equipment"},
            {"name": "Mass Memory Unit", "code_suffix": "MMU", "level": "equipment"},
            {"name": "Remote Terminal Unit", "code_suffix": "RTU", "level": "equipment", "quantity": 2},
        ],
        "TCS": [
            {"name": "MLI Blankets", "code_suffix": "MLI", "level": "equipment"},
            {"name": "Heater Lines", "code_suffix": "HTR", "level": "equipment"},
            {"name": "Radiator Panel", "code_suffix": "RAD", "level": "equipment"},
            {"name": "Heat Pipe", "code_suffix": "HP", "level": "equipment", "quantity": 4},
        ],
        "PROP": [
            {"name": "Thruster", "code_suffix": "THR", "level": "equipment", "quantity": 4},
            {"name": "Propellant Tank", "code_suffix": "TNK", "level": "equipment"},
            {"name": "Pressure Regulator", "code_suffix": "PR", "level": "equipment"},
            {"name": "Fill & Drain Valve", "code_suffix": "FDV", "level": "equipment"},
        ],
        "STR": [
            {"name": "Primary Structure", "code_suffix": "PRI", "level": "equipment"},
            {"name": "Secondary Structure", "code_suffix": "SEC", "level": "equipment"},
            {"name": "Interface Ring", "code_suffix": "IFR", "level": "equipment"},
        ],
        "MECH": [
            {"name": "Solar Array Drive Mechanism", "code_suffix": "SADM", "level": "equipment"},
            {"name": "Hold-Down & Release Mechanism", "code_suffix": "HDRM", "level": "equipment"},
            {"name": "Deployment Mechanism", "code_suffix": "DPL", "level": "equipment"},
        ],
    }
    return templates.get(subsystem_type, [])
