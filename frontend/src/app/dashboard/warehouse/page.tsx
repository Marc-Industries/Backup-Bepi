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

interface InventoryItem {
  name: string;
  pn: string;
  mait: string;
  qty: number;
  location: string;
  supplier: string;
  ordered: string;
  delivered: boolean;
}

const INITIAL_INVENTORY: InventoryItem[] = [
  { name: "Star Tracker", pn: "STR-2000", mait: "FM", qty: 2, location: "Clean Room A", supplier: "Sodern", ordered: "2025-05-01", delivered: true },
  { name: "Reaction Wheel", pn: "RW-400S", mait: "QM", qty: 4, location: "AIT Lab", supplier: "RocketLab", ordered: "2025-06-15", delivered: true },
  { name: "S-Band Transceiver", pn: "SBT-X100", mait: "EM", qty: 1, location: "RF Lab", supplier: "RUAG", ordered: "2025-07-01", delivered: true },
  { name: "EO Camera", pn: "CAM-HR5", mait: "BB", qty: 1, location: "Supplier", supplier: "Leonardo", ordered: "2025-04-01", delivered: false },
  { name: "Solar Panel Assembly", pn: "SA-3G30", mait: "QM", qty: 2, location: "Clean Room B", supplier: "Airbus DS", ordered: "2025-06-01", delivered: true },
  { name: "AF-M315E Thruster", pn: "GMP-T1", mait: "BB", qty: 1, location: "Supplier", supplier: "Aerojet", ordered: "2025-08-01", delivered: false },
  { name: "Li-Ion Battery Pack", pn: "BAT-28V60", mait: "EM", qty: 2, location: "EPS Lab", supplier: "SAFT", ordered: "2025-05-15", delivered: true },
  { name: "OBC Module", pn: "OBC-RAD750", mait: "QM", qty: 1, location: "Avionics Lab", supplier: "BAE Systems", ordered: "2025-04-15", delivered: true },
];

const MAIT_LEVELS = ["BB", "EM", "QM", "FM"] as const;

const maitColor: Record<string, string> = {
  BB: "bg-zinc-500/15 text-zinc-400",
  EM: "bg-blue-500/15 text-blue-400",
  QM: "bg-amber-500/15 text-amber-400",
  FM: "bg-emerald-500/15 text-emerald-400",
};

const inputClass = "w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring";
const labelClass = "text-xs font-medium text-muted-foreground";

