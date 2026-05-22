import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { getRequirements, getProductTree } from "@/lib/data";
import { RequirementsClient } from "./_components/requirements-client";

export default async function RequirementsPage() {
  const [requirements, productTree] = await Promise.all([
    getRequirements(),
    getProductTree(),
  ]);

  const allocationMap = Object.fromEntries(
    productTree.map((n) => [n.id, n.name])
  );

  const total = requirements.length;
  const verified = requirements.filter((r) => r.status === "verified").length;
  const coverage = ((verified / total) * 100).toFixed(1);
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Requirements</h1>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="border-t-2 border-t-blue-500">
          <CardHeader className="pb-1">
            <p className="text-xs text-muted-foreground">Total</p>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{total}</p>
          </CardContent>
        </Card>
        <Card className="border-t-2 border-t-green-500">
          <CardHeader className="pb-1">
            <p className="text-xs text-muted-foreground">Verified</p>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{verified}</p>
          </CardContent>
        </Card>
        <Card className="border-t-2 border-t-purple-500">
          <CardHeader className="pb-1">
            <p className="text-xs text-muted-foreground">Coverage</p>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{coverage}%</p>
          </CardContent>
        </Card>
      </div>

      {/* Client component for filtering + table */}
      <RequirementsClient
        requirements={requirements}
        allocationMap={allocationMap}
      />
    </div>
  );
}
