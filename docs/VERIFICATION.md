# Dedicated duplicate agent — 8 November 2026

Read [DUPLICATE_AGENT.md](DUPLICATE_AGENT.md). Implemented and locally tested:
durable local duplicate lane, conservative identity evidence, caption/sign
co-reference, full-clique checks, short locked fresh revalidation, held-source
manual merges, conflict-safe hash redirects/legacy cleanup, explicit private UI,
terminal retry/version handling and account export/erasure. No new model trained.

- **345 backend tests passed in 78.94s** after the final branch-conflict guard;
  new files pass configured Ruff, repository `--select F` checks pass, strict web
  build passed. A broader optional lint selection found existing style findings
  in unrelated files (not claimed fixed/clean).
- **20 isolated desktop/mobile checks passed in 34.9s**. These include eight new
  duplicate desk checks, pagination, accessibility, unselected branch confirmation,
  no merge on load, explicit held-source merge, and no automatic mutation replay.
  An earlier run lost its isolated server during a controlled service stop and
  had connection-refused failures; restarting that isolated service and rerunning
  the full selected suite passed. No synthetic venue/approval entered local data.
- Separate full-size real-data copy: 989 eligible rows / 6,965 pairs; three merges
  in 20.095s, repeat zero in 20.786s, integrity `ok`. This is a rehearsal of saved
  evidence, not independently labelled accuracy.
- Fresh pre-apply backup `data/backups/batore-20261108T142244Z.db`. Actual tracked
  local pass: 1,007 eligible rows / 7,150 pairs; three merged drafts, **12.961s**
  execution. Repeat zero. All originals retained; no venue/claim writes.
- Real API/worker restarted; one interrupted owned analysis job requeued without
  resetting request/spending counters. The independent lane completed a scan,
  authenticated status HTTP200, zero model calls. Local initial unlimited mode
  remains enabled. New worker error log empty at the recorded short check.
- 14:26 UTC / 19:56 IST: 948 active / 144 held / 16 merged =1,108 originals;
  372 sources, 41/168 grid combinations scheduled, zero venues/claims. At the stable
  duplicate scan, 215 possible pairs awaited review. Healthy structural SQL audit:
  integrity `ok`, no audited orphans/duplicate identity-key groups. This does not
  imply an absence of physical duplicates or prove fact accuracy.
- Human exact-branch/duplicate decisions, measured real merge accuracy, sustained
  growing-inventory reliability, city completeness and customer validation remain
  open. All locations still need explicit approval before recommendations.

Ignored receipts: `data/duplicate-agent/` (separate rehearsal, live jobs, API/lane
checks, controlled recovery); progress/CSV snapshot: `data/city-collection/`.

14:29 UTC / 19:59 IST follow-up: API health and authenticated duplicate status
HTTP200, latest independently completed duplicate job `done`; **218 possible
pairs** as collection added evidence. Structural audit still healthy. Consistent
post-change backup: `data/backups/batore-20261108T142926Z.db`. The earlier 215-pair
count is a historical scan, not a fixed total or confirmed-duplicate count.

---

# Instagram workflow documentation — 8 November 2026

Current code and non-secret settings traced into
[INSTAGRAM_AGENT_FLOW.md](INSTAGRAM_AGENT_FLOW.md): discovery/direct collection,
caption → video → comments order, immediate draft persistence, repeated known-place
checks, sampling, identity/trust/approval gates and correction retrieval. The example
is explicitly fictional and was not inserted into the DB. Documentation-only;
no new test run, connector/accuracy verification or runtime change is claimed.

---

# SQLite contention repair — 8 November 2026, 15:13 IST

Read [SQLITE_RELIABILITY.md](SQLITE_RELIABILITY.md) for the measured scope and
remaining limitations. This supersedes the earlier repair-unverified status.

- **292 backend tests passed in 37.24s**; required Ruff and strict production web
  build passed; **12 isolated desktop/mobile checks passed in 17.9s**. New checks
  cover reconciliation parity/complexity and SQLite retry/checkpoint behavior,
  sanitized API 503, read retries and no automatic mutation replay.
- Separate-copy full-inventory cleanup/commit on 811 originals: **3.7926s / 3.6023s**,
  no merge/hold/evidence changes, integrity `ok`. Concurrent writer probe: one
  completed write, 7.425s across both passes, zero errors. The earlier ~60s old
  fuzzy-pass comparison is an extrapolation from a 50×679 sample, not a measured
  full before/after cleanup benchmark or an accuracy claim.
- Pre-change consistent backup `data/backups/batore-20261108T093634Z.db`; controlled
  stopped-worker recovery requeues four owned interrupted/stale jobs, refunds only
  their interrupted claim, preserves source checkpoints/request/spending counters.
- Actual restart local/unlimited; repeated launch preserves API23848/worker18256
  redirector PIDs and ownership records. Live cleanup HTTP200/7.063s; **24/24**
  concurrent API reads HTTP200, max7.435s. No new lock errors at the short check.
- 09:43 UTC: 692 identified/111 held/12 merged, 168 sources, zero real venues or
  accepted claims. No user approval, training, paid activation or city completion.
- Long-running/growing-inventory validation remains open. Evidence is under
  `data/reliability/`; current inventory/progress snapshots remain separate files.

09:45 UTC follow-up: live structural/integrity audit healthy; current progress/CSV
snapshots refreshed; no new restarted-log error/traceback/lock matches at final
check. Consistent post-change backup created at
`data/backups/batore-20261108T094543Z.db`. This remains short-run evidence only.

---

# Live status audit — 8 November 2026, 14:51 IST

Read-only runtime/SQL audit; application tests were not rerun and no code/config
was changed. Refreshed local progress and CSV snapshots.

- 09:21 UTC: 679 identified, 110 quarantined, 12 merged originals; 801 total.
  156 source records, zero real venues/accepted claims. 15/168 queries scheduled.
  Gaps: 424 menu/price, 586 hours observations, 643 vibes, 679 Maps reviews.
- API healthy; worker heartbeat 5.29s old. Initial unlimited mode enabled, preserved
  aggregate counter 1,396/browser 80. Snapshot records 776 done, 594 queued and four
  `running` rows. At the preceding read one running lease was expired: these rows
  are not proof of four concurrent active tasks. No terminal failed jobs recorded.
- Most queued work has source cooldown waits. Logs also show intermittent SQLite
  write-lock exceptions in worker claim/API counter operations. The collector
  continued progressing; lock root cause and remediation remain unverified/open.
- Live schema-7 structural/integrity audit healthy: no missing tables/indexes,
  duplicate identity-key groups, audited orphans or integrity violations. This
  does not disprove intermittent contention or establish physical branch accuracy.

---

# Initial collection without daily count caps — 8 November 2026

User explicitly authorized removing app daily caps until the initial database is
collected. Read [BULK_COLLECTION.md](BULK_COLLECTION.md). Older 300/300-wait checkpoints
below are historical, not the current effective cap.

- **Implemented/local tests:** **283 passed in 51.92s**, Ruff passed. Coverage
  includes preserving/incrementing an exhausted counter beyond 300; browser counts
  above the old daily cap while host spacing remains; local-only activation and
  normal-mode restoration; zero paid budget blocks HTTP; persistent Retry-After
  waits; fair queue selection; transient deferrals retain retry allowance; private
  queue resumption; unlimited daily cases/bounded simultaneous work; explicit INR
  menu/hour/amenity observations and unassigned multi-business menu data.
- **Web:** strict production build and **eight desktop/mobile checks in 14.7s**
  passed, including unlimited usage copy plus existing coverage/skip/full-inspection
  controls. Source-mutating fixture requests intercepted; no real approvals/labels
  or invented venues inserted. Browser API reads use the actual local operator.
- **Actual operation:** pre-change consistent backup
  `data/backups/batore-20261108T070103Z.db`; enable local bulk flag and resume CLI
  wakes **541** owned queued legacy/app-limit waits. Counters/cooldowns preserved.
  API/worker restored. At 07:12 UTC aggregate counter **333** (was exhausted at 300),
  new classified free attempts **33**, browser visits **20** (was 14), sources
  **86** (was 83), and seven grid queries scheduled (was five). This establishes
  real progress after removing the cap; counts are attempts/reservations and do
  not audit every HTTP request inside browser/search subprocesses.
