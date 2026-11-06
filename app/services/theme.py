"""Theme tokens and brand packs (BRIEF section 5.3).

The repository ships a neutral theme in ``app/brand_default``. An institution's
brand pack is a folder mounted at ``BRAND_PACK_PATH``. It holds a ``theme.json``
and its logo and font files, and stays outside the repository. Its values
override the defaults one by one, so a pack only has to name what differs.

The tokens reach the browser as a generated stylesheet, ``/brand/theme.css``.
Changing brand therefore needs a restart but no rebuild, and the first paint
already has the right colours.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_DIR = Path(__file__).resolve().parent.parent / "brand_default"
ASSET_SUFFIXES = {
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".ico",
    ".woff2",
    ".woff",
    ".otf",
    ".ttf",
}

_TOKEN_NAME = re.compile(r"^[a-z0-9-]+$")
# Token values end up in a stylesheet, so anything that could close a declaration
# or a block is refused.
_TOKEN_VALUE = re.compile(r"""^[\w\s#,.%()'"/+-]+$""")
_FONT_FAMILY_NAME = "Brand Wordmark"
_FONT_FORMATS = {".woff2": "woff2", ".woff": "woff", ".otf": "opentype", ".ttf": "truetype"}


@dataclass(frozen=True)
class Theme:
    name: str
    tokens: dict[str, str]
    # Overrides on small screens: the NU guideline has separate PC and phone scales.
    tokens_small: dict[str, str] = field(default_factory=dict)
    logo: str | None = None
    logo_alt_en: str | None = None
    logo_alt_ja: str | None = None
    favicon: str | None = None
    wordmark_font: str | None = None
    pack_dir: Path | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)


def _safe_tokens(raw: object, warnings: list[str]) -> dict[str, str]:
    if not isinstance(raw, dict):
        warnings.append("tokens is not an object")
        return {}
    tokens: dict[str, str] = {}
    for name, value in raw.items():
        if (
            isinstance(name, str)
            and isinstance(value, str)
            and _TOKEN_NAME.match(name)
            and _TOKEN_VALUE.match(value)
        ):
            tokens[name] = value
        else:
            warnings.append(f"token ignored: {name!r}")
    return tokens


def _read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return None
    return data if isinstance(data, dict) else None


@lru_cache
def load_theme() -> Theme:
    """Return the default theme with the brand pack, if any, laid over it."""
    default = _read_json(DEFAULT_DIR / "theme.json")
    if default is None:
        raise RuntimeError("The default theme is missing from the application image")
    warnings: list[str] = []
    tokens = _safe_tokens(default.get("tokens"), warnings)
    tokens_small = _safe_tokens(default.get("tokens_small", {}), warnings)
    merged = dict(default)

    pack_dir = Path(get_settings().BRAND_PACK_PATH)
    pack = _read_json(pack_dir / "theme.json") if pack_dir.is_dir() else None
    if pack is None:
        pack_dir = None
    else:
        tokens |= _safe_tokens(pack.get("tokens", {}), warnings)
        tokens_small |= _safe_tokens(pack.get("tokens_small", {}), warnings)
        merged |= {
            key: value for key, value in pack.items() if key not in ("tokens", "tokens_small")
        }

    for warning in warnings:
        logger.warning("Brand pack: %s", warning)

    return Theme(
        name=str(merged.get("name", "Default")),
        tokens=tokens,
        tokens_small=tokens_small,
        logo=merged.get("logo"),
        logo_alt_en=merged.get("logo_alt_en"),
        logo_alt_ja=merged.get("logo_alt_ja"),
        favicon=merged.get("favicon"),
        wordmark_font=merged.get("wordmark_font"),
        pack_dir=pack_dir,
        warnings=tuple(warnings),
    )


def resolve_asset(relative_path: str) -> Path | None:
    """Find an asset in the brand pack, then in the defaults.

    Returns None for anything outside those folders or of an unlisted type,
    which also keeps ``theme.json`` itself from being served.
    """
    roots = [root for root in (load_theme().pack_dir, DEFAULT_DIR) if root is not None]
    for root in roots:
        resolved_root = root.resolve()
        target = (resolved_root / relative_path).resolve()
        if (
            target.is_relative_to(resolved_root)
            and target.suffix.lower() in ASSET_SUFFIXES
            and target.is_file()
        ):
            return target
    return None


def theme_css(theme: Theme | None = None) -> str:
    """Render the theme as a stylesheet of custom properties."""
    theme = theme or load_theme()
    declarations = {f"--{name}": value for name, value in theme.tokens.items()}
    font_face = ""
    font_format = _FONT_FORMATS.get(Path(theme.wordmark_font or "").suffix.lower())
    if theme.wordmark_font and font_format and resolve_asset(theme.wordmark_font):
        font_face = (
            f'@font-face{{font-family:"{_FONT_FAMILY_NAME}";'
            f'src:url("/brand/assets/{theme.wordmark_font}") format("{font_format}");'
            "font-display:swap}\n"
        )
        declarations["--font-wordmark"] = f'"{_FONT_FAMILY_NAME}", var(--font-heading)'
    body = ";".join(f"{name}:{value}" for name, value in declarations.items())
    small = ";".join(f"--{name}:{value}" for name, value in theme.tokens_small.items())
    small_rule = f"@media (max-width:767px){{:root{{{small}}}}}\n" if small else ""
    return f"{font_face}:root{{{body}}}\n{small_rule}"
