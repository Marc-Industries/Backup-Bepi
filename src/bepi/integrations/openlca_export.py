"""OpenLCA JSON-LD export — generates .zip archives importable by OpenLCA 2.

Converts BEPI product tree + mass budget into an LCA process with material
exchanges, grouped by subsystem. Includes launch segment as separate process.
"""
from __future__ import annotations

import json
import uuid
import io
import zipfile
from dataclasses import dataclass, field

# Stable UUIDs from ecoinvent / openLCA reference data
_MASS_PROPERTY_ID = "93a60a56-a3c8-11da-a746-0800200b9a66"
_MASS_UNIT_ID = "20aadc24-a391-41cf-b340-3e4529f44bde"
_MASS_UNIT_GROUP_ID = "93a60a56-a3c8-11da-a746-0800200c9a66"
_ENERGY_PROPERTY_ID = "f6811440-ee37-11de-8a39-0800200c9a66"
_ENERGY_UNIT_ID = "52765a6c-3896-43c2-b2f4-c679f94ef07c"


SATELLITE_MATERIALS: dict[str, dict] = {
    "Aluminium alloy (6061-T6)": {"category": "Metals", "density_kg_m3": 2700},
    "Aluminium honeycomb panel": {"category": "Metals", "density_kg_m3": 80},
    "CFRP (carbon fibre reinforced polymer)": {"category": "Composites", "density_kg_m3": 1600},
    "Titanium alloy (Ti-6Al-4V)": {"category": "Metals", "density_kg_m3": 4430},
    "Stainless steel (316L)": {"category": "Metals", "density_kg_m3": 8000},
    "Invar 36": {"category": "Metals", "density_kg_m3": 8050},
    "Copper (harness/wiring)": {"category": "Metals", "density_kg_m3": 8960},
    "GaAs triple-junction solar cell": {"category": "Electronics", "density_kg_m3": 5320},
    "Silicon solar cell": {"category": "Electronics", "density_kg_m3": 2330},
    "Li-ion battery cells": {"category": "Electronics", "density_kg_m3": 2500},
    "PCB (FR4 + components)": {"category": "Electronics", "density_kg_m3": 1850},
    "Electronic components (generic)": {"category": "Electronics", "density_kg_m3": 2000},
    "Kapton (MLI / thermal blankets)": {"category": "Polymers", "density_kg_m3": 1420},
    "Mylar (MLI layers)": {"category": "Polymers", "density_kg_m3": 1390},
    "PTFE / Teflon": {"category": "Polymers", "density_kg_m3": 2200},
    "Optical solar reflector (OSR)": {"category": "Thermal", "density_kg_m3": 2500},
    "Heat pipe (Al/NH3)": {"category": "Thermal", "density_kg_m3": 2700},
    "Hydrazine (N2H4)": {"category": "Propellant", "density_kg_m3": 1004},
    "AF-M315E (green propellant)": {"category": "Propellant", "density_kg_m3": 1466},
    "Xenon (electric propulsion)": {"category": "Propellant", "density_kg_m3": 1100},
    "MON-3 / MMH (bipropellant)": {"category": "Propellant", "density_kg_m3": 1200},
}

SUBSYSTEM_MATERIAL_DEFAULTS: dict[str, str] = {
    "STR": "Aluminium alloy (6061-T6)",
    "EPS": "Li-ion battery cells",
    "AOCS": "Electronic components (generic)",
    "COM": "Electronic components (generic)",
    "CDH": "PCB (FR4 + components)",
    "TCS": "Kapton (MLI / thermal blankets)",
    "PROP": "Titanium alloy (Ti-6Al-4V)",
    "PL": "Electronic components (generic)",
    "HRN": "Copper (harness/wiring)",
    "SA": "GaAs triple-junction solar cell",
}

IMPACT_CATEGORIES = [
    {"name": "Climate change (GWP100)", "unit": "kg CO2-eq", "method": "ReCiPe 2016 Midpoint (H)"},
    {"name": "Ozone depletion (ODP)", "unit": "kg CFC-11-eq", "method": "ReCiPe 2016 Midpoint (H)"},
    {"name": "Mineral resource depletion", "unit": "kg Sb-eq", "method": "ReCiPe 2016 Midpoint (H)"},
    {"name": "Fossil resource depletion", "unit": "MJ", "method": "ReCiPe 2016 Midpoint (H)"},
    {"name": "Human toxicity (non-cancer)", "unit": "CTUh", "method": "USEtox 2"},
    {"name": "Freshwater ecotoxicity", "unit": "CTUe", "method": "USEtox 2"},
    {"name": "Cumulative Energy Demand", "unit": "MJ", "method": "CED"},
]

