import type { Mission, ProductTreeNode, Requirement, Risk, ScheduleTask, BudgetSummary } from "./types";

export const DEMO_MISSION: Mission = {
  id: "demo-001",
  name: "BEPI-SAT",
  description: "LEO Earth Observation SmallSat",
  orbit: "SSO 550 km, 97.6 deg",
  target_launch: "2027-06",
  lifetime_years: 5,
  phase: "B2",
  framework: "ESA",
  mass_limit_kg: 350,
  power_limit_w: 500,
  propellant_mass_kg: 25,
  created_at: "2025-01-01",
};

export const DEMO_PRODUCT_TREE: ProductTreeNode[] = [
  { id: "sc", mission_id: "demo-001", parent_id: null, name: "BEPI-SAT S/C", node_type: "spacecraft", mass_kg: 0, power_w: 0, qty: 1, maturity_margin: 0, trl: 0, mait_status: null, created_at: "2025-01-01" },
  { id: "plt", mission_id: "demo-001", parent_id: "sc", name: "Platform", node_type: "subsystem", mass_kg: 0, power_w: 0, qty: 1, maturity_margin: 0, trl: 0, mait_status: null, created_at: "2025-01-01" },
  { id: "pld", mission_id: "demo-001", parent_id: "sc", name: "Payload", node_type: "subsystem", mass_kg: 0, power_w: 0, qty: 1, maturity_margin: 0, trl: 0, mait_status: null, created_at: "2025-01-01" },
  { id: "adcs", mission_id: "demo-001", parent_id: "plt", name: "ADCS", node_type: "equipment", mass_kg: 12.5, power_w: 45, qty: 1, maturity_margin: 10, trl: 7, mait_status: "EM", created_at: "2025-01-01" },
  { id: "eps", mission_id: "demo-001", parent_id: "plt", name: "EPS", node_type: "equipment", mass_kg: 18.0, power_w: 15, qty: 1, maturity_margin: 5, trl: 8, mait_status: "QM", created_at: "2025-01-01" },
  { id: "obc", mission_id: "demo-001", parent_id: "plt", name: "OBC", node_type: "equipment", mass_kg: 3.2, power_w: 25, qty: 1, maturity_margin: 5, trl: 8, mait_status: "QM", created_at: "2025-01-01" },
  { id: "com", mission_id: "demo-001", parent_id: "plt", name: "COM", node_type: "equipment", mass_kg: 8.5, power_w: 65, qty: 1, maturity_margin: 10, trl: 7, mait_status: "EM", created_at: "2025-01-01" },
  { id: "tcs", mission_id: "demo-001", parent_id: "plt", name: "TCS", node_type: "equipment", mass_kg: 6.8, power_w: 30, qty: 1, maturity_margin: 15, trl: 6, mait_status: "EM", created_at: "2025-01-01" },
  { id: "str", mission_id: "demo-001", parent_id: "plt", name: "Structure", node_type: "equipment", mass_kg: 45.0, power_w: 0, qty: 1, maturity_margin: 5, trl: 8, mait_status: "QM", created_at: "2025-01-01" },
  { id: "prop", mission_id: "demo-001", parent_id: "plt", name: "Propulsion", node_type: "equipment", mass_kg: 15.3, power_w: 35, qty: 1, maturity_margin: 10, trl: 6, mait_status: "BB", created_at: "2025-01-01" },
  { id: "cam", mission_id: "demo-001", parent_id: "pld", name: "Camera (EO)", node_type: "equipment", mass_kg: 22.0, power_w: 80, qty: 1, maturity_margin: 20, trl: 5, mait_status: "BB", created_at: "2025-01-01" },
  { id: "str_trk", mission_id: "demo-001", parent_id: "pld", name: "Star Tracker", node_type: "equipment", mass_kg: 2.5, power_w: 12, qty: 2, maturity_margin: 5, trl: 9, mait_status: "FM", created_at: "2025-01-01" },
];

export function computeBudgetSummary(
  tree: ProductTreeNode[],
  massLimit = 350,
  powerLimit = 500,
  propellant = 25,
): BudgetSummary {
  const equipment = tree.filter(n => n.node_type === "equipment");
  let totalMass = 0;
  let totalPower = 0;
  for (const eq of equipment) {
    const m = eq.mass_kg * eq.qty * (1 + eq.maturity_margin / 100);
    totalMass += m;
    totalPower += eq.power_w * eq.qty;
  }
  return {
    total_dry_mass_kg: Math.round(totalMass * 10) / 10,
    total_wet_mass_kg: Math.round((totalMass + propellant) * 10) / 10,
    total_power_w: Math.round(totalPower * 10) / 10,
    mass_margin_kg: Math.round((massLimit - totalMass - propellant) * 10) / 10,
    power_margin_w: Math.round((powerLimit - totalPower) * 10) / 10,
    mass_limit_kg: massLimit,
    power_limit_w: powerLimit,
  };
}

