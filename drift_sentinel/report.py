"""Render the diff view: a console table and a Markdown report file."""

import datetime
import os

COLUMNS = ("class", "baseline", "candidate", "status")


def render_table(rows: list) -> str:
    """Plain-text console table, zero third-party deps."""
    headers = ["class", "baseline", "candidate", "status"]
    formatted = [
        [
            r["class"],
            f"{r['baseline']:.0f}%",
            f"{r['candidate']:.0f}%",
            r["status"],
        ]
        for r in rows
    ]
    widths = [
        max(len(headers[i]), *(len(row[i]) for row in formatted)) if formatted else len(headers[i])
        for i in range(len(headers))
    ]

    def fmt_row(cells):
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells))

    lines = [fmt_row(headers), fmt_row(["-" * w for w in widths])]
    lines += [fmt_row(row) for row in formatted]
    return "\n".join(lines)


def write_markdown_report(rows: list, threshold: float, path: str = "report.md", generated_at: str = None) -> None:
    generated_at = generated_at or datetime.datetime.utcnow().isoformat() + "Z"
    lines = [
        "# Drift Sentinel Report",
        "",
        f"Generated: {generated_at}",
        f"Regression threshold: {threshold} percentage points",
        "",
        "| class | baseline | candidate | delta | status |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['class']} | {r['baseline']:.0f}% | {r['candidate']:.0f}% | "
            f"{r['delta']:+.0f}pp | {r['status']} |"
        )

    regressed = [r for r in rows if r["status"] == "REGRESSED"]
    lines.append("")
    if regressed:
        lines.append("## Regressions")
        lines.append("")
        for r in regressed:
            lines.append(
                f"- **{r['class']}** regressed {r['baseline']:.0f}% -> "
                f"{r['candidate']:.0f}% (threshold {threshold}pp)"
            )
    else:
        lines.append("No regressions detected.")

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