- **Unchanged gates:** monthly paid spending reservations, actual source-side
  retry/access handling, GPU model precision, canonical deduplication/held originals,
  ownership, current-fact/location approval and internal-only release. No cloud
  inference/paid connector activated, trained weights produced, human label/approval
  manufactured or finished-city guarantee made. Real 429-path behavior is covered
  by controlled tests, not a newly induced live 429.
- **Remaining:** inventory 568 active/98 held/12 merged at that snapshot. Additional
  sources need analysis and place/fact corroboration; source growth alone does not
  establish a new venue or improved factual accuracy. Current facts, broader
  coverage, representative human evaluation and explicit final location approvals
  remain unfinished. See current `data/city-collection/runtime.json` / `PROGRESS.md`.

Follow-up 07:17 UTC: counter **410**, new free adapter reservations/attempts **110**,
browser **24**, sources **88**, inventory **574 identified / 98 held / 12 merged**
(684 originals); zero real venues/accepted claims. API healthy, heartbeat 2.75s old.
Snapshot `data/backups/batore-20261108T071743Z.db`. Final focused suite **12 passed
in 1.92s**, including mocked HTTP-429 → saved Retry-After → no second HTTP request
during cooldown. Current coverage gaps 455 menu/price, 515 hours observations,
539 vibes, all 574 Maps-unreviewed. No live 429 was manufactured.

---

# Coimbatore collection — 8 November 2026, 11:47 IST

Read [COIMBATORE_COLLECTION.md](COIMBATORE_COLLECTION.md). This supersedes the earlier
86-active-draft runtime checkpoint below; it does not supersede its accuracy limits.

- **Isolated tests:** full backend suite **271 passed in 57.16s**, required Ruff
  passed; final targeted directory suite **21 passed in 1.98s** after adding an
  additional privacy/export/erasure regression. Coverage includes repeat-safe
  source IDs, owner separation, address/distance branch conflicts, weak area-only
  holds, merged/rejected originals, category/radius/NaN/invalid-ID rejection,
  partial/missing-boundary failure, cache reuse without HTTP, scope reconciliation,
  private API/export/erasure, unsafe website hints and caption persistence before
  a location-lookup failure. No fixtures/labels were inserted in the real DB.
- **Web:** strict production build passed; **six controlled desktop/mobile tests
  passed in 12.5s** (attribution/raw-hours/coverage display plus existing known-spot
  skip/full-inspection controls). Separate actual local inventory browser reads
  loaded all **568 cards** on both devices in approximately 2.6/2.3s including
  navigation; no page errors or horizontal overflow. This is a limited local UI
  smoke, not a service latency SLA or a collection throughput measurement.
- **Actual collection:** two HTTP-200 public Overpass responses. Broad: 635 entries,
  526 in radius/categories, 523 new originals and three updates. A scope audit
  found Kerala entries in the radius; a Coimbatore administrative-area query
  returned 477 entries (three boundaries + 474 POI objects). The latter corresponds
  to 471 retained candidate identities: 453 active/18 held. District relation
  1819317 plus North/South subdivision metadata is retained. This is not a precise
  municipal census or independent branch verification. The original broad cache
  is archived; 51 previously active absent references were quarantined for review.
- **Rehearsals:** separate-file broad import/replay 523/0 new originals;
  `quick_check=ok`. Separate scope rehearsal and repeat: zero new rows, 51/0 new
  scope holds, integrity healthy. Actual tracked broad job completed in 107.8s;
  scoped job completed in 4.04s using the already fetched cache. These timings
  exclude the network fetch and do not measure whole-city investigation speed.
- **Local inference:** six queued caption jobs completed on actual retained source
  text; drafts increased from 86 to 115 before directory insertion. Existing Ollama
  and full-GPU request retained; no newly trained weights or human labels. This
  demonstrates execution/persistence, not correct extraction of every candidate.
- **Final DB:** **678 retained originals = 568 identified + 98 quarantined + 12
  merged**. **83 research sources, zero venues, zero accepted claims, zero human
  location approvals/corrections/creator assessments**. Live schema-7 audit healthy,
  no missing tables/indexes, duplicate identity-key groups, or audited orphans;
  SQLite integrity `ok`. Physical duplicates where identity evidence is weak remain
  unmeasured. Consistent post-import backup:
  `data/backups/batore-20261108T061709Z.db`.
  That snapshot was independently opened read-only: `quick_check=ok`, 678 original
  rows. Final SQL audit confirms 474 scoped objects map to 471 rows and there are
  zero repeated active directory references (`final-sql-check.json`). This does
  not establish the physical identity of unresolved similar-name locations.
- **Runtime:** API healthy in local mode; autonomous worker separately running,
  heartbeat 2.06 seconds old at receipt. Directory mode enabled, existing
  pipeline/reuse/known-skip/full-GPU settings retained. Shared external allowance
  **300/300**, browser **14/30**, directory **2/2** this ISO week. No allowance reset,
  paid provider activation, Google Maps identity confirmation or public release.
  534 queued jobs at the recorded snapshot; pending external requests wait for
  ordinary allowance availability. This does not mean they are downloading now.
- **Evidence:** `data/city-collection/` raw/archived/scoped fetch JSON/receipts,
  `rehearsal-result.json`, `scope-rehearsal-result.json`, `runtime.json`,
  `coverage.json`, active/held/all CSVs, `PROGRESS.md`, `live-ui.json` and screenshots.
  OSM attribution/licence retained per record and in the UI/exports.
- **Unfinished:** 455 drafts without menu/price evidence, 512 without hours
  observations, 533 without vibes, 568 without operator Maps review; current facts,
  representative accuracy/correction/creator evaluations and final user approvals
  remain open. Five of 168 search-grid queries scheduled is not city completion.

---

# Known-location policy, canonical inventory and GPU — 8 November 2026

Read [KNOWN_LOCATION_EARLY_EXIT.md](KNOWN_LOCATION_EARLY_EXIT.md). This is the latest
implementation/runtime checkpoint; historical measurements below remain retained.

- **Backend:** final **251 passed in 51.22s** with isolated databases; required Ruff
  passed. Nineteen new policy/identity regressions cover exact known-post exit
  before network/inference, caption branch matching, multi-venue/compilation and
  unknown-address rejection, different houses, manual/maintenance bypass, held
  and labelled sources, owner boundaries, immediate draft persistence, actual
  inspected-frame coverage on early exit, cache rejection of partial results,
  repeat-safe backfill/unassigned evidence, ambiguous duplicate holds, concurrent
  alias insertion and export/erasure of retained skip references.
- **Web:** strict TypeScript/production build passed; final **20 passed in 58.7s**
  on desktop/mobile Chromium. Includes skipped-coverage notice, retained original
  links, explicit full-inspection request, existing location/approval/correction,
  timing and evaluation gates. Covered accessibility checks passed. Source/label
  mutations intercepted; no test fixtures inserted into real inventory.
- **Real DB:** consistent pre-change backup, separate-copy rehearsal and actual
  backfill, then repeat. **83 sources, 126 spot originals retained: 86 identified,
  12 merged, 28 quarantined.** Cleanup adds one supported merge/four ambiguous
  holds; no new location insertion was necessary. Second replay yields zero
  insertions/cleanup changes. Source/spot evidence is retained. No accepted claims,
  real venues, creator assessments, correction examples or human labels exist.
- **SQL:** read-only duplicate checks report zero repeated identity keys and zero
  duplicate explicit Maps references. These do not prove physical identity where
  addresses are unknown. SQLite write serialization/unique-conflict handling is
  implemented and concurrency tested. Live DB and consistent restored snapshot
  pass schema-7 structural/integrity/index/duplicate/orphan checks. No migration
  or PostgreSQL deployment occurred.
- **GPU:** `gpu-all-layers-smoke.json` records two real retained-caption calls with
  999 requested GPU layers, 100% model GPU placement, 12.332s initial/4.396s warm,
  peak 2,783 MiB and 91% utilization. `gpu-vision-smoke.json` records a controlled
  four-frame 768×768 synthetic memory test at unchanged 8,192 context, full GPU
  placement, peak 3,345 MiB and utilization 100%. No weights, model precision,
  sampling budget or KV precision changed. These are limited placement/memory
  smokes, not an extraction-accuracy, sustained-load or complete-reel speed proof.
