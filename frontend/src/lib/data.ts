import { supabase, hasSupabase } from "./supabase";
import {
  DEMO_MISSION, DEMO_PRODUCT_TREE, DEMO_REQUIREMENTS, DEMO_RISKS, DEMO_TASKS,
  computeBudgetSummary
} from "./mock-data";
import type { Mission, ProductTreeNode, Requirement, Risk, ScheduleTask, BudgetSummary } from "./types";
import { resolveActiveMissionId } from "./active-mission";
export type { Mission };

// ---------------------------------------------------------------------------
// Generic fetch with mock fallback
// ---------------------------------------------------------------------------

async function fetchOrFallback<T>(
  table: string,
  fallback: T[],
  mapper?: (row: Record<string, unknown>) => T,
  missionId?: string | null,
): Promise<T[]> {
  if (!hasSupabase) return fallback;
  try {
    const activeMissionId = missionId ?? await resolveActiveMissionId();
    if (!activeMissionId) return fallback;
    const { data, error } = await supabase
      .from(table)
      .select("*")
      .eq("mission_id", activeMissionId);
    // If we have a real mission but the table is empty, return empty rather than demo data.
    if (error || !data) return [];
    if (data.length === 0) return [];
    return mapper ? data.map(mapper) : (data as T[]);
  } catch {
    return [];
  }
}

// ---------------------------------------------------------------------------
// Mission
// ---------------------------------------------------------------------------

export async function getMission(): Promise<Mission> {
  if (!hasSupabase) return DEMO_MISSION;
  try {
    const activeMissionId = await resolveActiveMissionId();
    if (!activeMissionId) return DEMO_MISSION;
    const { data, error } = await supabase
      .from("missions")
      .select("*")
      .eq("id", activeMissionId)
      .single();
    if (error || !data) return DEMO_MISSION;
    return {
      id: data.id,
      name: data.name,
      description: data.description ?? "",
      orbit: data.orbit_type ?? "",
      target_launch: data.target_launch_date ?? "",
      lifetime_years: data.lifetime_years ?? 5,
      phase: data.phase ?? "B1",
      framework: "ESA",
      mass_limit_kg: data.mass_limit_kg ?? 350,
      power_limit_w: data.power_limit_w ?? 500,
      propellant_mass_kg: data.propellant_mass_kg ?? 25,
      created_at: data.created_at,
    };
  } catch {
    return DEMO_MISSION;
  }
}

// ---------------------------------------------------------------------------
// Product Tree
// ---------------------------------------------------------------------------

export async function getProductTree(): Promise<ProductTreeNode[]> {
  const activeMissionId = await resolveActiveMissionId();
  return fetchOrFallback<ProductTreeNode>("product_tree_nodes", DEMO_PRODUCT_TREE, (r) => ({
    id: r.id as string,
    mission_id: r.mission_id as string,
    parent_id: (r.parent_id as string) ?? null,
    name: r.name as string,
    node_type: (r.level as string) === "satellite" ? "spacecraft" : (r.level as string) as ProductTreeNode["node_type"],
    mass_kg: 0,
    power_w: 0,
    qty: (r.quantity as number) ?? 1,
    maturity_margin: 0,
    trl: (r.trl as number) ?? 0,
    mait_status: null,
    created_at: r.created_at as string,
  }), activeMissionId);
}

// ---------------------------------------------------------------------------
// Budget Summary
// ---------------------------------------------------------------------------

export async function getBudgetSummary(mission?: Mission): Promise<BudgetSummary> {
  const tree = await getProductTree();
  const m = mission ?? await getMission();
  return computeBudgetSummary(tree, m.mass_limit_kg, m.power_limit_w, m.propellant_mass_kg);
}

// ---------------------------------------------------------------------------
// Requirements
// ---------------------------------------------------------------------------

export async function getRequirements(): Promise<Requirement[]> {
  const activeMissionId = await resolveActiveMissionId();
  return fetchOrFallback<Requirement>("requirements", DEMO_REQUIREMENTS, (r) => ({
    id: r.id as string,
    mission_id: r.mission_id as string,
    req_id: r.req_id as string,
    title: r.title as string,
    description: r.text as string,
    req_type: (r.category as string) as Requirement["req_type"],
    priority: (r.priority as string) === "mandatory" ? "shall" : (r.priority as string) === "desirable" ? "should" : "may",
    status: (r.status as string) === "approved" ? "active" : (r.status as string) as Requirement["status"],
    verification_method: (r.verification_method as string) as Requirement["verification_method"],
    allocated_to: null,
    parent_req_id: (r.parent_id as string) ?? null,
    created_at: r.created_at as string,
  }), activeMissionId);
}

// ---------------------------------------------------------------------------
// Risks
// ---------------------------------------------------------------------------

export async function getRisks(): Promise<Risk[]> {
  const activeMissionId = await resolveActiveMissionId();
  return fetchOrFallback<Risk>("risks", DEMO_RISKS, (r) => ({
    id: r.id as string,
    mission_id: r.mission_id as string,
    risk_id: r.risk_id as string,
    title: r.title as string,
    description: r.description as string,
    category: r.category as string,
    likelihood: r.likelihood as number,
    consequence: r.consequence as number,
    status: (r.status as string) === "mitigating" ? "mitigated" : (r.status as string) as Risk["status"],
    mitigation: (r.mitigation_strategy as string) ?? "",
    owner: (r.owner as string) ?? "",
    created_at: r.created_at as string,
  }), activeMissionId);
}

// ---------------------------------------------------------------------------
// Schedule Tasks
// ---------------------------------------------------------------------------

export async function getTasks(): Promise<ScheduleTask[]> {
  const activeMissionId = await resolveActiveMissionId();
  return fetchOrFallback<ScheduleTask>("schedule_tasks", DEMO_TASKS, (r) => ({
    id: r.id as string,
    mission_id: r.mission_id as string,
    name: r.name as string,
    start_date: r.start_date as string,
    end_date: r.end_date as string,
    progress: (r.progress_pct as number) ?? 0,
    responsible: (r.assigned_to as string) ?? "",
    predecessors: [],
    milestone: (r.is_milestone as boolean) ?? false,
    created_at: r.created_at as string,
  }), activeMissionId);
}
