"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogClose,
} from "@/components/ui/dialog";

interface TeamMember {
  name: string;
  role: string;
  subsystem: string;
  org: string;
  email: string;
}

const INITIAL_TEAM: TeamMember[] = [
  { name: "Marco Rossi", role: "PM", subsystem: "Mission", org: "UniPD", email: "m.rossi@unipd.it" },
  { name: "Laura Bianchi", role: "SE", subsystem: "System", org: "UniPD", email: "l.bianchi@unipd.it" },
  { name: "Andrea Verdi", role: "SSL", subsystem: "ADCS", org: "UniPD", email: "a.verdi@unipd.it" },
  { name: "Sofia Conti", role: "SSL", subsystem: "EPS", org: "UniPD", email: "s.conti@unipd.it" },
  { name: "Luca Marino", role: "SSL", subsystem: "COM", org: "UniPD", email: "l.marino@unipd.it" },
  { name: "Giulia Ferrari", role: "SSL", subsystem: "OBC", org: "UniPD", email: "g.ferrari@unipd.it" },
  { name: "Davide Ricci", role: "SSL", subsystem: "TCS", org: "UniPD", email: "d.ricci@unipd.it" },
  { name: "Elena Romano", role: "SSL", subsystem: "STR", org: "UniPD", email: "e.romano@unipd.it" },
  { name: "Matteo Colombo", role: "SSL", subsystem: "Propulsion", org: "UniPD", email: "m.colombo@unipd.it" },
  { name: "Chiara Gallo", role: "SSL", subsystem: "Payload", org: "UniPD", email: "c.gallo@unipd.it" },
  { name: "Francesco Bruno", role: "QA", subsystem: "System", org: "UniPD", email: "f.bruno@unipd.it" },
  { name: "Alessia Greco", role: "AIT", subsystem: "AIT", org: "UniPD", email: "a.greco@unipd.it" },
  { name: "Simone Costa", role: "CM", subsystem: "System", org: "UniPD", email: "s.costa@unipd.it" },
];

const ROLES = ["PM", "SE", "SSL", "QA", "AIT", "CM"];
const SUBSYSTEMS = ["Mission", "System", "ADCS", "EPS", "COM", "OBC", "TCS", "STR", "Propulsion", "Payload", "AIT"];

const roleColor: Record<string, string> = {
  PM: "bg-purple-500/15 text-purple-400",
  SE: "bg-blue-500/15 text-blue-400",
  SSL: "bg-emerald-500/15 text-emerald-400",
  QA: "bg-amber-500/15 text-amber-400",
  AIT: "bg-orange-500/15 text-orange-400",
  CM: "bg-cyan-500/15 text-cyan-400",
};

const roleLabel: Record<string, string> = {
  PM: "Project Manager",
  SE: "Systems Engineer",
  SSL: "Subsystem Lead",
  QA: "Quality Assurance",
  AIT: "Assembly Integration & Test",
  CM: "Configuration Manager",
};

const inputClass = "w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring";
const labelClass = "text-xs font-medium text-muted-foreground";

export default function TeamPage() {
  const [team, setTeam] = useState<TeamMember[]>(INITIAL_TEAM);
  const [addOpen, setAddOpen] = useState(false);
  const [editingEmail, setEditingEmail] = useState<string | null>(null);
  const [editRole, setEditRole] = useState("");
  const [editSubsystem, setEditSubsystem] = useState("");

  // Add form
  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState("SSL");
  const [newSubsystem, setNewSubsystem] = useState("System");
  const [newOrg, setNewOrg] = useState("UniPD");
  const [newEmail, setNewEmail] = useState("");

  const roleCounts = team.reduce((acc, m) => { acc[m.role] = (acc[m.role] || 0) + 1; return acc; }, {} as Record<string, number>);

  function handleAdd() {
    if (!newName || !newEmail) { alert("Name and email are required"); return; }
    setTeam([...team, { name: newName, role: newRole, subsystem: newSubsystem, org: newOrg, email: newEmail }]);
    setAddOpen(false);
    setNewName(""); setNewEmail("");
  }

  function handleDelete(email: string) {
    if (!confirm("Remove this team member?")) return;
    setTeam(team.filter(m => m.email !== email));
  }

  function handleEditSave(email: string) {
    setTeam(team.map(m => m.email === email ? { ...m, role: editRole, subsystem: editSubsystem } : m));
    setEditingEmail(null);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Team</h1>
          <p className="text-muted-foreground mt-1">Mission team roster and role assignments</p>
        </div>
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogTrigger render={<Button size="sm" />}>+ Add Member</DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Add Team Member</DialogTitle>
            </DialogHeader>
            <div className="grid gap-3">
              <div>
                <label className={labelClass}>Name</label>
                <input className={inputClass} value={newName} onChange={e => setNewName(e.target.value)} placeholder="Full name" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className={labelClass}>Role</label>
                  <select className={inputClass} value={newRole} onChange={e => setNewRole(e.target.value)}>
                    {ROLES.map(r => <option key={r} value={r}>{r} - {roleLabel[r]}</option>)}
                  </select>
                </div>
                <div>
                  <label className={labelClass}>Subsystem</label>
                  <select className={inputClass} value={newSubsystem} onChange={e => setNewSubsystem(e.target.value)}>
                    {SUBSYSTEMS.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className={labelClass}>Organization</label>
                  <input className={inputClass} value={newOrg} onChange={e => setNewOrg(e.target.value)} />
                </div>
                <div>
                  <label className={labelClass}>Email</label>
                  <input className={inputClass} value={newEmail} onChange={e => setNewEmail(e.target.value)} placeholder="email@org.it" />
                </div>
              </div>
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
              <Button onClick={handleAdd}>Add</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        {Object.entries(roleCounts).map(([role, count]) => (
          <Card key={role}>
            <CardHeader className="pb-1 pt-3 px-4">
              <CardTitle className="text-xs text-muted-foreground">{roleLabel[role] || role}</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-3">
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold">{count}</span>
                <Badge variant="outline" className={roleColor[role]}>{role}</Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader><CardTitle>Team Roster</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Subsystem</TableHead>
                <TableHead>Organization</TableHead>
                <TableHead>Email</TableHead>
                <TableHead className="w-20">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {team.map((m) => (
                <TableRow key={m.email}>
                  <TableCell className="font-medium">{m.name}</TableCell>
                  <TableCell>
                    {editingEmail === m.email ? (
                      <select className="rounded border border-border bg-background px-1 py-0.5 text-xs" value={editRole} onChange={e => setEditRole(e.target.value)}>
                        {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                      </select>
                    ) : (
                      <Badge variant="outline" className={roleColor[m.role]}>{m.role}</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    {editingEmail === m.email ? (
                      <select className="rounded border border-border bg-background px-1 py-0.5 text-xs" value={editSubsystem} onChange={e => setEditSubsystem(e.target.value)}>
                        {SUBSYSTEMS.map(s => <option key={s} value={s}>{s}</option>)}
                      </select>
                    ) : (
                      m.subsystem
                    )}
                  </TableCell>
                  <TableCell>{m.org}</TableCell>
                  <TableCell className="font-mono text-xs">{m.email}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {editingEmail === m.email ? (
                        <>
                          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => handleEditSave(m.email)}>Save</Button>
                          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => setEditingEmail(null)}>Cancel</Button>
                        </>
                      ) : (
                        <>
                          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => { setEditingEmail(m.email); setEditRole(m.role); setEditSubsystem(m.subsystem); }}>Edit</Button>
                          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs text-red-400" onClick={() => handleDelete(m.email)}>Del</Button>
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
    </div>
  );
}
