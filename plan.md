# Drift Sentinel — Local MVP Scaffold Plan

## Core value being proven

Given a "golden set" of representative prompts, detect when an LLM
endpoint's *behavior* has silently changed (format compliance, refusal
rate, task completion) even though nothing in the endpoint name/version
string changed — and produce a diff view + an alert message showing
exactly which prompt classes regressed.

The riskiest/most valuable thing to prove locally is the **diff and
scoring engine**, not the act of calling a live API (any HTTP client can
do that). So the MVP is built so the whole pipeline runs **offline, with
zero API keys**, using two bundled canned response sets that stand in for
"before the provider changed something" and "after." A live mode (hitting
a real OpenAI/Anthropic key) is included as a thin optional path, but the
default demo never needs one.

## Stack

**Python 3 CLI, stdlib-first.**

- No web framework, no database, no queue, no async runtime.
- Golden set + run snapshots are plain JSON/YAML files on disk.
- `argparse` for the CLI (no click/typer dependency needed at this scale).
- Optional deps kept to a minimum: `pyyaml` (golden set format), `rich` or
  `tabulate` (nicer console diff table — plain `print` would also work if
  we want zero third-party deps at all).
- Live mode (optional, not required for the demo) uses the official
  `openai` / `anthropic` python SDKs, imported lazily so the offline demo
  never needs them installed.

Why Python over Node/Go: fastest to hand-roll simple heuristic scorers
(regex/JSON-validity/keyword checks) and JSON diffing with no build step,
and it's the ecosystem the golden-set/eval space already lives in, so a
throwaway script reads naturally as a v0 of the real thing.

## Explicitly out of scope for this local MVP

- **Auth / user accounts** — single local user, no login, no multi-tenant.
- **Billing** — not a product yet, nothing to charge for.
- **Hosting / deployment** — runs as a local CLI only, no server process.
- **Real Slack/email delivery** — "alerting" is a formatted message printed
  to the console and appended to a local `alerts.log`. A Slack webhook
  *could* be a one-line `requests.post`, but wiring up a real webhook
  requires the user to have a Slack app/account set up, which isn't
  needed to prove the detection logic — so it's explicitly stubbed, not
  implemented.
- **Scheduling/cron daemon** — no background process that "runs on a
  schedule" or polls for provider model updates. The CLI is invoked
  manually; scheduling is a one-line note ("wire this to cron/GH Actions
  later"), not code.
- **LLM-judge scoring** — no second LLM call to grade quality. Scoring is
  deterministic heuristics (JSON-validity, refusal-phrase detection,
  expected-substring/regex match, output-length ratio). This is the
  correct MVP simplification: it proves the drift-detection *mechanism*
  without needing to also validate an LLM-as-judge.
  end, sub-second demo.
- **Web dashboard** — the "diff view" is a console table plus a generated
  Markdown report file, not a UI.
- **Database** — run history is just timestamped JSON files in `runs/`.

The one thing that IS in scope despite touching an external system: an
optional **live mode** that calls a real provider API if the user has
already exported an API key. It's a thin, isolated code path (not
required to run the demo) because "does this actually work against a
real endpoint" is worth proving cheaply once the offline engine works —
but it is not wired into any auth/account system, it just reads the key
already sitting in the user's shell env.

## File / directory layout

```
drift-sentinel/
├── plan.md
├── README.md
├── pyproject.toml                 # or requirements.txt — minimal deps
├── golden_set.yaml                # curated prompts w/ id, class, checks
├── fixtures/
│   ├── baseline_run.json          # canned "before" responses per prompt id
│   └── drifted_run.json           # canned "after" responses (simulated regression)
├── drift_sentinel/
│   ├── __init__.py
│   ├── cli.py                     # entrypoint: run / compare / demo subcommands
│   ├── runner.py                  # executes golden set -> run snapshot (fixture or live)
│   ├── scorer.py                  # per-prompt heuristics: format/refusal/task-completion
│   ├── differ.py                  # compares two snapshots, flags regressed prompt classes
│   ├── report.py                  # renders console table + writes report.md
│   └── alert.py                   # formats alert message, writes alerts.log (stub notifier)
├── runs/                          # generated run snapshots land here (gitignored)
└── tests/
    ├── test_scorer.py
    └── test_differ.py
```

## Golden set shape (illustrative, not final)

Each entry has: `id`, `class` (e.g. `code-generation`, `json-extraction`,
`refusal-boundary`, `summarization`), `prompt`, and a `check` spec
(`expects_json: true`, `expects_keywords: [...]`, `must_not_refuse: true`,
etc.) — deliberately simple, deterministic checks rather than fuzzy
quality scoring.

## How this gets verified

1. **Unit tests** (`pytest tests/`) — `scorer.py` and `differ.py` are pure
   functions over plain dicts, so they're fully testable without any
   network or fixture files:
   - format-compliance scorer correctly flags invalid JSON
   - refusal scorer correctly flags "I'm sorry, I can't help with that"
   - differ correctly computes per-class drift and applies the
     regression threshold
   - differ run against two *identical* snapshots reports zero drift
     (no false positives)

2. **Manual end-to-end run-through** (the actual demo):
   ```
   python -m drift_sentinel demo
   ```
   This loads `golden_set.yaml`, treats `fixtures/baseline_run.json` and
   `fixtures/drifted_run.json` as two runs of the same prompts, computes
   the diff, and should print a console table showing something like:

   ```
   class               baseline    candidate   status
   code-generation      92%         35%         REGRESSED
   json-extraction      88%         85%         ok
   refusal-boundary      2%          2%         ok
   summarization        90%         91%         ok

   ALERT: code-generation regressed 92% -> 35% (threshold 15%)
   ```

   and write `report.md` (the diff view) and append the alert text to
   `alerts.log`.

3. **Optional live-mode smoke test** (not required to consider the MVP
   working, but worth a manual check once the offline path is solid):
   ```
   export OPENAI_API_KEY=...
   python -m drift_sentinel run --mode live --provider openai --out runs/today.json
   python -m drift_sentinel compare fixtures/baseline_run.json runs/today.json
   ```
