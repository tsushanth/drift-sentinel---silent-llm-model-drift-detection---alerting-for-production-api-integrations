"""Aggregate per-prompt scores into per-class pass rates, and diff two runs."""

from drift_sentinel.scorer import score_response

DEFAULT_REGRESSION_THRESHOLD = 20  # percentage points


def score_run(golden_set: list, run_snapshot: dict) -> list:
    """Score every prompt in `golden_set` against its response in
    `run_snapshot` (a dict of prompt id -> response text).

    Returns a list of per-prompt result dicts: id, class, passed, failures.
    Missing responses are scored as failures rather than skipped, since a
    prompt an endpoint no longer answers at all is itself a drift signal.
    """
    results = []
    for entry in golden_set:
        response = run_snapshot.get(entry["id"])
        if response is None:
            results.append(
                {
                    "id": entry["id"],
                    "class": entry["class"],
                    "passed": False,
                    "failures": ["no response found in run snapshot"],
                }
            )
            continue
        score = score_response(entry.get("check", {}), response)
        results.append(
            {
                "id": entry["id"],
                "class": entry["class"],
                "passed": score["passed"],
                "failures": score["failures"],
            }
        )
    return results


def aggregate_by_class(scored_results: list) -> dict:
    """Collapse per-prompt results into a per-class pass rate (0-100)."""
    totals = {}
    passes = {}
    for r in scored_results:
        cls = r["class"]
        totals[cls] = totals.get(cls, 0) + 1
        if r["passed"]:
            passes[cls] = passes.get(cls, 0) + 1
    return {
        cls: round(100 * passes.get(cls, 0) / total, 1) for cls, total in totals.items()
    }


def diff_runs(
    baseline_scored: list,
    candidate_scored: list,
    threshold: float = DEFAULT_REGRESSION_THRESHOLD,
) -> list:
    """Compare two scored runs class-by-class.

    Returns a list of rows: class, baseline (pct), candidate (pct), delta,
    status ("REGRESSED" if the pass rate dropped by more than `threshold`
    percentage points, else "ok"). Sorted by class name for stable output.
    """
    baseline_rates = aggregate_by_class(baseline_scored)
    candidate_rates = aggregate_by_class(candidate_scored)

    classes = sorted(set(baseline_rates) | set(candidate_rates))
    rows = []
    for cls in classes:
        baseline_pct = baseline_rates.get(cls, 0.0)
        candidate_pct = candidate_rates.get(cls, 0.0)
        delta = round(candidate_pct - baseline_pct, 1)
        status = "REGRESSED" if -delta > threshold else "ok"
        rows.append(
            {
                "class": cls,
                "baseline": baseline_pct,
                "candidate": candidate_pct,
                "delta": delta,
                "status": status,
            }
        )
    return rows
