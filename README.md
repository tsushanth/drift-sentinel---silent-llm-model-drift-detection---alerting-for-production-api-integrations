# Drift Sentinel

Silent LLM model-drift detection & alerting for production API integrations.

Providers routinely change model behavior behind a stable endpoint name and
version string. A prompt that used to return working code can start
returning prose; a prompt that used to return clean JSON can start
returning JSON wrapped in commentary; a borderline-but-legitimate request
can suddenly get refused. Nothing in your config changed, but your
production automations quietly break.

Drift Sentinel replays a curated **golden set** of representative prompts
against a live endpoint, scores each response with deterministic
heuristics (not another LLM call), and diffs the results against a
previous run. If a class of prompts (code-generation, json-extraction,
refusal-boundary, summarization, ...) regresses past a threshold, it
prints a console diff, writes a Markdown report, and raises an alert.

## What this MVP actually proves

The riskiest part of this idea isn't "can I call an LLM API" — any HTTP
client can do that. It's **the diff and scoring engine**: given two sets of
responses to the same prompts, can you reliably and deterministically tell
which prompt classes regressed? So this scaffold runs entirely **offline,
with zero API keys**, using two bundled canned response sets
(`fixtures/baseline_run.json` and `fixtures/drifted_run.json`) that stand
in for "before the provider changed something" and "after."

A live mode that calls a real OpenAI/Anthropic endpoint is included as a
thin optional path, but it is not required to see the tool work.

## Quickstart (offline demo, no API keys)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

python -m drift_sentinel demo
```

This loads `golden_set.yaml`, scores `fixtures/baseline_run.json` and
`fixtures/drifted_run.json` against it, diffs the two, and prints:

```
class             baseline  candidate  status
----------------  --------  ---------  ---------
code-generation   100%      20%        REGRESSED
json-extraction   100%      80%        ok
refusal-boundary  100%      100%       ok
summarization     80%       100%       ok

Wrote diff report to report.md

ALERT: drift detected
  code-generation regressed 100% -> 20% (threshold 20pp)
Appended alert to alerts.log
```

It also writes `report.md` (the diff view) and appends the alert text to
`alerts.log`. The command exits non-zero when a regression is detected, so
it's easy to wire into a CI job or cron script later.

## How scoring works

There is deliberately **no LLM-as-judge** in this MVP — that would require
also validating a second model's grading before you could trust the first
result. Instead, each golden-set prompt carries a `check` spec evaluated by
plain deterministic heuristics (`drift_sentinel/scorer.py`):

- `expects_json: true` — response must parse as valid JSON
- `expects_regex: "..."` — response must contain a regex match (e.g. a
  specific function signature)
- `expects_keywords: [...]` — response must contain every listed keyword
- `must_not_refuse: true` — response must not look like a refusal
- `min_length` / `max_length` — response length bounds

A prompt passes only if every check in its spec passes. Per-class pass
rates are aggregated and compared between two runs
(`drift_sentinel/differ.py`); a class is flagged `REGRESSED` if its pass
rate drops by more than the threshold (default 20 percentage points).

## Other commands

Run the golden set against a canned fixture and save a snapshot:

```bash
python -m drift_sentinel run --mode fixture --fixture fixtures/baseline_run.json --out runs/today.json
```

Compare any two run snapshots (e.g. today's live run vs. yesterday's):

```bash
python -m drift_sentinel compare fixtures/baseline_run.json runs/today.json --threshold 20
```

### Optional live mode

If you already have a provider API key exported in your shell, you can
replay the golden set against the real endpoint instead of a fixture:

```bash
export OPENAI_API_KEY=...
pip install -e ".[live]"

python -m drift_sentinel run --mode live --provider openai --out runs/today.json
python -m drift_sentinel compare fixtures/baseline_run.json runs/today.json
```

(`--provider anthropic` works the same way with `ANTHROPIC_API_KEY` set.)
The `openai`/`anthropic` SDKs are only imported inside this code path, so
the offline demo never needs them installed.

## Running tests

```bash
pip install -e ".[dev]"
pytest tests/
```

`scorer.py` and `differ.py` are pure functions over plain dicts, so they're
fully unit-tested without any network access or fixture files — including
a check that diffing two identical runs reports zero drift (no false
positives).

## What's intentionally not here

This is a local MVP scaffold, scoped to prove the detection mechanism —
see `plan.md` for the full reasoning. Explicitly out of scope for now:

- Auth, accounts, multi-tenancy, billing
- A hosted server or background scheduler (this is a CLI you invoke
  manually, or point a cron job / GitHub Action at later)
- Real Slack/email delivery (alerts are console output + `alerts.log`;
  swapping in a real Slack webhook is a one-line `requests.post` away)
- A web dashboard (the diff view is a console table + `report.md`)
- A database (run history is just JSON files under `runs/`)

## Layout

```
drift_sentinel/
├── cli.py       # entrypoint: demo / run / compare subcommands
├── runner.py    # loads the golden set, loads/saves snapshots, live-mode API calls
├── scorer.py    # per-prompt deterministic heuristics
├── differ.py    # per-class pass-rate aggregation + regression diff
├── report.py    # console table + report.md
└── alert.py     # alert message formatting + alerts.log
golden_set.yaml  # curated prompts with id/class/prompt/check
fixtures/        # canned "before" and "after" response sets for the offline demo
runs/            # generated run snapshots land here (gitignored)
tests/           # unit tests for scorer.py and differ.py
```
