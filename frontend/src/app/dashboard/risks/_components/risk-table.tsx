"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { supabase } from "@/lib/supabase";
import type { Risk } from "@/lib/types";

const MISSION_ID = "00000000-0000-0000-0000-000000000001";
const RISK_STATUSES = ["open", "mitigated", "accepted", "closed"] as const;
const RISK_CATEGORIES = ["technical", "schedule", "cost", "programmatic", "environmental"] as const;

const inputClass = "w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring";
const labelClass = "text-xs font-medium text-muted-foreground";

function statusVariant(status: string) {
  switch (status) {
    case "open": return "destructive" as const;
    case "mitigated": return "secondary" as const;
    case "accepted": return "outline" as const;
    case "closed": return "default" as const;
    default: return "outline" as const;
  }
}

export function RiskTable({ risks }: { risks: Risk[] }) {
  const [addOpen, setAddOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editL, setEditL] = useState(0);
  const [editC, setEditC] = useState(0);
  const [editStatus, setEditStatus] = useState("");

  // Add form
  const [newRiskId, setNewRiskId] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newCategory, setNewCategory] = useState("technical");
  const [newL, setNewL] = useState(3);
  const [newC, setNewC] = useState(3);
  const [newOwner, setNewOwner] = useState("");
  const [newMitigation, setNewMitigation] = useState("");

  async function handleAdd() {
    if (!newRiskId || !newTitle) { alert("Risk ID and Title are required"); return; }
    const { error } = await supabase.from("risks").insert({
      mission_id: MISSION_ID,
      risk_id: newRiskId,
      title: newTitle,
      description: newDesc,
      category: newCategory,
      likelihood: newL,
      consequence: newC,
      status: "open",
      owner: newOwner,
      mitigation_strategy: newMitigation,
    });
    if (error) { alert("Error: " + error.message); return; }
    setAddOpen(false);
    window.location.reload();
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this risk?")) return;
    const { error } = await supabase.from("risks").delete().eq("id", id);
    if (error) { alert("Error: " + error.message); return; }
    window.location.reload();
  }

  async function handleInlineEdit(id: string) {
    const updates: Record<string, unknown> = {};
    if (editL) updates.likelihood = editL;
    if (editC) updates.consequence = editC;
    if (editStatus) updates.status = editStatus === "mitigated" ? "mitigating" : editStatus;
    if (Object.keys(updates).length === 0) { setEditingId(null); return; }
    const { error } = await supabase.from("risks").update(updates).eq("id", id);
    if (error) { alert("Error: " + error.message); return; }
    setEditingId(null);
    window.location.reload();
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Risk Register</CardTitle>
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogTrigger render={<Button size="sm" />}>+ Add Risk</DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Add Risk</DialogTitle>
            </DialogHeader>
            <div className="grid gap-3">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className={labelClass}>Risk ID</label>
                  <input className={inputClass} value={newRiskId} onChange={e => setNewRiskId(e.target.value)} placeholder="RSK-005" />
                </div>
                <div>
                  <label className={labelClass}>Category</label>
                  <select className={inputClass} value={newCategory} onChange={e => setNewCategory(e.target.value)}>
                    {RISK_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className={labelClass}>Title</label>
                <input className={inputClass} value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="Risk title" />
              </div>
              <div>
                <label className={labelClass}>Description</label>
                <textarea className={inputClass + " min-h-[60px]"} value={newDesc} onChange={e => setNewDesc(e.target.value)} />
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className={labelClass}>Likelihood (1-5)</label>
                  <input type="number" min={1} max={5} className={inputClass} value={newL} onChange={e => setNewL(Number(e.target.value))} />
                </div>
                <div>
                  <label className={labelClass}>Consequence (1-5)</label>
                  <input type="number" min={1} max={5} className={inputClass} value={newC} onChange={e => setNewC(Number(e.target.value))} />
                </div>
                <div>
                  <label className={labelClass}>Owner</label>
                  <input className={inputClass} value={newOwner} onChange={e => setNewOwner(e.target.value)} placeholder="PM" />
                </div>
              </div>
              <div>
                <label className={labelClass}>Mitigation Strategy</label>
                <textarea className={inputClass + " min-h-[40px]"} value={newMitigation} onChange={e => setNewMitigation(e.target.value)} />
              </div>
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
              <Button onClick={handleAdd}>Add</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-24">ID</TableHead>
              <TableHead>Title</TableHead>
              <TableHead>Category</TableHead>
              <TableHead className="text-center">L</TableHead>
              <TableHead className="text-center">C</TableHead>
              <TableHead className="text-center">Score</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Owner</TableHead>
              <TableHead>Mitigation</TableHead>
              <TableHead className="w-20">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {risks.map((r) => (
              <TableRow key={r.id}>
                <TableCell className="font-mono text-xs">{r.risk_id}</TableCell>
                <TableCell className="font-medium">{r.title}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{r.category}</TableCell>
                <TableCell className="text-center">
                  {editingId === r.id ? (
                    <input type="number" min={1} max={5} className="w-12 rounded border border-border bg-background px-1 py-0.5 text-xs text-center" value={editL} onChange={e => setEditL(Number(e.target.value))} />
                  ) : (
                    <span className="font-mono">{r.likelihood}</span>
                  )}
                </TableCell>
                <TableCell className="text-center">
                  {editingId === r.id ? (
                    <input type="number" min={1} max={5} className="w-12 rounded border border-border bg-background px-1 py-0.5 text-xs text-center" value={editC} onChange={e => setEditC(Number(e.target.value))} />
                  ) : (
                    <span className="font-mono">{r.consequence}</span>
                  )}
                </TableCell>
                <TableCell className="text-center font-mono font-bold">
                  {editingId === r.id ? editL * editC : r.likelihood * r.consequence}
                </TableCell>
                <TableCell>
                  {editingId === r.id ? (
                    <select className="rounded border border-border bg-background px-1 py-0.5 text-xs" value={editStatus} onChange={e => setEditStatus(e.target.value)}>
                      {RISK_STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  ) : (
                    <Badge variant={statusVariant(r.status)}>{r.status}</Badge>
                  )}
                </TableCell>
                <TableCell className="text-xs">{r.owner}</TableCell>
                <TableCell className="max-w-[200px] truncate text-xs text-muted-foreground">{r.mitigation}</TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    {editingId === r.id ? (
                      <>
                        <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => handleInlineEdit(r.id)}>Save</Button>
                        <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => setEditingId(null)}>Cancel</Button>
                      </>
                    ) : (
                      <>
                        <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => { setEditingId(r.id); setEditL(r.likelihood); setEditC(r.consequence); setEditStatus(r.status); }}>Edit</Button>
                        <Button variant="ghost" size="sm" className="h-6 px-2 text-xs text-red-400" onClick={() => handleDelete(r.id)}>Del</Button>
                      </>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
