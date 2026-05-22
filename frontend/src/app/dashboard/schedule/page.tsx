"use client"

import { useEffect, useMemo, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogClose,
} from "@/components/ui/dialog"
import { supabase } from "@/lib/supabase"
import { DEMO_TASKS } from "@/lib/mock-data"
import { resolveActiveMissionId } from "@/lib/active-mission"
import type { ScheduleTask } from "@/lib/types"

const inputClass = "w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
const labelClass = "text-xs font-medium text-muted-foreground"

type ScheduleTaskRow = {
  id: string
  mission_id: string
  name: string
  start_date: string
  end_date: string
  progress_pct: number | null
  assigned_to: string | null
  is_milestone: boolean | null
  created_at: string | null
}

function parseDate(d: string) { return new Date(d + "T00:00:00") }
function formatDate(d: string) {
  return new Date(d + "T00:00:00").toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
}

function monthsBetween(start: Date, end: Date) {
  const months: { label: string; date: Date }[] = []
  const cur = new Date(start.getFullYear(), start.getMonth(), 1)
  while (cur <= end) {
    months.push({ label: cur.toLocaleDateString("en-GB", { month: "short", year: "2-digit" }), date: new Date(cur) })
    cur.setMonth(cur.getMonth() + 1)
  }
  return months
}

function statusColor(task: ScheduleTask) {
  if (task.milestone) return "bg-purple-500"
  if (task.progress === 100) return "bg-emerald-500"
  if (task.progress > 0) return "bg-blue-500"
  return "bg-zinc-600"
}

function statusLabel(task: ScheduleTask) {
  if (task.milestone && task.progress === 100) return "Completed"
  if (task.milestone) return "Milestone"
  if (task.progress === 100) return "Completed"
  if (task.progress > 0) return "In Progress"
  return "Not Started"
}

function statusBadgeVariant(task: ScheduleTask): "default" | "secondary" | "outline" | "destructive" {
  if (task.progress === 100) return "default"
  if (task.progress > 0) return "secondary"
  return "outline"
}

