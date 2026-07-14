"""gates.py against an in-memory fake Supabase client (no live DB needed)."""
import pytest

from bepi.ecss import gates, corpus


class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, store, table):
        self.store, self.table = store, table
        self._filters, self._op, self._payload = [], "select", None

    def select(self, *_a, **_k):
        self._op = "select"; return self

    def insert(self, payload):
        self._op, self._payload = "insert", payload; return self

    def update(self, payload):
        self._op, self._payload = "update", payload; return self

    def eq(self, k, v):
        self._filters.append(("eq", k, v)); return self

    def in_(self, k, vals):
        self._filters.append(("in", k, list(vals))); return self

    def _match(self, row):
        for kind, k, v in self._filters:
            if kind == "eq" and row.get(k) != v:
                return False
            if kind == "in" and row.get(k) not in v:
                return False
        return True

    def execute(self):
        rows = self.store.setdefault(self.table, [])
        if self._op == "select":
            return _Resp([dict(r) for r in rows if self._match(r)])
        if self._op == "insert":
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            out = []
            for p in payloads:
                r = dict(p)
                r.setdefault("id", f"{self.table}-{len(rows) + 1}")
                rows.append(r); out.append(dict(r))
            return _Resp(out)
        if self._op == "update":
            out = []
            for r in rows:
                if self._match(r):
                    r.update(self._payload); out.append(dict(r))
            return _Resp(out)
        return _Resp([])


class FakeClient:
    def __init__(self, store):
        self.store = store

    def table(self, name):
        return _Query(self.store, name)


@pytest.fixture
def fake(monkeypatch):
    store = {"missions": [{"id": "M1", "ecss_tailoring": None}]}
    monkeypatch.setattr(gates, "_client", lambda: FakeClient(store))
    return store


def test_initialise_gate_populates_and_is_idempotent(fake):
    expected = len(corpus.deliverables_for_review("PDR"))
    assert expected > 0
    added = gates.initialise_gate("M1", "PDR")
    assert added == expected
    assert len(fake["reviews"]) == 1
    assert fake["reviews"][0]["phase_before"] == "B2"  # PDR = B2->C, NOT NULL satisfied
    assert len(fake["review_deliverables"]) == expected
    # second run adds nothing
    assert gates.initialise_gate("M1", "PDR") == 0
    assert len(fake["review_deliverables"]) == expected


def test_load_review_gates_groups_deliverables(fake):
    gates.initialise_gate("M1", "PDR")
    loaded = gates.load_review_gates("M1")
    assert "PDR" in loaded
    assert loaded["PDR"]["status"] == "not_ready"
    assert len(loaded["PDR"]["deliverables"]) == len(corpus.deliverables_for_review("PDR"))


def test_set_deliverable_status(fake):
    gates.initialise_gate("M1", "PDR")
    row = fake["review_deliverables"][0]
    gates.set_deliverable_status(row["id"], "approved", owner="F. Toson")
    assert row["status"] == "approved"
    assert row["owner"] == "F. Toson"


def test_tailoring_roundtrip_and_exclusions(fake):
    payload = {"product_type": "Space segment equipment", "decisions": [
        {"req": "5.1a", "decision": "NON APPLICABILE", "rationale": "no heritage"},
        {"req": "5.3.4a", "decision": "APPLICABILE", "rationale": ""},
    ]}
    gates.save_tailoring("M1", payload)
    assert gates.load_tailoring("M1")["product_type"] == "Space segment equipment"
    assert gates.excluded_requirements("M1") == {"5.1a"}