LAUNCH_VEHICLES_LCA: dict[str, dict] = {
    "Falcon 9": {"propellant_kg": 395700, "fuel_type": "RP-1/LOX", "co2_kg_per_launch": 336000, "gwp_factor": 1.0},
    "Vega-C": {"propellant_kg": 137000, "fuel_type": "Solid/UDMH", "co2_kg_per_launch": 230000, "gwp_factor": 1.2},
    "Ariane 6": {"propellant_kg": 540000, "fuel_type": "LH2/LOX+Solid", "co2_kg_per_launch": 400000, "gwp_factor": 1.0},
    "PSLV": {"propellant_kg": 228000, "fuel_type": "Solid/UDMH", "co2_kg_per_launch": 190000, "gwp_factor": 1.3},
    "Electron": {"propellant_kg": 9250, "fuel_type": "RP-1/LOX", "co2_kg_per_launch": 7800, "gwp_factor": 1.0},
    "Soyuz-2": {"propellant_kg": 297000, "fuel_type": "RP-1/LOX", "co2_kg_per_launch": 252000, "gwp_factor": 1.0},
}


@dataclass
class LCAItem:
    name: str
    subsystem: str
    material: str
    mass_kg: float
    quantity: int = 1


@dataclass
class LCAModel:
    mission_name: str = "BEPI Mission"
    items: list[LCAItem] = field(default_factory=list)
    launch_vehicle: str = "Falcon 9"
    manufacturing_energy_mj_per_kg: float = 500.0
    ait_energy_mj: float = 50000.0
    propellant_type: str = "Hydrazine (N2H4)"
    propellant_mass_kg: float = 25.0


def _uuid(seed: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"bepi.lca.{seed}"))


def _flow_json(flow_id: str, name: str, category: str, flow_type: str = "PRODUCT_FLOW") -> dict:
    return {
        "@type": "Flow",
        "@id": flow_id,
        "name": name,
        "category": category,
        "flowType": flow_type,
        "flowProperties": [{
            "flowProperty": {"@type": "FlowProperty", "@id": _MASS_PROPERTY_ID, "name": "Mass"},
            "conversionFactor": 1.0,
            "isRefFlowProperty": True,
        }],
    }


def _exchange(internal_id: int, flow_id: str, flow_name: str, amount: float,
              is_input: bool = True, is_ref: bool = False) -> dict:
    return {
        "@type": "Exchange",
        "internalId": internal_id,
        "isInput": is_input,
        "isQuantitativeReference": is_ref,
        "amount": amount,
        "flow": {"@type": "Flow", "@id": flow_id, "name": flow_name, "flowType": "PRODUCT_FLOW"},
        "flowProperty": {"@type": "FlowProperty", "@id": _MASS_PROPERTY_ID, "name": "Mass"},
        "unit": {"@type": "Unit", "@id": _MASS_UNIT_ID, "name": "kg"},
    }


def generate_lca_summary(model: LCAModel) -> dict:
    by_material: dict[str, float] = {}
    by_subsystem: dict[str, float] = {}
    for item in model.items:
        mat = item.material or SUBSYSTEM_MATERIAL_DEFAULTS.get(item.subsystem, "Electronic components (generic)")
        by_material[mat] = by_material.get(mat, 0) + item.mass_kg * item.quantity
        by_subsystem[item.subsystem] = by_subsystem.get(item.subsystem, 0) + item.mass_kg * item.quantity

    total_dry = sum(by_material.values())
    total_wet = total_dry + model.propellant_mass_kg
    mfg_energy = total_dry * model.manufacturing_energy_mj_per_kg + model.ait_energy_mj

    lv = LAUNCH_VEHICLES_LCA.get(model.launch_vehicle, LAUNCH_VEHICLES_LCA["Falcon 9"])
    launch_co2 = lv["co2_kg_per_launch"] * lv["gwp_factor"]

    mfg_co2 = mfg_energy * 0.06  # ~60 g CO2/MJ average grid

    return {
        "mission_name": model.mission_name,
        "total_dry_mass_kg": total_dry,
        "total_wet_mass_kg": total_wet,
        "propellant_mass_kg": model.propellant_mass_kg,
        "propellant_type": model.propellant_type,
        "by_material": by_material,
        "by_subsystem": by_subsystem,
        "manufacturing_energy_mj": mfg_energy,
        "ait_energy_mj": model.ait_energy_mj,
        "launch_vehicle": model.launch_vehicle,
        "launch_co2_kg": launch_co2,
        "manufacturing_co2_kg": mfg_co2,
        "total_co2_kg": launch_co2 + mfg_co2,
        "launch_share_pct": launch_co2 / (launch_co2 + mfg_co2) * 100 if (launch_co2 + mfg_co2) > 0 else 0,
    }


