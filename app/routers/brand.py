"""Theme and brand assets (R5.3.1). Public, because the sign-in page needs them."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.institution import get_institution
from app.services.theme import load_theme, resolve_asset, theme_css

api_router = APIRouter(tags=["brand"])
asset_router = APIRouter(tags=["brand"])


class LogoOut(BaseModel):
    url: str
    alt_en: str | None
    alt_ja: str | None


class BrandOut(BaseModel):
    theme: str
    institution_name_en: str
    institution_name_ja: str | None
    timezone: str
    # Further zones a release time is shown in, in order (empty places left out).
    display_time_zones: list[str]
    logo: LogoOut | None


@api_router.get("/brand", response_model=BrandOut)
async def brand(db: AsyncSession = Depends(get_db)) -> BrandOut:
    theme = load_theme()
    institution = await get_institution(db)
    logo = None
    if theme.logo and resolve_asset(theme.logo):
        logo = LogoOut(
            url=f"/brand/assets/{theme.logo}", alt_en=theme.logo_alt_en, alt_ja=theme.logo_alt_ja
        )
    return BrandOut(
        theme=theme.name,
        institution_name_en=institution.name_en,
        institution_name_ja=institution.name_ja,
        timezone=institution.timezone,
        display_time_zones=[zone for zone in institution.display_time_zones if zone],
        logo=logo,
    )


@asset_router.get("/brand/theme.css")
async def theme_stylesheet() -> Response:
    return Response(
        content=theme_css(),
        media_type="text/css",
        headers={"Cache-Control": "no-cache"},
    )


@asset_router.get("/brand/favicon")
async def favicon() -> RedirectResponse:
    theme = load_theme()
    if not theme.favicon or not resolve_asset(theme.favicon):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    return RedirectResponse(f"/brand/assets/{theme.favicon}", status_code=status.HTTP_302_FOUND)


@asset_router.get("/brand/assets/{path:path}")
async def brand_asset(path: str) -> FileResponse:
    target = resolve_asset(path)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    return FileResponse(target, headers={"Cache-Control": "public, max-age=3600"})