- **Runtime:** healthy local API, worker heartbeat six seconds old at receipt;
  existing pipeline/reuse/browser settings retained, known-spot skipping true,
  GPU layers requested 999. No quotas reset, paid connector/cloud model activated,
  approval fabricated or public release enabled. No existing pending record
  qualified for a real skip at this audit; live cases were not manufactured to
  create a success claim. Skip behaviour has isolated/backend/browser evidence.
- **Artifacts:** backup `data/backups/before-known-spot-skip-20261108T051054Z.db`;
  rehearsal/live backfill, GPU, SQL and runtime JSON plus restored snapshot under
  `data/known-spots/`; `locations-for-review.csv` contains source/address/menu and
  held-record references for later operator review; `browser-final/` holds traces
  on failures. Read-only SQL in `resources/sql/private_inventory_checks.sqlite.sql`.

Remaining: actual branch/menu/freshness accuracy and user approvals, normal live
skip executions and sustained throughput; other proposed CPU-preparation/output
experiments were not implemented by this step. A discovery skip explicitly leaves
remaining evidence uninspected and cannot be called a complete fresh investigation.

---

# Read-only worker speed profiling — 8 November 2026

Receipt `data/performance/speed-audit-20261108.json` records retained actual worker
deliveries: 46 model responses/calls, 1,162.32s model phase, 926.78s generation
(79.7%); six speech passes average 33.47s. Eight completed source-analysis jobs
have median execution 144.15s and range 34.29–595.16s. These exclude preceding
collection, queue/quota and approval waits, can include missing modalities, and
do not establish accuracy or representative capacity. Nested phases overlap.
Current UTC-day shared counter 300/300, browser 14/30. No code/runtime settings,
models, quotas or approvals changed; tests were not rerun for this documentation
and read-only inspection. Prior local tests below remain historical evidence.
Next proposals are recorded in PERFORMANCE_IMPLEMENTATION and the master checklist.

---

# Investigation improvements — 7 November 2026, 23:40 IST

Implementation: [PERFORMANCE_IMPLEMENTATION.md](PERFORMANCE_IMPLEMENTATION.md); P01–P10 derive from [INVESTIGATION_SPEED_AND_QUALITY.md](INVESTIGATION_SPEED_AND_QUALITY.md). This section supersedes the proposal-only status of the historical audit below. No model training, hosted inference, quota reset or operator approval occurred.

- **Backend:** final full run **232 passed in 35.22s**, isolated temporary SQLite; required Ruff passed. Thirty added performance regressions cover late/clustered frame sampling, Unicode/recursive offsets, explicit metadata/context/output overflow, all-venue/branch retention, failed/retried delivery timing, queue versus quota delay, owner/model/correction/holdout/expiry/erasure cache boundaries, changed-comment batches/indexes, durable pipeline and restart recovery, cancellation during GPU waits, browser EOF/context recovery, independent-label benchmark guards and new metrics export/submission/account erasure. Existing planner/menu/taste/approval/expiry/privacy tests remain passing.
- **Web:** strict TypeScript and production build passed. Final local operator/performance run **16 passed in 48.6s**, desktop/mobile; separate demo run **30 passed in 1.9 minutes**, two intentional viewport-specific skips. These are **46 distinct passing browser checks**. Local mutations/labels/benchmark requests were intercepted; demo records used `data/performance/demo-ui.db`, not the real DB. An over-exact test selector caused the initial new benchmark-UI test to time out; the locator was corrected and the complete final local suite passed.
- **Visual/accessibility:** actual Data readiness screen inspected at 1440×1050 and 390×844; no browser errors or horizontal overflow in those checks. Covered-state automated WCAG A/AA assertions passed. Receipts/screenshots: `data/performance/visual-check.json`, `readiness-desktop.png`, `readiness-mobile.png`; final browser artifacts in `browser-local-passed/` and `browser-demo-final/`. These are emulated Chromium checks, not physical-device/customer validation.
- **Actual local model:** `data/performance/smoke.json` records one retained agent-collected real caption, initially absent model, 18.026s first call including 11.174s load, then 5.912s immediate warm repetition including 0.015s load. Later guarded/persistent-client receipt `pooled-client-smoke.json`: 7.401s initial tokenizer construction, 5.251s warm reuse; token-guard time falls from 1.687s to 0.088s. Output counts are unlabelled and do not prove correct names/branches or equal factual accuracy. These few caption calls are not per-reel, ASR/vision, paired old/new or sustained-throughput results.
- **Model placement:** Qwen3-VL 2B instruct unchanged. Ollama reported model bytes 2,338,198,648 and VRAM bytes 1,863,361,494, context 4,096 in caption calls. Partial GPU placement was observed. Subsequent idle `nvidia-smi`: 2,649/4,096 MiB, 0% utilization. No peak vision memory or purchase justification established. Whisper base, eight baseline frames, thirty collected-comment target and ordinary allowances retained.
- **Browser runtime:** two controlled offline pages ran in one actual Chromium process. Each fresh context started with zero cookies and ended with its own fixture cookie; matching caption and two exposed fixture comments retained; configured readiness reached. Per-request context closure, helper reuse/EOF restart and partial-sample waits tested. **This is not live verification of the new reused-helper path against public Instagram**; old direct-browser live receipts remain historical evidence for the older path.
- **Runtime/storage:** local API/worker restarted with reuse/pipeline/browser flags true and `OLLAMA_KEEP_ALIVE=10m`; fresh-checkout defaults remain off. `data/performance/runtime-final.json` confirms local healthy API and heartbeat age five seconds. Schema stays **7**, no migration required. A consistent SQLite backup restored to `restore-audit.db` passes integrity/structural/duplicate/orphan audits. The original pre-change backup is `data/backups/batore-20261107T142616Z.db`.
- **Actual data preserved:** before-enable comparison confirms **70 source records; 111 identified-spot originals** (76 active, 11 merged, 24 held); **zero real venue claims/venues, corrections, source assessments, labels or publications**. Jobs at the receipt: 279 done, two cancelled, 59 queued. Source/spot counts and empty publication/label state stayed unchanged; normal worker scheduling/timing and operator session counters changed. No fixture approval or gold label was inserted.
- **Allowances/reporting:** shared external counter **300/300** and browser **30/30** on the UTC day remain exhausted. Report includes 61 measured job deliveries and 279 earlier unmeasured jobs; its short delivery percentile consists largely of quick deferrals, **not fast reel inference**. Scheduled waits and failures remain visible. Worker suspension during implementation also contributes to eligible queue age. No counters were reset or caps raised. Temporary demo API/worker were stopped; real local port 8000 remains healthy.
- **Privacy/rollback:** detailed owner job timings join account export and erasure. Submission removal also removes related source/comparison/watch jobs and correction rows; standalone timed submission analysis is erased with the account. Cache copies retain original computation time and origin identity. The three switches and bounded residency setting provide independent rollback; pending jobs/evidence are retained and no SQL downgrade is required.

**Still unverified:** independently labelled English/Tamil/code-switched extraction, real exact branches/visual clues and unsupported-fact rates, correction benefit, creator calibration, new-browser live coverage, whole-reel speed/memory under load, matched baseline wall times, several days of operation and invited-user outcomes. The uncached benchmark implementation supports labelled retained captions/comments; it cannot supply missing human labels, historical timing or representative video/branch coverage. No claim that all P01–P10 validation is complete or that customer-ready accuracy is established.

---

# Read-only speed/quality audit — 7 November 2026, 19:43 IST

Report: [INVESTIGATION_SPEED_AND_QUALITY.md](INVESTIGATION_SPEED_AND_QUALITY.md); receipt `data/investigation-speed-audit.json`. Inspected current code/config/SQLite and local hardware, plus official Ollama/faster-whisper documentation. External shared allowance 300/300 and browser allowance 30/30 exhausted, 55 jobs queued. GPU RTX 3050 Laptop 4,096 MiB; six-core/twelve-thread Ryzen 5600H. No inference was active during `ollama ps`; the idle zero-VRAM observation is not evidence that actual inference uses CPU.

No execution-start or stage-duration fields exist in job/task records; queue age is not measured inference duration. Zero independent labels/corrections prevent a no-accuracy-loss claim. Code inspection identified frame endpoint loss under candidate-budget truncation, blind local input slicing and multi-venue candidate limits; proposed regressions/fixes are recorded, not implemented in this step. P01–P10 remain planned. No code/config changes, counter resets, source collection, model training/cloud inference or benchmark execution; application tests were not rerun for this documentation-only task. Local API/worker left unchanged.

