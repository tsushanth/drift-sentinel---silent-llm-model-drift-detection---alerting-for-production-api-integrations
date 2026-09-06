"""Format and record alerts. Real Slack/email delivery is explicitly out of
scope for this MVP: an alert is a formatted message printed to the console
and appended to a local alerts.log. Wiring a real Slack webhook later is a
one-line requests.post from format_alert()'s output.
"""

import datetime
import os


def format_alert(rows: list, threshold: float) -> str:
    """Return an alert message for any regressed classes, or None if the
    run is clean."""
    regressed = [r for r in rows if r["status"] == "REGRESSED"]
    if not regressed:
        return None

    lines = ["ALERT: drift detected"]
    for r in regressed:
        lines.append(
            f"  {r['class']} regressed {r['baseline']:.0f}% -> "
            f"{r['candidate']:.0f}% (threshold {threshold}pp)"
        )
    return "\n".join(lines)


def append_alert_log(text: str, path: str = "alerts.log", timestamp: str = None) -> None:
    timestamp = timestamp or datetime.datetime.utcnow().isoformat() + "Z"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a") as f:
        f.write(f"[{timestamp}]\n{text}\n\n")
