import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { getMission, getBudgetSummary, getProductTree } from "@/lib/data";
import { SubsystemPieCharts } from "./_components/subsystem-pie-charts";
import { EditLimits } from "./_components/edit-limits";

function trlBadgeVariant(trl: number) {
  if (trl >= 8) return "default" as const;
  if (trl >= 6) return "secondary" as const;
  return "outline" as const;
}

export default async function BudgetsPage() {
  const mission = await getMission();
  const [budget, productTree] = await Promise.all([
    getBudgetSummary(mission),
    getProductTree(),
  ]);

  const equipment = productTree.filter((n) => n.node_type === "equipment");

  // Group by parent subsystem
  function getSubsystemName(parentId: string | null): string {
    const parent = productTree.find((n) => n.id === parentId);
    return parent?.name ?? "Unknown";
  }

  const subsystemBreakdown = equipment.reduce<
    Record<string, { mass: number; power: number }>
  >((acc, eq) => {
    const sub = getSubsystemName(eq.parent_id);
    if (!acc[sub]) acc[sub] = { mass: 0, power: 0 };
    acc[sub].mass += eq.mass_kg * eq.qty * (1 + eq.maturity_margin / 100);
    acc[sub].power += eq.power_w * eq.qty;
    return acc;
  }, {});

  const SUMMARY_CARDS = [
    { label: "Dry Mass", value: `${budget.total_dry_mass_kg} kg`, color: "border-t-blue-500" },
    { label: "Wet Mass", value: `${budget.total_wet_mass_kg} kg`, color: "border-t-blue-400" },
    { label: "Total Power", value: `${budget.total_power_w} W`, color: "border-t-orange-500" },
    {
      label: "Mass Margin",
      value: `${budget.mass_margin_kg} kg (${((budget.mass_margin_kg / budget.mass_limit_kg) * 100).toFixed(1)}%)`,
      color: "border-t-green-500",
    },
    {
      label: "Power Margin",
      value: `${budget.power_margin_w} W (${((budget.power_margin_w / budget.power_limit_w) * 100).toFixed(1)}%)`,
      color: "border-t-green-400",
    },
  ];
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Mass &amp; Power Budgets</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {SUMMARY_CARDS.map((c) => (
          <Card key={c.label} className={`border-t-2 ${c.color}`}>
            <CardHeader className="pb-1">
              <p className="text-xs text-muted-foreground">{c.label}</p>
            </CardHeader>
            <CardContent>
              <p className="text-xl font-bold">{c.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Pie charts */}
      <SubsystemPieCharts breakdown={subsystemBreakdown} />

      {/* Edit limits */}
      <EditLimits massLimit={budget.mass_limit_kg} powerLimit={budget.power_limit_w} propellant={mission.propellant_mass_kg} />

      {/* Equipment table */}
      <Card>
        <CardHeader>
          <CardTitle>Equipment List</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Subsystem</TableHead>
                <TableHead className="text-right">Mass (kg)</TableHead>
                <TableHead className="text-right">Power (W)</TableHead>
                <TableHead className="text-right">Qty</TableHead>
                <TableHead className="text-right">Margin (%)</TableHead>
                <TableHead className="text-right">Mass w/ margin</TableHead>
                <TableHead className="text-center">TRL</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {equipment.map((eq) => {
                const massWithMargin = (
                  eq.mass_kg *
                  eq.qty *
                  (1 + eq.maturity_margin / 100)
                ).toFixed(1);
                return (
                  <TableRow key={eq.id}>
                    <TableCell className="font-medium">{eq.name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {getSubsystemName(eq.parent_id)}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {eq.mass_kg}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {eq.power_w}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {eq.qty}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {eq.maturity_margin}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {massWithMargin}
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge variant={trlBadgeVariant(eq.trl)}>
                        TRL {eq.trl}
                      </Badge>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
