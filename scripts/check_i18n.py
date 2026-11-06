#!/usr/bin/env python3
"""Check that the EN and JA catalogues match (R5.4.1) and JA strings are tracked (R5.4.7).

Fails if the key sets differ, a value is empty, the placeholders of a pair differ,
the Manual is missing in one language or its sections differ, or a JA string is
not listed in docs/ja-review.md.

    python3 scripts/check_i18n.py                     check, for CI
    python3 scripts/check_i18n.py --update-ja-review  add missing strings to the list
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOGUES = {
    "frontend": ROOT / "frontend/src/i18n/locales",
    "backend": ROOT / "app/i18n",
}
MANUAL_DIR = ROOT / "frontend/src/manual"
JA_REVIEW = ROOT / "docs/ja-review.md"
# i18next uses {{name}}, the backend catalogue uses {name}. Both match this.
PLACEHOLDER = re.compile(r"\{\{?\s*(\w+)\s*\}?\}")
HEADING = re.compile(r"^#{1,6} ", re.MULTILINE)


def flatten(node: dict, prefix: str = "") -> dict[str, str]:
    flat: dict[str, str] = {}
    for key, value in node.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            flat |= flatten(value, f"{path}.")
        else:
            flat[path] = str(value)
    return flat


def compare(name: str, english: dict[str, str], japanese: dict[str, str]) -> list[str]:
    problems: list[str] = []
    for key in sorted(english.keys() - japanese.keys()):
        problems.append(f"{name}: {key} is missing from ja.json")
    for key in sorted(japanese.keys() - english.keys()):
        problems.append(f"{name}: {key} is missing from en.json")
    for key in sorted(english.keys() & japanese.keys()):
        if not english[key].strip() or not japanese[key].strip():
            problems.append(f"{name}: {key} is empty")
        if set(PLACEHOLDER.findall(english[key])) != set(PLACEHOLDER.findall(japanese[key])):
            problems.append(f"{name}: {key} has different placeholders in en and ja")
    return problems


def load(directory: Path) -> tuple[dict[str, str], dict[str, str]]:
    return tuple(
        flatten(json.loads((directory / f"{language}.json").read_text(encoding="utf-8")))
        for language in ("en", "ja")
    )


def check_manual() -> list[str]:
    english = MANUAL_DIR / "en.md"
    japanese = MANUAL_DIR / "ja.md"
    if not english.is_file() or not japanese.is_file():
        return ["manual: en.md and ja.md must both exist"]
    counts = [
        len(HEADING.findall(path.read_text(encoding="utf-8"))) for path in (english, japanese)
    ]
    if counts[0] != counts[1]:
        return [f"manual: en.md has {counts[0]} headings, ja.md has {counts[1]}"]
    return []


def review_id(source: str, key: str) -> str:
    return f"{source}:{key}"


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def missing_from_review(catalogues: dict[str, tuple[dict, dict]]) -> list[tuple[str, str, str]]:
    listed = JA_REVIEW.read_text(encoding="utf-8") if JA_REVIEW.is_file() else ""
    missing: list[tuple[str, str, str]] = []
    for source, (english, japanese) in catalogues.items():
        for key in sorted(japanese):
            identifier = review_id(source, key)
            if f"`{identifier}`" not in listed:
                missing.append((identifier, english.get(key, ""), japanese[key]))
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update-ja-review", action="store_true")
    arguments = parser.parse_args()

    catalogues = {source: load(directory) for source, directory in CATALOGUES.items()}
    problems: list[str] = []
    for source, (english, japanese) in catalogues.items():
        problems += compare(source, english, japanese)
    problems += check_manual()

    missing = missing_from_review(catalogues)
    if arguments.update_ja_review and missing:
        rows = "".join(
            f"| `{identifier}` | {cell(english)} | {cell(japanese)} | pending |\n"
            for identifier, english, japanese in missing
        )
        with JA_REVIEW.open("a", encoding="utf-8") as handle:
            handle.write(rows)
        print(f"Added {len(missing)} strings to {JA_REVIEW.relative_to(ROOT)}")
    else:
        problems += [f"ja-review: {identifier} is not listed" for identifier, _, _ in missing]

    if problems:
        print("\n".join(problems), file=sys.stderr)
        print(f"\n{len(problems)} problem(s).", file=sys.stderr)
        return 1
    keys = sum(len(english) for english, _ in catalogues.values())
    print(f"i18n OK: {keys} keys in EN and JA.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