export default function WarehousePage() {
  const [inventory, setInventory] = useState<InventoryItem[]>(INITIAL_INVENTORY);
  const [addOpen, setAddOpen] = useState(false);
  const [editingPn, setEditingPn] = useState<string | null>(null);
  const [editMait, setEditMait] = useState("");
  const [editLocation, setEditLocation] = useState("");
  const [editDelivered, setEditDelivered] = useState(false);

  // Add form
  const [newName, setNewName] = useState("");
  const [newPn, setNewPn] = useState("");
  const [newMait, setNewMait] = useState("BB");
  const [newQty, setNewQty] = useState(1);
  const [newLocation, setNewLocation] = useState("");
  const [newSupplier, setNewSupplier] = useState("");

  const delivered = inventory.filter(i => i.delivered).length;
  const pending = inventory.filter(i => !i.delivered).length;

  function handleAdd() {
    if (!newName || !newPn) { alert("Name and P/N are required"); return; }
    setInventory([...inventory, {
      name: newName,
      pn: newPn,
      mait: newMait,
      qty: newQty,
      location: newLocation,
      supplier: newSupplier,
      ordered: new Date().toISOString().slice(0, 10),
      delivered: false,
    }]);
    setAddOpen(false);
    setNewName(""); setNewPn(""); setNewLocation(""); setNewSupplier("");
  }

  function handleDelete(pn: string) {
    if (!confirm("Remove this item?")) return;
    setInventory(inventory.filter(i => i.pn !== pn));
  }

  function handleEditSave(pn: string) {
    setInventory(inventory.map(i => i.pn === pn ? { ...i, mait: editMait, location: editLocation, delivered: editDelivered } : i));
    setEditingPn(null);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Warehouse / MAIT</h1>
          <p className="text-muted-foreground mt-1">Component inventory, procurement and MAIT status tracking</p>
        </div>
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogTrigger render={<Button size="sm" />}>+ Add Item</DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Add Inventory Item</DialogTitle>
            </DialogHeader>
            <div className="grid gap-3">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className={labelClass}>Component Name</label>
                  <input className={inputClass} value={newName} onChange={e => setNewName(e.target.value)} placeholder="Component name" />
                </div>
                <div>
                  <label className={labelClass}>Part Number</label>
                  <input className={inputClass} value={newPn} onChange={e => setNewPn(e.target.value)} placeholder="XX-000" />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className={labelClass}>MAIT Status</label>
                  <select className={inputClass} value={newMait} onChange={e => setNewMait(e.target.value)}>
                    {MAIT_LEVELS.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
                <div>
                  <label className={labelClass}>Quantity</label>
                  <input type="number" min={1} className={inputClass} value={newQty} onChange={e => setNewQty(Number(e.target.value))} />
                </div>
                <div>
                  <label className={labelClass}>Supplier</label>
                  <input className={inputClass} value={newSupplier} onChange={e => setNewSupplier(e.target.value)} />
                </div>
              </div>
              <div>
                <label className={labelClass}>Location</label>
                <input className={inputClass} value={newLocation} onChange={e => setNewLocation(e.target.value)} placeholder="Clean Room A" />
              </div>
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
              <Button onClick={handleAdd}>Add</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Total Items</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold">{inventory.length}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Delivered</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold text-emerald-400">{delivered}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Pending</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold text-amber-400">{pending}</div></CardContent></Card>
        <Card><CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">At FM</CardTitle></CardHeader><CardContent><div className="text-2xl font-bold text-blue-400">{inventory.filter(i => i.mait === "FM").length}</div></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Component Inventory</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Component</TableHead>
                <TableHead>P/N</TableHead>
                <TableHead>MAIT</TableHead>
                <TableHead>Qty</TableHead>
                <TableHead>Location</TableHead>
                <TableHead>Supplier</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-20">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {inventory.map((item) => (
                <TableRow key={item.pn}>
                  <TableCell className="font-medium">{item.name}</TableCell>
                  <TableCell className="font-mono text-xs">{item.pn}</TableCell>
                  <TableCell>
                    {editingPn === item.pn ? (
                      <select className="rounded border border-border bg-background px-1 py-0.5 text-xs" value={editMait} onChange={e => setEditMait(e.target.value)}>
                        {MAIT_LEVELS.map(m => <option key={m} value={m}>{m}</option>)}
                      </select>
                    ) : (
                      <Badge variant="outline" className={maitColor[item.mait]}>{item.mait}</Badge>
                    )}
                  </TableCell>
                  <TableCell>{item.qty}</TableCell>
                  <TableCell>
                    {editingPn === item.pn ? (
                      <input className="w-28 rounded border border-border bg-background px-1 py-0.5 text-xs" value={editLocation} onChange={e => setEditLocation(e.target.value)} />
                    ) : (
                      item.location
                    )}
                  </TableCell>
                  <TableCell>{item.supplier}</TableCell>
                  <TableCell>
                    {editingPn === item.pn ? (
                      <label className="flex items-center gap-1 text-xs">
                        <input type="checkbox" checked={editDelivered} onChange={e => setEditDelivered(e.target.checked)} className="rounded" />
                        Delivered
                      </label>
                    ) : (
                      item.delivered
                        ? <Badge variant="outline" className="bg-emerald-500/15 text-emerald-400">Delivered</Badge>
                        : <Badge variant="outline" className="bg-amber-500/15 text-amber-400">Pending</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {editingPn === item.pn ? (
                        <>
                          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => handleEditSave(item.pn)}>Save</Button>
                          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => setEditingPn(null)}>Cancel</Button>
                        </>
                      ) : (
                        <>
                          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => { setEditingPn(item.pn); setEditMait(item.mait); setEditLocation(item.location); setEditDelivered(item.delivered); }}>Edit</Button>
                          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs text-red-400" onClick={() => handleDelete(item.pn)}>Del</Button>
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
