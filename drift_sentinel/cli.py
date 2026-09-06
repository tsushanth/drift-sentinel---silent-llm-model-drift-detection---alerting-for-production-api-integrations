"""Drift Sentinel CLI: demo / run / compare subcommands."""

import argparse
import sys

from drift_sentinel import alert, report, runner
from drift_sentinel.differ import DEFAULT_REGRESSION_THRESHOLD, diff_runs, score_run


def _print_and_alert(diff_rows, threshold, report_path, alert_log_path):
    print(report.render_table(diff_rows))
    print()

    report.write_markdown_report(diff_rows, threshold, path=report_path)
    print(f"Wrote diff report to {report_path}")

    alert_text = alert.format_alert(diff_rows, threshold)
    if alert_text:
        print()
        print(alert_text)
        alert.append_alert_log(alert_text, path=alert_log_path)
        print(f"Appended alert to {alert_log_path}")
    else:
        print("No regressions detected — nothing to alert on.")

    return 1 if alert_text else 0


def cmd_demo(args):
    golden_set = runner.load_golden_set(args.golden)
    baseline_snapshot = runner.load_snapshot("fixtures/baseline_run.json")
    candidate_snapshot = runner.load_snapshot("fixtures/drifted_run.json")

    baseline_scored = score_run(golden_set, baseline_snapshot)
    candidate_scored = score_run(golden_set, candidate_snapshot)
    diff_rows = diff_runs(baseline_scored, candidate_scored, threshold=args.threshold)

    return _print_and_alert(diff_rows, args.threshold, args.report, args.alert_log)


def cmd_run(args):
    golden_set = runner.load_golden_set(args.golden)

    if args.mode == "fixture":
        snapshot = runner.load_snapshot(args.fixture)
    else:
        snapshot = runner.run_live(golden_set, provider=args.provider, model=args.model)

    runner.save_snapshot(snapshot, args.out)
    print(f"Wrote run snapshot ({len(snapshot)} responses) to {args.out}")
    return 0


def cmd_compare(args):
    golden_set = runner.load_golden_set(args.golden)
    baseline_snapshot = runner.load_snapshot(args.baseline)
    candidate_snapshot = runner.load_snapshot(args.candidate)

    baseline_scored = score_run(golden_set, baseline_snapshot)
    candidate_scored = score_run(golden_set, candidate_snapshot)
    diff_rows = diff_runs(baseline_scored, candidate_scored, threshold=args.threshold)

    return _print_and_alert(diff_rows, args.threshold, args.report, args.alert_log)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="drift_sentinel",
        description="Detect silent behavior drift in LLM API endpoints.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser(
        "demo", help="Run the offline demo: bundled golden set + canned before/after fixtures."
    )
    demo.add_argument("--golden", default="golden_set.yaml")
    demo.add_argument("--threshold", type=float, default=DEFAULT_REGRESSION_THRESHOLD)
    demo.add_argument("--report", default="report.md")
    demo.add_argument("--alert-log", default="alerts.log")
    demo.set_defaults(func=cmd_demo)

    run = subparsers.add_parser(
        "run", help="Execute the golden set and write a run snapshot (fixture or live)."
    )
    run.add_argument("--golden", default="golden_set.yaml")
    run.add_argument("--mode", choices=["fixture", "live"], default="fixture")
    run.add_argument("--fixture", help="Path to a canned response snapshot (mode=fixture).")
    run.add_argument("--provider", choices=["openai", "anthropic"], help="Required for mode=live.")
    run.add_argument("--model", help="Override the default model for the chosen provider.")
    run.add_argument("--out", required=True, help="Where to write the resulting run snapshot JSON.")
    run.set_defaults(func=cmd_run)

    compare = subparsers.add_parser(
        "compare", help="Score two run snapshots against the golden set and diff them."
    )
    compare.add_argument("baseline", help="Path to the baseline run snapshot JSON.")
    compare.add_argument("candidate", help="Path to the candidate run snapshot JSON.")
    compare.add_argument("--golden", default="golden_set.yaml")
    compare.add_argument("--threshold", type=float, default=DEFAULT_REGRESSION_THRESHOLD)
    compare.add_argument("--report", default="report.md")
    compare.add_argument("--alert-log", default="alerts.log")
    compare.set_defaults(func=cmd_compare)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run" and args.mode == "fixture" and not args.fixture:
        parser.error("--fixture is required when --mode=fixture")
    if args.command == "run" and args.mode == "live" and not args.provider:
        parser.error("--provider is required when --mode=live")

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
