import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getRisks } from "@/lib/data";
import { RiskMatrix } from "./_components/risk-matrix";
import { RiskTable } from "./_components/risk-table";

export default async function RisksPage() {
  const risks = await getRisks();

  const open = risks.filter((r) => r.status === "open").length;
  const mitigated = risks.filter((r) => r.status === "mitigated").length;
  const accepted = risks.filter((r) => r.status === "accepted").length;
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Risk Management</h1>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="border-t-2 border-t-red-500">
          <CardHeader className="pb-1">
            <p className="text-xs text-muted-foreground">Total Risks</p>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{risks.length}</p>
          </CardContent>
        </Card>
        <Card className="border-t-2 border-t-orange-500">
          <CardHeader className="pb-1">
            <p className="text-xs text-muted-foreground">Open</p>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{open}</p>
          </CardContent>
        </Card>
        <Card className="border-t-2 border-t-yellow-500">
          <CardHeader className="pb-1">
            <p className="text-xs text-muted-foreground">Mitigated</p>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{mitigated}</p>
          </CardContent>
        </Card>
        <Card className="border-t-2 border-t-green-500">
          <CardHeader className="pb-1">
            <p className="text-xs text-muted-foreground">Accepted</p>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{accepted}</p>
          </CardContent>
        </Card>
      </div>

      {/* Risk matrix */}
      <RiskMatrix risks={risks} />

      {/* Risk table */}
      <RiskTable risks={risks} />
    </div>
  );
}