---

# UI refresh — 7 November 2026, 19:21 IST

See [UI_REFRESH.md](UI_REFRESH.md) for the Before/After review, arrangement and limits.

- **Implementation:** refreshed forest-green navigation, current-page header/title, compact Discover introduction and grouped planner fields, readable shared typography/controls, complete mobile cards, wrapped operator controls, preference grid and taste shortcuts, dedicated food/cafe menu tab, compact secondary venue views and explicit saved/operation selection states.
- **Interactions:** closed mobile sidebar inert/hidden; open drawer labelled, focus trapped, Escape dismisses and body scrolling locks; route/viewport changes close it. Native dialogs explicitly restore focus. Venue tabs expose labelled panel, roving focus and Arrow/Home/End handling. Search distinguishes loading, empty and error states and offers retry/reset.
- **Build:** strict TypeScript and production build passed. No new dependencies or hosted font/image services; backend code unchanged. The earlier 202 backend tests remain prior evidence, not a new run for this task.
- **Final demo run:** **30 passed in 1.7 minutes**, two intentional viewport-specific skips. Covers core plan/save/visit/profile, submission/processing, guided discovery/investigation outcomes, dish search/filter/diary/correction learning, new UI interactions, six-screen automated WCAG A/AA, and PWA/offline private-data exclusion. Output `web/test-results/ui-release/`.
- **Final local operator run:** **12 passed in 37.3s**, desktop/mobile, covering maintenance, independent label form, autonomous research controls, corrections/revocation, identified evidence and Maps/held review. Fixture mutations intercepted; no synthetic facts/labels/approvals entered real inventory. Output `web/test-results/ui-local/`.
- **Responsive/visual evidence:** geometry checks at 360, 600, 768, 900, 1024 and 1440 CSS pixels over Discover/Places/Taste/Sources/Operations. Six-screen before/after screenshots at 390/1440px plus menu/plan/card views under `data/ui-redesign/`. Captured reports showed no document overflow or page errors; main screens and detailed card/menu/plan views inspected. This is Chromium emulation, not physical-device/other-engine validation or a full assistive-technology audit.
- **Corrected failures:** strict build caught route-location shadowing; mobile review caught legacy 100%-image height clipping the card body; keyboard assertions caught missing dialog focus restoration. Initial expanded run lacked the separate demo worker; it was started with source discovery/browser collection disabled. The source test now allows the documented 15-second UI polling interval. Final runs passed; failures are not counted as passes.
- **Runtime/data:** actual local API/worker remained running; mode `local`, UI `en`, updated screen/browser title and 1440px fitting document observed at `http://127.0.0.1:8000`. Receipt `data/ui-redesign/local-mode.json` and screenshot. Only temporary demo API/worker stopped after checking their exact PIDs/commands. No DB schema change, provider activation, model training, real fact acceptance or location approval performed.

UI01–UI05 are implemented/local verified. FH14/real accuracy, reviewed inventory, explicit per-location user approval and invited-user testing remain pending.

---

# FavHiker shared features and schema 7 — 7 November 2026

This supersedes older competitor-coverage/schema/runtime counts below. Full research and operator procedure: [FAVHIKER_DEEP_REVIEW.md](FAVHIKER_DEEP_REVIEW.md).

- **Research:** official product/planner/format/category/mall/restaurant/connector pages, indexed Coimbatore pages and app stores reviewed. Four anonymous browser requests returned CloudFront 403 (`data/favhiker-deep-review/anonymous-browser.json`). Different cached versions appeared. Coimbatore presence and shared mood/budget/diary/AI-review capabilities are established as public feature evidence; authenticated behavior, menu truth and generated plan quality remain unverified.
- **Engineering:** typed reviewed menus, dish/cuisine search, same-item diet/price filters, reviewed formats/amenities, stable pagination, complete owner saved places, desired-state bookmarks, private dish diary, cuisine/spice choices, reversible learning, visit edit/delete/context snapshots, independent novelty, dish-aware planner prechecks, exact Maps links, balanced deduplicated review support and new-record privacy coverage. Fact acceptance never grants location approval.
- **Backend:** required Ruff passed; final full run **202 passed in 31.74s**, temporary isolated SQLite databases. Regressions cover invalid/unknown menu fields, NaN/bool/string prices, normalized duplicates, unknown diet, expired evidence, same-dish combined filters, records beyond first 300, repeat-safe saves/learning, ownership, opt-out/rebuild, future dates/collisions, edited/deleted history, privacy, approval gates and requested-dish priority within bounded live checks.
- **Review evidence:** typed praise/complaint/mixed/mention with links and dates. Shared URL/origin groups collapse transitively; conflicts become mixed. Expired/unaccepted signals cannot count. These are bounded reviewed groups, not independently verified people or all platform reviews. No live sentiment accuracy or latest-100 Google access is claimed.
- **Web:** strict TypeScript/production build passed. Final new-feature run **10 passed in 36.9s**; local research **12 passed in 52.3s**; earlier core/accessibility **8 passed**, desktop/mobile. Checks cover filters, unknown amenities, dish/outing price distinction, persistent diary/edit/delete, novelty constraints, reversible visits and balanced sources. Automated WCAG A/AA assertions passed in covered states. Local mutations intercepted; no fixture facts/labels/approvals written to real inventory. The review-support example is an intercepted UI fixture.
- **Visual:** menu/diary desktop/mobile screenshots inspected in `data/parity-visual/`; checked viewports had no horizontal overflow. Evidence dates now show years; source links underlined after accessibility caught insufficient distinction. This is not a full manual assistive-technology audit.
- **Corrected failures:** initial selectors/fixture endpoint, missing `km` import, duplicate normalized taste tags and source-link accessibility were fixed. Concurrent browser runs collided on the shared trace directory (ENOENT on teardown); final runs were sequential with separate outputs. Failed attempts are not counted as passes.
- **SQL:** actual local DB now **schema 7**: private diary, visit snapshot and unique owner/venue/dish and owner/venue/date indexes. Backup rehearsal and actual migration each executed twice, preserving every existing row count. Audit: integrity `ok`; no missing tables/indexes or detected duplicate/orphan groups. Receipts `data/parity-migration-rehearsal.json`, `data/parity-live-schema7.json`; SQL exports `resources/sql/schema-v7-sqlite.sql`/`schema-v7-postgresql.sql`. Relationships remain application managed; PostgreSQL execution/RLS-role testing remains unverified.
- **Restore:** final online snapshot `data/backups/parity-final-20261107T130916Z.db`, separate restored copy `parity-final-restore-20261107T130916Z.db`, schema-7 audit healthy; live DB not replaced. Receipt `data/parity-final-status.json`.
- **Actual inventory, 18:39 IST:** 56 active candidates, 10 merged and 24 held originals; 61 sources; **zero venue claims/approvals/venues, evaluation labels or corrections**. Twelve successful stored source watches have `access=public_content`, superseding the earlier deferred checkpoint. These do not prove universal comments, menu accuracy or sustained monitoring. Private packets exported to `data/review-packs/review-20261107T130632Z.md`/`.json` without approval.
- **Runtime:** local API/worker restarted, schema 7, `http://127.0.0.1:8000`; authenticated diary/saved-place/filtered-browse and maintenance returned successfully. Snapshot: 204 jobs done, two cancelled, 70 queued, one running; heartbeat age 143 seconds during synchronous work, not claimed as continuous liveness proof. Collection can change counts. No extra paid connector, cloud inference, training or public release.

FH01–FH13 engineering is implemented/local tested. Actual branch/menu/amenity review, explicit user approval, independent multilingual/sentiment labels, matched competitor outcomes and invited-user validation remain pending. Perfect accuracy, complete coverage and competitive superiority are not established.

---

> PDF export checked: `docs/exports/FavHiker-vs-Bites-by-Batore.pdf` reproduces the last user-facing competitor comparison across two pages. Extracted key text, rupee symbol and four source hyperlinks verified; both rendered pages visually inspected. Document-only work; no app tests or runtime changes required.

> 7 November competitor research: [FAVHIKER_COMPARISON.md](FAVHIKER_COMPARISON.md) records public product/store evidence and inspection limits. Food personalization and advertised mood-based planning overlap substantially. Planner routes returned HTTP 403; no authenticated plan or competitive quality benchmark was tested. Documentation only; application tests were not rerun and no runtime changes made.

