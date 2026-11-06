"""Default theme and brand packs."""

import json

import pytest

from app.config import get_settings
from app.services.theme import load_theme, resolve_asset, theme_css


@pytest.fixture
def brand_pack(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "BRAND_PACK_PATH", str(tmp_path))
    return tmp_path


def _write_theme(directory, **content) -> None:
    (directory / "theme.json").write_text(json.dumps(content), encoding="utf-8")


def test_without_a_pack_the_neutral_default_applies():
    theme = load_theme()
    assert theme.name == "Neutral"
    assert theme.pack_dir is None
    assert theme.logo is None
    assert "--surface-accent:#33556B" in theme_css()


def test_every_token_the_frontend_uses_has_a_default():
    required = {
        "surface-primary",
        "surface-accent",
        "surface-secondary",
        "surface-tertiary",
        "surface-alert",
        "text-primary",
        "text-accent",
        "text-secondary",
        "text-alert",
        "text-on-accent",
        "border-primary",
        "border-disabled",
        "gradient-start",
        "gradient-end",
        "font-heading",
        "font-body",
        "font-wordmark",
        "radius-sm",
        "radius-md",
        "radius-lg",
        "radius-full",
    }
    assert required <= load_theme().tokens.keys()


def test_pack_overrides_only_what_it_names(brand_pack):
    _write_theme(
        brand_pack,
        name="Example",
        logo="logo.svg",
        tokens={"surface-accent": "#006E4F"},
        tokens_small={"radius-md": "8px"},
    )
    css = theme_css()
    assert load_theme().name == "Example"
    assert "--surface-accent:#006E4F" in css
    assert "--surface-primary:#FFFFFF" in css
    assert "@media (max-width:767px){:root{" in css
    assert "--radius-md:8px" in css


@pytest.mark.parametrize(
    "value",
    [
        "red;} body{display:none",
        "url(https://evil.example/x)</style>",
        "#fff; --other: 1",
    ],
)
def test_values_that_could_escape_the_stylesheet_are_dropped(brand_pack, value):
    _write_theme(brand_pack, tokens={"surface-accent": value})
    theme = load_theme()
    assert theme.tokens["surface-accent"] == "#33556B"
    assert theme.warnings


def test_broken_theme_file_falls_back_to_the_default(brand_pack):
    (brand_pack / "theme.json").write_text("{not json", encoding="utf-8")
    assert load_theme().name == "Neutral"


def test_wordmark_font_from_the_pack(brand_pack):
    (brand_pack / "wordmark.otf").write_bytes(b"font")
    _write_theme(brand_pack, wordmark_font="wordmark.otf")
    css = theme_css()
    assert '@font-face{font-family:"Brand Wordmark"' in css
    assert 'url("/brand/assets/wordmark.otf") format("opentype")' in css
    assert '--font-wordmark:"Brand Wordmark", var(--font-heading)' in css


def test_missing_wordmark_font_keeps_the_heading_font(brand_pack):
    _write_theme(brand_pack, wordmark_font="missing.otf")
    assert "@font-face" not in theme_css()


def test_assets_are_limited_to_listed_types_inside_the_pack(brand_pack):
    (brand_pack / "logo.svg").write_text("<svg/>")
    _write_theme(brand_pack)
    assert resolve_asset("logo.svg") is not None
    assert resolve_asset("theme.json") is None
    assert resolve_asset("../../../etc/passwd") is None
    assert resolve_asset("missing.svg") is None


async def test_theme_stylesheet_endpoint(client):
    response = await client.get("/brand/theme.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    assert ":root{" in response.text


async def test_favicon_redirects_to_the_default_asset(client):
    response = await client.get("/brand/favicon")
    assert response.status_code == 302
    assert response.headers["location"] == "/brand/assets/favicon.svg"
    asset = await client.get("/brand/assets/favicon.svg")
    assert asset.status_code == 200
    assert asset.headers["content-type"].startswith("image/svg")


@pytest.mark.parametrize(
    "path",
    [
        "/brand/assets/theme.json",
        "/brand/assets/%2e%2e/%2e%2e/config.py",
        "/brand/assets/..%2f..%2fconfig.py",
        "/brand/assets/missing.svg",
    ],
)
async def test_asset_endpoint_refuses_anything_else(client, path):
    assert (await client.get(path)).status_code == 404


async def test_brand_endpoint_is_public_and_shows_the_institution(client):
    response = await client.get("/api/v1/brand")
    assert response.status_code == 200
    assert response.json() == {
        "theme": "Neutral",
        "institution_name_en": "Example University",
        "institution_name_ja": "例大学",
        "timezone": "Asia/Tokyo",
        "logo": None,
    }


async def test_brand_endpoint_shows_the_logo_from_the_pack(client, brand_pack):
    (brand_pack / "logo.svg").write_text("<svg/>")
    _write_theme(brand_pack, logo="logo.svg", logo_alt_en="Example", logo_alt_ja="例")
    logo = (await client.get("/api/v1/brand")).json()["logo"]
    assert logo == {"url": "/brand/assets/logo.svg", "alt_en": "Example", "alt_ja": "例"}
