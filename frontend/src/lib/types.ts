export interface Mission {
  id: string;
  name: string;
  description: string;
  orbit: string;
  target_launch: string;
  lifetime_years: number;
  phase: string;
  framework: "ESA" | "NASA";
  mass_limit_kg: number;
  power_limit_w: number;
  propellant_mass_kg: number;
  created_at: string;
}

export interface ProductTreeNode {
  id: string;
  mission_id: string;
  parent_id: string | null;
  name: string;
  node_type: "spacecraft" | "subsystem" | "equipment" | "component";
  mass_kg: number;
  power_w: number;
  qty: number;
  maturity_margin: number;
  trl: number;
  mait_status: "BB" | "EM" | "QM" | "FM" | null;
  created_at: string;
}

export interface Requirement {
  id: string;
  mission_id: string;
  req_id: string;
  title: string;
  description: string;
  req_type: "functional" | "performance" | "interface" | "environmental" | "operational" | "design";
  priority: "shall" | "should" | "may";
  status: "draft" | "active" | "verified" | "deleted";
  verification_method: "test" | "analysis" | "inspection" | "demonstration" | "review";
  allocated_to: string | null;
  parent_req_id: string | null;
  created_at: string;
}

export interface Risk {
  id: string;
  mission_id: string;
  risk_id: string;
  title: string;
  description: string;
  category: string;
  likelihood: number;
  consequence: number;
  status: "open" | "mitigated" | "closed" | "accepted";
  mitigation: string;
  owner: string;
  created_at: string;
}

export interface ScheduleTask {
  id: string;
  mission_id: string;
  name: string;
  start_date: string;
  end_date: string;
  progress: number;
  responsible: string;
  predecessors: string[];
  milestone: boolean;
  created_at: string;
}

export interface Review {
  id: string;
  mission_id: string;
  name: string;
  review_type: string;
  phase: string;
  planned_date: string;
  status: "planned" | "in_progress" | "completed";
  created_at: string;
}

export interface BudgetSummary {
  total_dry_mass_kg: number;
  total_wet_mass_kg: number;
  total_power_w: number;
  mass_margin_kg: number;
  power_margin_w: number;
  mass_limit_kg: number;
  power_limit_w: number;
}