# SQL schema 6 and stage continuation ? 7 November 2026, 00:39 IST

- **SQL implementation:** serialized/transactional additive migration and version ledger; rejects future schemas; unique source-per-case and task-ordinal indexes; six query/recovery indexes; corrected live startup schema constant; read-only integrity/orphan/duplicate audit; generated SQLite/PostgreSQL schema files. Application-managed relationships are audited; no universal SQL foreign-key enforcement claim is made.
- **Migration evidence:** pre-upgrade online snapshot `data/backups/batore-20261106T185613Z.db`; separate rehearsal upgraded twice with every existing table count preserved. Live schema 6 audit: integrity `ok`, no missing tables/indexes, no duplicate groups or orphaned audited relationships. Reports: `data/sql-migration-rehearsal-20261107.json`, `data/sql-live-audit-20261107.json`.
- **Final restore:** `data/backups/batore-20261106T190720Z.db` restored separately to `schema6-final-restore-20261107.db`; schema-6 structural audit healthy. Receipt `data/sql-final-restore-20261107.json`. Live DB was not replaced by the restore drill.
- **Stage 6 fixes:** browser/provider allowances reserve atomically, avoiding false visit consumption on a deferred call. Reel watches now have priority 98, ahead of bulk inventory; existing queued watches reprioritized without resetting counters. Changed captions queue a private repeat-safe fresh investigation; operator approval remains mandatory. Watched caption text expires using its own 24-hour timestamp.
- **Backend tests:** full suite **168 passed in 22.76s** before final retention/startup regressions; final affected suites **56 passed in 6.26s**. Covers concurrent migration startup, duplicate rollback preserving originals, future-schema refusal, generated SQLite execution, real-version startup gate, atomic quota failure/success, repeated changed-caption handling, and independent source-watch retention. Required Ruff check passed.
- **Browser tests:** **12 desktop/mobile checks passed in 36.0s** against the local instance. Fixture mutation requests intercepted; no fictional data, evaluation labels or approvals written to the real inventory. No web implementation changed in this continuation.
- **Live monitoring boundary:** direct attempt saved `data/reel-watch-check-20261107.json`: quota-deferred, allowance counters unchanged, no successful new watch receipt. UTC-based daily limits had not reset at 00:39 IST. Do not count this as a successful Instagram recollection or sustained monitoring validation.
- **Runtime:** one fresh local API tree and one worker tree; health `ok`, authenticated maintenance endpoint 200, heartbeat about four seconds old. Schema 6; 178 jobs done/two cancelled/48 queued. 49 active drafts, zero ready/approved/published, 59 page checks/eight overdue/one open conflict. `data/sql-stages-final-20261107.json` contains the snapshot.
- **Dataset/model comparison:** 51 source records, 47 distinct URLs, 26 video analyses; zero operator labels or corrections; seven retained raw captions, four transcripts, zero cached media payloads. Current GPU confirmed RTX 3050 Laptop 4,096 MiB, RAM about 15.4 GiB. Provider prices and capabilities checked against primary docs; calculations saved with explicit hypothetical token/FX/throughput assumptions. No paid requests, uploads, training or provider switch. See `MODEL_OPTIONS_COMPARISON.md`, `data/model-dataset-audit-20261107.json`, `data/model-cost-comparison-20261107.json`.
- **PostgreSQL boundary:** schema compilation/RLS statements exist; Docker engine unavailable. Actual PostgreSQL migration, role-based RLS and production restoration are not verified. Local-only SQLite operation remains the requested configuration.

The four stages remain open for real accuracy, verified inventory, user approvals and sustained live evidence. SQL engineering and automated tests do not satisfy those completion criteria. New private review packet: `data/review-packs/review-20261106T190719Z.md` and `.json`.

---

# Stages 1, 2, 3 and 6 execution ? 6 November 2026, 22:58 IST

Read [STAGES_1_2_3_6.md](STAGES_1_2_3_6.md). This is the latest execution record; older results below remain historical.

- **Implemented:** 168 topic/area discovery combinations; expanded first-party targets; explicit first-party cross-reference deduplication with conflicting evidence retained; owner-scoped maintenance reports/approval packets; daily page observations and retry checkpoints; weekly web/reel scheduling; critical-fact expiry holds and revision invalidation; alert-review audit; local Markdown/JSON export; held-out source correction exclusion.
- **Backend:** full suite **157 passed in 34.08s** before the final generic-description and expiry-audit privacy fixes. Final maintenance/identity/inventory suites **59 passed in 6.87s**, including generic-description and expiry-audit export/erasure regressions. A mistyped test filename initially caused a collection error/no tests; rerun used the actual `test_spot_quality.py` path. Required Ruff `--select F` passed. Tests use isolated DBs and do not label/approve real data.
- **Frontend:** strict TypeScript and production build passed. **12 desktop/mobile browser checks passed in 36.3s**, including maintenance alert review, private evaluation, scoped corrections and Maps/held-record review. Synthetic responses/mutations were intercepted; no invented fixtures or decisions entered the real inventory. Accessibility assertions passed in the covered screens.
- **Live collection:** first-party run fetched 11 distinct pages for 14 target entries. Kites Cafe remained unavailable. A duplicate Prozone Fun Unlimited target was joined using explicit first-party cross-reference, with both addresses/hours retained; a separate similarly named Instagram candidate was not automatically merged. One real alert records operator hours 11:00?22:00 versus mall hours 09:00?23:00. These observations are unverified.
- **Cleanup:** two generic descriptions (`a club in Coimbatore`, `Car Race Coimbatore`) were held with original evidence retained. Immediate repeat made zero changes. Current counts: **49 active drafts, 10 merged, 24 held; zero Maps-reviewed identities; zero prepared/published venues**. No approval was entered on behalf of the user.
- **Maintenance:** 59 persisted page-check records on active candidates, eight unavailable/overdue, one open conflicting-hours alert. These are page observations, not verified facts or 59 distinct sites. New reel-watch jobs have no successful live receipt yet: daily quotas deferred execution. Failure, change, retry, expiry and privacy paths have isolated regression coverage; sustained multi-day operation has not been proved.
- **Source evidence:** 51 records across 47 distinct URLs; 37 dated records; 26 with video analysis; 196 classified comments; six indexed reference images. Zero human evaluation labels; precision/recall and correction benefit remain unmeasured. Missing active-draft fields: 38 menu/price, 43 hours, 44 vibes. No exhaustive Coimbatore denominator exists.
- **Runtime:** API healthy in `local` mode at 22:58:33 IST; current worker heartbeat. 175 jobs done, two cancelled, 51 queued. Local provider allowance increased from 200 to 300; INR 3,000 target and 30/day browser pacing unchanged. Both daily allowances exhausted; queue waits for the next UTC date/05:30 IST allowance reset and scheduled retry. Counters were not reset; paid providers remain disabled.
- **Recovery:** consistent `data/backups/batore-20261106T172729Z.db` restored into a separate `restore-drill-20261106T172729Z.db`. Both passed SQLite `quick_check`; selected source/restored counts matched (83 spot originals, 51 sources, 228 jobs, zero venues). The live database was not replaced. This is a local restore drill, not cross-machine disaster recovery.
- **Artifacts:** `data/stages-1236-final-status.json`, `data/stages-1236-inventory.json`, `data/stages-1236-restore-drill.json` and `data/review-packs/review-20261106T172728Z.md`/`.json`. The manual `stages-1236-refresh.json` records quota deferral, not full refresh completion. Refresh private exports with `uv run python -m app.manage review-pack` from `backend/`.

Final restart verification at 23:04 IST found and resolved stale workspace-owned API/worker trees omitted by an older PID record. `scripts/stop.ps1` now discovers only redirector trees whose executable is this workspace's exact virtual-environment Python, retains PID creation-time checks, and leaves unrelated Python processes alone. Actual stop/start exercised the recovery; one fresh API tree and one fresh worker tree were confirmed, API health and authenticated maintenance report returned successfully, and the worker heartbeat was current. This does not install an automatic Windows startup service. The final expiry audit also follows owner-scoped export/erasure, with a passing regression test.

Full stage completion still needs representative independent labels, exact branch/fact review, sufficient city coverage, the user's location approvals, successful live reel monitoring and sustained maintenance/customer evidence. Mechanism tests do not satisfy these real-world dependencies.

---

# Owned-model feasibility research ? 6 November 2026

