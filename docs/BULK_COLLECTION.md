# Initial Coimbatore collection without daily count caps

8 November 2026. The user explicitly directed removing the 300-request/day app
limit until the initial database is collected, and continuing the collection
improvements. This supersedes the earlier decision to retain daily app allowances
during the first fill. It does not remove the INR 3,000/month operating target or
approve any venue/fact automatically.

## Implemented and enabled locally

- `LOCAL_BULK_COLLECTION=true` takes effect only in `APP_MODE=local`. Effective
  daily external-request, direct-browser and investigation limits are zero,
  meaning **unlimited counts** in this mode. Existing counters are incremented,
  not cleared, replaced with large fake limits or reset at startup.
- Normal defaults remain in configuration for later routine operation. Disabling
  the flag restores them. Live/demo modes cannot activate the local bypass.
- Public reads and paid-provider attempts now have separate counters
  `collection-free:YYYY-MM-DD` / `collection-paid:YYYY-MM-DD`, plus the preserved
  aggregate and browser counters. Historical requests were not back-classified.
  Counts record adapter reservations/attempts, not an audited count of every HTTP
  request inside a search/browser subprocess or a provider invoice.
- Paid API adapters retain monthly monetary reservations. A zero monetary budget
  still blocks paid HTTP; it never means unlimited spending. These reservations
  are configurable estimates; hosting/electricity/provider bills remain separate.
  No paid connector or new cloud model was activated by this task.
- The local daily-case cap and four-hour inter-case wait do not stop bulk work.
  Up to three investigations can be active at once by default, with the existing
  single model lane/backpressure. This is bounded concurrency, not a daily count
  cap. All relevant discovered references remain durable; model precision,
  sampling and evidence/publication gates are unchanged.
- Weighted queue selection shares control work across investigations, enrichment,
  page refresh, first-party inventory, reel watches and directory collection.
  A high-priority investigation no longer always takes the next eligible turn.
- Public search, HTML and Instagram metadata/browser paths retain persistent
  per-source pacing. Search failures back off exponentially. Applicable HTTP
  429/503/504 responses honor `Retry-After` delta/date headers and a durable
  cooldown. Direct browser challenges retain their separate existing cooldown.
  Removing our daily caps does not grant unlimited service-side access.
- Source waits have separate reasons (`source_pacing`, `source_cooldown`,
  `local_daily_limit`) and do not consume normal failure retries. Existing legacy
  quota/cooldown waits are woken through source guards; source cooldown counters,
  attempt histories, caches, cancelled jobs and other owners remain intact.
- The directory's artificial two-request/week count is also bypassed in bulk
  mode; its seven-day cache/scoped query/weekly scheduler remain. Re-downloading
  the same directory repeatedly does not improve menu or branch coverage.
- Website extraction now reads explicit JSON-LD INR menu offers, hours and select
  explicit amenities as **unverified observations**. No price/currency or quiet/
  romantic vibe is guessed. Pages listing multiple businesses/branches retain
  unassigned menu evidence instead of automatically attributing it to a venue.
- Admin usage and research-runtime UI show unlimited counts in initial mode.

## Commands and lifecycle

Keep these existing flags enabled locally: `AUTONOMOUS_DISCOVERY`,
`INVENTORY_COLLECTION_ENABLED`, `LOCAL_SEARCH_ENABLED`,
`INSTAGRAM_BROWSER_ENABLED`, plus `LOCAL_BULK_COLLECTION`.

```powershell
.\scripts\start.ps1 -SkipBuild
cd backend
uv run python -m app.manage bulk-collection-resume
uv run python -m app.manage city-collection-report
```

The resume CLI wakes only owned queued legacy/app-limit waits and unpauses local
research. It does not reset request/spending counters or erase error histories.
Do not repeatedly run it to defeat source-side retry times.

The flag remains enabled for the initial fill. After the initial data scope has
been reviewed and signed off, set it to false in ignored `.env` and restart for
routine operation. An empty queue or 168 scheduled searches must not automatically
declare full-city coverage or disable collection on that assumption. The machine
must stay awake/connected with API/worker running; this is not a Windows boot service.

## Verification and live evidence

- Full isolated backend suite: **283 passed in 51.92s**; Ruff passed. New tests cover
  counters continuing past 300, browser caps bypassed while pacing persists,
  local-only activation, restoring normal limits, a zero paid budget blocking HTTP,
  persistent source retry times, fair queue service, nonterminal deferrals, scoped
  queue wake-up, unlimited daily cases/bounded active cases, exact JSON-LD evidence
  and multi-venue menu attribution.
- Strict production build passed. **Eight desktop/mobile Chromium checks passed
  in 14.7s**, including unlimited usage labels and existing coverage/known-location
  controls. Mutating source fixtures were intercepted; no fictional venues or
  human labels/approvals were added to the real inventory.
- Pre-change consistent backup:
  `data/backups/batore-20261108T070103Z.db`. CLI resumed **541** owned queued waits.
  API/worker restarted locally; actual aggregate counter advanced **300 → 333**,
  browser visits **14 → 20**, research sources **83 → 86** at the 07:12 UTC snapshot.
  There were seven of 168 grid queries scheduled, compared with five before.
  These prove live progress past the old app limit; they do not prove source
  accuracy, real 429 coverage or a speed guarantee.
- The inventory still had 568 active unapproved drafts at that snapshot. Retained
  source count/observations can grow before a new valid place is extracted. No
  complete-city, final branch accuracy, creator calibration, trained-weight or
  customer-validation claim is made. Source-side availability and independent
  accuracy/approval work remain real dependencies.

Follow-up at **07:17 UTC / 12:47 IST**: counter **410**, new free adapter attempts
**110**, browser visits **24**, research sources **88**, and **574 active unapproved
drafts** (684 originals: 98 held/12 merged). API healthy; worker heartbeat 2.75s
old. Gap counts: 455 menu/price, 515 hours observations, 539 vibes, 574 Maps reviews.
Zero real venues/accepted claims. Post-change snapshot:
`data/backups/batore-20261108T071743Z.db`. Final focused suite **12 passed in 1.92s**,
including an HTTP-429 HTML adapter regression proving that the next read does not
issue another request during its saved 900-second Retry-After cooldown.

Current local snapshots: `data/city-collection/PROGRESS.md`, `coverage.json`,
`runtime.json` and active/held/all review CSVs. The app has current state; these
files represent their recorded timestamp. See `PROJECT_MASTER.md` and
`VERIFICATION.md` for the latest outcome.
