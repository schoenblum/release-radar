"""Message catalogue for text the backend produces: emails now, exports later.

The frontend has its own catalogue. ``scripts/check_i18n.py`` checks that the EN
and JA files of both have identical keys and placeholders (R5.4.1).
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

SUPPORTED_LANGUAGES = ("en", "ja")
DEFAULT_LANGUAGE = "en"

_CATALOGUE_DIR = Path(__file__).parent


@lru_cache
def _catalogue(language: str) -> dict[str, Any]:
    return json.loads((_CATALOGUE_DIR / f"{language}.json").read_text(encoding="utf-8"))


def normalise_language(language: str | None) -> str:
    return language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def t(language: str | None, key: str, **values: Any) -> str:
    """Return the message for a dotted key. A missing key raises, so tests catch it."""
    node: Any = _catalogue(normalise_language(language))
    for part in key.split("."):
        node = node[part]
    return str(node).format(**values)