export const DEMO_REQUIREMENTS: Requirement[] = [
  { id: "r1", mission_id: "demo-001", req_id: "MIS-001", title: "Mission Lifetime", description: "The satellite shall operate for a minimum of 5 years in orbit.", req_type: "performance", priority: "shall", status: "active", verification_method: "analysis", allocated_to: "sc", parent_req_id: null, created_at: "2025-01-01" },
  { id: "r2", mission_id: "demo-001", req_id: "MIS-002", title: "Orbit Maintenance", description: "The satellite shall maintain SSO orbit within +/- 5 km altitude.", req_type: "performance", priority: "shall", status: "active", verification_method: "analysis", allocated_to: "prop", parent_req_id: null, created_at: "2025-01-01" },
  { id: "r3", mission_id: "demo-001", req_id: "FUN-001", title: "EO Image Resolution", description: "The camera shall provide ground resolution better than 5 m GSD.", req_type: "functional", priority: "shall", status: "active", verification_method: "test", allocated_to: "cam", parent_req_id: null, created_at: "2025-01-01" },
  { id: "r4", mission_id: "demo-001", req_id: "FUN-002", title: "Data Downlink", description: "The COM subsystem shall support X-band downlink at 100 Mbps minimum.", req_type: "functional", priority: "shall", status: "verified", verification_method: "test", allocated_to: "com", parent_req_id: null, created_at: "2025-01-01" },
  { id: "r5", mission_id: "demo-001", req_id: "FUN-003", title: "Attitude Determination", description: "ADCS shall provide pointing accuracy better than 0.1 deg (3-sigma).", req_type: "functional", priority: "shall", status: "active", verification_method: "test", allocated_to: "adcs", parent_req_id: null, created_at: "2025-01-01" },
  { id: "r6", mission_id: "demo-001", req_id: "ENV-001", title: "Radiation Tolerance", description: "All electronics shall withstand 30 krad TID over mission lifetime.", req_type: "environmental", priority: "shall", status: "active", verification_method: "test", allocated_to: "sc", parent_req_id: null, created_at: "2025-01-01" },
  { id: "r7", mission_id: "demo-001", req_id: "ENV-002", title: "Thermal Range", description: "All units shall operate in the range -20C to +60C.", req_type: "environmental", priority: "shall", status: "active", verification_method: "test", allocated_to: "tcs", parent_req_id: null, created_at: "2025-01-01" },
  { id: "r8", mission_id: "demo-001", req_id: "IFN-001", title: "Launcher Interface", description: "The satellite shall be compatible with Vega-C rideshare adapter.", req_type: "interface", priority: "shall", status: "verified", verification_method: "inspection", allocated_to: "str", parent_req_id: null, created_at: "2025-01-01" },
  { id: "r9", mission_id: "demo-001", req_id: "IFN-002", title: "Ground Station IF", description: "TT&C shall be compatible with ESA ESTRACK ground stations.", req_type: "interface", priority: "shall", status: "active", verification_method: "demonstration", allocated_to: "com", parent_req_id: null, created_at: "2025-01-01" },
  { id: "r10", mission_id: "demo-001", req_id: "PER-001", title: "Power Generation", description: "EPS shall generate at least 500 W EOL in sunlight.", req_type: "performance", priority: "shall", status: "active", verification_method: "analysis", allocated_to: "eps", parent_req_id: null, created_at: "2025-01-01" },
  { id: "r11", mission_id: "demo-001", req_id: "PER-002", title: "Mass Budget", description: "Total wet mass shall not exceed 350 kg.", req_type: "performance", priority: "shall", status: "active", verification_method: "inspection", allocated_to: "sc", parent_req_id: null, created_at: "2025-01-01" },
  { id: "r12", mission_id: "demo-001", req_id: "OPS-001", title: "Autonomous Operation", description: "The satellite shall support autonomous operation for 72 hours.", req_type: "operational", priority: "should", status: "draft", verification_method: "demonstration", allocated_to: "obc", parent_req_id: null, created_at: "2025-01-01" },
  { id: "r13", mission_id: "demo-001", req_id: "DES-001", title: "Deorbit Compliance", description: "The satellite shall comply with 25-year deorbit guideline.", req_type: "design", priority: "shall", status: "active", verification_method: "analysis", allocated_to: "prop", parent_req_id: null, created_at: "2025-01-01" },
  { id: "r14", mission_id: "demo-001", req_id: "FUN-004", title: "Onboard Storage", description: "OBC shall provide at least 256 GB onboard data storage.", req_type: "functional", priority: "shall", status: "verified", verification_method: "inspection", allocated_to: "obc", parent_req_id: null, created_at: "2025-01-01" },
  { id: "r15", mission_id: "demo-001", req_id: "PER-003", title: "Battery Capacity", description: "Battery shall sustain eclipse operations for 35 minutes.", req_type: "performance", priority: "shall", status: "active", verification_method: "test", allocated_to: "eps", parent_req_id: null, created_at: "2025-01-01" },
];

