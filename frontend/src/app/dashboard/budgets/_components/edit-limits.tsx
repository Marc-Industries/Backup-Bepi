"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";
const supabase = supabaseUrl ? createClient(supabaseUrl, supabaseAnonKey) : null;

const MISSION_ID = "00000000-0000-0000-0000-000000000001";

interface Props {
  massLimit: number;
  powerLimit: number;
  propellant: number;
}

export function EditLimits({ massLimit, powerLimit, propellant }: Props) {
  const [mass, setMass] = useState(massLimit);
  const [power, setPower] = useState(powerLimit);
  const [prop, setProp] = useState(propellant);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function handleSave() {
    if (!supabase) return;
    setSaving(true);
    await supabase
      .from("missions")
      .update({ mass_limit_kg: mass, power_limit_w: power, propellant_mass_kg: prop })
      .eq("id", MISSION_ID);
    setSaving(false);
    setSaved(true);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Edit Budget Limits</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground">Mass Limit (kg)</p>
            <Input type="number" value={mass} onChange={(e) => { setMass(Number(e.target.value)); setSaved(false); }} />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground">Power Limit (W)</p>
            <Input type="number" value={power} onChange={(e) => { setPower(Number(e.target.value)); setSaved(false); }} />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground">Propellant Mass (kg)</p>
            <Input type="number" value={prop} onChange={(e) => { setProp(Number(e.target.value)); setSaved(false); }} />
          </div>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <Button onClick={handleSave} disabled={saving || !supabase} size="sm">
            {saving ? "Saving..." : "Save Limits"}
          </Button>
          {saved && <span className="text-sm text-green-600">Saved</span>}
        </div>
      </CardContent>
    </Card>
  );
}
