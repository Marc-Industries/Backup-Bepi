"""Import from external tool formats.

Supported formats:
- DOORS CSV/ReqIF (requirements)
- MS Project XML (schedule)
- Altium BOM CSV (product tree / components)
- Valispace JSON export
- Generic CSV/TSV
"""
import csv
import io
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass
class ImportResult:
    success: bool
    records: list[dict]
    warnings: list[str]
    source_format: str
    record_count: int = 0


# ── DOORS CSV Import ─────────────────────────────────────────────────

def import_doors_csv(file_bytes: bytes, encoding: str = "utf-8") -> ImportResult:
    """Import requirements from IBM DOORS CSV export.
    Expected columns: Object Identifier, Object Heading, Object Text,
    Object Type, IE Links (parent trace), etc.
    """
    warnings = []
    records = []
    text = file_bytes.decode(encoding, errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    col_map = {}
    if reader.fieldnames:
        for f in reader.fieldnames:
            fl = f.lower().strip()
            if "identifier" in fl or "id" in fl:
                col_map["req_id"] = f
            elif "heading" in fl or "title" in fl:
                col_map["title"] = f
            elif "text" in fl and "object" in fl:
                col_map["text"] = f
            elif "type" in fl:
                col_map["type"] = f
            elif "link" in fl or "trace" in fl or "parent" in fl:
                col_map["parent"] = f
            elif "level" in fl or "depth" in fl:
                col_map["level"] = f

    if "req_id" not in col_map and "title" not in col_map:
        return ImportResult(False, [], ["Cannot identify ID or Title column in DOORS CSV"], "DOORS CSV")

    for row in reader:
        req_id = row.get(col_map.get("req_id", ""), "").strip()
        title = row.get(col_map.get("title", ""), "").strip()
        text = row.get(col_map.get("text", ""), "").strip()
        parent = row.get(col_map.get("parent", ""), "").strip()

        if not req_id and not title:
            continue

        records.append({
            "req_id": req_id or f"IMP-{len(records)+1:03d}",
            "title": title or "(untitled)",
            "text": text,
            "parent_id": parent,
            "level": "system",
            "category": "functional",
            "verification_method": "",
            "verification_status": "not_started",
            "source": "DOORS import",
        })

    return ImportResult(True, records, warnings, "DOORS CSV", len(records))


# ── ReqIF Import ─────────────────────────────────────────────────────

def import_reqif(file_bytes: bytes) -> ImportResult:
    """Import requirements from ReqIF XML (Requirements Interchange Format).
    Used by DOORS, Polarion, codeBeamer, etc.
    """
    warnings = []
    records = []

    try:
        root = ET.fromstring(file_bytes)
    except ET.ParseError as e:
        return ImportResult(False, [], [f"XML parse error: {e}"], "ReqIF")

    ns = {"reqif": "http://www.omg.org/spec/ReqIF/20110401/reqif.xsd"}

    # Try with namespace
    spec_objects = root.findall(".//reqif:SPEC-OBJECT", ns)
    if not spec_objects:
        # Try without namespace
        spec_objects = root.findall(".//{http://www.omg.org/spec/ReqIF/20110401/reqif.xsd}SPEC-OBJECT")
    if not spec_objects:
        spec_objects = root.findall(".//SPEC-OBJECT")

    for obj in spec_objects:
        identifier = obj.get("IDENTIFIER", "")
        long_name = obj.get("LONG-NAME", "")

        # Extract attribute values
        text = ""
        values = obj.findall(".//ATTRIBUTE-VALUE-STRING") + obj.findall(
            ".//{http://www.omg.org/spec/ReqIF/20110401/reqif.xsd}ATTRIBUTE-VALUE-STRING")
        for v in values:
            val = v.get("THE-VALUE", "")
            if len(val) > len(text):
                text = val

        xhtml_values = obj.findall(".//ATTRIBUTE-VALUE-XHTML") + obj.findall(
            ".//{http://www.omg.org/spec/ReqIF/20110401/reqif.xsd}ATTRIBUTE-VALUE-XHTML")
        for v in xhtml_values:
            div = v.find(".//{http://www.w3.org/1999/xhtml}div")
            if div is not None and div.text:
                if len(div.text) > len(text):
                    text = div.text

        if not identifier and not long_name and not text:
            continue

        records.append({
            "req_id": identifier or f"RIF-{len(records)+1:03d}",
            "title": long_name or text[:80],
            "text": text,
            "level": "system",
            "category": "functional",
            "verification_method": "",
            "verification_status": "not_started",
            "source": "ReqIF import",
        })

    return ImportResult(True, records, warnings, "ReqIF", len(records))


# ── MS Project XML Import ────────────────────────────────────────────

def import_msproject_xml(file_bytes: bytes) -> ImportResult:
    """Import tasks from Microsoft Project XML export."""
    warnings = []
    records = []

    try:
        root = ET.fromstring(file_bytes)
    except ET.ParseError as e:
        return ImportResult(False, [], [f"XML parse error: {e}"], "MS Project XML")

    ns = {"msp": "http://schemas.microsoft.com/project"}

    tasks = root.findall(".//msp:Task", ns)
    if not tasks:
        tasks = root.findall(".//Task")

    uid_map = {}  # UID → name mapping for predecessors

    for task in tasks:
        uid = _xml_text(task, "UID", ns) or _xml_text(task, "UID")
        name = _xml_text(task, "Name", ns) or _xml_text(task, "Name") or ""
        wbs = _xml_text(task, "WBS", ns) or _xml_text(task, "WBS") or ""
        start = _xml_text(task, "Start", ns) or _xml_text(task, "Start") or ""
        finish = _xml_text(task, "Finish", ns) or _xml_text(task, "Finish") or ""
        duration = _xml_text(task, "Duration", ns) or _xml_text(task, "Duration") or ""
        pct = _xml_text(task, "PercentComplete", ns) or _xml_text(task, "PercentComplete") or "0"
        milestone = _xml_text(task, "Milestone", ns) or _xml_text(task, "Milestone") or "0"

        if not name or name == "":
            continue

        uid_map[uid] = name

        # Parse predecessors
        preds = []
        for pred_link in (task.findall("msp:PredecessorLink", ns) + task.findall("PredecessorLink")):
            pred_uid = _xml_text(pred_link, "PredecessorUID", ns) or _xml_text(pred_link, "PredecessorUID")
            if pred_uid:
                preds.append(pred_uid)

        # Parse duration (PT8H0M0S format)
        duration_days = 0
        if duration:
            if "D" in duration.upper():
                try:
                    d_str = duration.upper().replace("PT", "").split("D")[0]
                    duration_days = int(d_str)
                except ValueError:
                    pass
            elif "H" in duration.upper():
                try:
                    h_str = duration.upper().replace("PT", "").split("H")[0]
                    duration_days = int(h_str) // 8
                except ValueError:
                    pass

        records.append({
            "id": uid or f"T{len(records)+1}",
            "name": name,
            "wbs": wbs,
            "start": start[:10] if start else "",
            "end": finish[:10] if finish else "",
            "duration": duration_days,
            "progress": int(pct),
            "is_milestone": milestone == "1",
            "predecessor_uids": preds,
            "source": "MS Project import",
        })

    # Resolve predecessor UIDs to names
    for r in records:
        r["predecessors"] = [uid_map.get(uid, uid) for uid in r.pop("predecessor_uids", [])]

    return ImportResult(True, records, warnings, "MS Project XML", len(records))


def _xml_text(elem, tag: str, ns: dict | None = None) -> str | None:
    if ns:
        child = elem.find(f"msp:{tag}", ns)
    else:
        child = elem.find(tag)
    return child.text if child is not None else None


# ── Altium BOM CSV Import ────────────────────────────────────────────

def import_altium_bom(file_bytes: bytes, encoding: str = "utf-8") -> ImportResult:
    """Import component BOM from Altium Designer CSV export.
    Expected columns: Designator, Comment/Value, Footprint, Description,
    Quantity, Manufacturer, Part Number
    """
    warnings = []
    records = []
    text = file_bytes.decode(encoding, errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    col_map = {}
    if reader.fieldnames:
        for f in reader.fieldnames:
            fl = f.lower().strip()
            if "designator" in fl:
                col_map["code"] = f
            elif "comment" in fl or "value" in fl:
                col_map["value"] = f
            elif "description" in fl or "desc" in fl:
                col_map["name"] = f
            elif "quantity" in fl or "qty" in fl:
                col_map["quantity"] = f
            elif "manufacturer" in fl or "mfr" in fl:
                col_map["manufacturer"] = f
            elif "part" in fl and "number" in fl:
                col_map["part_number"] = f
            elif "footprint" in fl or "package" in fl:
                col_map["footprint"] = f

    for row in reader:
        code = row.get(col_map.get("code", ""), "").strip()
        name = row.get(col_map.get("name", ""), "").strip()
        value = row.get(col_map.get("value", ""), "").strip()
        qty_str = row.get(col_map.get("quantity", ""), "1").strip()
        mfr = row.get(col_map.get("manufacturer", ""), "").strip()
        pn = row.get(col_map.get("part_number", ""), "").strip()
        fp = row.get(col_map.get("footprint", ""), "").strip()

        if not code and not name:
            continue

        try:
            qty = int(qty_str)
        except ValueError:
            qty = 1

        records.append({
            "code": code or f"CMP-{len(records)+1:03d}",
            "name": name or value or code,
            "level": "component",
            "quantity": qty,
            "manufacturer": mfr,
            "part_number": pn,
            "footprint": fp,
            "value": value,
            "source": "Altium BOM import",
        })

    return ImportResult(True, records, warnings, "Altium BOM", len(records))


# ── Valispace JSON Import ────────────────────────────────────────────

def import_valispace_json(file_bytes: bytes) -> ImportResult:
    """Import components/requirements from Valispace JSON export."""
    warnings = []
    records = []

    try:
        data = json.loads(file_bytes)
    except json.JSONDecodeError as e:
        return ImportResult(False, [], [f"JSON parse error: {e}"], "Valispace JSON")

    # Valispace exports components as list of dicts
    items = data if isinstance(data, list) else data.get("results", data.get("components", []))

    for item in items:
        if not isinstance(item, dict):
            continue

        records.append({
            "code": item.get("unique_name", item.get("name", "")),
            "name": item.get("name", item.get("description", "")),
            "level": "equipment",
            "parent_code": item.get("parent", ""),
            "mass": item.get("mass", None),
            "power": item.get("power", None),
            "quantity": item.get("quantity", 1),
            "source": "Valispace import",
        })

    return ImportResult(True, records, warnings, "Valispace JSON", len(records))


# ── Auto-detect format ───────────────────────────────────────────────

def detect_and_import(file_bytes: bytes, filename: str) -> ImportResult:
    """Auto-detect file format and import."""
    fn = filename.lower()

    if fn.endswith(".xml"):
        # Try MS Project first
        if b"schemas.microsoft.com/project" in file_bytes or b"<Project" in file_bytes:
            return import_msproject_xml(file_bytes)
        elif b"ReqIF" in file_bytes or b"reqif" in file_bytes:
            return import_reqif(file_bytes)
        else:
            # Try both
            result = import_msproject_xml(file_bytes)
            if result.record_count > 0:
                return result
            return import_reqif(file_bytes)

    elif fn.endswith(".json"):
        return import_valispace_json(file_bytes)

    elif fn.endswith(".csv") or fn.endswith(".tsv"):
        text = file_bytes.decode("utf-8", errors="replace").lower()
        if "designator" in text or "footprint" in text:
            return import_altium_bom(file_bytes)
        elif "identifier" in text or "object heading" in text:
            return import_doors_csv(file_bytes)
        else:
            return import_doors_csv(file_bytes)  # Generic CSV fallback

    return ImportResult(False, [], [f"Unsupported file format: {filename}"], "unknown")