export const DEMO_RISKS: Risk[] = [
  { id: "rk1", mission_id: "demo-001", risk_id: "RSK-001", title: "Camera delivery delay", description: "EO camera supplier may deliver 3 months late due to supply chain issues.", category: "schedule", likelihood: 4, consequence: 4, status: "open", mitigation: "Identify backup supplier; negotiate penalty clause.", owner: "PM", created_at: "2025-01-01" },
  { id: "rk2", mission_id: "demo-001", risk_id: "RSK-002", title: "Radiation-induced SEU", description: "Single Event Upsets in OBC may cause data corruption in SAA region.", category: "technical", likelihood: 3, consequence: 3, status: "mitigated", mitigation: "Implement TMR on critical registers; EDAC on memory.", owner: "SE", created_at: "2025-01-01" },
  { id: "rk3", mission_id: "demo-001", risk_id: "RSK-003", title: "Propulsion qualification failure", description: "AF-M315E green propellant thruster may fail qualification tests.", category: "technical", likelihood: 2, consequence: 5, status: "open", mitigation: "Maintain hydrazine fallback option until QR.", owner: "SSL", created_at: "2025-01-01" },
  { id: "rk4", mission_id: "demo-001", risk_id: "RSK-004", title: "Launch cost overrun", description: "Vega-C rideshare price increase due to market conditions.", category: "cost", likelihood: 3, consequence: 2, status: "accepted", mitigation: "Budget 15% contingency; explore Falcon 9 rideshare.", owner: "PM", created_at: "2025-01-01" },
];

export const DEMO_TASKS: ScheduleTask[] = [
  { id: "t1", mission_id: "demo-001", name: "SRR", start_date: "2025-03-01", end_date: "2025-03-15", progress: 100, responsible: "SE", predecessors: [], milestone: true, created_at: "2025-01-01" },
  { id: "t2", mission_id: "demo-001", name: "Phase A Study", start_date: "2025-03-16", end_date: "2025-06-30", progress: 100, responsible: "SE", predecessors: ["t1"], milestone: false, created_at: "2025-01-01" },
  { id: "t3", mission_id: "demo-001", name: "MDR", start_date: "2025-07-01", end_date: "2025-07-15", progress: 100, responsible: "SE", predecessors: ["t2"], milestone: true, created_at: "2025-01-01" },
  { id: "t4", mission_id: "demo-001", name: "Phase B1 Design", start_date: "2025-07-16", end_date: "2025-12-31", progress: 100, responsible: "SE", predecessors: ["t3"], milestone: false, created_at: "2025-01-01" },
  { id: "t5", mission_id: "demo-001", name: "PRR", start_date: "2026-01-05", end_date: "2026-01-20", progress: 100, responsible: "PM", predecessors: ["t4"], milestone: true, created_at: "2025-01-01" },
  { id: "t6", mission_id: "demo-001", name: "Phase B2 Detailed Design", start_date: "2026-01-21", end_date: "2026-07-31", progress: 65, responsible: "SE", predecessors: ["t5"], milestone: false, created_at: "2025-01-01" },
  { id: "t7", mission_id: "demo-001", name: "PDR", start_date: "2026-08-01", end_date: "2026-08-20", progress: 0, responsible: "SE", predecessors: ["t6"], milestone: true, created_at: "2025-01-01" },
  { id: "t8", mission_id: "demo-001", name: "Phase C/D Manufacturing", start_date: "2026-08-21", end_date: "2027-02-28", progress: 0, responsible: "AIT", predecessors: ["t7"], milestone: false, created_at: "2025-01-01" },
  { id: "t9", mission_id: "demo-001", name: "CDR", start_date: "2027-01-10", end_date: "2027-01-25", progress: 0, responsible: "SE", predecessors: ["t6"], milestone: true, created_at: "2025-01-01" },
  { id: "t10", mission_id: "demo-001", name: "Launch Campaign", start_date: "2027-03-01", end_date: "2027-06-01", progress: 0, responsible: "PM", predecessors: ["t8", "t9"], milestone: false, created_at: "2025-01-01" },
];
