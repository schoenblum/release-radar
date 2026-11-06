"""Setup at every start: the institution row, built-in seeds and the first admin.

Safe to run repeatedly: it adds only what is absent. The container entrypoint runs it once
before Uvicorn starts its workers, so workers never race to create any of it.
"""

import asyncio
import logging
import sys

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import Institution, User, UserRole
from app.seeds import seed_defaults
from app.services.security import hash_password

logger = logging.getLogger(__name__)


async def bootstrap() -> None:
    settings = get_settings()
    domain = (settings.INSTITUTION_WEBSITE_DOMAIN or "").strip().lower() or None
    contact_email = (settings.INSTITUTION_CONTACT_EMAIL or "").strip().lower() or None
    async with SessionLocal() as db:
        institution = await db.scalar(select(Institution).order_by(Institution.created_at).limit(1))
        if institution is None:
            institution = Institution(
                name_en=settings.INSTITUTION_NAME_EN,
                name_ja=settings.INSTITUTION_NAME_JA,
                timezone=settings.INSTITUTION_TIMEZONE,
                website_domain=domain,
                contact_email=contact_email,
                settings={},
            )
            db.add(institution)
            await db.flush()
            logger.info("Institution created")
        else:
            # An install created before these settings existed.
            if institution.website_domain is None and domain:
                institution.website_domain = domain
            if institution.contact_email is None and contact_email:
                institution.contact_email = contact_email
        await seed_defaults(db, institution)

        admin_exists = await db.scalar(
            select(User.id)
            .where(User.institution_id == institution.id, User.role == UserRole.admin)
            .limit(1)
        )
        if admin_exists is None:
            if not settings.BOOTSTRAP_ADMIN_EMAIL or not settings.BOOTSTRAP_ADMIN_PASSWORD:
                raise RuntimeError(
                    "The database has no admin yet. Set BOOTSTRAP_ADMIN_EMAIL and "
                    "BOOTSTRAP_ADMIN_PASSWORD in .env."
                )
            db.add(
                User(
                    institution_id=institution.id,
                    email=settings.BOOTSTRAP_ADMIN_EMAIL.strip().lower(),
                    password_hash=hash_password(settings.BOOTSTRAP_ADMIN_PASSWORD),
                    role=UserRole.admin,
                    force_password_change=True,
                )
            )
            logger.info("First admin created; a new password is required at first sign-in")
        await db.commit()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(bootstrap())
    except RuntimeError as exc:
        logger.error("%s", exc)
        sys.exit(1)
