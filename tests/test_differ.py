from drift_sentinel.differ import aggregate_by_class, diff_runs, score_run

GOLDEN_SET = [
    {"id": "a1", "class": "code-generation", "check": {"expects_regex": "def foo"}},
    {"id": "a2", "class": "code-generation", "check": {"expects_regex": "def bar"}},
    {"id": "b1", "class": "summarization", "check": {"expects_keywords": ["revenue"]}},
    {"id": "b2", "class": "summarization", "check": {"expects_keywords": ["revenue"]}},
]


def test_score_run_marks_missing_response_as_failure():
    snapshot = {"a1": "def foo(): pass"}  # a2, b1, b2 missing
    scored = score_run(GOLDEN_SET, snapshot)
    by_id = {r["id"]: r for r in scored}
    assert by_id["a1"]["passed"] is True
    assert by_id["a2"]["passed"] is False
    assert "no response found" in by_id["a2"]["failures"][0]


def test_aggregate_by_class_computes_pass_rate():
    snapshot = {
        "a1": "def foo(): pass",
        "a2": "no code here",
        "b1": "revenue grew",
        "b2": "revenue grew",
    }
    scored = score_run(GOLDEN_SET, snapshot)
    rates = aggregate_by_class(scored)
    assert rates["code-generation"] == 50.0
    assert rates["summarization"] == 100.0


def test_diff_runs_reports_zero_drift_for_identical_snapshots():
    snapshot = {
        "a1": "def foo(): pass",
        "a2": "def bar(): pass",
        "b1": "revenue grew",
        "b2": "revenue grew",
    }
    scored = score_run(GOLDEN_SET, snapshot)
    rows = diff_runs(scored, scored, threshold=20)
    assert all(r["status"] == "ok" for r in rows)
    assert all(r["delta"] == 0.0 for r in rows)


def test_diff_runs_flags_regression_beyond_threshold():
    baseline_snapshot = {
        "a1": "def foo(): pass",
        "a2": "def bar(): pass",
        "b1": "revenue grew",
        "b2": "revenue grew",
    }
    candidate_snapshot = {
        "a1": "no code here",
        "a2": "no code here either",
        "b1": "revenue grew",
        "b2": "revenue grew",
    }
    baseline_scored = score_run(GOLDEN_SET, baseline_snapshot)
    candidate_scored = score_run(GOLDEN_SET, candidate_snapshot)
    rows = diff_runs(baseline_scored, candidate_scored, threshold=20)

    by_class = {r["class"]: r for r in rows}
    assert by_class["code-generation"]["status"] == "REGRESSED"
    assert by_class["code-generation"]["baseline"] == 100.0
    assert by_class["code-generation"]["candidate"] == 0.0
    assert by_class["summarization"]["status"] == "ok"


def test_diff_runs_does_not_flag_improvement():
    baseline_scored = score_run(GOLDEN_SET, {"a1": "no code", "a2": "no code", "b1": "x", "b2": "x"})
    candidate_scored = score_run(
        GOLDEN_SET, {"a1": "def foo(): pass", "a2": "def bar(): pass", "b1": "x", "b2": "x"}
    )
    rows = diff_runs(baseline_scored, candidate_scored, threshold=20)
    by_class = {r["class"]: r for r in rows}
    assert by_class["code-generation"]["status"] == "ok"
    assert by_class["code-generation"]["delta"] == 100.0


def test_diff_runs_respects_custom_threshold():
    baseline_scored = score_run(GOLDEN_SET, {"a1": "def foo(): pass", "a2": "def bar(): pass", "b1": "x", "b2": "x"})
    candidate_scored = score_run(GOLDEN_SET, {"a1": "def foo(): pass", "a2": "no code", "b1": "x", "b2": "x"})
    # delta is -50pp for code-generation
    loose = diff_runs(baseline_scored, candidate_scored, threshold=60)
    strict = diff_runs(baseline_scored, candidate_scored, threshold=10)
    assert {r["class"]: r["status"] for r in loose}["code-generation"] == "ok"
    assert {r["class"]: r["status"] for r in strict}["code-generation"] == "REGRESSED"