Documentation-only continuation. Read [OWNED_AI_FEASIBILITY.md](OWNED_AI_FEASIBILITY.md). Inspected hardware/configuration with CIM and nvidia-smi, read the existing local inference implementation, checked primary provider/framework/research sources and calculated costs with Python. Current data has 51 sources and zero saved independent evaluation tasks. No new model was trained, benchmarked or deployed; no weights or source files were uploaded; no spending occurred. GPU speeds, salaries, exchange conversion and electricity tariffs in the scenarios are assumptions, not verified measurements/quotes. Existing application tests below remain their historical results; this research did not require rerunning them. Product operation/configuration is unchanged.

---

# Instagram completion mechanisms ? 6 November 2026, 12:05 IST

This is the newest record and supersedes older statements that visual matching, structured comments and evaluation tooling are entirely unimplemented. Their real-world quality remains unverified. See [INSTAGRAM_COMPLETION.md](INSTAGRAM_COMPLETION.md) for the complete workflow and remaining checklist.

- **Implemented:** local ORB/reference-image geometry matching; branch/address conflict ranking and fresh Maps candidate ranking; resumable five-comment batches with explicit categories; bounded public reply-control expansion; owner-scoped creator history with uncertainty and prospective calibration metrics; private name/ASR/OCR/comment labels, origin-grouped holdout reporting, local correction comparison jobs, and evaluation-dependent release gates. No venue auto-approval or trained-weight claim was added.
- **Backend validation:** full suite **142 passed in 20.91 seconds**. After final image-decoding, label validation, input fingerprint and comparison revocation safeguards, the affected suite passed **14 tests in 5.71 seconds**. Required project Ruff `--select F` checks passed. An initial unrestricted Ruff invocation inherited additional rules and reported 316 findings; the project's required undefined/unused check is the passing result, not an all-rules lint claim. `git diff --check` passed.
- **Web validation:** strict TypeScript and production build passed. Eight existing local desktop/mobile checks passed. The new accuracy-review test initially used the wrong tab label (`Quality` instead of `Data readiness`); after fixing the test selector, both desktop/mobile cases passed in **10.6 seconds**, including accessibility checks. Review mutation requests and source records were intercepted; no fictional venue, gold label or correction was stored in the real DB.
- **Real local comment inference:** source `211eb963-c95e-44f0-bfff-dacbb9ae8054`, post `C7sl-Wloucq`, produced 12 classifications from 12 collected comments: 2 firsthand claims, 5 opinions, 3 questions, 2 unclear. These are model outputs, not independently verified categories. Receipt: `data/structured-comments-live-smoke.json`.
- **Revised public collector:** an actual anonymous request to that post returned HTTP 200, playable-video visibility and 12 source-bound visible comments. It reported more comments available and **zero expanded controls**, because exact-post controls were unavailable. Offline Chromium fixture tests exercise expansion and post scoping; successful real expansion is not claimed. Receipt: `data/comment-expansion-live-smoke.json`.
- **Real reference indexing:** first-party refresh read eight pages for nine existing targets. One WAGHOBA page image was indexed locally with 500 ORB features. A cross-host Prozone image was skipped with a recorded reason. No real reel-to-branch match was independently verified. Receipt: `data/visual-reference-live-smoke.json`.
- **Runtime checkpoint 12:05:27 IST:** API healthy in `local` mode; worker heartbeat seven seconds old. 51 source records, 37 with publication dates, 25 with video analysis; 46 active drafts; one indexed image; zero Maps-reviewed identities; zero human evaluation labels; zero published real venues. Missing evidence: 42 drafts without hours, 39 without vibes. A menu link is only an available lead, not a verified menu. Counts may include repeated sources across cases and are not exhaustive city coverage.
- **Background processing:** 97 jobs done, 74 queued (including 30 comment-upgrade jobs), two marked running at the snapshot. A running lease from the controlled restart is reclaimed by the durable worker after expiry; this is not a claim of two simultaneous executing workers. One owned API and one owned worker process tree were confirmed. Quota counters were not reset.
- **Backup:** consistent SQLite snapshot `data/backups/batore-20261106T063509Z.db`, read-only `quick_check=ok`. Runtime receipt: `data/instagram-completion-final-status.json`. No restore drill was performed in this step.

Still required: independent representative labels, successful real visual branch matches and false-match evaluation, measured correction-assisted improvement, prospective creator outcomes, optional provider validation, current critical venue facts, explicit user location approvals and invited-user outcomes. Public Instagram collection itself does not require Meta/Apify/Google keys. Everything remains local and internal; no locations were published.

---

# Identity and relevance verification - 6 November 2026

This is the newest verification record. [SPOT_IDENTITY_QUALITY.md](SPOT_IDENTITY_QUALITY.md) documents the workflow and limitations.

- **Implemented:** pre-insert normalized name/branch checks, conservative relevance holds, aliases, same-source evidence deduplication, ambiguous duplicate suggestions, retained merged/quarantined records, multi-venue observation isolation, explicit Maps-name/place review, and duplicate prepared-place guards. A specific place-ID/CID link is required; generic Maps search/coordinates do not confirm identity. Operator-reviewed false-positive names can collect further evidence for the same branch; new conflicting issues still cause a hold.
- **Actual existing-data cleanup:** at 10:59:16 IST, 66 originals became 36 active drafts, 8 merged records and 22 held records. No original records were deleted. Fifteen repeated list entries were deduplicated and 31 ambiguous observation/vibe associations moved out of venue-specific facts. The immediately repeated check made zero changes. Zero real venues were published. Later collection may increase counts.
- **Backend:** the full suite passed **128 tests in 21.74 seconds**. Additional final affected-suite results and runtime checkpoint are recorded below. Ruff undefined/unused checks passed. Coverage includes different owners/branches, missing areas, reordered/accented names, Tamil marks, different house numbers, source refresh receipts, idempotent cleanup, landmark/speech-only rejection, precise Maps URL validation, duplicate place guards, operator identity corrections/reapproval, held-list privacy and review export/erasure. Tests use isolated databases.
- **Actual local-model smoke:** two synthetic text examples, no inventory writes. The first model response incorrectly proposed `cafe near VOC Park`; the initial deterministic filter also missed it. A relative-description rule and regression case now hold that saved output. The outside-city fixture yielded no candidates. Replaying saved outputs through the repaired filter yields zero eligible candidates. This is a narrow failure-driven check, not proof of general extraction accuracy.
- **Frontend:** strict TypeScript and production build passed. Eight desktop/mobile checks passed in the initial UI run, including identified-spots accessibility and the new Maps-review/held-record flow. Synthetic UI records and mutation requests were intercepted; no fictional venue or reviewer correction was written to the real database. Final browser-run timing is recorded below.
- **Maps:** precise references and operator-confirmation boundaries are locally tested. The optional live Places lookup is not verified/configured in this environment. Existing names have not been independently checked on Maps by this maintenance work. The UI labels them unconfirmed and offers explicit review. Places API response payloads are transient; operator-reviewed identity data and place references are recorded separately. Public Instagram collection does not require Google, Meta or Apify credentials.
- **Backup before cleanup:** `data/backups/batore-20261105T190637Z.db` (UTC filename; 6 November in India). Final post-change backup/runtime evidence follows below. Local artifacts: `data/spot-quality-cleanup-2026-11-06.json`, `data/spot-quality-local-model-smoke.json`.

The full original Instagram scope remains unfinished: advanced visual place matching, calibrated creator reliability, broader accessible comments/replies, representative multilingual accuracy evaluation, live optional-provider validation, verified current city inventory, operator approvals and customer evaluation. None is marked complete by these data-quality fixes.

Final checkpoint, **6 November at 11:09:43 IST**:

