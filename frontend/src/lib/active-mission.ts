import { hasSupabase, supabase } from "./supabase";

const LEGACY_MISSION_ID = "00000000-0000-0000-0000-000000000001";

export async function resolveActiveMissionId(): Promise<string | null> {
  if (!hasSupabase) return null;

  // Prefer the legacy hard-coded mission id if it exists (older seeds).
  try {
    const { data: legacy, error: legacyError } = await supabase
      .from("missions")
      .select("id")
      .eq("id", LEGACY_MISSION_ID)
      .maybeSingle();
    if (!legacyError && legacy?.id) return legacy.id as string;
  } catch {
    // ignore and fall through
  }

  try {
    const { data, error } = await supabase
      .from("missions")
      .select("id")
      .order("created_at", { ascending: false })
      .limit(1);
    if (error) return null;
    return (data?.[0]?.id as string | undefined) ?? null;
  } catch {
    return null;
  }
}

