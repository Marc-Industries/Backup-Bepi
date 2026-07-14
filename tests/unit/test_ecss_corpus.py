from bepi.ecss import corpus


def test_deliverables_loaded():
    d = corpus.deliverables()
    assert len(d) == 37
    ids = [x["id"] for x in d]
    assert len(ids) == len(set(ids)), "deliverable ids must be unique"
    for x in d:
        assert x["id"].startswith("DRD-")
        assert x["title"] and x["standard"] and x["reviews"]


def test_review_range_expansion():
    # SEP spans MDR..AR (Table A-1 "MDR -> AR") -> 7 reviews, no ORR/FRR.
    sep = corpus.deliverable_by_id("DRD-SEP")
    assert sep["reviews"] == ["MDR", "PRR", "SRR", "PDR", "CDR", "QR", "AR"]
    assert sep["called_by"] == ["5.1a", "5.3.4a"]


def test_deliverables_for_review():
    mdr = {d["id"] for d in corpus.deliverables_for_review("MDR")}
    assert {"DRD-MDD", "DRD-SCR", "DRD-SEP"} <= mdr
    assert "DRD-ICD" not in mdr  # ICD starts at SRR
    assert corpus.deliverables_for_review("PDR")  # non-empty


def test_reviews_in_corpus_order():
    r = corpus.reviews_in_corpus()
    assert r[0] == "MDR"
    assert r.index("PDR") < r.index("CDR") < r.index("MCR")


def test_tailoring_points():
    eq = corpus.tailoring_points("Space segment equipment")
    assert eq["decisions"] == 66
    assert len(eq["points"]) == 66
    assert corpus.tailoring_points("Space system")["decisions"] == 0
    assert "5.3.4a" in corpus.tailoring_points("Space segment element/sub-system")["points"]


def test_lessons_join_on_stable_ids():
    ll = [x["id"] for x in corpus.lessons_for_deliverable("DRD-VP")]
    assert ll == ["LL-001", "LL-002"]
    assert [x["id"] for x in corpus.lessons_for_deliverable("DRD-ICD")] == ["LL-002"]
    assert corpus.lessons_for_deliverable("DRD-TB") == []  # no lesson attached


def test_revision_present():
    assert "Rev.1" in corpus.current_revision()
    assert corpus.current_revision() in corpus.available_baselines()