- Final affected backend suites: **42 passed in 10.32 seconds** after the last reviewed-name refresh change. Final desktop/mobile browser run: **8 passed in 29.2 seconds**. Strict build and Ruff checks passed.
- API healthy in `local` mode. Worker heartbeat age 27 seconds; 76 durable jobs done, 59 queued and one running. One interrupted job was requeued during the controlled owned-process restart, preserving collected source progress and all quota counters.
- Autonomous collection added three further candidates after the initial cleanup. Current checkpoint: **39 active drafts, 8 merged and 22 quarantined records (69 stored originals), zero published real venues**. A final reconciliation set aside one more ambiguous association from newly collected evidence. These counts are not independently verified venue counts.
- Two actual public Instagram sources in case `eab94123-c606-475f-b9e8-c9224b44c1b6` now have local `observations_only` video results with **eight sampled frames each**: source `0774876b-373c-486d-a306-0955afc0fd26` (`DeGbKQBNpC1`) and source `2969fbc2-bee9-46d6-ada9-faddfd2f13f6` (`Dd1S8FTO1zR`). This closes the earlier deferred real eight-frame execution smoke; it does not measure factual, transcription or exact-location accuracy.
- An actual call to the Maps candidate endpoint returned `unavailable`, consistent with the unconfigured Google Places key. No Maps verification was inferred from the endpoint's existence.
- Post-cleanup snapshot `data/backups/batore-20261106T053906Z.db` passed read-only SQLite `quick_check` (`ok`). Runtime evidence: `data/spot-quality-final-status.json`. Backups preserve point-in-time data and have their own retention lifecycle; a restore exercise was not performed here.

---

# Inventory and all-source verification - 5 November 2026

This is the newest record. See [INVENTORY_COLLECTION.md](INVENTORY_COLLECTION.md) for the end-user review flow, collection procedure and original Instagram requirements that remain open.

- Real expanded Instagram case `64ae5da9-a63c-40e3-9367-1c4acf2dffa2` retained and streamed all **15** discovered sources. It downloaded **14 videos**, collected **83 loaded comments**, and saved **15 caption, 12 comment and 13 video** observation results. All eight stages finished in `review`; missing modalities remain gaps. This demonstrates removal of the former top-three cutoff, not exhaustive Instagram coverage.
- Date metadata was probed before selection and sorted newest-known-first. Browser data later supplied more precise dates for previously undated sources; initial selection ranks remain in evidence. Source fetching time and engagement counts do not rank sources as newer.
- Schema 5 adds owner-scoped identified spots. Automatic insertion during source processing and final verification yielded **66 candidate records** at the recorded checkpoint, including uncertain names/branches that need review and deduplication. No real location is approved or published.
- First-party inventory collection fetched **eight distinct pages** for **nine targets**. Stored data includes **120 menu item/price pairs**, map links, two destination-coordinate leads, listed park fees/hours, activity offerings and attributed vibe statements. These are proposals, not current accepted venue facts or per-person meal costs.
- Removed the accepted-facts auto-publication path. A separate explicit operator location approval and current essential facts are required. The planner excludes non-demo venues without location approval. Preparing a spot only creates a pending venue.
- New regression coverage checks six-source retention despite a two-source batch size, ten-source resumable date probes without repeated search, Meta cursor continuation, per-source draft creation across batches, daily-limit deferral without losing pending sources, menu item price units, source ownership/export/erasure, owned enrichment-job erasure, explicit publication gating, pending-venue preparation, unverified web enrichment and persistence after a DB reload.
- Scene detection was checked with an actual synthetic two-colour ffmpeg clip. An eight-frame grouping check verifies that every selected frame reaches a local inference group. Requested follow-up timestamps now work with the local path as well. The new real eight-frame browser replay was **deferred by the configured daily browser cap**, not declared passed. The 15-source live run predates that scene/grouping deployment and used four frames per video.
- Six desktop/mobile Playwright checks passed in **30.3 seconds**, including identified-spots accessibility, runtime visibility and correction flows. New source links initially failed the link-distinguishability check; underlining them fixed it. Correction mutations remain mocked to avoid polluting the live learning DB. Production TypeScript/build passed.
- Full backend suite: **99 tests passed**; final execution details and runtime/backup checkpoint are appended below. Ruff undefined/unused checks passed. All backend tests use isolated SQLite databases; no fictional test venue was inserted into the real inventory.
- After source processing, the browser daily allowance was exhausted. New reel jobs remain queued rather than discarding remaining sources. Public/official-page enrichment has its separate shared external-call allowance. Local pacing is 30 browser visits/day and 200 external operations/day; optional paid connectors remain disabled.

Final checkpoint, **5 November 2026 at 17:56:51 UTC**:

- Full backend suite finished with **99 passed in 39.46 seconds**. The six local browser checks and strict production build above passed against this update.
- An actual local Ollama run processed a generated two-colour video using eight sampled frames in two inference groups. It returned observations and no venue candidates; nothing was inserted into the inventory. Evidence: `data/layered-synthetic-smoke.json`. This exercises real local inference but is not real-reel accuracy validation.
- After restart, the loopback API reported healthy `local` mode, schema 5, eight-frame budget, three-source processing batches and daily inventory refresh enabled. Worker heartbeat age was two seconds; durable jobs contained 75 done and 57 queued. One adventure/go-karting case remained running with pending collection. Queued work is not completed work.
- The database contained 66 identified candidate records, 51 source records and **zero published real venues**. Seventeen draft spots had persisted web-search work and eight candidate web-source associations. Those pages remain unverified candidates, not authenticated first-party evidence.
- SQLite backup `data/backups/batore-20261105T175647Z.db` passed read-only `PRAGMA quick_check` (`ok`). Runtime and backup details are recorded in ignored local artifact `data/inventory-final-status.json`. This is an integrity check, not a full restore exercise.

Still open: advanced visual reference-image geolocation, calibrated creator reliability, broader public comment/reply coverage, representative labelled speech/OCR/location/comment accuracy, verified current Coimbatore inventory, operator location approvals, and real customer evaluation. Official Meta/Apify paths are implemented but not live verified. Locally running third-party models are not owned trained weights. These gaps mean the full original Instagram plan is **not** complete.

---

# Direct Instagram verification - 5 November 2026

This is the latest verification record. The 4 November metadata-only results below are historical and are superseded for the specific direct-browser path tested here. Full procedure: [DIRECT_INSTAGRAM.md](DIRECT_INSTAGRAM.md).

## Completed checks

- **Backend:** 86 tests passed in 16.18 seconds; Ruff undefined/unused checks passed. Tests use isolated databases. New coverage includes exact-post association, recommendation exclusion, visible-comment sampling, a real Chromium JavaScript fixture with network blocked, URL/media boundaries, challenge cooldown, persistent daily limits, separate audio/video joining, receipts, transcript retention, speech gaps, job cancellation/lease renewal, bounded model contracts and distinct emoji comments.
- **Frontend:** strict TypeScript and production build passed. Four local-mode Playwright checks passed in 12.7 seconds across desktop/mobile, including accessibility, local runtime status and correction save/revoke. Correction mutations are mocked to avoid contaminating the real learning database. A new status assertion initially omitted a colon present in the UI; the locator was corrected and all four checks rerun successfully. The twelve demo checks recorded on 4 November were not rerun in this update.
- **Actual public Instagram collection:** investigation `e4f4578d-3999-4450-9c7b-c4c372d00a22`, query `Coimbatore sushi Tamil food review`, selected its own sources. Three real videos and captions, plus 11 + 12 + 9 loaded comments, were retrieved directly without signing in, supplying example URLs, API keys or a paid provider. Two clear audio tracks were joined locally. The third source explicitly reported no audio. Byte counts, SHA-256 receipts and public shortcode references are in DIRECT_INSTAGRAM.md and the private local case.
- **Actual local interpretation:** all three caption, three comment and three video passes have stored `observations_only` results after the text repairs. Four frames were sampled across each clip. One audio track yielded a machine transcript detected as Tamil; another yielded no speech segments. No manually labelled language, transcription or visual accuracy measurement was performed. The final model/schema also passed a separate real silent-video smoke with four frame samples and an explicit no-audio result.
- **Failures found and repaired:** the first full batch had output-budget and evidence-structure failures on text passes. A diagnostic reproduced invented calendar timestamps in `timestamp_seconds`. The revised contract forces null timestamps on text, bounds string/list output, permits a bounded 1,536-token response, excludes commenter mentions from venue candidates, rejects placeholder venues/descriptive non-prices and deduplicates observations. A real second text pass completed all six analyses. Original failed text results and the maintenance repair reason were retained in an audit entry. Model interpretations can still be wrong.
- **Review/publication:** the tested case is `review`, with three independent exact-branch confirmation gaps, no eligible venues and no automatically accepted venue facts. Zero local venues are published.
- **Runtime after verification:** API healthy in `local` mode; Qwen3-VL instruct installed; public search, direct browser and autonomous discovery enabled; optional Meta/Apify connector disabled. At 12:04:52 UTC, worker heartbeat age was zero seconds and no jobs were failed. The database contained 20 source records across seven review cases and one unavailable case; this includes older and autonomous runs beyond the three-source batch described above. These totals are not counts of verified venues or accuracy evaluations.
- **Backup:** consistent local SQLite snapshot `data/backups/batore-20261105T120451Z.db`; read-only `PRAGMA quick_check` returned `ok`. This checks snapshot integrity, not production restore readiness. Standalone raw browser diagnostic video/screenshot were removed after testing; the summary receipt remains. Existing point-in-time database backups can contain source text from snapshot time and must be handled separately from active-database retention.

