# Latest inventory workflow

The product is a Coimbatore food/entertainment itinerary planner. Its agent now
keeps all discovered relevant sources, processes newest known dates first, and
saves map/menu/vibe proposals to **Admin -> Identified spots**. Each location
requires your explicit approval before itinerary suggestions. See
[INVENTORY_COLLECTION.md](docs/INVENTORY_COLLECTION.md) for the current workflow,
real data counts, tests and unfinished requirements.

# Current local research workflow

The active setup uses local models and an isolated real-evidence database. Open
http://127.0.0.1:8000/admin and choose Investigations. The agent finds example reels itself.
Read [LOCAL_RESEARCH.md](docs/LOCAL_RESEARCH.md) for setup, learning, tested capabilities
and remaining evaluation gaps. [DIRECT_INSTAGRAM.md](docs/DIRECT_INSTAGRAM.md) records
the direct public-browser collector: three agent-selected real videos, captions and
32 loaded comments retrieved without login or API keys, then analysed locally.

# Bites by Batore

**Start here: [Master project record and completion tracker](PROJECT_MASTER.md).**
It records the full agreed product, evidence-backed completed work, unfinished
features, dependencies and execution steps. The local app below is a partial
implementation; the full autonomous Instagram investigation system is unfinished.

The [latest implementation update](docs/BUILD_UPDATE_2026-11-04.md) adds durable
specialist investigations, Meta/third-party collection adapters, local frame
extraction, branch/source review, guided discovery, up to four stops, package/session
records and a data-readiness gate before invited testers. Direct public Instagram
collection has bounded live evidence; real city verification remains outstanding. The initial operating target is INR 3,000/month.

An English-language, mobile-friendly PWA for food and entertainment outings in
Coimbatore. Starting location, available time, group size, budget and taste produce
up to three feasible plans, with a selectable maximum of one to four stops. Duration ends at the last stop:
there is no return-trip planning.

## Run locally

Prerequisites: Python 3.12+, uv and Node 24, already present on this computer.

```powershell
cd 'C:\Users\sriva\Desktop\insta glg gmap bot'
.\scripts\start.ps1
```

Open **http://127.0.0.1:8000**. The script installs locked dependencies, builds the
web app and launches the API and worker in the background. Stop these processes
with `.\scripts\stop.ps1`. Logs and the persistent database live in ignored `data/`.
Subsequent starts can use `-SkipBuild` if web files have not changed.

Default **local demonstration mode** has twelve fictional places, prices, hours
and routes, visibly labelled and never mixed into live recommendations. No keys
are needed to exercise the user and administration flows.

## Implemented

- Guided mood discovery, explicit cuisine/activity requests and transparent reasons.
- Budget/time, opening-window, movie-session, capacity, access and dietary filters;
  itemised estimates, contingency, stop locking/swapping and fresh replanning.
- Private saved plans/places, confirmed visits, editable tastes, modest learning,
  memory clearing and application-data export/erasure.
- Supabase email-link/Google authentication in live mode; isolated demo sessions.
- Supplied social links/text/video, multilingual Gemini analysis adapter, YouTube
  metadata/comment sampling and candidate branch matching through Google Places.
- Durable jobs with leases, deduplication, retries, discovery, scheduled refresh,
  priority for saved upcoming plans and honest timestamps.
- Admin evidence review, venue publication/operational details, provider status,
  job controls and decision audit.
- Responsive UI, PWA manifest, public-shell offline fallback, production build,
  Windows launch scripts and container deployment files.

## Keys and launch

The start script copies `.env.example` to `.env` without replacing an existing
file. Fill values locally using [the credential checklist](docs/KEYS.md). Do not
paste private keys into chat or commit `.env`.

**This is not yet a verified live city guide.** Real venue coverage, source access,
provider smoke tests and deployment are external launch gates. An Instagram key
does not provide unrestricted reel access. Missing live access/facts produce
explicit unavailable states. See [setup](docs/SETUP.md) and
[verification](docs/VERIFICATION.md) before enabling live mode.

## Verify

```powershell
.\scripts\check.ps1
cd web
npm run test:e2e
```

Browser tests require the built app served on port 8000 and create separate demo
accounts. Backend tests use a separate temporary database.

## Guide

- [Confirmed plan](docs/PLAN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Setup](docs/SETUP.md)
- [Credentials](docs/KEYS.md)
- [Operations and release gates](docs/OPERATIONS.md)
- [Signed merchant updates](docs/MERCHANT_UPDATES.md)
- [Integration constraints](docs/INTEGRATIONS.md)
- [Acceptance criteria](docs/ACCEPTANCE.md)
- [Selective reference review](docs/REFERENCE_REVIEW.md)
- API explorer while running: http://127.0.0.1:8000/docs

`backend/`: FastAPI, planner, persistence, adapters and worker. `web/`: React and
TypeScript. Provider secrets stay on the server; the Supabase public key is
intentionally public. See architecture for the first release's explicit limits.
