"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

type ReportStatus = "ready" | "generating" | "completed"

interface ReportDef {
  id: string
  title: string
  description: string
  icon: string
  status: ReportStatus
}

const INITIAL_REPORTS: ReportDef[] = [
  {
    id: "budget",
    title: "Budget Report",
    description:
      "Mass and power budget summary with margins, maturity corrections, and subsystem breakdown. LaTeX-generated PDF.",
    icon: "\u2696",
    status: "ready",
  },
  {
    id: "requirements",
    title: "Requirements Document",
    description:
      "Full requirements specification with traceability matrix, verification methods, and compliance status.",
    icon: "\u2611",
    status: "ready",
  },
  {
    id: "risk",
    title: "Risk Assessment",
    description:
      "Risk register with likelihood/consequence matrix, FMECA summary, fault tree analysis, and mitigation plans.",
    icon: "\u26A0",
    status: "ready",
  },
  {
    id: "design",
    title: "Design Definition",
    description:
      "Design Definition File (DDF) covering system architecture, product tree, interface definitions, and trade-offs.",
    icon: "\u2699",
    status: "ready",
  },
  {
    id: "review",
    title: "Review Data Package",
    description:
      "Consolidated data package for milestone reviews (PDR/CDR). Includes all budgets, requirements status, and open items.",
    icon: "\u{1F4CB}",
    status: "ready",
  },
]

function statusBadge(status: ReportStatus) {
  switch (status) {
    case "ready":
      return (
        <Badge variant="outline" className="text-[10px]">
          Ready
        </Badge>
      )
    case "generating":
      return (
        <Badge variant="secondary" className="text-[10px] animate-pulse">
          Generating...
        </Badge>
      )
    case "completed":
      return (
        <Badge variant="default" className="text-[10px] bg-emerald-600">
          Completed
        </Badge>
      )
  }
}

export default function ReportsPage() {
  const [reports, setReports] = useState(INITIAL_REPORTS)

  function handleGenerate(id: string) {
    setReports((prev) =>
      prev.map((r) => (r.id === id ? { ...r, status: "generating" as const } : r))
    )
    // Simulate generation
    setTimeout(() => {
      setReports((prev) =>
        prev.map((r) =>
          r.id === id ? { ...r, status: "completed" as const } : r
        )
      )
    }, 2000)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Reports</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Generate ECSS-compliant documents and review data packages
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {reports.map((report) => (
          <Card
            key={report.id}
            className="flex flex-col justify-between"
          >
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <span className="text-3xl">{report.icon}</span>
                {statusBadge(report.status)}
              </div>
              <CardTitle className="text-base mt-2">{report.title}</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4 flex-1">
              <p className="text-sm text-muted-foreground flex-1">
                {report.description}
              </p>
              <Button
                className="w-full"
                variant={report.status === "completed" ? "secondary" : "default"}
                disabled={report.status === "generating"}
                onClick={() => handleGenerate(report.id)}
              >
                {report.status === "completed"
                  ? "Regenerate"
                  : report.status === "generating"
                    ? "Generating..."
                    : "Generate"}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
