import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const INTEGRATIONS = [
  { name: "GMAT", desc: "General Mission Analysis Tool — orbit propagation & maneuver planning", status: "active", category: "Orbit" },
  { name: "FreeFlyer", desc: "Astrodynamics simulation for orbit design & station keeping", status: "active", category: "Orbit" },
  { name: "SPENVIS / SpacePy", desc: "Space environment & radiation analysis (trapped particles, SEE, TID)", status: "active", category: "Environment" },
  { name: "DRAMA", desc: "ESA debris risk assessment & re-entry analysis", status: "active", category: "Environment" },
  { name: "MATLAB / Octave", desc: "Script generation for link budget, power, thermal, structural sizing", status: "active", category: "Analysis" },
  { name: "Systema", desc: "Thermal model geometry & node export", status: "active", category: "Thermal" },
  { name: "OpenLCA", desc: "Life Cycle Assessment export for environmental impact", status: "beta", category: "LCA" },
  { name: "SPICE Kernels", desc: "NAIF SPICE kernel management for ephemeris data", status: "active", category: "Navigation" },
  { name: "Excel I/O", desc: "Import/export product tree, requirements, risks, schedule", status: "active", category: "Data" },
  { name: "LaTeX Reports", desc: "Generate PDF reports from LaTeX templates", status: "active", category: "Reports" },
];

const statusColor: Record<string, string> = {
  active: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
  beta: "bg-amber-500/15 text-amber-400 border-amber-500/20",
  planned: "bg-zinc-500/15 text-zinc-400 border-zinc-500/20",
};

export default function IntegrationsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Integrations</h1>
        <p className="text-muted-foreground mt-1">External tools and data exchange interfaces</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {INTEGRATIONS.map((intg) => (
          <Card key={intg.name} className="hover:border-primary/30 transition-colors">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{intg.name}</CardTitle>
                <Badge variant="outline" className={statusColor[intg.status]}>{intg.status}</Badge>
              </div>
              <CardDescription className="text-xs">{intg.category}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">{intg.desc}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
