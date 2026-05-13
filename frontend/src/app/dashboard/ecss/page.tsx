"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { DEMO_PRODUCT_TREE, DEMO_MISSION } from "@/lib/mock-data"

const ESA_PHASES = [
  { id: "0", name: "Mission Analysis", margin: 30 },
  { id: "A", name: "Feasibility", margin: 20 },
  { id: "B1", name: "Preliminary Definition", margin: 20 },
  { id: "B2", name: "Detailed Definition", margin: 10 },
  { id: "C", name: "Qualification & Production", margin: 5 },
  { id: "D", name: "Final Production", margin: 5 },
  { id: "E1", name: "Commissioning", margin: 0 },
  { id: "E2", name: "Operations", margin: 0 },
  { id: "F", name: "Disposal", margin: 0 },
]

const NASA_PHASES = [
  { id: "Pre-A", name: "Concept Studies", margin: 25 },
  { id: "A", name: "Concept & Technology Development", margin: 20 },
  { id: "B", name: "Preliminary Design & Technology Completion", margin: 15 },
  { id: "C", name: "Final Design & Fabrication", margin: 10 },
  { id: "D", name: "System Assembly, Integration & Test", margin: 5 },
  { id: "E", name: "Operations & Sustainment", margin: 0 },
  { id: "F", name: "Closeout", margin: 0 },
]

const ESA_REVIEWS = [
  { name: "SRR", full: "System Requirements Review", phase: "A", status: "completed" as const },
  { name: "MDR", full: "Mission Definition Review", phase: "A", status: "completed" as const },
  { name: "PRR", full: "Preliminary Requirements Review", phase: "B1", status: "completed" as const },
  { name: "PDR", full: "Preliminary Design Review", phase: "B2", status: "planned" as const },
  { name: "CDR", full: "Critical Design Review", phase: "C", status: "planned" as const },
  { name: "QR", full: "Qualification Review", phase: "C", status: "planned" as const },
  { name: "AR", full: "Acceptance Review", phase: "D", status: "planned" as const },
  { name: "ORR", full: "Operational Readiness Review", phase: "E1", status: "planned" as const },
  { name: "LRR", full: "Launch Readiness Review", phase: "E1", status: "planned" as const },
]

const TRL_TARGETS: Record<string, number> = {
  "0": 1,
  A: 3,
  B1: 4,
  B2: 5,
  C: 6,
  D: 8,
  E1: 9,
  E2: 9,
  F: 9,
}

export default function EcssPage() {
  const [framework, setFramework] = useState<"ESA" | "NASA">(
    DEMO_MISSION.framework
  )
  const phases = framework === "ESA" ? ESA_PHASES : NASA_PHASES
  const currentPhase = phases.find((p) => p.id === DEMO_MISSION.phase) ?? phases[3]
  const equipment = DEMO_PRODUCT_TREE.filter((n) => n.node_type === "equipment")
  const trlTarget = framework === "ESA" ? (TRL_TARGETS[DEMO_MISSION.phase] ?? 5) : 5

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">ECSS Framework</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Standards, phases, reviews, margins, and TRL tracking
        </p>
      </div>

      {/* Framework selector */}
      <Tabs
        value={framework}
        onValueChange={(v) => setFramework(v as "ESA" | "NASA")}
      >
        <TabsList>
          <TabsTrigger value="ESA">ESA (ECSS)</TabsTrigger>
          <TabsTrigger value="NASA">NASA</TabsTrigger>
        </TabsList>

        <TabsContent value={framework} className="mt-6 space-y-6">
          {/* Current phase info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-3">
                Current Phase
                <Badge variant="default" className="text-xs">
                  Phase {currentPhase.id}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-6">
                <div>
                  <span className="text-xs text-muted-foreground">Phase</span>
                  <div className="text-lg font-bold">
                    {currentPhase.id} &mdash; {currentPhase.name}
                  </div>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">
                    Mass Margin
                  </span>
                  <div className="text-lg font-bold">
                    {currentPhase.margin}%
                  </div>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground">
                    TRL Target
                  </span>
                  <div className="text-lg font-bold">TRL {trlTarget}</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Review timeline */}
          {framework === "ESA" && (
            <Card>
              <CardHeader>
                <CardTitle>Review Timeline</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-1 overflow-x-auto pb-2">
                  {ESA_REVIEWS.map((rev, i) => {
                    const isCompleted = rev.status === "completed"
                    return (
                      <div key={rev.name} className="flex items-center">
                        <div className="flex flex-col items-center gap-1.5">
                          <div
                            className={`w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold border-2 ${
                              isCompleted
                                ? "bg-emerald-500/20 border-emerald-500 text-emerald-400"
                                : "bg-muted border-border text-muted-foreground"
                            }`}
                          >
                            {rev.name}
                          </div>
                          <span className="text-[10px] text-muted-foreground text-center w-20 leading-tight">
                            {rev.full}
                          </span>
                          <Badge
                            variant={isCompleted ? "default" : "outline"}
                            className="text-[9px]"
                          >
                            {rev.phase}
                          </Badge>
                        </div>
                        {i < ESA_REVIEWS.length - 1 && (
                          <div
                            className={`h-0.5 w-6 mx-1 ${
                              isCompleted && ESA_REVIEWS[i + 1]?.status === "completed"
                                ? "bg-emerald-500"
                                : "bg-border"
                            }`}
                          />
                        )}
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Margins table */}
          <Card>
            <CardHeader>
              <CardTitle>Phase Margins</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Phase</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead className="text-right">Mass Margin</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {phases.map((p) => {
                    const isCurrent = p.id === currentPhase.id
                    return (
                      <TableRow
                        key={p.id}
                        className={isCurrent ? "bg-muted/50" : ""}
                      >
                        <TableCell className="font-mono font-bold">
                          {p.id}
                        </TableCell>
                        <TableCell>{p.name}</TableCell>
                        <TableCell className="text-right tabular-nums">
                          {p.margin > 0 ? `${p.margin}%` : "--"}
                        </TableCell>
                        <TableCell>
                          {isCurrent ? (
                            <Badge variant="default">Current</Badge>
                          ) : (
                            <Badge variant="outline">
                              {phases.indexOf(p) < phases.indexOf(currentPhase)
                                ? "Past"
                                : "Future"}
                            </Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* TRL tracking */}
          <Card>
            <CardHeader>
              <CardTitle>TRL Tracking</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Equipment</TableHead>
                    <TableHead>Current TRL</TableHead>
                    <TableHead>Target TRL</TableHead>
                    <TableHead>MAIT</TableHead>
                    <TableHead>Gap</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {equipment.map((eq) => {
                    const gap = trlTarget - eq.trl
                    return (
                      <TableRow key={eq.id}>
                        <TableCell className="font-medium">{eq.name}</TableCell>
                        <TableCell>
                          <span
                            className={`font-mono font-bold ${
                              eq.trl >= trlTarget
                                ? "text-emerald-400"
                                : eq.trl >= trlTarget - 1
                                  ? "text-yellow-400"
                                  : "text-red-400"
                            }`}
                          >
                            {eq.trl}
                          </span>
                        </TableCell>
                        <TableCell className="font-mono">{trlTarget}</TableCell>
                        <TableCell>
                          {eq.mait_status ? (
                            <Badge variant="secondary">{eq.mait_status}</Badge>
                          ) : (
                            "--"
                          )}
                        </TableCell>
                        <TableCell>
                          {gap > 0 ? (
                            <Badge variant="destructive">-{gap}</Badge>
                          ) : (
                            <Badge variant="default">OK</Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
