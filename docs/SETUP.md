> Current internal research uses local SQLite, Ollama and faster-whisper. Gemini and Supabase keys are not required in local mode. See [LOCAL_RESEARCH.md](LOCAL_RESEARCH.md). Meta/Apify access is still needed to verify full Instagram video/comments when public pages do not expose them. The cloud setup below applies to a later live deployment.

# Setup and environments

## Local demonstration

`scripts/start.ps1` preserves `.env`, installs locked dependencies, builds the
client and starts hidden API/worker processes. Open http://127.0.0.1:8000.
`scripts/stop.ps1` stops only recorded application processes with matching commands
and start times. Database and logs persist in `data/`.

Fresh browsers get separate private demo accounts. Sessions last seven days.
Demo users can explore admin because inventory is fictional. The demo account
endpoint is loopback-only by default. Do not publish demo mode as a public service.

Manual development, in separate terminals from the project root:

```powershell
# API
cd backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Worker (new terminal)
cd backend
uv run python -m app.jobs

# Client (new terminal)
cd web
npm run dev
```

Development UI: http://127.0.0.1:5173. Vite proxies `/api`. Production/browser-test
UI: http://127.0.0.1:8000, after `npm run build` in `web/`.

## Live mode

1. Create a dedicated PostgreSQL/Supabase project, separate from demo storage.
   Fill `docs/KEYS.md` values. Set `APP_MODE=live` and your HTTPS `WEB_ORIGIN`.
2. Configure Supabase email delivery, Google OAuth, site URL and redirect origins.
3. From `backend/`, run `uv run python -m app.manage migrate`. Schema version 3
   enables RLS on backend-owned tables; no direct browser policies are installed.
   The backend connection needs the database owner role.
4. Start the API, sign in and configure approved UUIDs in `ADMIN_USER_IDS`. Restart
   the API and worker after changing environment values.
5. Exercise provider smoke checks in `OPERATIONS.md`. A key being configured is
   never presented as proof that the integration has been verified.
6. Use the venue desk for independently sourced venue identities and evidence.
   Confirm exact branches and essential facts. Do not copy entire Google responses
   into the owned venue database.
7. Run the worker under a supervisor. It claims jobs and schedules due work every
   minute. Adjust provider capacity to actual coverage and budget.
8. Serve the API and built client behind HTTPS. Pass the documented launch gates
   before serving customers. Live mode never falls back to fictional inventory.

Live planning checks at most ten nearby published venues per request, their
current operating/opening information and road routes. Unconfirmed essential facts
exclude a candidate. This is an initial-city release, not exhaustive search.

## Containers

`Dockerfile` builds the client and a non-root Python runtime. `compose.yaml` runs
API/worker with `.env` and a shared volume. Run migrations before live deployment.
Demo compose publishes only on `127.0.0.1`; its internal network allowance handles
Docker's bridge address. Never expose it publicly. Container files are provided;
consult `VERIFICATION.md` for actual execution status.

## Troubleshooting

- Port occupied: check the running app; the start script does not kill other apps.
- Windows dependency file lock: stop this project's Vite development server before
  reinstalling `node_modules`; a running native bundler can keep files open.
- Empty live plans: inspect current evidence, branch ID, capacity, provider errors,
  requested departure and full opening/screening windows.
- Submission queued: check worker logs or use admin's process-next-job action.
  Missing media is an access issue, not evidence that a video was inspected.
- Expired session: sign in again. A new demo account cannot read an old account's
  private plans.
- Offline: the app shell may open, but private APIs and current checks need a
  connection. Private data is never cached by the service worker.


## Internal data work before invited users

Keep `RELEASE_STAGE=internal` until the real Coimbatore inventory and operational
checks are ready. The server admin UUID allowlist is the only live access path in
this stage; valid non-admin sign-in receives a closed-testing message. Obtain the
admin UUID from the Supabase dashboard and restart after configuring it.

Use Admin ? Data readiness to inspect gaps and import the official-source lead pack.
The import creates investigations, not published venues. After actual verification,
record the data review, set `RELEASE_STAGE=test`, and populate `TEST_USER_IDS` with
invited UUIDs. Public release is a later explicit rollout step. See the
[activation record](BUILD_UPDATE_2026-11-04.md) for new source and budget settings.
