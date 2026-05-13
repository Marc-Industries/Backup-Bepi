import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import select, text

from bepi.core.enums import BudgetType, Phase
from bepi.core.models.budget import BudgetAllocation, BudgetLimit
from bepi.core.models.mission import Mission
from bepi.core.models.product_tree import ProductNode
from bepi.db.session import AsyncSessionLocal
from bepi.ecss.margins import get_component_margin, get_system_margin
from bepi.services.product_tree import ProductNodeData, build_tree

app = typer.Typer(no_args_is_help=True)
mission_app = typer.Typer(no_args_is_help=True)
tree_app = typer.Typer(no_args_is_help=True)
budget_app = typer.Typer(no_args_is_help=True)
report_app = typer.Typer(no_args_is_help=True)

app.add_typer(mission_app, name="mission")
app.add_typer(tree_app, name="tree")
app.add_typer(budget_app, name="budget")
app.add_typer(report_app, name="report")

console = Console()


@mission_app.command("list")
def mission_list():
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Mission).order_by(Mission.id))
            missions = result.scalars().all()
        return missions

    missions = asyncio.run(_run())

    table = Table(title="Missions")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Phase")
    table.add_column("Orbit")
    table.add_column("Customer")

    for m in missions:
        table.add_row(
            str(m.id),
            m.name,
            m.phase.value if m.phase else "-",
            m.orbit_type or "-",
            m.customer or "-",
        )

    console.print(table)


@mission_app.command("create")
def mission_create(
    name: str = typer.Option(..., "--name"),
    phase: Optional[Phase] = typer.Option(None, "--phase"),
    orbit_type: Optional[str] = typer.Option(None, "--orbit-type"),
):
    async def _run():
        async with AsyncSessionLocal() as db:
            m = Mission(name=name, phase=phase, orbit_type=orbit_type)
            db.add(m)
            await db.commit()
            await db.refresh(m)
            return m

    m = asyncio.run(_run())
    console.print(f"[green]Created mission[/green] id={m.id} name={m.name!r}")


@mission_app.command("show")
def mission_show(mission_id: int = typer.Argument(...)):
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Mission).where(Mission.id == mission_id))
            return result.scalar_one_or_none()

    m = asyncio.run(_run())
    if m is None:
        console.print(f"[red]Mission {mission_id} not found[/red]")
        raise typer.Exit(1)

    table = Table(show_header=False, title=f"Mission {m.id}")
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("ID", str(m.id))
    table.add_row("Name", m.name)
    table.add_row("Phase", m.phase.value if m.phase else "-")
    table.add_row("Orbit Type", m.orbit_type or "-")
    table.add_row("Customer", m.customer or "-")
    table.add_row("Prime Contractor", m.prime_contractor or "-")
    table.add_row("Target Launch", str(m.target_launch_date) if m.target_launch_date else "-")
    table.add_row("Description", m.description or "-")
    console.print(table)


def _render_tree(node: ProductNodeData, prefix: str = "", is_last: bool = True):
    connector = "└── " if is_last else "├── "
    label = f"[{node.level}] {node.code} — {node.name}"
    if node.quantity > 1:
        label += f" ×{node.quantity}"
    console.print(f"{prefix}{connector}{label}")
    child_prefix = prefix + ("    " if is_last else "│   ")
    for i, child in enumerate(node.children):
        _render_tree(child, child_prefix, i == len(node.children) - 1)


@tree_app.command("show")
def tree_show(mission_id: int = typer.Argument(...)):
    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ProductNode).where(ProductNode.mission_id == mission_id).order_by(ProductNode.id)
            )
            nodes = result.scalars().all()
        return nodes

    nodes = asyncio.run(_run())
    if not nodes:
        console.print(f"[yellow]No product tree nodes for mission {mission_id}[/yellow]")
        raise typer.Exit(0)

    raw = [
        {
            "id": n.id,
            "code": n.code,
            "name": n.name,
            "level": n.level.value if hasattr(n.level, "value") else n.level,
            "parent_id": n.parent_id,
            "subsystem_type": n.subsystem_type.value if n.subsystem_type and hasattr(n.subsystem_type, "value") else n.subsystem_type,
            "quantity": n.quantity,
        }
        for n in nodes
    ]

    root = build_tree(raw)
    if root is None:
        console.print("[red]Could not build tree (no root node found)[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Product Tree — Mission {mission_id}[/bold]")
    console.print(f"[bold]{root.code} — {root.name}[/bold]")
    for i, child in enumerate(root.children):
        _render_tree(child, "", i == len(root.children) - 1)
    console.print()


