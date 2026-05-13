"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Risk } from "@/lib/types";

function cellColor(l: number, c: number): string {
  const score = l * c;
  if (score >= 15) return "bg-red-600/80";
  if (score >= 10) return "bg-orange-500/70";
  if (score >= 5) return "bg-yellow-500/50";
  return "bg-green-600/40";
}

export function RiskMatrix({ risks }: { risks: Risk[] }) {
  // Build lookup: key = "L-C", value = risk IDs
  const lookup: Record<string, Risk[]> = {};
  for (const r of risks) {
    const key = `${r.likelihood}-${r.consequence}`;
    if (!lookup[key]) lookup[key] = [];
    lookup[key].push(r);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk Matrix (Likelihood vs Consequence)</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <div className="inline-grid grid-cols-[auto_repeat(5,1fr)] gap-1 text-xs">
            {/* Header row */}
            <div />
            {[1, 2, 3, 4, 5].map((c) => (
              <div key={c} className="flex h-8 w-20 items-center justify-center font-medium text-muted-foreground">
                C={c}
              </div>
            ))}

            {/* Matrix rows — likelihood from 5 (top) to 1 (bottom) */}
            {[5, 4, 3, 2, 1].map((l) => (
              <React.Fragment key={l}>
                <div className="flex h-20 w-12 items-center justify-center font-medium text-muted-foreground">
                  L={l}
                </div>
                {[1, 2, 3, 4, 5].map((c) => {
                  const cellRisks = lookup[`${l}-${c}`] ?? [];
                  return (
                    <div
                      key={`${l}-${c}`}
                      className={`flex h-20 w-20 flex-col items-center justify-center rounded-md ${cellColor(l, c)}`}
                    >
                      {cellRisks.map((r) => (
                        <span
                          key={r.id}
                          className="mb-0.5 rounded bg-background/80 px-1 py-0.5 text-[10px] font-mono font-bold leading-tight"
                          title={r.title}
                        >
                          {r.risk_id}
                        </span>
                      ))}
                    </div>
                  );
                })}
              </React.Fragment>
            ))}
          </div>
        </div>
        <div className="mt-3 flex items-center gap-4 text-[10px] text-muted-foreground">
          <span className="flex items-center gap-1"><span className="inline-block h-3 w-3 rounded bg-green-600/40" /> Low (1-4)</span>
          <span className="flex items-center gap-1"><span className="inline-block h-3 w-3 rounded bg-yellow-500/50" /> Medium (5-9)</span>
          <span className="flex items-center gap-1"><span className="inline-block h-3 w-3 rounded bg-orange-500/70" /> High (10-14)</span>
          <span className="flex items-center gap-1"><span className="inline-block h-3 w-3 rounded bg-red-600/80" /> Critical (15-25)</span>
        </div>
      </CardContent>
    </Card>
  );
}
