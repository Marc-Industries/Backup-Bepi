"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { createClient } from "@supabase/supabase-js";
import { resolveActiveMissionId } from "@/lib/active-mission";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";
const supabase = supabaseUrl ? createClient(supabaseUrl, supabaseAnonKey) : null;

interface MissionForm {
  name: string;
  description: string;
  phase: string;
  orbit: string;
  target_launch: string;
  lifetime_years: number;
  mass_limit_kg: number;
  power_limit_w: number;
  propellant_mass_kg: number;
}

function Field({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string | number;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <div className="space-y-1">
      <p className="text-sm font-medium text-muted-foreground">{label}</p>
      <Input type={type} value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

const DEFAULTS: MissionForm = {
  name: "BEPI-SAT",
  description: "LEO Earth Observation SmallSat",
  phase: "B2",
  orbit: "SSO 550 km, 97.6 deg",
  target_launch: "2027-06",
  lifetime_years: 5,
  mass_limit_kg: 350,
  power_limit_w: 500,
  propellant_mass_kg: 25,
};

export default function SettingsPage() {
  const [form, setForm] = useState<MissionForm>(DEFAULTS);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!supabase) return;
    (async () => {
      const missionId = await resolveActiveMissionId();
      if (!missionId) return;
      const { data } = await supabase
        .from("missions")
        .select("*")
        .eq("id", missionId)
        .single();
      if (!data) return;
      setForm({
        name: data.name ?? DEFAULTS.name,
        description: data.description ?? DEFAULTS.description,
        phase: data.phase ?? DEFAULTS.phase,
        orbit: data.orbit_type ?? DEFAULTS.orbit,
        target_launch: data.target_launch_date ?? DEFAULTS.target_launch,
        lifetime_years: data.lifetime_years ?? DEFAULTS.lifetime_years,
        mass_limit_kg: data.mass_limit_kg ?? DEFAULTS.mass_limit_kg,
        power_limit_w: data.power_limit_w ?? DEFAULTS.power_limit_w,
        propellant_mass_kg: data.propellant_mass_kg ?? DEFAULTS.propellant_mass_kg,
      });
    })();
  }, []);

  function set(key: keyof MissionForm, value: string | number) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }

  async function handleSave() {
    if (!supabase) return;
    const missionId = await resolveActiveMissionId();
    if (!missionId) { alert("No mission found in Supabase"); return; }
    setSaving(true);
    await supabase
      .from("missions")
      .update({
        name: form.name,
        description: form.description,
        phase: form.phase,
        orbit_type: form.orbit,
        target_launch_date: form.target_launch,
        lifetime_years: form.lifetime_years,
        mass_limit_kg: form.mass_limit_kg,
        power_limit_w: form.power_limit_w,
        propellant_mass_kg: form.propellant_mass_kg,
      })
      .eq("id", missionId);
    setSaving(false);
    setSaved(true);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Mission Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle>General</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <Field label="Mission Name" value={form.name} onChange={(v) => set("name", v)} />
          <Field label="Description" value={form.description} onChange={(v) => set("description", v)} />
          <Field label="Phase" value={form.phase} onChange={(v) => set("phase", v)} />
          <Field label="Orbit" value={form.orbit} onChange={(v) => set("orbit", v)} />
          <Field label="Target Launch" value={form.target_launch} onChange={(v) => set("target_launch", v)} />
          <Field label="Lifetime (years)" type="number" value={form.lifetime_years} onChange={(v) => set("lifetime_years", Number(v))} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Budget Limits</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <Field label="Mass Limit (kg)" type="number" value={form.mass_limit_kg} onChange={(v) => set("mass_limit_kg", Number(v))} />
          <Field label="Power Limit (W)" type="number" value={form.power_limit_w} onChange={(v) => set("power_limit_w", Number(v))} />
          <Field label="Propellant Mass (kg)" type="number" value={form.propellant_mass_kg} onChange={(v) => set("propellant_mass_kg", Number(v))} />
        </CardContent>
      </Card>

      <div className="flex items-center gap-3">
        <Button onClick={handleSave} disabled={saving || !supabase}>
          {saving ? "Saving..." : "Save Changes"}
        </Button>
        {saved && <span className="text-sm text-green-600">Saved successfully</span>}
        {!supabase && <span className="text-sm text-muted-foreground">Supabase not configured -- changes {"won't"} persist</span>}
      </div>
    </div>
  );
}
