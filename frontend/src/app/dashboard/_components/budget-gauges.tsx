"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function DonutGauge({
  value,
  max,
  label,
  unit,
  color,
}: {
  value: number;
  max: number;
  label: string;
  unit: string;
  color: string;
}) {
  const pct = Math.min(value / max, 1);
  const radius = 70;
  const stroke = 14;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - pct);

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width="180" height="180" viewBox="0 0 180 180">
        <circle
          cx="90"
          cy="90"
          r={radius}
          fill="none"
          stroke="currentColor"
          className="text-muted/30"
          strokeWidth={stroke}
        />
        <circle
          cx="90"
          cy="90"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          transform="rotate(-90 90 90)"
          className="transition-all duration-700"
        />
        <text
          x="90"
          y="82"
          textAnchor="middle"
          className="fill-foreground text-2xl font-bold"
          fontSize="24"
          fontWeight="bold"
        >
          {value}
        </text>
        <text
          x="90"
          y="102"
          textAnchor="middle"
          className="fill-muted-foreground"
          fontSize="12"
        >
          / {max} {unit}
        </text>
      </svg>
      <p className="text-sm font-medium">{label}</p>
      <p className="text-xs text-muted-foreground">
        {((pct) * 100).toFixed(1)}% used &middot; {(max - value).toFixed(1)} {unit} margin
      </p>
    </div>
  );
}

export function BudgetGauges({
  massUsed,
  massLimit,
  powerUsed,
  powerLimit,
}: {
  massUsed: number;
  massLimit: number;
  powerUsed: number;
  powerLimit: number;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Budget Overview</CardTitle>
      </CardHeader>
      <CardContent className="flex items-center justify-around">
        <DonutGauge
          value={massUsed}
          max={massLimit}
          label="Mass Budget"
          unit="kg"
          color="#3b82f6"
        />
        <DonutGauge
          value={powerUsed}
          max={powerLimit}
          label="Power Budget"
          unit="W"
          color="#f97316"
        />
      </CardContent>
    </Card>
  );
}
