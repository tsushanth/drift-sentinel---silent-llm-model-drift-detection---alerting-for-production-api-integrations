"""Deterministic heuristic scoring for a single (prompt, response) pair.

No LLM-as-judge here on purpose: every check is a pure function over plain
strings/dicts so it's cheap, reproducible, and fully unit-testable.
"""

import json
import re

# Phrases that indicate the model declined to answer. Matched case-insensitively
# against the start/body of the response.
REFUSAL_PATTERNS = [
    r"i'?m sorry,?\s*(but\s*)?i (can'?t|cannot|won'?t|am not able to)",
    r"i (can'?t|cannot|won'?t) (help|assist) with that",
    r"as an ai( language model)?,?\s*i (can'?t|cannot)",
    r"i'?m not able to (help|assist) with that",
    r"i won'?t (provide|generate) (that|this)",
    r"i must decline",
]

_REFUSAL_RE = re.compile("|".join(REFUSAL_PATTERNS), re.IGNORECASE)


def is_refusal(response: str) -> bool:
    """Return True if the response looks like a refusal to answer."""
    return bool(_REFUSAL_RE.search(response or ""))


def _extract_json(response: str):
    """Try to parse response as JSON, first strictly, then from the first
    '{' to the last '}' as a lenient fallback for minor wrapping. Still
    deterministic and still rejects malformed JSON (e.g. trailing commas)."""
    text = (response or "").strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return None


def score_response(check: dict, response: str) -> dict:
    """Score a single response against a check spec.

    Returns {"passed": bool, "failures": [reason, ...]}. A response passes
    only if every check key present in `check` is satisfied.
    """
    check = check or {}
    response = response or ""
    failures = []

    if check.get("expects_json"):
        if _extract_json(response) is None:
            failures.append("response is not valid JSON")

    if "expects_regex" in check:
        pattern = check["expects_regex"]
        if not re.search(pattern, response):
            failures.append(f"response did not match /{pattern}/")

    if "expects_keywords" in check:
        lowered = response.lower()
        missing = [kw for kw in check["expects_keywords"] if kw.lower() not in lowered]
        if missing:
            failures.append(f"missing expected keyword(s): {missing}")

    if check.get("must_not_refuse"):
        if is_refusal(response):
            failures.append("response looks like a refusal")

    if "min_length" in check:
        if len(response) < check["min_length"]:
            failures.append(f"response shorter than min_length={check['min_length']}")

    if "max_length" in check:
        if len(response) > check["max_length"]:
            failures.append(f"response longer than max_length={check['max_length']}")

    return {"passed": len(failures) == 0, "failures": failures}
