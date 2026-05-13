import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getMission, getBudgetSummary, getRequirements, getRisks, getTasks } from "@/lib/data";
import { BudgetGauges } from "./_components/budget-gauges";

export default async function DashboardPage() {
  const mission = await getMission();
  const [budget, requirements, risks, tasks] = await Promise.all([
    getBudgetSummary(mission),
    getRequirements(),
    getRisks(),
    getTasks(),
  ]);

  const nextReview = tasks.filter((t) => t.milestone && t.progress === 0).sort(
    (a, b) => a.start_date.localeCompare(b.start_date)
  )[0];

  const openRisks = risks.filter((r) => r.status === "open").length;

  const KPI_CARDS = [
    {
      label: "Wet Mass",
      value: `${budget.total_wet_mass_kg} kg`,
      sub: `Limit ${budget.mass_limit_kg} kg`,
      color: "border-t-blue-500",
    },
    {
      label: "Total Power",
      value: `${budget.total_power_w} W`,
      sub: `Limit ${budget.power_limit_w} W`,
      color: "border-t-orange-500",
    },
    {
      label: "Requirements",
      value: `${requirements.length}`,
      sub: `${requirements.filter((r) => r.status === "verified").length} verified`,
      color: "border-t-green-500",
    },
    {
      label: "Open Risks",
      value: `${openRisks}`,
      sub: `${risks.length} total`,
      color: "border-t-red-500",
    },
    {
      label: "Next Review",
      value: nextReview?.name ?? "—",
      sub: nextReview?.start_date ?? "",
      color: "border-t-purple-500",
    },
  ];

  const MISSION_PARAMS = [
    ["Mission", mission.name],
    ["Phase", `${mission.phase} (${mission.framework})`],
    ["Orbit", mission.orbit],
    ["Target Launch", mission.target_launch],
    ["Lifetime", `${mission.lifetime_years} years`],
    ["Dry Mass", `${budget.total_dry_mass_kg} kg`],
    ["Wet Mass", `${budget.total_wet_mass_kg} kg`],
    ["Mass Margin", `${budget.mass_margin_kg} kg (${((budget.mass_margin_kg / budget.mass_limit_kg) * 100).toFixed(1)}%)`],
  ];
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Mission Overview</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {KPI_CARDS.map((kpi) => (
          <Card key={kpi.label} className={`border-t-2 ${kpi.color}`}>
            <CardHeader className="pb-1">
              <p className="text-xs text-muted-foreground">{kpi.label}</p>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{kpi.value}</p>
              <p className="text-xs text-muted-foreground">{kpi.sub}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Mission Parameters + Gauges */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Mission Parameters</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <tbody>
                {MISSION_PARAMS.map(([label, value]) => (
                  <tr key={label} className="border-b border-border/40 last:border-0">
                    <td className="py-2 pr-4 font-medium text-muted-foreground">{label}</td>
                    <td className="py-2 font-mono">{value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>

        <BudgetGauges
          massUsed={budget.total_wet_mass_kg}
          massLimit={budget.mass_limit_kg}
          powerUsed={budget.total_power_w}
          powerLimit={budget.power_limit_w}
        />
      </div>
    </div>
  );
}