def export_openlca_jsonld(model: LCAModel) -> bytes:
    buf = io.BytesIO()
    flows = {}
    process_id = _uuid(f"process.{model.mission_name}")
    launch_process_id = _uuid(f"process.launch.{model.mission_name}")

    # Reference product flow
    sat_flow_id = _uuid(f"flow.satellite.{model.mission_name}")
    flows[sat_flow_id] = _flow_json(sat_flow_id, f"{model.mission_name} — Satellite", "Space / Satellite")

    exchanges = []
    idx = 1

    # Output: the satellite
    exchanges.append(_exchange(idx, sat_flow_id, f"{model.mission_name} — Satellite", 1.0,
                               is_input=False, is_ref=True))
    idx += 1

    # Material inputs
    by_material: dict[str, float] = {}
    for item in model.items:
        mat = item.material or SUBSYSTEM_MATERIAL_DEFAULTS.get(item.subsystem, "Electronic components (generic)")
        by_material[mat] = by_material.get(mat, 0) + item.mass_kg * item.quantity

    for mat_name, mass in sorted(by_material.items()):
        mat_info = SATELLITE_MATERIALS.get(mat_name, {})
        flow_id = _uuid(f"flow.material.{mat_name}")
        cat = mat_info.get("category", "Materials")
        flows[flow_id] = _flow_json(flow_id, mat_name, f"Space / Materials / {cat}")
        exchanges.append(_exchange(idx, flow_id, mat_name, round(mass, 3)))
        idx += 1

    # Propellant
    if model.propellant_mass_kg > 0:
        prop_flow_id = _uuid(f"flow.propellant.{model.propellant_type}")
        flows[prop_flow_id] = _flow_json(prop_flow_id, model.propellant_type, "Space / Materials / Propellant")
        exchanges.append(_exchange(idx, prop_flow_id, model.propellant_type, model.propellant_mass_kg))
        idx += 1

    # Manufacturing energy
    total_dry = sum(by_material.values())
    mfg_energy = total_dry * model.manufacturing_energy_mj_per_kg + model.ait_energy_mj
    energy_flow_id = _uuid("flow.energy.manufacturing")
    flows[energy_flow_id] = {
        "@type": "Flow", "@id": energy_flow_id,
        "name": "Electricity, manufacturing + AIT",
        "category": "Space / Energy",
        "flowType": "PRODUCT_FLOW",
        "flowProperties": [{
            "flowProperty": {"@type": "FlowProperty", "@id": _ENERGY_PROPERTY_ID, "name": "Energy"},
            "conversionFactor": 1.0, "isRefFlowProperty": True,
        }],
    }
    energy_ex = {
        "@type": "Exchange", "internalId": idx, "isInput": True,
        "isQuantitativeReference": False, "amount": round(mfg_energy, 1),
        "flow": {"@type": "Flow", "@id": energy_flow_id, "name": "Electricity, manufacturing + AIT",
                 "flowType": "PRODUCT_FLOW"},
        "flowProperty": {"@type": "FlowProperty", "@id": _ENERGY_PROPERTY_ID, "name": "Energy"},
        "unit": {"@type": "Unit", "@id": _ENERGY_UNIT_ID, "name": "MJ"},
    }
    exchanges.append(energy_ex)
    idx += 1

    # Manufacturing process
    mfg_process = {
        "@type": "Process", "@id": process_id,
        "name": f"{model.mission_name} — Satellite Manufacturing",
        "processType": "UNIT_PROCESS",
        "category": "Space / Satellite / Manufacturing",
        "lastInternalId": idx - 1,
        "exchanges": exchanges,
    }

    # Launch process
    lv = LAUNCH_VEHICLES_LCA.get(model.launch_vehicle, LAUNCH_VEHICLES_LCA["Falcon 9"])
    launch_flow_id = _uuid(f"flow.launch.{model.launch_vehicle}")
    flows[launch_flow_id] = _flow_json(launch_flow_id, f"Launch service — {model.launch_vehicle}",
                                        "Space / Launch")

    co2_flow_id = _uuid("flow.emission.co2")
    flows[co2_flow_id] = {
        "@type": "Flow", "@id": co2_flow_id,
        "name": "Carbon dioxide, to air", "category": "Elementary flows / Emissions to air",
        "flowType": "ELEMENTARY_FLOW",
        "flowProperties": [{
            "flowProperty": {"@type": "FlowProperty", "@id": _MASS_PROPERTY_ID, "name": "Mass"},
            "conversionFactor": 1.0, "isRefFlowProperty": True,
        }],
    }

    launch_process = {
        "@type": "Process", "@id": launch_process_id,
        "name": f"{model.mission_name} — Launch ({model.launch_vehicle})",
        "processType": "UNIT_PROCESS",
        "category": "Space / Launch",
        "lastInternalId": 3,
        "exchanges": [
            _exchange(1, launch_flow_id, f"Launch service — {model.launch_vehicle}", 1.0,
                      is_input=False, is_ref=True),
            _exchange(2, sat_flow_id, f"{model.mission_name} — Satellite",
                      total_dry + model.propellant_mass_kg, is_input=True),
            {
                "@type": "Exchange", "internalId": 3, "isInput": False,
                "isQuantitativeReference": False,
                "amount": round(lv["co2_kg_per_launch"] * lv["gwp_factor"], 0),
                "flow": {"@type": "Flow", "@id": co2_flow_id, "name": "Carbon dioxide, to air",
                         "flowType": "ELEMENTARY_FLOW"},
                "flowProperty": {"@type": "FlowProperty", "@id": _MASS_PROPERTY_ID, "name": "Mass"},
                "unit": {"@type": "Unit", "@id": _MASS_UNIT_ID, "name": "kg"},
            },
        ],
    }

    # Build zip
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("olca-schema.json", json.dumps({"version": "2.0"}, indent=2))
        for fid, fdata in flows.items():
            zf.writestr(f"flows/{fid}.json", json.dumps(fdata, indent=2))
        zf.writestr(f"processes/{process_id}.json", json.dumps(mfg_process, indent=2))
        zf.writestr(f"processes/{launch_process_id}.json", json.dumps(launch_process, indent=2))

        # Flow properties and unit groups (required for standalone import)
        zf.writestr(f"flow_properties/{_MASS_PROPERTY_ID}.json", json.dumps({
            "@type": "FlowProperty", "@id": _MASS_PROPERTY_ID, "name": "Mass",
            "unitGroup": {"@type": "UnitGroup", "@id": _MASS_UNIT_GROUP_ID, "name": "Units of mass"},
        }, indent=2))
        zf.writestr(f"flow_properties/{_ENERGY_PROPERTY_ID}.json", json.dumps({
            "@type": "FlowProperty", "@id": _ENERGY_PROPERTY_ID, "name": "Energy",
        }, indent=2))
        zf.writestr(f"unit_groups/{_MASS_UNIT_GROUP_ID}.json", json.dumps({
            "@type": "UnitGroup", "@id": _MASS_UNIT_GROUP_ID, "name": "Units of mass",
            "units": [{"@type": "Unit", "@id": _MASS_UNIT_ID, "name": "kg",
                        "conversionFactor": 1.0, "isRefUnit": True}],
        }, indent=2))

    return buf.getvalue()


def export_lca_csv(model: LCAModel) -> str:
    summary = generate_lca_summary(model)
    lines = ["Category,Item,Mass (kg),Material,Subsystem"]
    for item in model.items:
        mat = item.material or SUBSYSTEM_MATERIAL_DEFAULTS.get(item.subsystem, "unknown")
        lines.append(f"Satellite,{item.name},{item.mass_kg * item.quantity:.3f},{mat},{item.subsystem}")
    if model.propellant_mass_kg > 0:
        lines.append(f"Propellant,{model.propellant_type},{model.propellant_mass_kg:.3f},{model.propellant_type},PROP")
    lines.append(f"Energy,Manufacturing,{summary['manufacturing_energy_mj']:.1f},Electricity,MFG")
    lines.append(f"Energy,AIT,{model.ait_energy_mj:.1f},Electricity,AIT")
    lines.append(f"Launch,{model.launch_vehicle},{summary['launch_co2_kg']:.0f},CO2-eq,LAUNCH")
    return "\n".join(lines)
