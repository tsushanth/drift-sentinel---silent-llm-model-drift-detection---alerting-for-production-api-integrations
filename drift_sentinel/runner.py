"""Produce and load run snapshots.

A "run snapshot" is just a JSON file mapping golden-set prompt id -> response
text. The offline demo path reads these from fixtures/. The optional live
path builds one by actually calling a provider API; the SDKs are imported
lazily so the offline demo never needs them installed.
"""

import json
import os

import yaml


def load_golden_set(path: str = "golden_set.yaml") -> list:
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return data["prompts"]


def load_snapshot(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def save_snapshot(snapshot: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(snapshot, f, indent=2, sort_keys=True)


def run_live(golden_set: list, provider: str, model: str = None) -> dict:
    """Call a real provider for every prompt in the golden set and return a
    snapshot dict. Requires the relevant API key already set in the shell
    env (OPENAI_API_KEY / ANTHROPIC_API_KEY) and the provider's SDK
    installed. Not required for the offline demo.
    """
    if provider == "openai":
        return _run_openai(golden_set, model or "gpt-4o")
    if provider == "anthropic":
        return _run_anthropic(golden_set, model or "claude-3-5-sonnet-latest")
    raise ValueError(f"unknown provider: {provider!r} (expected 'openai' or 'anthropic')")


def _run_openai(golden_set: list, model: str) -> dict:
    from openai import OpenAI  # lazy import: not a dependency of the offline demo

    client = OpenAI()
    snapshot = {}
    for entry in golden_set:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": entry["prompt"]}],
        )
        snapshot[entry["id"]] = completion.choices[0].message.content
    return snapshot


def _run_anthropic(golden_set: list, model: str) -> dict:
    import anthropic  # lazy import: not a dependency of the offline demo

    client = anthropic.Anthropic()
    snapshot = {}
    for entry in golden_set:
        message = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": entry["prompt"]}],
        )
        snapshot[entry["id"]] = "".join(
            block.text for block in message.content if block.type == "text"
        )
    return snapshot
