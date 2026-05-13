"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const COLORS = [
  "#3b82f6", "#f97316", "#22c55e", "#ef4444", "#a855f7",
  "#06b6d4", "#eab308", "#ec4899", "#64748b",
];

function PieChart({
  data,
  title,
  unit,
}: {
  data: { label: string; value: number }[];
  title: string;
  unit: string;
}) {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) return null;

  const size = 180;
  const cx = size / 2;
  const cy = size / 2;
  const r = 70;

  let cumAngle = -Math.PI / 2;
  const slices = data.map((d, i) => {
    const angle = (d.value / total) * 2 * Math.PI;
    const startX = cx + r * Math.cos(cumAngle);
    const startY = cy + r * Math.sin(cumAngle);
    const endX = cx + r * Math.cos(cumAngle + angle);
    const endY = cy + r * Math.sin(cumAngle + angle);
    const largeArc = angle > Math.PI ? 1 : 0;
    const path = `M ${cx} ${cy} L ${startX} ${startY} A ${r} ${r} 0 ${largeArc} 1 ${endX} ${endY} Z`;
    cumAngle += angle;
    return { path, color: COLORS[i % COLORS.length], label: d.label, value: d.value };
  });

  return (
    <div className="flex flex-col items-center gap-3">
      <p className="text-sm font-medium">{title}</p>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {slices.map((s, i) => (
          <path key={i} d={s.path} fill={s.color} stroke="hsl(var(--background))" strokeWidth="1.5" />
        ))}
      </svg>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        {slices.map((s, i) => (
          <div key={i} className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: s.color }} />
            <span className="text-muted-foreground">{s.label}</span>
            <span className="ml-auto font-mono">{s.value.toFixed(1)} {unit}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SubsystemPieCharts({
  breakdown,
}: {
  breakdown: Record<string, { mass: number; power: number }>;
}) {
  const entries = Object.entries(breakdown);
  const massData = entries.map(([label, v]) => ({ label, value: Math.round(v.mass * 10) / 10 }));
  const powerData = entries.map(([label, v]) => ({ label, value: Math.round(v.power * 10) / 10 }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Subsystem Breakdown</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-wrap items-start justify-around gap-8">
        <PieChart data={massData} title="Mass by Subsystem" unit="kg" />
        <PieChart data={powerData} title="Power by Subsystem" unit="W" />
      </CardContent>
    </Card>
  );
}
