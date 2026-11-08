# Release Radar

Release Radar is a press-release evaluation tool for university communications
offices. It replaces a shared spreadsheet with fast data entry, fills in what can be
filled in automatically, reminds people about the rest, and gives the office an
evaluation dashboard. Researchers get a feedback form and a summary page for their
release.

The interface, list values, surveys and exports are bilingual (English and Japanese).

**Status:** early development. Phase 1, step 1.8: sign-in, language switching, theming,
scheduling and backups, the data model with its audit log, the admin Settings area, the
Data page (a spreadsheet-like grid with what is due, filters, search, sorting and a bilingual
Excel or CSV export), the Writers page with monthly counts, and an import of the old
spreadsheet with a dry run and a review report. Polish and end-to-end tests come next.

## Run it

You need Docker with Compose. No other tools are needed on the host: the backend and
the frontend both build and run inside containers.

```bash
python3 scripts/generate_env.py
docker compose up --build
```

On macOS, Docker needs a Linux VM. [Colima](https://github.com/abiosoft/colima) is a free,
open-source option.

| Address | What |
|---|---|
| <http://localhost:5173> | The app, with live reload |
| <http://localhost:8000/docs> | API documentation (development only) |
| <http://localhost:8025> | Mailpit, which catches all outgoing email in development |

Sign in with `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` from your `.env`.
You'll be asked to choose a new password.

## Check it

This runs the same checks as CI, inside the containers:

```bash
sh scripts/check.sh
```

## Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL 16 |
| Jobs | APScheduler, with single-firing across workers through Postgres |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, react-i18next |
| Containers | Docker Compose, with images for `linux/amd64` and `linux/arm64` |

## Layout

```
app/        Backend: routers, models, services, message catalogue, default theme
alembic/    Database migrations
frontend/   Frontend: pages, components, translations, Manual
ops/        Backup restore, lockout recovery, HTTPS proxy
scripts/    Environment setup and checks
tests/      Backend tests, which run against a real PostgreSQL
docs/       Japanese strings awaiting native-speaker review
```

## Configuration

All configuration is in `.env`, which is never committed. `.env.example` explains each
value. `COMPOSE_PROFILES` chooses what runs: `dev`, `prod`, or `prod,proxy`.

## Branding

The repository ships a neutral theme in `app/brand_default/`. An institution adds its
own logo, colours and fonts through a **brand pack**: a folder with a `theme.json` and
its asset files, kept outside this repository. Point `BRAND_PACK_HOST_PATH` at it and
restart. A pack only has to name the values that differ from the defaults:

```json
{
  "name": "My University",
  "logo": "logo.svg",
  "logo_alt_en": "My University",
  "favicon": "mark.svg",
  "tokens": { "surface-accent": "#123456", "text-accent": "#123456" }
}
```

## Data protection

Release Radar is installed separately for each institution, and its data stays in that
install. This repository holds code only. Tests and documentation use synthetic data.

## Licence

[MIT](LICENSE)