@budget_app.command("summary")
def budget_summary(
    mission_id: int = typer.Argument(...),
    budget_type: BudgetType = typer.Option(BudgetType.MASS_KG, "--type", "-t"),
):
    async def _run():
        async with AsyncSessionLocal() as db:
            mission_result = await db.execute(select(Mission).where(Mission.id == mission_id))
            mission = mission_result.scalar_one_or_none()
            if mission is None:
                return None, [], None

            nodes_result = await db.execute(
                select(ProductNode).where(ProductNode.mission_id == mission_id)
            )
            nodes = nodes_result.scalars().all()

            alloc_node_ids = [n.id for n in nodes]
            allocs = []
            if alloc_node_ids:
                alloc_result = await db.execute(
                    select(BudgetAllocation).where(
                        BudgetAllocation.node_id.in_(alloc_node_ids),
                        BudgetAllocation.budget_type == budget_type,
                    )
                )
                allocs = alloc_result.scalars().all()

            limit_result = await db.execute(
                select(BudgetLimit).where(
                    BudgetLimit.mission_id == mission_id,
                    BudgetLimit.budget_type == budget_type,
                )
            )
            limit = limit_result.scalar_one_or_none()

        return mission, nodes, allocs, limit

    mission, nodes, allocs, limit = asyncio.run(_run())

    if mission is None:
        console.print(f"[red]Mission {mission_id} not found[/red]")
        raise typer.Exit(1)

    phase = mission.phase.value if mission.phase else "B1"

    node_map = {n.id: n for n in nodes}

    subsystem_nodes = [n for n in nodes if (n.level.value if hasattr(n.level, "value") else n.level) == "subsystem"]
    if not subsystem_nodes:
        subsystem_nodes = [n for n in nodes if n.parent_id is None or not any(
            nn.parent_id == n.parent_id for nn in nodes if nn.id != n.id
        )]

    alloc_by_node: dict[int, list] = {}
    for a in allocs:
        alloc_by_node.setdefault(a.node_id, []).append(a)

    def get_descendants(node_id: int) -> list[int]:
        result = [node_id]
        for n in nodes:
            if n.parent_id == node_id:
                result.extend(get_descendants(n.id))
        return result

    table = Table(title=f"Budget Summary — Mission {mission_id} — {budget_type.value} — Phase {phase}")
    table.add_column("Subsystem", style="cyan")
    table.add_column("Name")
    table.add_column("Nominal", justify="right")
    table.add_column("+Margin", justify="right")
    table.add_column("Margin %", justify="right")

    subtotal_nominal = 0.0
    subtotal_margin = 0.0

    for ss in subsystem_nodes:
        desc_ids = get_descendants(ss.id)
        nominal = 0.0
        with_margin = 0.0
        for nid in desc_ids:
            for a in alloc_by_node.get(nid, []):
                node = node_map[nid]
                qty = node.quantity
                margin = a.margin_pct if a.margin_pct > 0 else get_component_margin(phase, a.maturity.value if hasattr(a.maturity, "value") else a.maturity)
                nominal += a.nominal_value * qty
                with_margin += a.nominal_value * (1 + margin / 100) * qty

        margin_pct = ((with_margin / nominal - 1) * 100) if nominal > 0 else 0.0
        subtotal_nominal += nominal
        subtotal_margin += with_margin

        ss_code = ss.code
        ss_name = ss.name
        table.add_row(ss_code, ss_name, f"{nominal:.2f}", f"{with_margin:.2f}", f"{margin_pct:.1f}%")

    table.add_section()
    table.add_row("[bold]Subtotal[/bold]", "", f"[bold]{subtotal_nominal:.2f}[/bold]", f"[bold]{subtotal_margin:.2f}[/bold]", "")

    sys_margin = get_system_margin(phase)
    total = subtotal_margin * (1 + sys_margin / 100)
    table.add_row(f"[bold]System Margin ({sys_margin}%)[/bold]", "", "", f"[bold]{total:.2f}[/bold]", "")

    if limit:
        remaining = limit.limit_value - total
        pct = (remaining / limit.limit_value * 100) if limit.limit_value > 0 else 0
        status_color = "green" if pct >= 20 else ("yellow" if pct >= 10 else "red")
        table.add_row(
            f"[bold]Limit[/bold]",
            "",
            "",
            f"[bold]{limit.limit_value:.2f}[/bold]",
            f"[{status_color}]{pct:.1f}% remaining[/{status_color}]",
        )

    console.print(table)


@report_app.command("generate")
def report_generate(
    mission_id: int = typer.Argument(...),
    report_type: str = typer.Argument(...),
):
    console.print(f"[yellow]Report generation not yet implemented.[/yellow]")
    console.print(f"  mission_id={mission_id}, type={report_type!r}")