Local evidence: `data/direct-browser-final-status.json`, `data/direct-browser-runtime-status.json`, `data/direct-browser-video-analysis.json`. These are ignored local artifacts, not public fixtures or published venue records.

## Still unverified

Representative anonymous-access success rates; complete comments/replies or city coverage; speech/OCR/location/comment factual accuracy; independent venue facts and freshness; customer outcomes; configured Meta/Apify/Maps provider access; production PostgreSQL/containers/restore; and owned-model training. A successful browser collection is evidence for the sampled posts only. No external paid provider, hosted Gemini inference or public release was activated.

---

# Local research verification - 4 November 2026

This update supersedes older demo-only runtime statements retained below.

- Backend: 65 tests passed; Ruff undefined/unused checks passed. Includes local auth/DB isolation, correction scope/owner isolation, retrieval/revocation/export/erasure, autonomous rotation/dedup/pause, no hosted AI fallback, no speech observation without audio, engagement-price rejection and real short-video frame bounds.
- Frontend: strict TypeScript/production build passed. Four local-mode Playwright checks passed on desktop/mobile, including accessibility and correction save/revoke (mocked mutations to avoid polluting real data). All 12 existing demo checks passed against an isolated test SQLite database; the four local tests were intentionally skipped in that separate demo run.
- Real public source smoke: the app discovered and saved three Instagram sources for Coimbatore sushi. Anonymous metadata retrieval worked. Two caption passes returned local-model observations; one was rejected for unsupported modality attribution. Subsequent schema constrains basis to the actually supplied modality. A second real investigation after the fixes completed all three caption analyses successfully; across both runs there are six stored source records for four distinct Instagram links. No video/comments were exposed by those public pages.
- Local model smoke: Qwen3-VL 2B instruct returned structured observations/candidates. The thinking tag exhausted its output budget and was replaced. This is not an accuracy benchmark.
- Local audio/video smoke: generated synthetic test speech was transcribed locally; two red video frames at 0 and 5 seconds were inspected together with the transcript. No real venue was invented. Results are ignored files data/local-speech-smoke.json and data/local-video-smoke.json, not venue records. English synthetic media is not a Tamil/multilingual quality evaluation.
- The real smoke caught PyAV 19 incompatibility; av==16.1.0 is locked. Duration probing avoids decoding beyond short clips. User correction data has not yet been supplied, so learned accuracy is not established.
- Demo database backed up before local-mode activation. Real evidence lives in separate data/local-research.db, schema 4. No external paid provider activated, no Supabase/Gemini inference, no public release and no independently verified published local venues.

Procedure and limitations: [LOCAL_RESEARCH.md](LOCAL_RESEARCH.md).

---

Historical verification follows.

# Verification report

Build date: 4 November 2026. This report covers this workspace, not historical
claims from the reference project.

## Investigation update ? 4 November 2026

Implemented and checked the durable eight-stage workflow, owner isolation/export/
erasure, cancelled/failed jobs, bounded async-provider polling, restart recovery,
old-delivery stage binding, actual synthetic-video frame extraction, creator-history
origin deduplication, proposed social facts remaining in review, multi-stop/package
planning, explicit no-evidence conclusions, automatic inventory-gap cases, gated
launch review and idempotent official-lead import. The final small import/identity
changes passed the 19-test investigation regression suite after the 55-test full run.

Strict TypeScript and production build passed. The 12-test browser suite passed
on desktop/mobile, including budget preservation in guided discovery, persisted
investigation progress, honest demo unavailability and disabled data signoff.

No live source/model/account calls or paid provider activation were used. Nine
real official-source research pointers were saved as **unverified leads**, not
published venues. Docker was rechecked: daemon pipe unavailable and no Docker
Desktop executable at its standard path. PostgreSQL/container/live-source checks
remain unverified. A SQLite backup was taken before the schema-3 local upgrade.

## Executed locally

| Check | Result |
|---|---|
| Python compilation and Ruff undefined/unused-symbol checks | Passed |
| Backend tests | 55 passed, using a temporary isolated SQLite database; latest investigation-only regression rerun: 19 passed |
| TypeScript strict build and unused-symbol checking | Passed |
| Production web build | Passed; fonts self-hosted and optional Auth/admin/source bundles split |
| Desktop/mobile core browser journeys | 6 passed |
| Automated WCAG A/AA checks across six main screens | Passed on desktop and mobile |
| Complete browser suite | 12 passed against the built app and running worker, including guided discovery and investigation readiness |
| PWA install assets / offline behavior | PNG icons and manifest verified; offline shell reconnect state works; API responses excluded from caches |
| Windows one-command launcher | Locked install, production build, hidden API/worker startup and health check passed |
| Windows stop/restart | Verified termination of Python redirector children and restart with `-SkipBuild` |
| Worker operation | Heartbeat recorded; no failed jobs at final local check |
| SQLite online backup | Snapshot created, integrity check `ok`, twelve demo venues present |

Core browser journeys cover plan creation, detail viewing, saving, reload
persistence, confirmed visits, taste learning, profile persistence, source queue
processing, empty results, and viewport overflow. Backend tests additionally cover
cross-account access, live/demo separation, admin role enforcement, opening/movie
constraints, source dates, revisions, job leases/retries, upload replacement,
invalid URLs, provider partial errors, model output handling, call limits and
signed merchant updates with replay checks.

Playwright screenshots and failure traces are written under ignored
`web/test-results/`. Every test run can replace that folder. Human visual inspection
was performed on desktop and mobile layouts. Automated accessibility checks are
not a substitute for a full manual assistive-technology audit.

One dependency emits a Starlette TestClient deprecation warning for its current
httpx transport. Tests pass; production HTTP calls use httpx independently. No
warning is being counted as proof of production integration health.

## Not verified / external gates

- Supabase live authentication, PostgreSQL migration/RLS/restore, Google Places/
  Routes, Gemini multilingual media quality, Brave and YouTube account access:
  credentials were deliberately left blank. Tests of provider contracts use mocks.
- Docker executable exists but its Linux engine was not running; `docker version`
  could not connect. Container build/run and PostgreSQL container checks were not
  claimed as passed. Windows local execution is the tested path.
- Broad Instagram reel discovery, complete comments, live cinema seats and partner
  activity availability require access not provided by a generic API key.
- No real city inventory, real customer visits, production scale, paid provider
  use, public deployment, real merchant onboarding or uptime guarantee is claimed.

The app is a working local release with integration code and explicit unavailable
states. It is not certified accurate for customer travel until the live-data and
launch checks in OPERATIONS.md have been completed.

Local app left running at http://127.0.0.1:8000 with the background worker.
Stop/start instructions and the credential checklist are linked from README.md.

Final restart check for the investigation update: API `ok`, schema 3, worker
heartbeat three seconds old, zero failed jobs. Mode remains `demo`, Instagram
connector `disabled`, release stage `internal`, and there are zero live venues.
These are deliberately explicit: healthy processes do not mean a live Instagram
collector or a verified city database is operating.

Local backup follow-up: a consistent SQLite research snapshot was created at data/backups/batore-20261104T155248Z.db and opened read-only. PRAGMA quick_check returned ok; six source records and zero venues were present. This verifies snapshot readability, not a production disaster-recovery exercise.

Final connector regression: public caption metadata must not prevent a configured full provider from retrieving video/comments. Provider-sample markers prevent duplicate paid recollection. Covered by an isolated mocked-provider test; no paid connector was called.

Final runtime evidence (4 November 2026): API healthy in local mode; Qwen3-VL instruct installed; public search and autonomous discovery enabled; worker heartbeat 1 second old; zero failed jobs; six source records/four distinct Instagram links; two review cases and one unavailable query; zero published venues. Full Instagram provider is still disabled. Report saved locally as data/local-final-status.json.
