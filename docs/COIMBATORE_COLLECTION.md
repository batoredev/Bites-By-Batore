# Coimbatore internal data collection

Started 8 November 2026. This is an internal inventory build, not a declaration
that Coimbatore is complete or that these places are verified recommendations.

**Latest update:** the user subsequently requested no app daily count limits until
the initial database is collected. [BULK_COLLECTION.md](BULK_COLLECTION.md) records
the enabled local initial mode, separate spending/source controls and live progress
past 300. Earlier first-pass allowance/count statements below are historical;
normal-mode defaults apply again only after that initial mode is disabled.

## What the collector does

1. Obtain a bounded named-place extract through OpenStreetMap's Overpass API
   within its named Coimbatore administrative areas (district relation 1819317
   and matching North/South subdivisions in the actual response). Keep the raw
   response and fetch receipt under `data/city-collection/`. Missing district
   boundary metadata fails closed; there is no broad-radius fallback.
2. Filter to supported food, cafés, cinema, parks, gaming, bowling and adventure
   categories and the product's existing 40 km radius around 11.0168, 76.9558.
   This is district coverage clipped to an operating radius, **not the municipal
   boundary or a venue census**. It can include nearby district towns; the user
   must review applicability. The initial broad-radius pass caught Kerala leads;
   51 earlier active records absent from the scoped pass were held, retaining
   every original. Subsequent imports flag absent directory references for review
   rather than silently deleting them or claiming closure.
3. Insert unapproved, owner-private `identified_spots`, preserving the OSM object
   reference, original names/English aliases, source URL, coordinates and licence.
   Geometry centres are not checked entrances. Raw opening-hours/cuisine/website
   tags remain observations; no prices, hours, branch identities or approvals are
   invented. Unusual and ambiguous candidates enter the held queue.
4. Reuse the same OSM reference on repeated imports. Follow merges without
   reactivating rejected/held originals. Combine same-name points within 25 m
   only when branch/address clues do not conflict and exactly one candidate fits.
   Strong distance/address conflicts stay separate; weak overlap with a social
   lead is held for review. These are provisional inventory identities, not proof
   of a physical branch. Cross-script aliases and uncertain duplicates still need
   independent checking.
5. Enrich through the existing private website/menu and Instagram discovery
   pipeline. Venue website hints are checked as unverified sources; OSM listing
   pages are excluded from daily HTML maintenance. Existing content can be
   analysed locally even when the external-request allowance is exhausted.
6. Rotate the 168 area/topic discovery queries (14 neighbourhoods × 12 topics),
   retain all relevant discovered references, order by newest known publication
   before collection, and stop eligible known-location discovery clips with an
   explicit coverage receipt. Unknown publication dates remain unknown.
7. Persist drafts after each source. Keep quota-blocked work queued and resume
   automatically. Initial mode bypasses external/browser/daily-case count caps;
   no paid provider has been activated by this collection task.
8. Show field gaps in Identified spots and retain source attribution. Every
   location still requires the user's exact-branch review and final approval;
   accepted current facts and location approval remain separate publication gates.

## Scheduling and operation

`CITY_DIRECTORY_ENABLED=true` enables this additional internal-local path. It is
off in fresh-checkout/test defaults and unavailable outside local operation.
The existing autonomous/inventory flags must remain enabled for continuous work.

The scoped directory response is cached for seven days; scheduling uses one durable job
per ISO week and owner, with at most two requests per ISO week in normal mode.
Initial local mode removes that count cap while retaining cache reuse. A week boundary
may reuse the existing cache; this does **not** mean a new fetch occurred. This
baseline refresh is separate from daily website checks, periodic reel watches and
ongoing source investigations. Public Overpass outages/429/503/504 defer work.
Partial responses fail closed. It is a shared public service, not unlimited
infrastructure: [Overpass resource guidance](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html).

The four-hour inter-case delay is removed only for this local city-collection
profile; initial bulk mode also removes daily case/provider/browser count caps
while retaining source pacing and bounded active work. An unfinished case is resumed rather than silently abandoned for a new
query. A 168-query grid is a discovery strategy, not a completeness denominator.

Run from the project folder:

```powershell
.\scripts\start.ps1 -SkipBuild
cd backend
uv run python -m app.manage city-collection-report
```

The start command is idempotent and can also be issued locally with
`uv run python -m app.manage city-collection-start`. Authenticated admin endpoints
are `POST /api/admin/city-collection/start` and
`GET /api/admin/city-collection`. The coverage response is owner-scoped and
explicitly returns `city_complete: false`.

The API and worker must keep running and the computer must remain awake and
connected. Stopping Codex does not stop the separately launched worker. This is
not a Windows boot service, and switching off the computer pauses collection.

## Attribution and data handling

Directory-derived records retain **© OpenStreetMap contributors · ODbL 1.0** and
link to [OpenStreetMap copyright and licensing](https://www.openstreetmap.org/copyright).
The attribution is visible on each applicable admin card and retained in JSON
exports; review CSVs include attribution and source references. Public map cache
files contain directory data, not account history. Private inventory and owned
jobs participate in existing account export/erasure. Local operator review
exports and SQLite backups are separate files and must be removed manually when
erasing those offline copies.

No Nominatim POI enumeration or general-purpose geocoding connector was added.
No Google Maps identity, menu freshness, licence-free ownership or human accuracy
measurement is inferred from an OSM record. Review redistribution obligations
before public publication of a combined database; this task leaves it internal.

## Completion requirements

- Expand geographic/category coverage beyond whatever one directory/search index
  exposes; log gaps and independently assess a defined first-release scope.
- Corroborate actual operating status, exact branch names/addresses/coordinates,
  current menus/prices/hours and attributed vibe evidence. Parks and other free
  activities need applicability review rather than invented menu prices.
- Resolve held duplicates and conflicting sources without deleting originals.
- Measure multilingual extraction and branch accuracy against independent human
  labels and observe whether corrections improve later results.
- Obtain explicit location approval before suggestions; test invited-user outings
  only after the agreed data/quality gates are met.

No fixed completion date or “every place covered” accuracy guarantee is currently
supported. See the latest `PROJECT_MASTER.md` and `VERIFICATION.md` checkpoint for
actual counts, completed local/live checks and remaining gaps.

## Actual 8 November checkpoint

- Broad request: 635 entries, 526 in the radius/category filter; 523 new originals,
  three evidence updates. Broad response retained for audit, not used for recurring collection.
- Scoped request: 477 entries = three administrative boundaries plus 474 supported
  place objects, representing 471 retained candidate identities. Eighteen are held;
  453 active drafts have scoped directory evidence. A district boundary is still
  a crowdsourced scope, not independent branch validation.
- Six actual local caption jobs completed: active drafts increased 86 → 115 before
  the directory pass. Final active drafts **568**; retained originals **678** = 568
  identified + 98 quarantined + 12 merged. **Zero real venues or accepted claims**.
- Gaps: 455 without menu/price evidence; 512 without any hours observation; 533
  without vibe evidence; all 568 lack operator Maps review. A raw hours tag does
  not resolve current-hours verification. Five of 168 planned queries have been
  scheduled; that is not five completed area/topic coverage audits.
- API/worker restored to local mode; the shared external-read counter is 300/300
  today and browser visits 14/30. Durable requests wait for normal allowance
  availability; no counter reset or paid provider activation. Two real Overpass
  requests were separately accounted against the two-request weekly allowance.
- Human-readable snapshot: `data/city-collection/PROGRESS.md`; active/held/all CSVs,
  `coverage.json`, `runtime.json`, both import rehearsals and raw fetch receipts
  are in that folder. The app shows current data; files are snapshots.