export default function SchedulePage() {
  const [missionId, setMissionId] = useState<string | null>(null)
  const [tasks, setTasks] = useState<ScheduleTask[]>(DEMO_TASKS)

  useEffect(() => {
    (async () => {
      const activeId = await resolveActiveMissionId()
      setMissionId(activeId)
      if (!activeId) return

      const { data, error } = await supabase
        .from("schedule_tasks")
        .select("*")
        .eq("mission_id", activeId)
        .order("start_date", { ascending: true })

      if (error) return
      if (!data) return

      const mapped: ScheduleTask[] = (data as unknown as ScheduleTaskRow[]).map((r) => ({
        id: r.id,
        mission_id: r.mission_id,
        name: r.name,
        start_date: r.start_date,
        end_date: r.end_date,
        progress: r.progress_pct ?? 0,
        responsible: r.assigned_to ?? "",
        predecessors: [],
        milestone: r.is_milestone ?? false,
        created_at: r.created_at ?? "",
      }))

      // If the DB is empty for this mission, show an empty schedule instead of demo tasks.
      setTasks(mapped)
    })()
  }, [])

  const { timelineStart, months, totalDays } = useMemo(() => {
    if (tasks.length === 0) {
      const now = new Date()
      const s = new Date(now.getFullYear(), now.getMonth(), 1)
      const e = new Date(now.getFullYear(), now.getMonth() + 1, 0)
      return { timelineStart: s, months: monthsBetween(s, e), totalDays: 30 }
    }
    const starts = tasks.map((t) => parseDate(t.start_date))
    const ends = tasks.map((t) => parseDate(t.end_date))
    const min = new Date(Math.min(...starts.map((d) => d.getTime())))
    const max = new Date(Math.max(...ends.map((d) => d.getTime())))
    const s = new Date(min.getFullYear(), min.getMonth(), 1)
    const e = new Date(max.getFullYear(), max.getMonth() + 1, 0)
    const ms = monthsBetween(s, e)
    const total = (e.getTime() - s.getTime()) / (1000 * 60 * 60 * 24)
    return { timelineStart: s, months: ms, totalDays: total }
  }, [tasks])

  function dayOffset(dateStr: string) {
    const d = parseDate(dateStr)
    return ((d.getTime() - timelineStart.getTime()) / (1000 * 60 * 60 * 24) / totalDays) * 100
  }

  function dayWidth(startStr: string, endStr: string) {
    const s = parseDate(startStr)
    const e = parseDate(endStr)
    return (((e.getTime() - s.getTime()) / (1000 * 60 * 60 * 24)) / totalDays) * 100
  }

  const completed = tasks.filter((t) => t.progress === 100).length
  const inProgress = tasks.filter((t) => t.progress > 0 && t.progress < 100).length
  const milestones = tasks.filter((t) => t.milestone).length

  // Add task dialog
  const [addOpen, setAddOpen] = useState(false)
  const [newName, setNewName] = useState("")
  const [newStart, setNewStart] = useState("")
  const [newEnd, setNewEnd] = useState("")
  const [newResponsible, setNewResponsible] = useState("")
  const [newMilestone, setNewMilestone] = useState(false)

  // Inline edit
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editProgress, setEditProgress] = useState(0)

  async function handleAdd() {
    if (!newName || !newStart || !newEnd) { alert("Name, start and end dates are required"); return }
    if (!missionId) { alert("No mission found in Supabase"); return }
    const { error } = await supabase.from("schedule_tasks").insert({
      mission_id: missionId,
      name: newName,
      start_date: newStart,
      end_date: newEnd,
      assigned_to: newResponsible,
      is_milestone: newMilestone,
      progress_pct: 0,
    })
    if (error) { alert("Error: " + error.message); return }
    setAddOpen(false)
    window.location.reload()
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this task?")) return
    const { error } = await supabase.from("schedule_tasks").delete().eq("id", id)
    if (error) { alert("Error: " + error.message); return }
    window.location.reload()
  }

  async function handleProgressSave(id: string) {
    const { error } = await supabase.from("schedule_tasks").update({ progress_pct: editProgress }).eq("id", id)
    if (error) { alert("Error: " + error.message); return }
    setEditingId(null)
    window.location.reload()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Schedule</h1>
          <p className="text-muted-foreground text-sm mt-1">Mission timeline, milestones, and task progress</p>
        </div>
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogTrigger render={<Button size="sm" />}>+ Add Task</DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Add Task</DialogTitle>
            </DialogHeader>
            <div className="grid gap-3">
              <div>
                <label className={labelClass}>Name</label>
                <input className={inputClass} value={newName} onChange={e => setNewName(e.target.value)} placeholder="Task name" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className={labelClass}>Start Date</label>
                  <input type="date" className={inputClass} value={newStart} onChange={e => setNewStart(e.target.value)} />
                </div>
                <div>
                  <label className={labelClass}>End Date</label>
                  <input type="date" className={inputClass} value={newEnd} onChange={e => setNewEnd(e.target.value)} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className={labelClass}>Responsible</label>
                  <input className={inputClass} value={newResponsible} onChange={e => setNewResponsible(e.target.value)} placeholder="SE" />
                </div>
                <div className="flex items-end gap-2 pb-1">
                  <input type="checkbox" id="milestone" checked={newMilestone} onChange={e => setNewMilestone(e.target.checked)} className="rounded" />
                  <label htmlFor="milestone" className="text-sm">Milestone</label>
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

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card><CardContent className="pt-4 pb-4"><div className="text-2xl font-bold">{tasks.length}</div><div className="text-xs text-muted-foreground">Total Tasks</div></CardContent></Card>
        <Card><CardContent className="pt-4 pb-4"><div className="text-2xl font-bold text-emerald-400">{completed}</div><div className="text-xs text-muted-foreground">Completed</div></CardContent></Card>
        <Card><CardContent className="pt-4 pb-4"><div className="text-2xl font-bold text-blue-400">{inProgress}</div><div className="text-xs text-muted-foreground">In Progress</div></CardContent></Card>
        <Card><CardContent className="pt-4 pb-4"><div className="text-2xl font-bold text-purple-400">{milestones}</div><div className="text-xs text-muted-foreground">Milestones</div></CardContent></Card>
      </div>

      {/* Gantt Chart */}
      <Card>
        <CardHeader><CardTitle>Gantt Chart</CardTitle></CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <div className="relative h-8 mb-2 border-b border-border">
              {months.map((m, i) => {
                const left = ((m.date.getTime() - timelineStart.getTime()) / (1000 * 60 * 60 * 24) / totalDays) * 100
                return (
                  <div key={i} className="absolute text-[10px] text-muted-foreground font-medium" style={{ left: `${left}%` }}>{m.label}</div>
                )
              })}
            </div>
            <div className="space-y-1.5">
              {tasks.map((task) => {
                const left = dayOffset(task.start_date)
                const width = dayWidth(task.start_date, task.end_date)
                return (
                  <div key={task.id} className="flex items-center h-8 gap-3">
                    <div className="w-48 shrink-0 text-xs font-medium truncate text-foreground/80">
                      {task.milestone && <span className="text-purple-400 mr-1">&#9670;</span>}
                      {task.name}
                    </div>
                    <div className="relative flex-1 h-6">
                      {task.milestone ? (
                        <div className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rotate-45 bg-purple-500 border border-purple-400" style={{ left: `${left}%` }} />
                      ) : (
                        <div className={`absolute top-1/2 -translate-y-1/2 h-5 rounded-sm ${statusColor(task)}/20 border border-current/10`} style={{ left: `${left}%`, width: `${Math.max(width, 0.5)}%` }}>
                          <div className={`h-full rounded-sm ${statusColor(task)}`} style={{ width: `${task.progress}%` }} />
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
          <div className="flex gap-5 mt-6 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-emerald-500" /> Completed</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-blue-500" /> In Progress</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-zinc-600" /> Not Started</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rotate-45 bg-purple-500" /> Milestone</span>
          </div>
        </CardContent>
      </Card>

      {/* Task table */}
      <Card>
        <CardHeader><CardTitle>Task Details</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Start</TableHead>
                <TableHead>End</TableHead>
                <TableHead className="text-right">Progress</TableHead>
                <TableHead>Responsible</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="w-20">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasks.map((task) => (
                <TableRow key={task.id}>
                  <TableCell className="font-medium">
                    {task.milestone && <span className="text-purple-400 mr-1">&#9670;</span>}
                    {task.name}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-xs">{formatDate(task.start_date)}</TableCell>
                  <TableCell className="text-muted-foreground text-xs">{formatDate(task.end_date)}</TableCell>
                  <TableCell className="text-right">
                    {editingId === task.id ? (
                      <div className="flex items-center gap-2 justify-end">
                        <input type="range" min={0} max={100} value={editProgress} onChange={e => setEditProgress(Number(e.target.value))} className="w-20" />
                        <span className="text-xs tabular-nums w-8">{editProgress}%</span>
                      </div>
                    ) : (
                      <span className="tabular-nums">{task.progress}%</span>
                    )}
                  </TableCell>
                  <TableCell><Badge variant="outline">{task.responsible}</Badge></TableCell>
                  <TableCell><Badge variant={statusBadgeVariant(task)}>{statusLabel(task)}</Badge></TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {editingId === task.id ? (
                        <>
                          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => handleProgressSave(task.id)}>Save</Button>
                          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => setEditingId(null)}>Cancel</Button>
                        </>
                      ) : (
                        <>
                          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => { setEditingId(task.id); setEditProgress(task.progress) }}>Edit</Button>
                          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs text-red-400" onClick={() => handleDelete(task.id)}>Del</Button>
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
  )
}
