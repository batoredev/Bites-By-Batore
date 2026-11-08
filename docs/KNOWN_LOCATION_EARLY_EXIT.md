# Known-location early exit and local inventory

Implemented 8 November 2026. The user authorized stopping remaining reel work once
an already identified location is recognized, saving locations locally before
their own later review, preventing duplicate active locations and using the GPU
fully. This changes the earlier discovery policy: retain the source/evidence
reference, but intentionally skip remaining analysis when the known-place check
succeeds. It does not remove approval gates or require public release.

## Discovery workflow

1. Check an Instagram permalink against the owner's previously processed sources
   and active private locations, before recency probes, browser work or downloads.
   All previous recorded candidates must resolve to active locations. Held,
   rejected, unaccounted and other-owner records cannot authorize skipping.
2. For a different reel, inspect the caption first. Every extracted candidate
   must match one pre-existing named branch with matching detailed address
   evidence, including a house number or postcode. Name or neighbourhood alone
   cannot discard a potentially new branch. Compilation hints require enough
   accounted candidates; an unknown candidate keeps the source in processing.
3. Save newly identified caption locations immediately in the canonical local
   `identified_spots` table. Process video before comments when this policy is on.
4. Video passes can stop after a pass recognizes the known branch. Sampling and
   visual signatures then include only inspected frames. Frame/audio preparation
   may already have run before the first visual match; no claim of avoiding that
   earlier work is made. Remaining frame calls/reinspection/comments are skipped.
5. Attach a private discovery reference to the existing location. Strip transient
   media, mark remaining modalities `skipped_known_location`, record the matching
   IDs/reason/stage and `coverage_complete=false`, then move to the next source.
   Source rows and their original links remain available for audit/export/erasure.

`streamed=true` now means a source reached a recorded processing outcome: completed
work **or** an explicit discovery-policy skip. It must not be interpreted as full
clip coverage. The UI distinguishes skipped modalities, and verification retains
a gap rather than claiming fresh prices, hours, comments or creator reliability.

Matching and compilation detection are conservative heuristics, not independent
physical location verification or a guarantee that every hidden venue is known.
The adopted early-exit policy deliberately leaves remaining clip evidence
uninspected. Later inspection remains available when needed.

## Review and refresh

Use **From my feed → Inspect known locations again, including the remaining reel
evidence** to request a full pass. API: `force_full_analysis=true` on
`POST /api/investigations`. Source-watch changes and maintenance refreshes bypass
discovery skipping. Labelled evaluation origins are excluded. A partial video
result cannot become a complete cached analysis; the pipeline key is now
`2026-11-08-coverage-v4`, including GPU placement configuration.

Nothing here confirms a Maps name, accepts facts, renews existing fact expiry,
judges a creator or publishes an itinerary location. Those remain explicit checks.

## Canonical SQL inventory and duplicate handling

The canonical local database is `data/local-research.db`, table `identified_spots`.
There is no second writable location database. Pending locations can be saved with
unknown coordinates; the app does not invent map coordinates to create venue rows.
The public/recommendation `venues` table stays separate until location/fact review.

- Backfill all saved caption/video extractions, including unfinished investigations,
  through the same relevance and identity checks used for new data.
- Serialize identity reads/writes using SQLite `BEGIN IMMEDIATE`; equivalent
  PostgreSQL transaction locking is implemented but not live verified.
- Existing SQL uniqueness on `identity_key` plus insert-conflict handling prevents
  concurrent duplicate identity inserts. Alias insertion concurrency is tested.
- Merge supported duplicates without erasing their original records/evidence.
- Hold indistinguishable same-name proposals when no evidence separates branches.
  They remain in **Show held and merged records**, with related record IDs. This
  avoids another active location without asserting that two branches are one.
- Keep explicit different addresses/house numbers/neighbourhoods/place identities
  separate. Similar spelling remains a review suggestion, not confirmation.
- Do not reassign previously held multi-venue observations on every replay.

CLI from `backend`: `uv run python -m app.manage sync-inventory`. The existing
**Add existing investigation findings** action uses this same repeat-safe operation.
Read-only SQL: `resources/sql/private_inventory_checks.sqlite.sql`, with `:owner`
bound to the private operator ID. Physical duplicate uncertainty still requires
the user's location review; SQL key uniqueness alone cannot prove real identity.

## Actual backfill

Backup before mutation: `data/backups/before-known-spot-skip-20261108T051054Z.db`.
Rehearsed on a separate consistent SQLite copy, then executed on the real local DB.
Receipts: `data/known-spots/backfill-final-rehearsal.json`, `backfill-live.json` and
`inventory-final.json`.

All **83 saved source records** were examined. Existing valid extracted locations
were already stored, so this replay inserted **zero new location records**. Cleanup
merged one supported duplicate and held four ambiguous duplicate proposals. The
result is **86 active pending locations**, with **126 originals retained**, including
held/merged history. A second replay inserted nothing and made zero cleanup changes.
SQL checks found zero repeated identity keys or duplicate explicit Maps identities.
No real venue was published or operator label/approval fabricated.

Main review export: `data/known-spots/pending-locations.csv` contains the 86 active
pending records. `identity-review-queue.csv` contains 28 held proposals separately;
`locations-for-review.csv` is the complete 126-original audit snapshot, including
merged history, address clues, source/menu links and duplicate-review references. CSV
formula-like values are escaped. It is a snapshot for review, not another live DB.
No existing pending queue record qualified for a live skip at the inventory audit;
the new skip paths are isolated-test/browser-fixture evidence until normal work
encounters a qualifying known reel. No live duplicate was manufactured as a test.

## GPU use

`OLLAMA_GPU_LAYERS=999` requests all supported model layers; `-1` restores automatic
placement. `KNOWN_SPOT_SKIP_ENABLED=true` enables discovery exits; false restores
full discovery processing. Fresh-checkout defaults remain conservative. The local
installation enables both after its recorded checks. Model weights, precision,
eight baseline frames and 4,096 text / 8,192 vision context remain unchanged.

Actual retained-caption smoke: `data/known-spots/gpu-all-layers-smoke.json`.
Ollama reported 100% GPU placement; calls took 12.332s initially and 4.396s warm.
Peak sampled memory 2,783 MiB, utilization 91%. A controlled four-frame 768×768
vision smoke at 8,192 context also completed with 100% model GPU placement, peak
3,345 MiB and utilization 100%; receipt `gpu-vision-smoke.json`.
These are limited placement/memory tests, not representative speed/accuracy or
sustained-load guarantees. Available GPU memory can change with other programs.
Local CPU speech transcription remains separate; no lower-precision model/cache,
smaller evidence sample, cloud provider or quota increase was introduced.

Final test/runtime evidence is recorded in the newest `docs/VERIFICATION.md` entry.
Further CPU preparation overlap and output-format experiments from the speed
proposal remain separate work; they must not be described as delivered here.
