"""Importers for DAS, DRAMA and MASTER output files."""
from __future__ import annotations

import csv
import io
import re
import xml.etree.ElementTree as ET

from bepi.integrations.importers import ImportResult


# ── DAS XML Output ──────────────────────────────────────────────────────

def import_das_xml(file_bytes: bytes) -> ImportResult:
    warnings: list[str] = []
    records: list[dict] = []

    try:
        root = ET.fromstring(file_bytes)
    except ET.ParseError as e:
        return ImportResult(False, [], [f"XML parse error: {e}"], "DAS XML")

    for check in root.iter():
        tag = check.tag.lower()
        if "compliance" in tag or "result" in tag or "assessment" in tag:
            rec: dict = {"tag": check.tag}
            rec.update(check.attrib)
            if check.text and check.text.strip():
                rec["value"] = check.text.strip()
            for child in check:
                ctag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if child.text and child.text.strip():
                    rec[ctag] = child.text.strip()
            if len(rec) > 1:
                records.append(rec)

    compliance_nodes = root.findall(".//ComplianceResult") or root.findall(".//compliance")
    for node in compliance_nodes:
        rec = {}
        for child in node:
            ctag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            rec[ctag] = child.text.strip() if child.text else ""
        if rec:
            records.append(rec)

    if not records:
        for elem in root.iter():
            if elem.text and elem.text.strip():
                records.append({
                    "tag": elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag,
                    "value": elem.text.strip(),
                    **elem.attrib,
                })

    return ImportResult(True, records, warnings, "DAS XML", len(records))


# ── DRAMA CSV/TXT Output ───────────────────────────────────────────────

def import_drama_output(file_bytes: bytes, encoding: str = "utf-8") -> ImportResult:
    warnings: list[str] = []
    records: list[dict] = []
    text = file_bytes.decode(encoding, errors="replace")
    lines = text.strip().splitlines()

    header_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("%"):
            continue
        parts = re.split(r"[,\t;]+", stripped)
        if len(parts) >= 2 and not _is_numeric(parts[0]):
            header_idx = i
            break

    if header_idx is not None:
        header_line = lines[header_idx]
        sep = _detect_separator(header_line)
        headers = [h.strip() for h in header_line.split(sep)]
        for line in lines[header_idx + 1:]:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("%"):
                continue
            vals = [v.strip() for v in stripped.split(sep)]
            rec = {}
            for j, h in enumerate(headers):
                val = vals[j] if j < len(vals) else ""
                rec[h] = _try_float(val)
            records.append(rec)
    else:
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("%"):
                continue
            if ":" in stripped:
                key, _, val = stripped.partition(":")
                records.append({"parameter": key.strip(), "value": _try_float(val.strip())})
            elif "=" in stripped:
                key, _, val = stripped.partition("=")
                records.append({"parameter": key.strip(), "value": _try_float(val.strip())})

    return ImportResult(True, records, warnings, "DRAMA output", len(records))


# ── MASTER .dat Output ──────────────────────────────────────────────────

def import_master_dat(file_bytes: bytes, encoding: str = "utf-8") -> ImportResult:
    warnings: list[str] = []
    records: list[dict] = []
    text = file_bytes.decode(encoding, errors="replace")
    lines = text.strip().splitlines()

    headers: list[str] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if not _is_numeric(parts[0]) and len(parts) >= 2:
            headers = parts
            continue
        if _is_numeric(parts[0]):
            if headers and len(parts) <= len(headers):
                rec = {}
                for j, h in enumerate(headers):
                    rec[h] = _try_float(parts[j]) if j < len(parts) else None
                records.append(rec)
            else:
                records.append({
                    f"col_{j}": _try_float(v) for j, v in enumerate(parts)
                })

    return ImportResult(True, records, warnings, "MASTER dat", len(records))


# ── Comparison ──────────────────────────────────────────────────────────

def compare_with_bepi(imported_data: dict, bepi_data: dict) -> dict:
    all_keys = sorted(set(imported_data.keys()) | set(bepi_data.keys()))
    rows = []
    for key in all_keys:
        iv = imported_data.get(key)
        bv = bepi_data.get(key)
        delta = None
        delta_pct = None
        if isinstance(iv, (int, float)) and isinstance(bv, (int, float)):
            delta = bv - iv
            if iv != 0:
                delta_pct = round(abs(delta) / abs(iv) * 100, 2)
        rows.append({
            "field": key,
            "imported": iv,
            "bepi": bv,
            "delta": delta,
            "delta_pct": delta_pct,
            "match": delta_pct is not None and delta_pct < 10.0 if delta_pct is not None else iv == bv,
        })

    return {
        "comparisons": rows,
        "fields_matched": sum(1 for r in rows if r["match"]),
        "fields_total": len(rows),
    }


# ── Helpers ─────────────────────────────────────────────────────────────

def _is_numeric(s: str) -> bool:
    try:
        float(s.replace(",", "."))
        return True
    except (ValueError, AttributeError):
        return False


def _try_float(val: str):
    try:
        return float(val.replace(",", "."))
    except (ValueError, AttributeError):
        return val


def _detect_separator(line: str) -> str:
    for sep in ["\t", ";", ","]:
        if sep in line:
            return sep
    return ","
