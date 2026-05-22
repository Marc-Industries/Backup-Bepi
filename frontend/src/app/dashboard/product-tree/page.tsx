"use client"

import { useEffect, useMemo, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog"
import { supabase } from "@/lib/supabase"
import { DEMO_PRODUCT_TREE } from "@/lib/mock-data"
import type { ProductTreeNode } from "@/lib/types"
import { resolveActiveMissionId } from "@/lib/active-mission"

const NODE_TYPES = ["spacecraft", "subsystem", "equipment", "component"] as const

const inputClass = "w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
const labelClass = "text-xs font-medium text-muted-foreground"

type ProductTreeNodeRow = {
  id: string
  mission_id: string
  parent_id: string | null
  name: string
  level: string
  trl: number | null
  quantity: number | null
  created_at: string | null
}

function trlColor(trl: number) {
  if (trl >= 8) return "text-emerald-400"
  if (trl >= 6) return "text-yellow-400"
  if (trl >= 4) return "text-orange-400"
  return "text-red-400"
}

function typeColor(type: ProductTreeNode["node_type"]) {
  switch (type) {
    case "spacecraft": return "bg-blue-500/15 text-blue-400 border-blue-500/30"
    case "subsystem": return "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
    case "equipment": return "bg-orange-500/15 text-orange-400 border-orange-500/30"
    case "component": return "bg-zinc-500/15 text-zinc-400 border-zinc-500/30"
  }
}

function buildTree(nodes: ProductTreeNode[]) {
  const map = new Map<string | null, ProductTreeNode[]>()
  for (const n of nodes) {
    const kids = map.get(n.parent_id) ?? []
    kids.push(n)
    map.set(n.parent_id, kids)
  }
  return map
}

function TreeNode({
  node,
  childrenMap,
  depth,
  selected,
  onSelect,
}: {
  node: ProductTreeNode
  childrenMap: Map<string | null, ProductTreeNode[]>
  depth: number
  selected: string | null
  onSelect: (id: string) => void
}) {
  const [expanded, setExpanded] = useState(true)
  const children = childrenMap.get(node.id) ?? []
  const hasChildren = children.length > 0
  const isSelected = selected === node.id

  return (
    <div>
      <div
        className={`flex items-center gap-2 px-3 py-2 rounded-md cursor-pointer transition-colors hover:bg-muted/50 ${
          isSelected ? "bg-muted ring-1 ring-ring/20" : ""
        }`}
        style={{ paddingLeft: `${depth * 24 + 12}px` }}
        onClick={() => onSelect(node.id)}
      >
        {hasChildren ? (
          <button
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded) }}
            className="w-5 h-5 flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
          >
            <span className={`text-xs transition-transform ${expanded ? "rotate-90" : ""}`}>&#9654;</span>
          </button>
        ) : (
          <span className="w-5" />
        )}

        <div className="flex items-center gap-3 flex-1 min-w-0">
          <span className="font-medium text-sm truncate">{node.name}</span>
          <Badge variant="outline" className={`text-[10px] shrink-0 ${typeColor(node.node_type)}`}>{node.node_type}</Badge>
        </div>

        {node.node_type === "equipment" && (
          <div className="flex items-center gap-4 text-xs text-muted-foreground shrink-0">
            <span>{node.mass_kg} kg</span>
            <span>{node.power_w} W</span>
            <span className={`font-mono font-bold ${trlColor(node.trl)}`}>TRL {node.trl}</span>
            {node.mait_status && (
              <Badge variant="secondary" className="text-[10px]">{node.mait_status}</Badge>
            )}
          </div>
        )}
      </div>

      {hasChildren && expanded && (
        <div>
          {children.map((child) => (
            <TreeNode key={child.id} node={child} childrenMap={childrenMap} depth={depth + 1} selected={selected} onSelect={onSelect} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function ProductTreePage() {
  const [missionId, setMissionId] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [tree, setTree] = useState<ProductTreeNode[]>(DEMO_PRODUCT_TREE)

  useEffect(() => {
    (async () => {
      const activeId = await resolveActiveMissionId()
      setMissionId(activeId)
      if (!activeId) return

      const { data, error } = await supabase
        .from("product_tree_nodes")
        .select("*")
        .eq("mission_id", activeId)
        .order("created_at", { ascending: true })

      if (error) return
      if (!data) return

      const mapped: ProductTreeNode[] = (data as unknown as ProductTreeNodeRow[]).map((r) => ({
        id: r.id,
        mission_id: r.mission_id,
        parent_id: r.parent_id ?? null,
        name: r.name,
        node_type: r.level === "satellite" ? "spacecraft" : (r.level as ProductTreeNode["node_type"]),
        mass_kg: 0,
        power_w: 0,
        qty: r.quantity ?? 1,
        maturity_margin: 0,
        trl: r.trl ?? 0,
        mait_status: null,
        created_at: r.created_at ?? "",
      }))

      setTree(mapped)
    })()
  }, [])

  const childrenMap = useMemo(() => buildTree(tree), [tree])
  const roots = childrenMap.get(null) ?? []

  const equipment = tree.filter((n) => n.node_type === "equipment")
  const totalNodes = tree.length
  const avgTrl = equipment.length > 0
    ? Math.round((equipment.reduce((s, e) => s + e.trl, 0) / equipment.length) * 10) / 10
    : 0

  const selectedNode = selected ? tree.find((n) => n.id === selected) : null

  // Add node dialog
  const [addOpen, setAddOpen] = useState(false)
  const [newName, setNewName] = useState("")
  const [newType, setNewType] = useState<string>("equipment")
  const [newParent, setNewParent] = useState<string>(tree[0]?.id ?? "")
  const [newTrl, setNewTrl] = useState(5)
  const [newQty, setNewQty] = useState(1)
  const [newMass, setNewMass] = useState(0)

  // Edit mode
  const [editing, setEditing] = useState(false)
  const [editName, setEditName] = useState("")
  const [editTrl, setEditTrl] = useState(0)
  const [editQty, setEditQty] = useState(1)

  async function handleAdd() {
    if (!newName) { alert("Name is required"); return }
    if (!missionId) { alert("No mission found in Supabase"); return }
    const { error } = await supabase.from("product_tree_nodes").insert({
      mission_id: missionId,
      name: newName,
      level: newType === "spacecraft" ? "satellite" : newType,
      parent_id: newParent || null,
      trl: newTrl,
      quantity: newQty,
    })
    if (error) { alert("Error: " + error.message); return }
    setAddOpen(false)
    window.location.reload()
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this node and all children?")) return
    const { error } = await supabase.from("product_tree_nodes").delete().eq("id", id)
    if (error) { alert("Error: " + error.message); return }
    window.location.reload()
  }

  async function handleEditSave() {
    if (!selectedNode) return
    const { error } = await supabase.from("product_tree_nodes").update({
      name: editName,
      trl: editTrl,
      quantity: editQty,
    }).eq("id", selectedNode.id)
    if (error) { alert("Error: " + error.message); return }
    setEditing(false)
    window.location.reload()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Product Tree</h1>
          <p className="text-muted-foreground text-sm mt-1">Spacecraft hardware breakdown structure</p>
        </div>
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogTrigger render={<Button size="sm" />}>+ Add Node</DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Add Node</DialogTitle>
            </DialogHeader>
            <div className="grid gap-3">
              <div>
                <label className={labelClass}>Name</label>
                <input className={inputClass} value={newName} onChange={e => setNewName(e.target.value)} placeholder="Node name" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className={labelClass}>Level</label>
                  <select className={inputClass} value={newType} onChange={e => setNewType(e.target.value)}>
                    {NODE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className={labelClass}>Parent</label>
                  <select className={inputClass} value={newParent} onChange={e => setNewParent(e.target.value)}>
                    <option value="">(root)</option>
                    {tree.map(n => <option key={n.id} value={n.id}>{n.name}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className={labelClass}>TRL</label>
                  <input type="number" min={1} max={9} className={inputClass} value={newTrl} onChange={e => setNewTrl(Number(e.target.value))} />
                </div>
                <div>
                  <label className={labelClass}>Quantity</label>
                  <input type="number" min={1} className={inputClass} value={newQty} onChange={e => setNewQty(Number(e.target.value))} />
                </div>
                <div>
                  <label className={labelClass}>Mass (kg)</label>
                  <input type="number" min={0} step={0.1} className={inputClass} value={newMass} onChange={e => setNewMass(Number(e.target.value))} />
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

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="text-2xl font-bold">{totalNodes}</div>
            <div className="text-xs text-muted-foreground">Total Nodes</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="text-2xl font-bold text-orange-400">{equipment.length}</div>
            <div className="text-xs text-muted-foreground">Equipment Items</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className={`text-2xl font-bold ${trlColor(avgTrl)}`}>{avgTrl}</div>
            <div className="text-xs text-muted-foreground">Avg TRL</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tree */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Hierarchy</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-border/50">
              {roots.map((root) => (
                <TreeNode key={root.id} node={root} childrenMap={childrenMap} depth={0} selected={selected} onSelect={setSelected} />
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Detail panel */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Details</CardTitle>
            {selectedNode && !editing && (
              <div className="flex gap-1">
                <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => { setEditing(true); setEditName(selectedNode.name); setEditTrl(selectedNode.trl); setEditQty(selectedNode.qty); }}>Edit</Button>
                <Button variant="ghost" size="sm" className="h-7 text-xs text-red-400" onClick={() => handleDelete(selectedNode.id)}>Delete</Button>
              </div>
            )}
          </CardHeader>
          <CardContent>
            {selectedNode ? (
              editing ? (
                <div className="space-y-3">
                  <div>
                    <label className={labelClass}>Name</label>
                    <input className={inputClass} value={editName} onChange={e => setEditName(e.target.value)} />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className={labelClass}>TRL</label>
                      <input type="number" min={1} max={9} className={inputClass} value={editTrl} onChange={e => setEditTrl(Number(e.target.value))} />
                    </div>
                    <div>
                      <label className={labelClass}>Quantity</label>
                      <input type="number" min={1} className={inputClass} value={editQty} onChange={e => setEditQty(Number(e.target.value))} />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" onClick={handleEditSave}>Save</Button>
                    <Button variant="outline" size="sm" onClick={() => setEditing(false)}>Cancel</Button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <h3 className="font-semibold text-lg">{selectedNode.name}</h3>
                    <Badge variant="outline" className={`mt-1 ${typeColor(selectedNode.node_type)}`}>{selectedNode.node_type}</Badge>
                  </div>

                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-muted-foreground block text-xs">Mass</span>
                      <span className="font-mono font-medium">{selectedNode.mass_kg} kg</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-xs">Power</span>
                      <span className="font-mono font-medium">{selectedNode.power_w} W</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-xs">Quantity</span>
                      <span className="font-mono font-medium">{selectedNode.qty}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-xs">Maturity Margin</span>
                      <span className="font-mono font-medium">{selectedNode.maturity_margin}%</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-xs">TRL</span>
                      <span className={`font-mono font-bold ${trlColor(selectedNode.trl)}`}>{selectedNode.trl || "N/A"}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-xs">MAIT Status</span>
                      {selectedNode.mait_status ? (
                        <Badge variant="secondary">{selectedNode.mait_status}</Badge>
                      ) : (
                        <span className="text-muted-foreground">--</span>
                      )}
                    </div>
                  </div>

                  {selectedNode.trl > 0 && (
                    <div>
                      <span className="text-xs text-muted-foreground">TRL Progress</span>
                      <div className="mt-1 h-2 w-full rounded-full bg-muted overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            selectedNode.trl >= 8 ? "bg-emerald-500" : selectedNode.trl >= 6 ? "bg-yellow-500" : "bg-orange-500"
                          }`}
                          style={{ width: `${(selectedNode.trl / 9) * 100}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )
            ) : (
              <p className="text-muted-foreground text-sm">Select a node to view details</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
