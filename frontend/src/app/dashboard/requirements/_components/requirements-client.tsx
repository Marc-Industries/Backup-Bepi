"use client";

import { useState, useMemo } from "react";
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
import type { Requirement } from "@/lib/types";

const MISSION_ID = "00000000-0000-0000-0000-000000000001";

const REQ_TYPES = ["all", "functional", "performance", "interface", "environmental", "operational", "design"] as const;
const STATUSES = ["all", "draft", "active", "verified", "deleted"] as const;
const PRIORITIES = ["all", "shall", "should", "may"] as const;
const VERIFICATION_METHODS = ["test", "analysis", "inspection", "demonstration", "review"] as const;

function statusColor(status: string) {
  switch (status) {
    case "verified": return "default" as const;
    case "active": return "secondary" as const;
    case "draft": return "outline" as const;
    default: return "destructive" as const;
  }
}

function typeColor(type: string) {
  switch (type) {
    case "functional": return "default" as const;
    case "performance": return "secondary" as const;
    default: return "outline" as const;
  }
}

const inputClass = "w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring";
const labelClass = "text-xs font-medium text-muted-foreground";

export function RequirementsClient({
  requirements,
  allocationMap,
}: {
  requirements: Requirement[];
  allocationMap: Record<string, string>;
}) {
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [addOpen, setAddOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editStatus, setEditStatus] = useState("");
  const [editPriority, setEditPriority] = useState("");

  // Add form state
  const [newReqId, setNewReqId] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [newText, setNewText] = useState("");
  const [newType, setNewType] = useState<string>("functional");
  const [newPriority, setNewPriority] = useState<string>("shall");
  const [newVerification, setNewVerification] = useState<string>("test");

  const filtered = useMemo(() => {
    return requirements.filter((r) => {
      if (typeFilter !== "all" && r.req_type !== typeFilter) return false;
      if (statusFilter !== "all" && r.status !== statusFilter) return false;
      if (priorityFilter !== "all" && r.priority !== priorityFilter) return false;
      return true;
    });
  }, [requirements, typeFilter, statusFilter, priorityFilter]);

  async function handleAdd() {
    if (!newReqId || !newTitle) { alert("Req ID and Title are required"); return; }
    const { error } = await supabase.from("requirements").insert({
      mission_id: MISSION_ID,
      req_id: newReqId,
      title: newTitle,
      text: newText,
      category: newType,
      priority: newPriority === "shall" ? "mandatory" : newPriority === "should" ? "desirable" : "optional",
      status: "draft",
      verification_method: newVerification,
      level: "mission",
    });
    if (error) { alert("Error: " + error.message); return; }
    setAddOpen(false);
    window.location.reload();
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this requirement?")) return;
    const { error } = await supabase.from("requirements").delete().eq("id", id);
    if (error) { alert("Error: " + error.message); return; }
    window.location.reload();
  }

  async function handleInlineEdit(id: string) {
    const updates: Record<string, string> = {};
    if (editStatus) {
      updates.status = editStatus === "active" ? "approved" : editStatus;
    }
    if (editPriority) {
      updates.priority = editPriority === "shall" ? "mandatory" : editPriority === "should" ? "desirable" : "optional";
    }
    if (Object.keys(updates).length === 0) { setEditingId(null); return; }
    const { error } = await supabase.from("requirements").update(updates).eq("id", id);
    if (error) { alert("Error: " + error.message); return; }
    setEditingId(null);
    window.location.reload();
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Requirements List ({filtered.length})</CardTitle>
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogTrigger render={<Button size="sm" />}>+ Add Requirement</DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Add Requirement</DialogTitle>
            </DialogHeader>
            <div className="grid gap-3">
              <div>
                <label className={labelClass}>Req ID</label>
                <input className={inputClass} value={newReqId} onChange={e => setNewReqId(e.target.value)} placeholder="FUN-005" />
              </div>
              <div>
                <label className={labelClass}>Title</label>
                <input className={inputClass} value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="Requirement title" />
              </div>
              <div>
                <label className={labelClass}>Description</label>
                <textarea className={inputClass + " min-h-[60px]"} value={newText} onChange={e => setNewText(e.target.value)} />
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className={labelClass}>Type</label>
                  <select className={inputClass} value={newType} onChange={e => setNewType(e.target.value)}>
                    {REQ_TYPES.filter(t => t !== "all").map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className={labelClass}>Priority</label>
                  <select className={inputClass} value={newPriority} onChange={e => setNewPriority(e.target.value)}>
                    {PRIORITIES.filter(p => p !== "all").map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
                <div>
                  <label className={labelClass}>Verification</label>
                  <select className={inputClass} value={newVerification} onChange={e => setNewVerification(e.target.value)}>
                    {VERIFICATION_METHODS.map(v => <option key={v} value={v}>{v}</option>)}
                  </select>
                </div>
              </div>
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
              <Button onClick={handleAdd}>Add</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Filter bar */}
        <div className="flex flex-wrap gap-3">
          <FilterSelect label="Type" value={typeFilter} onChange={setTypeFilter} options={REQ_TYPES} />
          <FilterSelect label="Status" value={statusFilter} onChange={setStatusFilter} options={STATUSES} />
          <FilterSelect label="Priority" value={priorityFilter} onChange={setPriorityFilter} options={PRIORITIES} />
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-24">ID</TableHead>
              <TableHead>Title</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Verification</TableHead>
              <TableHead>Allocated To</TableHead>
              <TableHead className="w-20">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((r) => (
              <TableRow key={r.id}>
                <TableCell className="font-mono text-xs">{r.req_id}</TableCell>
                <TableCell className="font-medium">{r.title}</TableCell>
                <TableCell>
                  <Badge variant={typeColor(r.req_type)}>{r.req_type}</Badge>
                </TableCell>
                <TableCell>
                  {editingId === r.id ? (
                    <select className="rounded border border-border bg-background px-1 py-0.5 text-xs" value={editPriority || r.priority} onChange={e => setEditPriority(e.target.value)}>
                      {PRIORITIES.filter(p => p !== "all").map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                  ) : (
                    <span className="text-xs uppercase">{r.priority}</span>
                  )}
                </TableCell>
                <TableCell>
                  {editingId === r.id ? (
                    <select className="rounded border border-border bg-background px-1 py-0.5 text-xs" value={editStatus || r.status} onChange={e => setEditStatus(e.target.value)}>
                      {STATUSES.filter(s => s !== "all").map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  ) : (
                    <Badge variant={statusColor(r.status)}>{r.status}</Badge>
                  )}
                </TableCell>
                <TableCell className="text-xs">{r.verification_method}</TableCell>
                <TableCell className="text-muted-foreground text-xs">
                  {r.allocated_to ? allocationMap[r.allocated_to] ?? r.allocated_to : "\u2014"}
                </TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    {editingId === r.id ? (
                      <>
                        <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => handleInlineEdit(r.id)}>Save</Button>
                        <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => setEditingId(null)}>Cancel</Button>
                      </>
                    ) : (
                      <>
                        <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => { setEditingId(r.id); setEditStatus(r.status); setEditPriority(r.priority); }}>Edit</Button>
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

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: readonly string[];
}) {
  return (
    <div className="flex items-center gap-2">
      <label className="text-xs text-muted-foreground">{label}:</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-border bg-background px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o === "all" ? "All" : o.charAt(0).toUpperCase() + o.slice(1)}
          </option>
        ))}
      </select>
    </div>
  );
}
