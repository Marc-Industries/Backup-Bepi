"""Per-mission ECSS project data: review gates, deliverable status, tailoring.

This is the *project-data* layer (per-tenant, mutable) — it lives in Supabase
with RLS, unlike the shared corpus (bepi.ecss.corpus). It wires up the
`reviews` / `review_deliverables` tables and the `missions.ecss_tailoring`
jsonb field, all of which already existed in the schema but were never used by
the app. All access goes through the user-scoped client so RLS enforces
per-mission isolation (audit S4).
"""
from __future__ import annotations

from bepi.ecss import corpus


def _client():
    # Lazy so importing this module (e.g. in tests) doesn't pull in streamlit /
    # the supabase client. Tests patch this to inject a fake client.
    from bepi.supabase_client import get_supabase
    return get_supabase()

# reviews.phase_before / phase_after are NOT NULL and typed `phase` (ESA enum
# '0'..'F'). Map every review to a valid ESA phase pair so the row can always be
# created — independent of the UI phase selector (which may be NASA-style).
_REVIEW_PHASES = {
    "MDR": ("0", "A"), "PRR": ("A", "B1"), "SRR": ("B1", "B2"), "PDR": ("B2", "C"),
    "CDR": ("C", "D"), "QR": ("D", "E1"), "AR": ("D", "E1"), "ORR": ("E1", "E2"),
    "FRR": ("E1", "E2"), "LRR": ("E1", "E2"), "CRR": ("E2", "F"), "ELR": ("E2", "F"),
    "MCR": ("F", "F"),
}


# --- Review gates + deliverable status ------------------------------------

def load_review_gates(mission_id: str) -> dict:
    """Return {review_type: {"id","status","planned_date","deliverables":[...]}}
    for a mission. Empty dict if no client / not initialised."""
    client = _client()
    if not client or not mission_id:
        return {}
    reviews = (client.table("reviews")
               .select("id, review_type, status, planned_date, actual_date")
               .eq("mission_id", mission_id).execute().data) or []
    if not reviews:
        return {}
    ids = [r["id"] for r in reviews]
    dels = (client.table("review_deliverables")
            .select("id, review_id, drd_code, title, status, owner, due_date")
            .in_("review_id", ids).execute().data) or []
    by_review: dict[str, list] = {}
    for d in dels:
        by_review.setdefault(d["review_id"], []).append(d)
    out = {}
    for r in reviews:
        out[r["review_type"]] = {
            "id": r["id"], "status": r.get("status"),
            "planned_date": r.get("planned_date"), "actual_date": r.get("actual_date"),
            "deliverables": sorted(by_review.get(r["id"], []), key=lambda x: x.get("drd_code") or ""),
        }
    return out


def ensure_review(mission_id: str, review_type: str) -> str | None:
    """Get-or-create the `reviews` row for (mission, review_type). Returns id.
    phase_before/after are NOT NULL, so they are always supplied from the map."""
    client = _client()
    if not client or not mission_id or not review_type:
        return None
    existing = (client.table("reviews").select("id")
                .eq("mission_id", mission_id).eq("review_type", review_type)
                .execute().data)
    if existing:
        return existing[0]["id"]
    before, after = _REVIEW_PHASES.get(review_type, ("0", "A"))
    res = client.table("reviews").insert({
        "mission_id": mission_id, "review_type": review_type,
        "phase_before": before, "phase_after": after, "status": "not_ready",
    }).execute()
    return res.data[0]["id"] if res.data else None


def initialise_gate(mission_id: str, review_type: str, baseline: str | None = None) -> int:
    """Populate a review's expected deliverables from the corpus (Table A-1).
    Update-then-insert per DRD so re-running is idempotent. Returns count added."""
    client = _client()
    if not client:
        return 0
    review_id = ensure_review(mission_id, review_type)
    if not review_id:
        return 0
    existing = {d.get("drd_code") for d in
                (client.table("review_deliverables").select("drd_code")
                 .eq("review_id", review_id).execute().data or [])}
    added = 0
    for d in corpus.deliverables_for_review(review_type, baseline):
        if d["id"] in existing:
            continue
        client.table("review_deliverables").insert({
            "review_id": review_id, "drd_code": d["id"],
            "title": d["title"], "status": "not_started",
        }).execute()
        added += 1
    return added


def set_deliverable_status(deliverable_row_id: str, status: str, owner: str | None = None) -> None:
    client = _client()
    if not client or not deliverable_row_id:
        return
    upd = {"status": status}
    if owner is not None:
        upd["owner"] = owner
    client.table("review_deliverables").update(upd).eq("id", deliverable_row_id).execute()


def set_review_status(review_id: str, status: str) -> None:
    client = _client()
    if not client or not review_id:
        return
    client.table("reviews").update({"status": status}).eq("id", review_id).execute()


# --- Tailoring decisions (missions.ecss_tailoring jsonb) -------------------

def load_tailoring(mission_id: str) -> dict:
    """Return the stored tailoring object: {product_type, decisions:[{req,decision,rationale}]}."""
    client = _client()
    if not client or not mission_id:
        return {}
    row = (client.table("missions").select("ecss_tailoring")
           .eq("id", mission_id).execute().data)
    val = (row[0].get("ecss_tailoring") if row else None) or {}
    return val if isinstance(val, dict) else {}


def save_tailoring(mission_id: str, tailoring: dict) -> None:
    client = _client()
    if not client or not mission_id:
        return
    client.table("missions").update({"ecss_tailoring": tailoring}).eq("id", mission_id).execute()


def excluded_requirements(mission_id: str) -> set[str]:
    """Requirement ids the mission's tailoring marks NON APPLICABILE."""
    t = load_tailoring(mission_id)
    return {d["req"] for d in t.get("decisions", []) if d.get("decision") == "NON APPLICABILE"}
