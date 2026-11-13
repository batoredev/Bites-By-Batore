# Bites by Batore — master project record and completion tracker

Last consolidated: **13 November 2026 (Asia/Calcutta)**.

## Owner edits, learning, relevance gate and wider directory — 13 November 2026

Read the 13 November section of [TEST_INVENTORY.md](docs/TEST_INVENTORY.md).

- [x] Place manager: edit, confirm, remove, restore and add places by hand;
  publish ready places. Each edit is kept on the record and reused as a rule
  (rejected names, categories by name and by agreed word, renames as aliases and
  reviewed examples, blocked creators). Not model training.
- [x] Relevance gate before analysis; video-derived names need a sign, speech or
  caption to back them; vague plan requests no longer start research.
- [x] Wider OpenStreetMap query: 628 objects, 149 new drafts, 141 published.
  Test inventory is 700 venues. Backup
  `data/backups/local-research-20261113T045700Z-pre-owner-edits.db`.
- [x] 413 backend tests, required Ruff check and production web build pass. Place
  manager checked in a headless browser without saving changes.
- [ ] Overture Maps import not done: needs a package install the owner must
  approve. No accuracy measurement yet. The relevance gate and video-name check
  are measured on stored data, not yet on a fresh collection run. 556 drafts
  still lack coordinates.

---

## Agent-approved test inventory, new categories and collector tuning — 12 November 2026

Read [TEST_INVENTORY.md](docs/TEST_INVENTORY.md). **Owner decision:** for the data
collected so far, skip per-location owner approval so the planner can be tested.
The agent dedupes and approves; missing prices and hours may be category estimates.
This supersedes "every location requires explicit operator approval" for the local
test inventory only. It is not verification and not a release decision.

- [x] 559 venues published as labelled test inventory (`details.test_inventory`,
  claims in source group `test-inventory`); 533 prices and 383 hours are estimates.
  One command reverts it. Backup `data/backups/local-research-20261112T111443Z-pre-test-inventory.db`.
- [x] Local planner works without a map provider: stored hours, travel estimated
  from straight-line distance, both stated as warnings on every plan.
- [x] Categories grew from 7 to 14 in one module; about 280 drafts recategorised.
  Stricter name gate held 188 descriptive or landmark names. Search topics retuned,
  with 16 city-wide activity topics.
- [x] Root cause of 163 failed reel analyses fixed (501 feature points against a
  500 limit) and the jobs requeued. Smaller video streams kept as fallback, limit
  20 MB. Duplicate scans limited to one per 30 minutes. One model context size.
- [x] Caption step: written-name check, Instagram location tag capture, and
  `qwen3:4b` for captions via `OLLAMA_TEXT_MODEL`. 24-caption comparison only.
- [x] Planner returns every distinct plan on request (`max_options`, up to 400);
  new admin tab lists unpublished places with reasons and filters.
- [x] 397 backend tests, required Ruff check and production web build pass.
- [ ] Browser end-to-end suite not re-run. No extraction accuracy measurement.
  597 active drafts still lack coordinates. Stream fallback, model swapping cost
  and location-tag yield are not measured at scale. Test venues may be closed,
  misnamed or the wrong branch. A reboot stops the API, worker and Ollama.

---

## Dedicated duplicate agent — 8 November 2026, 19:56 IST

Read [DUPLICATE_AGENT.md](docs/DUPLICATE_AGENT.md) for rules, operator controls,
real receipts and remaining validation. This follows the user's instruction to
choose the best duplicate-merging approach while continuing local collection.

- [x] Independent local duplicate worker lane/durable jobs, conservative candidate
  policy, complete-group validation, fresh serialized rechecks and retry/version
  handling. No additional model/provider/GPU inference or paid activation.
- [x] Fix caption/sign extraction variants, groups of three, held-source manual
  merges, legacy hash/redirect and cleanup conflict bypasses, shared-search-URL
  identity contamination and reciprocal manual-merge races. Originals/evidence
  and prior statuses retained; no publication/fact/Maps approval introduced.
- [x] Private duplicate review desk with explicit survivor, branch checkbox and
  reason; reports included in owner export/erasure. Clarify ambience evidence and
  area/topic search counters in the UI; 41/168 is scheduled combinations, not
  completed searches, verified places or city completeness.
- [x] **345 backend tests**, new-module Ruff/repository unused-name checks and
  strict web build passed. **20 isolated desktop/mobile checks** passed. Broader
  optional style lint still flags unrelated existing code; not claimed clean.
- [x] Separate-copy rehearsal merged three drafts; repeat zero. Fresh consistent
  backup `data/backups/batore-20261108T142244Z.db`; real tracked pass merged three
  drafts in 12.961s, repeat zero. Worker-run independent scan completed, status
  HTTP200, zero model calls. Real source/fact accuracy is not proven by these tests.
- [x] Local collection/API/worker restored, one interrupted owned analysis job
  safely requeued; counters/checkpoints retained. Unlimited initial counts and
  existing source pacing/monetary guards remain. Structural SQL audit healthy.
- [x] 14:26 UTC / 19:56 IST snapshot: **948 active unapproved drafts, 144 held,
  16 merged originals; 1,108 total**, 372 research sources, 41/168 search-grid
  combinations scheduled. **215 possible pairs** at the stable scan need review;
  zero real venues/claims/approvals. Collection continues, so counts change.
- [ ] Human duplicate/branch validation, measured multilingual extraction and
  merge accuracy, sustained growth/concurrency checks, complete current city
  inventory, explicit approvals and customer validation remain unfinished.

19:59 IST follow-up: latest autonomous scan completed; 218 possible review pairs
as collection continued. API/duplicate status HTTP200, structural audit healthy;
post-change backup `data/backups/batore-20261108T142926Z.db`. Earlier counts above
remain timestamped snapshots, not live totals.

---

## Instagram workflow walkthrough — 8 November 2026

- [x] Trace current source code and non-secret local model/provider settings;
  document flowchart, specialist roles, illustrative example and actual skip/
  identity/retry/learning/publication gates in
  [INSTAGRAM_AGENT_FLOW.md](docs/INSTAGRAM_AGENT_FLOW.md).
- [x] Distinguish sampled frames/loaded comments and public-web discovery from
  exhaustive coverage; optional unconfigured Places from operator Maps review;
  source claims/retrieved corrections from accepted facts/trained weights.
  Fictional example is explanation only; no example venue or approval inserted.
- [ ] Accuracy, complete-city coverage and human approvals remain unfinished.
  Documentation-only step; no new application test run or runtime change.

---

## Contention repair and collection resumed — 8 November 2026, 15:13 IST

Read [SQLITE_RELIABILITY.md](docs/SQLITE_RELIABILITY.md). The user authorized
continuing collection and finishing the remaining work; no new user input/API
keys were requested for the existing public-source path.

- [x] Reduce the all-inventory duplicate-cleanup comparisons performed under the
  SQLite write lock, preserving canonical branch predicates, fuzzy eligibility,
  row order, ownership, held originals and approvals. Full separate-copy passes
  on 811 originals completed in 3.7926s/3.6023s with zero data changes; concurrent
  write probe completed without error, integrity healthy.
- [x] Recognize SQLite busy conflicts; preserve source checkpoints and failure
  allowance through claim/execution/completion retries. Return sanitized API 503
  and retry reads only; never automatically repeat mutations.
- [x] Harden launcher port/ownership/exit/race checks. Actual repeated launch reused
  the same API/worker PIDs; no duplicate process was introduced.
- [x] **292 backend tests**, Ruff, production build and **12 isolated desktop/mobile
  checks** passed. Actual live cleanup plus 24 concurrent reads returned HTTP 200;
  no new lock errors in the restarted logs at the short check. Limited scope only.
- [x] Pre-change backup `data/backups/batore-20261108T093634Z.db`; recover four
  owned interrupted/stale jobs with worker stopped and launcher mutex held.
  Checkpoints/counters retained. Local unlimited collection restored and running.
- [x] 09:43 UTC checkpoint: **692 active drafts, 111 held, 12 merged originals**;
  **168 research sources**, zero real venues/accepted claims. No approvals invented.
- [ ] Observe sustained operation and growing-inventory contention; complete the
  remaining data/accuracy/branch work and explicit approvals. This repair does not
  establish full-city completeness, absolute correctness or production capacity.

---

## Live status audit — 8 November 2026, 14:51 IST

- [x] Read live DB/runtime and refresh `data/city-collection/` progress/CSV snapshots.
  **679 active unapproved drafts** (+105 since 07:17 UTC), **156 source records**
  (+68), 110 held and 12 merged originals; 801 originals total. Zero real venues
  and accepted claims. Fifteen of 168 area/topic queries scheduled, not complete.
- [x] API healthy; worker heartbeat 5.29s old at 09:21 UTC. Unlimited initial mode
  remains enabled. Aggregate counter 1,396; browser visits 80. DB structural and
  integrity audit healthy, no duplicate SQL identity-key groups or audited orphans.
- [ ] Runtime reliability issue observed: intermittent SQLite `database is locked`
  exceptions in API request counting and worker claiming; an expired running-job
  lease was also observed. Root cause/repair are not established by this status
  audit. No terminal failed jobs, but do not describe operation as error-free or
  equate all `running` rows with actively executing tasks. Most queued jobs are
  waiting on source cooldowns. No application code/config was changed here.
- [ ] Data gaps: 424 menu/price, 586 hours observations, 643 vibes; all 679 Maps
  unreviewed. Extraction/fact accuracy and final approval remain unfinished.

---

## Unlimited initial collection and queue progress — 8 November 2026

Latest user direction explicitly removes the app's 300/day request ceiling until
the initial DB is collected and authorizes the proposed collection improvements.
Read [BULK_COLLECTION.md](docs/BULK_COLLECTION.md). This supersedes the older daily
allowance decision below; it does not declare full-city completion or remove
spending/source/approval controls.

- [x] Enable local-only `LOCAL_BULK_COLLECTION=true`: no daily app count ceiling
  for external reads, browser visits or investigations. Effective zero means
  unlimited counts; monetary zero still blocks spending. Counters are retained.
- [x] Separate new free-read/paid-attempt counters, preserve INR 3,000 monthly paid
  reservations and all inactive provider credentials. No paid/cloud activation.
- [x] Remove local bulk inter-case delay/daily case cap; allow three active cases
  with existing model serialization and backpressure. Fairly rotate eligible
  investigation/enrichment/refresh/inventory/watch/directory work.
- [x] Add persistent source pacing and applicable Retry-After/exponential cooldowns;
  distinguish source waits from app quotas and preserve pending work without
  exhausting failure attempts. Preserve browser challenge handling/cache reuse.
- [x] Resume 541 owned legacy/app-cap queued waits without clearing counters,
  source cooldowns, cancelled jobs, attempt histories or other owners' work.
- [x] Add literal JSON-LD INR menu/hour/amenity observations and retain multi-branch
  menu pages unassigned. No factual acceptance, branch approval or guessed prices.
- [x] **283 backend tests**, Ruff, strict production build and **eight desktop/mobile
  browser checks** passed. Separate test data, mocked mutation endpoints and current
  runtime receipt retained. Backup `data/backups/batore-20261108T070103Z.db`.
- [x] Live worker advanced aggregate counter **300 → 333**, browser visits **14 →
  20**, source inventory **83 → 86**, scheduled grid queries five → seven by 07:12
  UTC. Initial mode is running beyond the previous cap; saved sources still need
  analysis/verification. No new place count was invented when sources increased.
- [x] Later 07:17 UTC checkpoint: counter **410**, browser visits **24**, sources
  **88**, active drafts **574**; 684 retained originals, zero real venues/accepted
  claims. API healthy and worker heartbeat 2.75s old. Post-change consistent backup
  `data/backups/batore-20261108T071743Z.db`; focused suite **12 passed**, including
  HTTP-429 adapter retry persistence. Current gaps/CSVs saved in the progress folder.
- [ ] Continue systematic discovery, menu/hours/vibe corroboration, held-record
  resolution and independent multilingual/branch accuracy work. All locations
  still require explicit user approval before recommendations. The initial mode
  remains on until the reviewed first-fill scope is accepted; queue exhaustion
  or scheduled-query counts cannot establish city-wide completeness.

---

## Coimbatore collection started and expanded — 8 November 2026

User authorized starting the city data collection now, aiming for full accurate
food/entertainment coverage. Read [COIMBATORE_COLLECTION.md](docs/COIMBATORE_COLLECTION.md).
**Collection has started; city-wide completeness and factual accuracy remain
unverified. No location approval or public release is implied.**

- [x] Add a bounded local Overpass directory collector, seven-day cache, owner/week
  durable job, two-request weekly allowance, attribution/licence preservation and
  owner-private API/CLI coverage reporting. No Nominatim POI collector added.
- [x] Actual broad request returned 635 entries. Scope audit caught neighbouring
  Kerala places inside the 40 km radius. A second real area-scoped request returned
  477 entries: three Coimbatore administrative boundary records + 474 supported
  place objects. Recurring collection now requires the district boundary metadata
  and clips to 40 km; no broad-radius fallback. This is **Coimbatore district in
  the operating radius**, not an independently verified municipal census.
- [x] Rehearse duplicate-safe imports on separate SQLite copies, replay without new
  rows, apply tracked jobs to the actual local DB, hold 51 earlier active references
  absent from the scoped pass, retain originals. Scope/branch ambiguity is review
  work; missing directory entries do not prove closure. Rejected/merged originals
  remain retained; exact source IDs, conflicting addresses and distant branches
  are respected. Provisional near-point merging is not physical identity proof.
- [x] Complete six actual local caption jobs from already collected sources without
  new external requests: active drafts 86 → 115 before the directory pass. Commit
  caption drafts before subsequent location lookup work, including quota waits.
- [x] Actual checkpoint: **678 originals = 568 active unapproved drafts + 98 held +
  12 merged**; 453 active drafts have scoped directory evidence. 83 research sources;
  **zero real venues/accepted claims/operator Maps reviews**. Active categories:
  food 382, cafés 82, parks 62, cinema 25, adventure 11, bowling 4, gaming 2.
- [x] Store observations rather than accepted facts; show OSM attribution, raw hours
  candidates and coverage gaps in Identified spots. Skip OSM listing pages during
  daily HTML maintenance; retain venue website hints as unverified fetch targets.
- [x] Save progress, raw receipts, scoped/broad copies and review CSVs under
  `data/city-collection/`; user-readable `PROGRESS.md`, `coverage.json`,
  `pending-locations.csv`, `held-and-merged.csv`, `all-originals.csv` and runtime/UI
  receipts. These exports/backups are offline snapshots requiring separate erasure.
- [x] **271 full-suite backend tests**, required Ruff and strict production build
  passed; **21 targeted directory tests** passed after the extra export/erasure
  regression. Six controlled desktop/mobile browser tests passed. Actual local UI
  loaded all 568 cards on desktop/mobile without page errors or horizontal overflow.
  Live schema-7 structural/integrity/index/duplicate/orphan audit healthy. Consistent
  backup `data/backups/batore-20261108T061709Z.db`; see VERIFICATION.md.
- [x] API and autonomous worker restored and healthy in local/internal mode; GPU
  request 999 retained. Six caption jobs and both tracked directory jobs completed.
  Existing allowances unchanged: shared external 300/300 today, browser 14/30,
  autonomous cases 3/day. Two actual directory requests accounted separately. No
  paid/cloud connector activated or quota reset. Further external work stays queued
  until allowances permit; keep the computer awake and connected.
- [ ] Remaining data gaps: 455 active drafts lack menu/price evidence, 512 lack an
  hours observation, 533 lack vibe evidence; all 568 require operator Maps review.
  Raw hours tags do not establish current verified hours. Only five of the 168
  area/topic queries have been scheduled; scheduling does not establish completion.
- [ ] Expand/reconcile coverage, corroborate current facts/exact branches, measure
  real multilingual accuracy/correction improvement and obtain explicit approval
  for every location before suggestions. No complete-city count, deadline, 100%
  accuracy, customer validation or owned-model training is claimed.

---

## Known-location early exit, SQL backfill and GPU — 8 November 2026

User explicitly authorized skipping remaining reel work for already identified
locations, filling the local private location inventory now and checking locations
personally later, preventing duplicates and using the GPU fully. Read
[KNOWN_LOCATION_EARLY_EXIT.md](docs/KNOWN_LOCATION_EARLY_EXIT.md).

- [x] Discovery-only early exits before recency/browser/download work for recorded
  permalinks; after caption recognition for exact existing branches; and after a
  video pass. All recorded candidates must be accounted for. Names/areas alone,
  ambiguous branches, new candidates and incomplete compilations keep processing.
- [x] Retain skipped source references/IDs, explicit partial coverage and skipped
  modality statuses. No freshness renewal, creator judgement or fact/location
  approval. Maintenance, labelled origins and explicit full inspection bypass it.
- [x] Save newly extracted caption locations before remaining specialist work;
  replay existing saved extraction through the same canonical SQL inventory path.
  Serialize identity writes, recover insert conflicts and retain held/merged history.
- [x] Hold indistinguishable same-name proposals for branch review rather than
  adding another active location or merging potentially different branches.
- [x] Rehearse on separate SQLite, backfill real DB twice: **83 source records;
  86 active pending locations, 12 merged originals, 28 held originals; 126 total**.
  One additional supported merge and four ambiguous holds. No new location row
  was needed; existing valid extractions were already saved. Repeat made zero
  insertions or cleanup changes. Zero repeated SQL identity keys/explicit Maps
  identities; physical branch correctness still requires the user's review.
- [x] Main review CSV `data/known-spots/pending-locations.csv`; separate held queue
  and complete original-record audit CSV retained; read-only SQL file
  `resources/sql/private_inventory_checks.sqlite.sql`; CLI `sync-inventory`.
- [x] `OLLAMA_GPU_LAYERS=999`: retained-caption and four-frame vision smokes show
  100% model GPU placement with unchanged weights/precision/context. Vision peak
  3,345 MiB of 4,096 MiB and sampled utilization 100%. Warm caption 4.396s;
  these limited tests establish placement, not universal speed/accuracy.
- [x] Final **251 backend tests**, Ruff, strict build and **20 desktop/mobile
  checks** passed; consistent separate-file SQL restore healthy. Local API/worker
  restored, skip flag true and full GPU requests active. No venue, fact or human
  label/approval invented; schema remains 7. Details in VERIFICATION.md.
- [ ] Normal live discovery has not yet encountered an eligible pending known
  reel at the audit (zero manufactured live skip examples). Representative
  physical branch accuracy, sustained speed, independent labels and final user
  approvals remain unverified. CPU-preparation overlap/output experiments from
  the earlier proposal are separate work, not claimed complete here.

Backup: `data/backups/before-known-spot-skip-20261108T051054Z.db`. Receipts in
`data/known-spots/`. The earlier retain-all-reels decision now means retaining
references and evidence; known-location discovery clips may intentionally stop.
All relevant unseen/ambiguous locations remain queued. Public suggestions still
require explicit approval and current facts. Cloud inference, quotas and model
training remain unchanged.

---

## Speed profiling follow-up — 8 November 2026

Read-only actual worker measurements now supplement the earlier caption-only smoke.
Receipt `data/performance/speed-audit-20261108.json`; details in
[PERFORMANCE_IMPLEMENTATION.md](docs/PERFORMANCE_IMPLEMENTATION.md).

- [x] Inspect recorded execution: eight completed source-analysis jobs, median 144.15s
  (range 34.29–595.16s), excluding preceding collection/queue/quota/approval waits.
  Missing modalities and factual accuracy remain separate limitations.
- [x] Identify the observed cost: 46 measured model calls/responses, 1,162.32s model
  phase, 926.78s generation (79.7%); six speech passes average 33.47s. Shared external
  UTC-day counter 300/300, browser 14/30; quotas are separate from inference speed.
- [ ] Benchmark concise complete output and transcript/visual interpretation reuse,
  bounded CPU/GPU preparation overlap, active-load GPU/backend settings and earlier
  staged draft visibility. These are next proposals, not newly implemented changes.

No code/runtime/model/quota changes or new test run in this read-only follow-up.
Existing worker remains autonomous; latest feature implementation/test checkpoints
below remain valid. No speed multiplier or real accuracy guarantee is established.

## Investigation improvements implemented — 7 November 2026

Read [PERFORMANCE_IMPLEMENTATION.md](docs/PERFORMANCE_IMPLEMENTATION.md) for P01–P10, measurements, commands, rollback and validation. This supersedes the proposal-only status in the historical audit below.

- [x] P01 — Persist delivery/start/eligible-queue/execution/retry measurements, stage/model load/prompt/generation/token timings and owner-private API/CLI/UI reporting. Historical jobs remain explicitly unmeasured; delivery percentiles are not reel latency.
- [x] P02 — Retain clip endpoints and temporal coverage; segment multilingual text with original offsets; check installed-model token budgets; split overflowing text/frame/comment batches; remove small venue-candidate and downstream matching limits while retaining separate branches/menu claims.
- [x] P03/P07 — Versioned owner/source/model/input/correction-safe interpretation and changed-comment-batch reuse; expiry/future-date rejection, evaluation-origin exclusion and deleted-origin handling. Reuse never renews venue facts or grants approval.
- [x] P04 — Durable source jobs, bounded collection/control and analysis lanes with separate SQL sessions, one model semaphore, backlog backpressure, missing-enqueue recovery and cancellation checks after GPU waits. Additional CPU concurrency remains a profiling experiment.
- [x] P05 — Bounded 10-minute residency and pooled loopback HTTP client; existing Qwen/Whisper, context/output limits, frame budget and external allowances retained. Real local caption/model placement measured; whole-reel throughput unmeasured.
- [x] P06 — Reusable hidden browser helper with per-source fresh contexts, readiness gates, idle expiry and error recovery. **Controlled Chromium tested; new helper path not live verified on public Instagram yet.**
- [x] P08/P09 — Retain baseline coverage and reinspection of uncertain timestamped clues; preserve follow-up evidence; keep approved-inventory/expiry/revision/current-route checks and add plan timing. No unapproved-inventory shortcut.
- [x] P10 tooling — Independent-label-only uncached caption/comment benchmark, current execution versus saved labelled prediction, explicit absence of historical timing, export/erasure and reversible flags. **A paired speed/accuracy and video/branch benchmark remains incomplete.**
- [x] Local checks — **232 backend tests**, required Ruff, strict web build and **46 desktop/mobile browser checks** passed (16 local, 30 demo; two intentional demo skips). Consistent restored SQLite snapshot is healthy. Actual source/spot counts and zero labels/publications preserved. Details in the newest [VERIFICATION.md](docs/VERIFICATION.md) section.
- [ ] P10 validation — Representative independent labels, matched video/branch/correction quality measurements, live new-browser reuse, real ASR/vision contention and sustained operation remain open. Actual venue approval and invited-user validation remain required.

Local configuration enables reuse/pipeline/browser switches and `OLLAMA_KEEP_ALIVE=10m`; fresh-checkout switches default off. Schema remains 7, using existing JSON fields. No cloud inference, quota reset, model-weight training, fictional real inventory or operator approval was introduced. Local API/worker restored and healthy; temporary demo API/worker stopped. Runtime receipt: `data/performance/runtime-final.json`; 70 sources, 111 spot originals, zero human labels/published venues; external/browser allowances remain exhausted and pending work retained.

Receipts in `data/performance/`: actual caption with initially absent model 18.026s including 11.174s load, immediate warm repetition 5.912s. Final pooled-client/guarded warm calls: 7.401s (tokenizer initialization) and 5.251s (reused tokenizer), including guard overhead. These are unlabelled caption calls, not a per-reel speed guarantee. Partial GPU placement observed; no hardware purchase made.

---

## Investigation speed/quality audit and plan — 7 November 2026, 19:43 IST

Read [INVESTIGATION_SPEED_AND_QUALITY.md](docs/INVESTIGATION_SPEED_AND_QUALITY.md). **Research/proposal only; no runtime optimization, quota/model change or speed benchmark performed.** Actual receipt `data/investigation-speed-audit.json`: local Qwen3-VL 2B instruct/Whisper base; eight frames; thirty collected-comment sample limit; three-source processing batches; 300/300 shared calls and 30/30 browser visits used; 55 queued jobs; zero human labels/corrections. Quota wait is distinct from inference speed. Job timestamps lack execution-start/stage timings, so no credible per-reel median/p95 is claimed.

- [x] P00 — Inspect sequential collection/analysis, model settings, hardware and active allowances; document P01–P10 and independent quality testing.
- [ ] P01–P02 — Add stage/queue/quota measurements; fix frame-endpoint retention, blind input truncation and multi-venue candidate coverage risks identified by code inspection.
- [ ] P03–P07 — Versioned owner-safe analysis reuse, bounded resource queues, warm-model experiments, browser lifecycle/readiness and changed-component refresh. Preserve retention, cancellations, source attribution and all relevant source queues.
- [ ] P08–P10 — Targeted difficult-segment escalation, approved-DB request path performance and paired independently labelled baseline/optimized benchmarks with rollback and sustained operation.

Existing streaming, completed-source/comment checkpoints, structured JSON and CPU int8/VAD are implemented; do not label these proposed improvements as already delivered. Parallel agent roles do not imply multiple models should run simultaneously on the current 4 GB GPU. Human location approval and the local-only/INR 3,000 target remain unchanged.

---

## Latest UI refresh — 7 November 2026, 19:21 IST

Read [UI_REFRESH.md](docs/UI_REFRESH.md). The shared features from FH01–FH13 are implemented/local tested; real-world accuracy and approved inventory remain pending. The redesign reorganizes their presentation without changing scope, models, data approval or source behavior.

- [x] UI01 — Forest-green navigation, destination descriptions/current-page header, compact planner introduction, grouped fields, larger text/control scale and consistent panels/cards across six primary screens. **Implemented and visually inspected desktop/mobile.**
- [x] UI02 — Dedicated food/cafe Menu & dishes tab with compact secondary views; proper keyboard tabs; My taste shortcuts and grouped preferences; readable saved/operations selected states. **Implemented/browser verified.**
- [x] UI03 — Inert closed mobile navigation, open-menu focus trap/Escape/body scroll control, restored dialog focus, search loading/error/retry/reset and corrected mobile card clipping. **Implemented/browser verified.**
- [x] UI04 — Strict build; **30 demo browser checks passed**, two intentional viewport-specific skips; **12 local operator checks passed**; six-width geometry matrix (360–1440px); automated accessibility and PWA checks; screenshot review. **Locally verified in Chromium emulation.**
- [x] UI05 — Local mode retained throughout; real API/worker left running, temporary demo API/worker stopped; current UI observed at port 8000. Reports/screenshots in `data/ui-redesign/`; no fictional venue facts, evaluation labels or user approvals inserted into real data.
- [ ] UI06 — Physical-device/other-engine and full assistive-technology validation, invited-user usability and actual outing accuracy remain unvalidated.

No backend implementation changed in this task. The earlier 202 backend tests are prior evidence; final verification for this task is the strict web build, 42 passing browser checks and the runtime inspection. Existing real inventory approval gates remain mandatory.

---

## Latest: FavHiker deep review and shared features — 7 November 2026, 18:45 IST

Read [FAVHIKER_DEEP_REVIEW.md](docs/FAVHIKER_DEEP_REVIEW.md) for the official-source inventory, FH01–FH13 matrix, implementation, operator procedure and accuracy boundaries. This supersedes older schema/count/competitor-coverage statements below; historical checkpoints remain retained.

**Competitive finding:** FavHiker has public Coimbatore restaurant/cuisine/dish pages, menu evidence, private/public diary distinctions, taste matching, amenities and an advertised planner with where/when/who/budget inputs. AI plus human review is also described. These are not exclusive to us. Anonymous browser requests were blocked (403); web/indexed content was readable, sometimes in different cached versions. Neither generated competitor plans nor head-to-head quality was verified. The older PDF remains a historical export.

- [x] FH01/FH05/FH08 — Server dish/cuisine/place search, reviewed practical/diet/price filters, same-item matching, pagination and complete owner saved-place retrieval; repeat-safe desired-state bookmarking. **Implemented/local tested.**
- [x] FH02/FH07 — Typed reviewed menus, preference-aware dish picks, explicit unknowns, balanced current review samples, transitive origin/source deduplication and source/date/expiry. **Implemented/local tested; no real accepted menu/verified review corpus yet.**
- [x] FH03/FH04/FH09 — Private dish diary, cuisine/spice settings, visit editing/deletion, experience snapshots, reversible taste rebuilding and opt-out. **Implemented; isolated lifecycle and desktop/mobile tests.** No owned weight training or validated taste prediction claim.
- [x] FH06/FH10 — Independent mood/novelty choices, boundary/negation-aware guide, current menu vocabulary in planning and query/locked-stop priority before live candidate checks. **Implemented/local tested.** Real plan quality remains unmeasured.
- [x] FH11/FH12/FH13 — Exact reviewed Maps links, approval gates, diary export/erasure/memory clearing, responsive forms and accessible evidence links. **Implemented/local tested.** No location approved on behalf of the user.
- [x] SQL7 — Actual DB upgraded after separate-backup rehearsal; migrate twice with all existing counts preserved; unique dish/visit indexes and visit snapshots; SQLite/PostgreSQL SQL generated; final separate-file restore audited. **Executed locally; PostgreSQL unverified.**
- [x] Verification — **202 backend tests**, required Ruff, strict build, **10 new desktop/mobile checks**, **12 local regression checks** and earlier **8 core/accessibility checks** passed. Menu/diary screenshots inspected. Local API/worker restored; authenticated new routes return 200.
- [ ] FH14 — Independently check actual branch/menu/amenity/freshness facts, obtain user approvals, compare matched real requests and validate with invited users. **Required before claiming accurate customer-ready parity.**

Actual 18:39 IST snapshot: schema 7; **56 active candidates + 10 merged + 24 held originals; 61 sources; zero real venue claims/venues/approvals and zero gold labels/corrections**. Twelve successful public-content reel-watch receipts now exist, superseding the older quota-deferred checkpoint; sustained refresh accuracy remains unproven. Receipt `data/parity-final-status.json`; review pack `data/review-packs/review-20261107T130632Z.md`/`.json`. Tests used separate databases or intercepted mutations. No extra paid provider, cloud inference, category or public release was enabled. APP_MODE remains local.

---

## FavHiker competitor review — 7 November 2026

Read [FAVHIKER_COMPARISON.md](docs/FAVHIKER_COMPARISON.md). Public product/store evidence establishes direct overlap in personalized food/dish discovery, taste history, AI review analysis and advertised mood-based day planning. These cannot be claimed as exclusive to us. Their reel pipeline, Coimbatore depth, constraint enforcement and per-field freshness were not established; missing documentation is not proof of absence. Public planner routes returned HTTP 403, so end-to-end behavior remains untested.

Potential differentiation remains practical verified Coimbatore food-plus-activity outings under starting-point/time/group/budget constraints, with traceable evidence and measured corrections. This is a hypothesis, not proven superiority. No product scope/runtime changed. A05 remains open for the broader matrix, comparative outcomes and customer validation.

PDF export of the user-facing comparison: [FavHiker vs Bites by Batore](docs/exports/FavHiker-vs-Bites-by-Batore.pdf). Two pages; table, rupee symbol and four clickable source links checked, with both pages visually inspected.

---

## SQL and requested-stage continuation ? 7 November 2026, 00:39 IST

The active local SQL DB has been upgraded to **schema 6** with preserved data. Read [DATABASE_SQL.md](docs/DATABASE_SQL.md) and [MODEL_OPTIONS_COMPARISON.md](docs/MODEL_OPTIONS_COMPARISON.md). SQLite storage was already implemented; this step completes additional local migration/integrity tooling, not a cloud database deployment or verified venue inventory.

- [x] Serialized transactional migration ledger, future-version rejection and corrected live startup schema check (previously incorrectly fixed at version 4).
- [x] SQL duplicate protection for sources within a case and task ordinals; queue/owner/current-claim/audit indexes; read-only structural audit; executable empty SQLite SQL and generated PostgreSQL/RLS SQL.
- [x] Rehearse the migration twice on a restored snapshot, preserve every existing table count, upgrade the live DB and restore-check a final schema-6 snapshot. No detected duplicate groups, missing structures or orphaned audited relationships. Relationships remain application-managed rather than universally enforced through SQL foreign keys.
- [x] Atomic provider/browser allowance reservation; quota deferral consumes neither allowance. Prior counters were preserved.
- [x] Give bounded reel-monitoring jobs priority before bulk collection. Changed captions queue an owner-scoped, repeat-safe fresh investigation; old predictions are not attached to changed input. Watched caption text follows its own 24-hour retention clock.
- [x] Full backend run: 168 passed; final affected suites: 56 passed after retention/startup checks; required Ruff and 12 desktop/mobile checks passed. Local API/worker restarted and authenticated maintenance endpoint checked.
- [x] Audit the actual model dataset and compare Qwen tuning, current cheap APIs and owned specialists/foundation training. No cloud inference, model training or provider switch performed.
- [ ] Stage 1: independent multilingual/branch labels, measured correction benefit and creator reliability evidence remain absent.
- [ ] Stage 2: 49 active unapproved drafts still need current facts and exact Maps reviews; SQL correctness does not fill those facts.
- [ ] Stage 3: explicit user approval of every location remains required; zero approved/published.
- [ ] Stage 6: new reel-watch live execution remains quota-deferred; sustained operation remains unproven. Actual deferred attempt is recorded, not counted as live verification.

Checkpoint: 178 jobs done, two cancelled, 48 queued; 59 page-check records, eight overdue; one source conflict; current heartbeat and healthy local API. Daily quotas still use UTC dates, so they had not reset at 00:39 IST; normal retries can resume after 05:30 IST. No quota reset or paid connector activation occurred.

Dataset: 51 source records / 47 URLs / 26 video analysis outputs, **zero saved operator labels or corrections**, seven currently retained captions, four transcripts and no cached media payloads. It is not a training-ready dataset. Existing source-cache retention was preserved. Current local models remain Qwen/Whisper; paid comparison is a proposal conditional on later permission for cloud inference. Owned weights remain a long-term requirement.

---

## Latest requested stages 1, 2, 3 and 6 — 6 November, 22:58 IST

Read [STAGES_1_2_3_6.md](docs/STAGES_1_2_3_6.md) for implementation, operating cadence, exact evidence boundaries, review procedure and private artifacts. This checkpoint supersedes older inventory counts below. Local API/worker are running; source collection is waiting on exhausted daily allowances, with work preserved. Current inventory: **49 active unapproved drafts, 10 merged originals, 24 held originals; zero Maps-reviewed identities and zero published venues**. Source data: 51 records across 47 distinct URLs, 26 video analyses, 196 classified comments and six indexed images. No gold labels, user approvals or measured accuracy were invented.

| ID | Step completed | Evidence level | Still open |
|---|---|---|---|
| L21 / stage 1 | Agent-found evaluation queue and holdout correction exclusion | Implemented; isolated tests; actual source queue exported | Representative independent labels, exact branch/visual accuracy, correction benefit and creator calibration |
| L22 / stage 2 | 168 discovery topic/area combinations; expanded first-party targets; conservative cross-reference merge and conflict retention | Implemented; 11 live pages read for 14 target entries; 49 active candidates after cleanup | Verified city coverage; missing menu/price (38), hours (43), vibes (44); exact Maps identity for every candidate |
| L23 / stage 3 | Private approval packets, blocker parity, alert review and repeatable Markdown/JSON export | Implemented; desktop/mobile tested; 49 actual location packets exported | Your final per-location review/approval; none approved on your behalf |
| L24 / stage 6 | Daily page monitoring, weekly web/reel scheduling, resumable retries, critical-fact expiry holds and plan revision invalidation | Implemented; isolated failure/recovery tests; 59 live page-check records, one real conflicting-hours alert; separate-file restore passed | New reel-watch live execution is quota-deferred; sustained multi-day timing and correction propagation remain unproven |

Execution checklist:

- [x] Implement and test the monitoring/review mechanisms described above.
- [x] Expand local collection, preserve conflicting evidence and hold two generic descriptions; immediate repeated cleanup made zero changes.
- [x] Export the real location review packets; expose all unresolved blockers.
- [x] Full backend run: 157 passed; final affected suites: 59 passed after the final generic-description and expiry-audit privacy fixes. Required Ruff check, strict web build and 12 desktop/mobile checks passed.
- [x] Restore a consistent snapshot into a separate file and verify integrity/counts without replacing the live DB.
- [x] Restart local API/worker with collection progress and quota counters preserved.
- [ ] Complete independent multilingual/branch accuracy evaluation and measure correction improvement.
- [ ] Fill and independently verify sufficient Coimbatore coverage; no exhaustive city total or completion date is established.
- [ ] Obtain explicit user approval for each location before itinerary suggestions.
- [ ] Verify the new reel-watch path live and collect sustained maintenance/customer evidence.

The local provider allowance is now 300 calls/day (previously 200); Instagram pacing remains 30 visits/day, and the INR 3,000/month target remains. Both daily allowances were exhausted at this checkpoint; counters reset by UTC date (05:30 IST), and queued retries can resume afterwards. No paid provider was enabled. The four requested stages are **not fully validated or customer-ready** merely because their mechanisms and tests exist.

---

This is the canonical working record for the product we discussed: what the user wants, what was decided, what exists, what still needs building, how it should work, and how completion must be demonstrated. Start here when resuming development. Supporting documents contain deeper implementation/runbook detail; they do not reduce the original product scope.

**Current truth: this is a Coimbatore food/entertainment itinerary planner. Its local collection pipeline retains discovered relevant sources, ranks known publication dates newest-first and fills an identified-spots review database. A real 15-source run downloaded 14 videos and collected 83 loaded comments. The 6 November cleanup of 66 originals left 36 active candidates, 8 merged and 22 held records; ongoing collection may increase counts. Extracted names remain Maps-unconfirmed until operator review. Zero real venues were published at that checkpoint. The full original Instagram vision and city-wide accuracy are NOT complete.** Read [SPOT_IDENTITY_QUALITY.md](docs/SPOT_IDENTITY_QUALITY.md), [INVENTORY_COLLECTION.md](docs/INVENTORY_COLLECTION.md) and [verification](docs/VERIFICATION.md) for exact evidence, gaps and review steps.

This record consolidates the available conversation, current workspace, previous verification report, and selectively reviewed references. It is a living engineering record, not a claim of perfect knowledge, market coverage, or accuracy. If a future check disproves an entry, correct the entry and retain the reason in the change log.

## Owned-model feasibility study ? 6 November 2026

The user requested resources, architecture, implementation/testing/deployment and calculations for removing external AI-model dependence. [OWNED_AI_FEASIBILITY.md](docs/OWNED_AI_FEASIBILITY.md) records the inspected laptop (Ryzen 5600H, approximately 16 GB RAM, 4 GB RTX 3050, 88.5 GiB free), current Qwen/Whisper dependencies, specialist-model versus general-model routes, training-data requirements, memory/compute/power/annotation calculations and a phased proposal. All prices, throughput and staffing assumptions are labelled. This is research only: no runtime change, training, purchasing, cloud upload or product-scope reduction was performed. Owned weights remain unbuilt; existing correction retrieval is not weight training. Proposed English/Tamil milestones do not cancel the multilingual-source requirement, and the INR 3,000/month operating target remains unchanged.

## Instagram completion work ? 6 November 2026

Read [INSTAGRAM_COMPLETION.md](docs/INSTAGRAM_COMPLETION.md) for the full workflow, review procedure and validation checklist. Added local reference-image geometry matching, combined branch/address conflict ranking, resumable structured comment classification, bounded visible reply expansion, uncertainty-aware creator history, prospective calibration measurement, owner-scoped multilingual accuracy labels and independent-correction A/B jobs. These are implemented mechanisms, not claims of calibrated reliability, universal access, trained owned weights or verified city coverage.

| ID | Completion step | Evidence | Remaining dependency |
|---|---|---|---|
| L16 | Local visual reference index and branch candidate ranking | [x] Implemented; geometry/conflict tests; one real page image indexed | Real reel-to-branch accuracy and exact Maps confirmation |
| L17 | Resumable per-comment classes and public reply controls | [x] Implemented; 12 real collected comments classified locally; revised collector fetched 12 | Live expansion controls unavailable on tested post; broader access/accuracy |
| L18 | Creator review uncertainty and prospective calibration report | [x] Implemented and locally tested | Sufficient independent future judgements; no calibrated reliability claim |
| L19 | Private accuracy-review UI, grouped metrics, release gates and paired correction comparisons | [x] Implemented and locally tested | Real independent human labels and measured improvement |
| L20 | Verified inventory and approvals | [ ] 46 active drafts at the first new checkpoint, zero Maps reviews | Current critical facts and explicit approval of every location |

No human gold labels or approvals were fabricated. Local inference, storage and testing remain local. The final runtime and test counts are in the newest [verification record](docs/VERIFICATION.md).

## Latest data quality direction - 6 November 2026

The user observed repeated and irrelevant records and requires duplicate checks before storage and proper names matching the exact Google Maps location. Implemented: conservative name/branch matching before inserts, held extraction reasons, replay-safe evidence merging, uncertain duplicate flags, operator draft merge, reviewable historical cleanup, and explicit Maps name/branch review before preparation/publication. Updated analyst instructions distinguish venue names from generic titles, nearby landmarks, dishes and creator handles. See [SPOT_IDENTITY_QUALITY.md](docs/SPOT_IDENTITY_QUALITY.md).

The real cleanup retained all 66 originals: 8 merged records, 22 held records and 36 active candidates at 10:59:16 IST. It removed 15 repeated list entries and set aside 31 ambiguous observation/vibe associations. The repeat cleanup made zero changes; no venue was published. Later autonomous collection may increase counts. Maps matching is currently an operator review with an optional fresh Places lookup; no automatic live Maps verification or globally accurate naming is claimed. Full original Instagram completion remains open.

Final checkpoint at 11:09:43 IST: the restarted local API/worker are healthy; ongoing collection brought the inventory to 39 active drafts plus 8 merged and 22 held records, with zero published real venues. Full backend suite: 128 passed; final affected suites: 42 passed; eight desktop/mobile checks, strict build and Ruff passed. Backup `data/backups/batore-20261106T053906Z.db` passed integrity checking. Two additional actual Instagram videos have local eight-frame observation results, closing the previous deferred eight-frame execution smoke; accuracy remains unmeasured. See the newest verification section and `data/spot-quality-final-status.json`.

| ID | Step | Evidence level | Remaining limit |
|---|---|---|---|
| L13 | Duplicate and relevance checks before storage; historical cleanup | [x] Implemented, isolated regression tests and actual local cleanup | Heuristics can hold legitimate names; ambiguous branches need review |
| L14 | Canonical name/Maps place review and duplicate prepared-place guard | [x] Implemented and locally tested, with precise place link and explicit operator check | Live Maps lookup unverified; existing names are not yet operator-confirmed |
| L15 | Multivenue evidence association and private review retention | [x] Implemented; old ambiguous associations set aside; owner export/erasure regression coverage | Model attribution accuracy still needs representative labelled evaluation |

## Latest product direction - 5 November 2026

The product is a small food and/or entertainment itinerary planner, not a standalone location-investigation product. Investigation is internal data collection supporting recommendations. Prioritize a Coimbatore venue database with branch/map details, menus or activity offerings and prices, vibe evidence, hours and practical planning facts. Search topics newest-first before selecting sources; distinguish publication dates from collection dates and label undated sources. No claim of exhaustive global chronological search is permitted when a source lacks a date.

The operator will approve **each location** before it appears in itinerary suggestions. Accepted facts or an agent-generated draft must never automatically publish a venue. Newly collected information goes to a private provenance-bearing identified-spots inventory. Unknown coordinates, prices and vibes stay unknown. Implemented: newest-known-first source ordering, all-found-source retention, resumable per-source processing, daily first-party inventory collection, queued web enrichment and explicit approval. The first 15-source expanded run is complete in review; further data collection continues subject to source access and pacing limits.

Final execution checkpoint (5 November, 17:56:51 UTC): API and worker healthy in local mode; 75 jobs done, 57 queued, 66 unapproved candidates and zero real published venues. Seventeen spots have persisted web-search work and eight unverified candidate web-source associations. All 99 backend tests passed in 39.46 seconds; six local browser checks and the strict build passed. Real local inference processed eight frames from a synthetic clip; a new real-reel eight-frame run remains deferred by the daily browser allowance. Backup `data/backups/batore-20261105T175647Z.db` passed SQLite integrity checking. See the latest verification section for evidence and remaining gaps.

## Latest local research execution - 5 November 2026

**This section supersedes the older demo-only runtime and cloud prerequisites below.** The user requires the agent to discover its own examples, present evidence and proposed entries, learn from manual corrections, and keep ML, tests, DB and storage local for now. Read [LOCAL_RESEARCH.md](docs/LOCAL_RESEARCH.md) for the complete procedure, configuration and limits.

The active ignored configuration uses `APP_MODE=local`, isolated `data/local-research.db`, Ollama Qwen3-VL 2B instruct, faster-whisper base CPU transcription, public discovery, and an internal-only release. Gemini and Supabase are not required for this mode. Fictional demo data remains in its separate database.

| ID | Step | Status and evidence | Remaining limit |
|---|---|---|---|
| L01 | Real-data local mode and persistent operator | [x] Isolation/auth tests pass | Loopback single-operator workstation |
| L02 | Self-selected discovery without supplied links | [x] Topics/areas rotate; bounded public search and broader-query fallback | Public search can be unavailable/incomplete |
| L03 | Real source collection and storage | [x] Initial three-reel test plus completed 15-source case: 14 videos and 83 loaded comments | Public page availability varies; comments are a sample |
| L04 | Local inference and speech/video processing | [x] Actual reel frames and available audio processed locally; Tamil detected in one source | Real Tamil/multilingual accuracy unmeasured; model output repairs documented |
| L05 | Correction learning | [x] Scoped retrieval, topic expansion, usage IDs, revoke/export/erase tested | No weight training or actual user correction dataset yet |
| L06 | Human review interface | [x] Evidence, candidate draft prefill, correction editor, run/pause controls; four desktop/mobile checks passed | Independent branch/essential facts still required |
| L07 | Automatic local operation | [x] Durable worker; one active automatic case; four-hour cooldown; three cases/day configured | Computer must stay on; no startup task installed |
| L08 | Regression and records | [x] 99 backend tests, strict build and six local desktop/mobile checks passed; SQLite backup integrity checked | Earlier 12 demo checks are historical; production/PG and quality unverified |
| L09a | Direct public Instagram video/comment sample access | [x] Implemented and live exercised on three agent-selected reels, no login/API token | 32 loaded comments only; not universal access |
| L09b | Broader access and coverage evaluation | [ ] Representative sampling, access failure rates and optional provider validation | Meta/Apify remain unconfigured alternatives |
| L10 | Verified launch database and owned models | [ ] Unfinished | 66 draft candidates are not verified unique venues; independent evidence, labels and training remain |
| L11 | Identified-spots inventory and location approval | [x] Schema 5, source/field drafts, menu/map/vibe UI, owner export/erase, no auto-publication; tests and first real collection pass | Operator approval and broad city coverage outstanding |
| L12 | Newest-first and all-found-source processing | [x] Date probes resume; all found sources retained; real 15-source workflow completed | Provider discovery can be incomplete; unknown dates remain explicit |

Learning retrieves up to four active whole-phrase scoped examples from the same owner/specialist, with a 90-day retrieval lifetime. It does not turn a correction into current venue truth. Local model outputs remain observations. Source text/previews expire after 24 hours; raw video bytes are temporary; observations and review records persist locally. The compact local model does not emit the broader hosted model's structured fact proposals: essential facts use the existing structured review flow.

Real tests caught and fixed: narrow search misses, thinking-model output exhaustion (use explicit instruct weights), PyAV 19 speech decoding incompatibility (pin below 17), out-of-range video seeks (probe duration), engagement counts mislabelled as prices, and duplicate candidates. Incorrect/ambiguous branch interpretation still needs review. No model accuracy percentage or exhaustive city coverage is claimed.

## Latest implementation and user decisions ? 4 November 2026

**Read [the implementation/activation update](docs/BUILD_UPDATE_2026-11-04.md) for the current code state.** The initial-build descriptions retained below are historical where explicitly superseded here.

The user confirmed: INR 3,000/month initial operating target; both Meta and replaceable third-party Instagram connectors with placeholders; internal Coimbatore data collection/verification before invited testers; public release only after successful testing. Owned models are a long-term requirement. The earlier suggested 100 daily active users is **not** an accepted launch commitment.

New code now covers persisted specialist cases/tasks; resumable Meta/Apify collection paths; caption/comment/video analysis contracts; bounded local/targeted frame extraction; branch alternatives and independent lookup leads; human source outcomes; social fact proposals entering review; existing/new branch review; source export/erasure; guided uncertainty discovery; up to four stops; package/dated-session records; occasion and per-companion scoring; internal/test/public access gates; quality metrics; estimated spending reservations; and a nine-entry official-source Coimbatore lead pack. Local checks are recorded in VERIFICATION.md. These do not establish live source access, trained-model quality or a verified city database.

Remaining release-critical dependencies are actual provider/account access, real inventory verification, representative multilingual/location/evidence evaluations, partner feed access, production PostgreSQL/restore/hosting and real invited-user outcomes. Local reference-image matching, uncertainty-aware creator history and prospective calibration measurement were added on 6 November (L16-L19). Broad visual-geolocation quality, calibrated reliability, unrestricted dialogue and owned-model training remain open; implementation is not validation.

## Contents

1. [How to maintain this record](#1-how-to-maintain-this-record)
2. [Product objective and customer need](#2-product-objective-and-customer-need)
3. [Confirmed decisions and boundaries](#3-confirmed-decisions-and-boundaries)
4. [Inputs, outputs and calculation rules](#4-inputs-outputs-and-calculation-rules)
5. [User journeys](#5-user-journeys)
6. [Target pipeline and agent responsibilities](#6-target-pipeline-and-agent-responsibilities)
7. [Data, evidence and publication](#7-data-evidence-and-publication)
8. [Freshness and continuous operation](#8-freshness-and-continuous-operation)
9. [LLMs, deterministic logic and learning](#9-llms-deterministic-logic-and-learning)
10. [Current architecture and code map](#10-current-architecture-and-code-map)
11. [Completion register](#11-completion-register)
12. [Remaining execution sequence](#12-remaining-execution-sequence)
13. [Credentials and external dependencies](#13-credentials-and-external-dependencies)
14. [Verification and release gates](#14-verification-and-release-gates)
15. [Operating procedures](#15-operating-procedures)
16. [Reference knowledge and market position](#16-reference-knowledge-and-market-position)
17. [Risks, unresolved decisions and change log](#17-risks-unresolved-decisions-and-change-log)

## 1. How to maintain this record

### Completion rules

- `[x]` means the **precisely worded subtask** is complete at the stated evidence level. It does not imply the whole feature is ready for customers.
- `[ ]` means unfinished, externally dependent, or not verified. Do not check it merely because code, credentials, a mock, or a design exists.
- **Documented**: decision or procedure recorded; implementation may be absent.
- **Implemented**: relevant code exists; live behavior may be untested.
- **Locally verified**: deterministic/local tests or a recorded manual flow passed.
- **Live verified**: the actual provider/account/data path passed a documented check. Public search, public Instagram metadata and direct browser collection have bounded live evidence; configured paid/API connectors do not.
- **Customer validated**: real outings demonstrate the intended benefit; currently not achieved.

For every completed step, record its ID, date, evidence location, validation performed, and remaining limitation. Reopen a checkbox if a regression invalidates it. Update this file in the same work session as the implementation and update [verification](docs/VERIFICATION.md) when checks change. Never silently replace the full vision with a smaller milestone or use a misleading overall completion percentage.

Decision precedence: explicit latest user instruction > earlier confirmed user decisions > implementation choices > historical reference material. Existing code describes what exists; it does not redefine what was requested.

### Development engagement

Initially the user requested learning/planning only. They later explicitly authorized building the complete application, using placeholder credentials and sensible provider choices, after collecting questions upfront. That build authorization persists. The current request is to consolidate knowledge and maintain progress, not to erase remaining development work.

The user wants initiative and no repeated routine questions mid-build. Record reasonable implementation decisions here; collect necessary provider/account dependencies without asking them to paste secrets into chat. The application itself may ask its end users questions to understand an outing: that is different from interrupting this development engagement.

## 2. Product objective and customer need

Help a person or group decide **where to eat and/or what entertainment activity to do**, then give a practical outing that fits their starting point, time, budget and preferences.

Two equally important entry points:

1. **Explicit intent**: “Coimbatore, sushi.” Investigate relevant places and supporting social content, identify the exact branch, verify practical facts, and propose feasible choices.
2. **Uncertain intent**: “I want to go somewhere / eat something different, but I don't know what.” Understand the person's current mood and previous experiences, present useful contrasts, and suggest a suitable degree of novelty.

The product should remove the work of switching among reels, comments, search, maps, friends' opinions, prices and opening hours. It must explain why a recommendation fits this person and this outing, not merely list popular places.

### Differentiation hypothesis, not a proven market claim

The proposed advantage is the combination of:

- Social-content investigation linked to exact local venues and individual offerings.
- Evidence and freshness visible at the level of important facts.
- Taste-aware novelty instead of generic “top rated nearby.”
- Group/time/budget feasibility, with an editable plan.
- Learning from real outcomes and correcting the database quickly.

These are customer-value hypotheses to validate through interviews and actual outings. We have not established that no competitor offers them, that we are first in India, or that users will switch/pay. Quality, local depth and execution must make the difference.

### Meaning of the “Person of Interest” inspiration

Retain objective continuity, shared investigation state, connecting evidence, alternative explanations, prioritizing consequential gaps, and finishing a job against explicit criteria. Implement this through traceable tasks and evidence relationships. Fictional omniscience is not a system requirement or an accuracy claim. Missing evidence must remain missing until obtained.

## 3. Confirmed decisions and boundaries

| ID | Decision | Status / interpretation |
|---|---|---|
| D01 | Product name: Bites by Batore | Retained proposed default |
| D02 | Coimbatore first supported city; INR | Retained proposed default; verified inventory still needed |
| D03 | Mobile-friendly web/PWA and admin dashboard | User selected this release platform |
| D04 | English interface only | Explicit user correction; do not add Tamil UI by assumption |
| D05 | Source videos may be in any language | Multilingual understanding is required; English results, uncertainty retained |
| D06 | Food and entertainment only | Restaurants, street food, cafés, parks, cinema, gaming/arcades, bowling, go-karting, adventure and related activities |
| D07 | Individual and group outings | Explicit requirement |
| D08 | Starting location, total time, party size and budget | Required planning inputs |
| D09 | Explicit search and uncertain “something different” requests | Both core flows, not optional future ideas |
| D10 | Record private tastes and confirmed visit history | Learn gradually; user can inspect/correct/delete |
| D11 | Ordinary well-supported updates may apply automatically | Unusual, conflicting or odd cases require human/admin review |
| D12 | Continuously maintained data before customer release | Scheduled work alone is insufficient without live sources and quality checks |
| D13 | Google/email accounts, local demo, free initially, external booking links | Confirmed commercial/account scope |
| D14 | Replaceable providers; keys supplied later through placeholders | User authorized provider selection, not a mandatory permanent Gemini dependency |
| D15 | Review supplied references selectively | No wholesale copying or installing the archive |
| D16 | Remove return target and the return-trip idea entirely | No return destination, deadline, travel leg or cost |
| D17 | No events or scenic drives | Explicit exclusion, even if old reference files suggest them |
| D18 | Full build requested after planning | Initial implementation does not satisfy all original requirements |

**Outside this release:** native mobile applications and in-app payments. Hotels, flights and stays were not added from old tourism references. Invitations, group voting, cross-account preference blending, subscriptions, sponsorship, notifications and multi-city expansion are possible extensions, not automatically confirmed requirements. Group suitability itself remains required.

**Implementation defaults, not user constraints:** current selectable maximum four stops, three alternatives, small candidate pools, keyword parsing, 100 provider calls/day, 24-hour refresh default, current model ID, SQLite demo and current scoring weights. These may change to fulfill the intended experience. The user subsequently set an initial INR 3,000/month target and internal-data-first rollout. Final hosting, public user count, production SLA and launch coverage target still require evidence-based operational choices.

## 4. Inputs, outputs and calculation rules

### Request contract

| Field | Requirement and meaning | Existing implementation / gap |
|---|---|---|
| Starting point | Named area or coordinates; resolve ambiguity | Named Coimbatore areas and GPS/custom coordinates exist |
| Available duration | Total outing minutes, beginning with first travel leg | Implemented; never interpret as just travel allowance |
| Party size | Positive person count | Implemented; richer adult/child pricing remains work |
| Budget | INR amount and explicit per-person/group basis | Implemented; per-person amount becomes group cap |
| Intent | Cuisine/dish/place/activity, or uncertain mood | Basic tags/keywords/chips exist; conversational reasoning missing |
| Departure | Date/time, with timezone | IST-aware planning; production date-specific source quality needs validation |
| Transport | Walking/driving/taxi/motorbike as supported | Current options exist; live routes and transport prices need checks |
| Hard needs | Diet, accessibility, relevant age/capacity needs | Basic vegetarian/access/children/capacity filters exist; detailed evidence needed |
| Soft preferences | Atmosphere, novelty, cuisine/activity likes, companion interests | Basic profile/tag support; deeper context learning missing |
| Existing context | Saved plan, locked stops, confirmed visits | Implemented baseline; full group history merging absent |

Hard constraints may exclude candidates. Preferences rank candidates that pass. Never quietly raise a user's budget or relax a stated accessibility/diet requirement. An unknown critical attribute is not a verified “yes.” Asking to broaden the search is a user choice.

### Time and cost

`outing time = first-leg travel + inter-stop travel + waits/check-in + visit/activity durations + contingency`

`group cost = person-priced items × applicable people + shared costs + outbound/inter-stop transport + applicable fees + contingency`

There is no return leg. Full visit windows must fit opening times; open-at-arrival alone is insufficient. Cinema requires the correct session date/time and runtime. Activity packages can require fixed slots, durations, minimum age or group limits. Prices must identify units, inclusions, taxes/fees, date and uncertainty.

Current baseline uses a 15-minute time buffer and a 10% cost reserve; demo travel uses straight-line distance adjusted by 1.35 and simulated speed/cost. These are labelled estimates, not real road routes or quotes. Variable package pricing, complex mixed-age groups and broader multi-stop optimization remain unfinished.

### Recommendation output contract

The target output contains: a small set of distinct alternatives; exact venue and branch; stop order; departure/arrival/wait/activity times; itemized group costs and price basis; total duration; why it fits the request and history; what makes it familiar or different; evidence links and observation/check dates; uncertain or unavailable facts; external directions/booking links; and controls to save, swap, lock or replan.

When no supported feasible plan exists, explain the limiting constraint or missing fact. Do not invent a place, route, available seat, opening time or price to complete the answer. Existing demo results must remain visibly fictional; live mode must not substitute demo inventory.

## 5. User journeys

| Journey | Required behavior | Completion gap |
|---|---|---|
| Specific search | Collect practical inputs → search relevant evidence/venues → verify → rank feasible plans → explain | Local inventory planning exists; automatic external investigation for an unknown request does not |
| “Something different” | Distinguish adventurous vs comfortable, active vs relaxed, food vs entertainment; use history; offer meaningful contrasts | Mood chips/basic novelty exist; adaptive conversation and deeper taste interpretation missing |
| Group outing | Respect every hard need and shared total budget; explain compromises among preferences | Party calculations/basic interests exist; richer group fit remains |
| Reel submission | Accept supported reference/media → report actual access → analyze available modalities → resolve branch → verify facts → recommend/review | Durable investigation chain and autonomous local discovery/collection exist; sampled real evidence reaches review, with accuracy and branch verification pending |
| Revise/save | Lock selected stops, swap alternatives, recompute, save private snapshot, recheck changed facts | Baseline locally verified; larger plans remain |
| After visit | Ask whether actually visited; gather ratings/reasons/context; update relevant tastes, allow correction | Confirmed visits and bounded tag changes exist; reason/context understanding incomplete |
| Correction | Capture wrong hours/price/location with evidence → triage → review/apply → invalidate affected plans | Evidence/revision infrastructure exists; comprehensive public correction experience and operational response need evaluation |
| Admin operations | Inspect coverage, conflicts, source health, queues and costs; publish supported venues; audit changes | Basic desk exists; complete coverage/trust/alert dashboards missing |

All customer surfaces need clear loading, empty, partial, failure, unavailable-source, expired-session and recovery states. Offline shell access is not offline access to current recommendations or private data.

## 6. Target pipeline and agent responsibilities

This section specifies the **full target system**. It is not a claim that independently cooperating specialist agents have already been implemented. The original single-request baseline has now been extended into eight persisted specialist stages. Multilingual and location quality still need live evaluation; see the latest update above.

### End-to-end stage contracts

| Stage | Required inputs | Work and method | Output / completion criterion |
|---|---|---|---|
| P01 Understand request | User text/forms and consented profile | LLM for ambiguous language; schema/rules for units and hard constraints | Valid request, explicit unknowns and constraints |
| P02 Plan investigation | Request, inventory, freshness and provider state | Coordinator identifies missing evidence and bounded tasks | Case record, task dependencies, source plan, cost/time limits |
| P03 Discover leads | City, category/dish, local aliases, hashtags, candidate queries | Search/social/maps connectors; deduplication | Traceable URLs/source IDs and candidate venues; no facts published yet |
| P04 Collect content | Lead and actual access permissions | Fetch supported media/captions/comments/metrics; retain acquisition status | Evidence bundle with modality/access/sample/age information |
| P05 Analyze modalities | Video/audio/text bundle | Speech, translation, scene/keyframe inspection, OCR, caption/comment analysis | Timestamped observations, extracted candidate facts, ambiguity flags |
| P06 Resolve identity | Names, signage, addresses, landmarks, map candidates | Search tools plus evidence comparison | Exact branch confirmed, conflicting candidates, or unresolved location |
| P07 Assess sources | Source history, comments, engagement, independent evidence | Separate reliability, popularity, sponsorship and taste relevance | Claim-level support and source limitations; not a blanket truth score |
| P08 Verify/reconcile | Candidate claims and current authoritative evidence | Rules plus targeted investigation; human review for unusual cases | Accepted/rejected/pending claims, applicability/expiry and reasons |
| P09 Publish/update | Essential verified facts and branch identity | Transactional data changes and revision propagation | Eligible venue/offering or review queue; affected plans invalidated |
| P10 Plan/rank | Eligible venues, routes, costs, slots, preferences | Deterministic constraint engine; learned ranking only where evaluated | Feasible alternatives or specific reasons none can be supported |
| P11 Explain/deliver | Structured computed plan and evidence | Templates or constrained LLM; never invent arithmetic/facts | Understandable plan with sources, estimates and actions |
| P12 Learn/maintain | Confirmed outcomes, corrections, changed sources | Profile update, evaluation, refresh scheduler | Relevant learning, scheduled checks, measurable quality improvements |

### Specialist responsibilities

- **Coordinator:** retain the objective; manage task state, dependencies, evidence gaps, retry limits, provider budgets and completion conditions. Prioritize uncertainty that could change the recommendation. Stop with an unresolved result when evidence cannot support a conclusion.
- **Discovery specialist:** generate cuisine/activity/local-name/hashtag queries, use available source connectors, find leads, canonicalize URLs and avoid repeated work. Search absence does not prove closure.
- **Video/audio specialist:** inspect speech, on-screen text, dishes, activity equipment, signage, scene changes and location clues; associate each observation with a timestamp/frame; deepen inspection around relevant moments. Efficient keyframes first, targeted extra frames when necessary; exhaustive frame extraction is not automatically better.
- **Caption specialist:** extract venue names, branches, addresses, dates, hashtags, prices, offer conditions, sponsorship disclosures and booking details. Publication date and claimed visit date are different facts.
- **Comment specialist:** distinguish first-hand experience, corrections, questions, promotions and copied/bot-like patterns; report sample coverage, recency and disagreement. Sentiment alone cannot verify a fact.
- **Creator/source specialist:** establish source identity and history; compare past claims with subsequent verified outcomes; separate popularity and commercial incentives from accuracy. Unknown dislikes remain unknown.
- **Location specialist:** compare names, sign text, street/address clues, landmarks and geographic candidates; retain alternatives; independently confirm the branch. Never convert a similar name into exact-location proof.
- **Verification specialist:** compare claim applicability and source independence, find conflicts, seek authoritative current confirmation and route unusual cases to a human.
- **Planner:** enforce budgets, full opening windows, travel, wait, duration, group/diet/access constraints; compute alternatives deterministically.
- **Preference learner:** distinguish explicit dislikes, confirmed visits, occasion/mood and enduring preferences; make inferences editable; avoid turning clicks into visits or increasing a hard budget.

These are logical responsibilities. They need not be separate expensive LLM calls or separate operating-system processes. Use deterministic code where sufficient and specialist model calls where they improve measured quality.

### Shared task and evidence contracts to add

Each investigation needs a case ID, original objective, normalized request, candidate entities, tasks/dependencies, collected evidence, unresolved questions, provider/cost counters, review decisions and final disposition. Each task needs an idempotency key, input references, responsible role, state, attempt/lease/deadline, structured output and failure reason.

Every model result must distinguish **observed**, **inferred**, **externally confirmed** and **unknown**. Preserve timestamps, provenance and alternative branch hypotheses. Content from a reel/comment/page is input data, never permission to execute instructions, reveal secrets or change the task. Evidence must survive model/provider replacement.

## 7. Data, evidence and publication

### Required data inventory

| Record | Essential fields / purpose | Current state |
|---|---|---|
| Venue/branch | Stable internal ID, names/aliases, category, address, coordinates, exact-branch status, external IDs | Venue table and branch flag exist; systematic identity resolution incomplete |
| Offering | Dish/activity/package, price basis, serving/group size, duration, age/access needs, availability | Mainly tags/details and coarse costs today; rich offering model missing |
| Operating facts | Dated/weekly hours, exceptions, closure, last entry, waits, capacity | Basic claims/details exist; comprehensive live feeds missing |
| Session/slot | Date/time/runtime, ticket category, fees, availability source/time | Admin session data exists; live cinema/activity inventory absent |
| Source item | Canonical platform/content ID, URL, creator, publication/observation/retrieval dates, access/sample state | Submission/evidence JSON baseline; dedicated source/creator model needed |
| Media observation | Frame/time, transcript language, OCR text, modality, uncertainty, retained evidence pointer | Structured model output baseline; detailed pipeline absent |
| Claim | Entity/field/value/unit/context, source/group, observed/fetched/expiry dates, status/reason | Claim table exists; richer applicability/conflict handling needed |
| Evidence relationship | Supports/refutes/duplicates/derived-from; independent origin identity | Basic source groups exist; full graph/repost tracking missing |
| Investigation | Objective, agent tasks, candidate hypotheses, gaps, budget, conclusion | Jobs exist; full shared case model missing |
| User/profile | Private identity, explicit and inferred preferences, relevant consent/context | Existing profile JSON; deeper separation/evaluation needed |
| Visit/outcome | Confirmed visit, rating dimensions, occasion, reasons, changed facts | Visit records exist; richer inference missing |
| Plan | Request and result snapshot, owner, venue revisions, estimates, saved state | Implemented |
| Operations | Job leases/retries/results, audit, counters, freshness and provider health | Baseline implemented; alerting and coverage metrics incomplete |

Current database tables: `users`, `demo_sessions`, `venues`, `claims`, `plans`, `saved_venues`, `visits`, `submissions`, `jobs`, `audit`, `counters`, `investigations`, `research_tasks`, `research_sources`, `source_assessments` (schema 3). Current category keys are `food`, `cafe`, `park`, `cinema`, `gaming`, `bowling`, `adventure`; street food falls under food and go-karting under adventure unless a later taxonomy change is recorded.

### Evidence rules

1. A search result is a **lead**, an AI extraction is an **observation**, and a supported accepted claim is a **usable fact**. Keep those states distinct.
2. Store when content was published, when the reported experience happened, when it was fetched, and when the relevant fact was verified. They are not interchangeable timestamps.
3. Reposts, copied captions and syndicated articles may share one origin. Ten copies are not ten independent confirmations.
4. Resolve exact branches before attaching prices, hours or reviews. Preserve competing candidates until resolved.
5. A trusted source can be wrong, outdated or speaking about a different package/date. Assess each claim, not only its author.
6. Retain conflicts and review reasons. New arrival order does not make old observations newer.
7. Expiry is field-specific. A verified address does not refresh a ticket price. A successful HTTP response does not verify everything in a venue record.
8. Source popularity, evidence confidence and personal taste fit are separate dimensions. Likes or unavailable dislikes must not become invented reliability evidence.
9. Track the sampling boundary: partial comments or reviews must be described as a sample.
10. Keep owned/merchant facts and provider-restricted content distinguishable. Review current source storage and attribution terms before enabling collection; do not build an unrestricted permanent mirror from a provider response.

### Publication policy

Target automatic acceptance requires identity, source provenance, applicable/current evidence, acceptable confidence and no consequential unresolved conflict. Ordinary well-supported facts can publish; unusual cases enter admin review. No model output alone should silently establish a price, accessible entrance or exact branch.

Current rules accept certain ordinary trusted merchant/official updates. Zero or large price changes (currently more than 35%), consequential closure/address/access/diet changes and other unusual cases require review. Visitors cannot self-declare an official source. Duplicate URL/field/observation combinations are deduplicated; older facts do not replace newer applicable facts. These are baseline rules, not proof of a fully calibrated evidence policy.

A pending venue can become publishable after exact-branch confirmation and accepted current essential price/hours/closure facts. Admin can publish/pause; accepted updates increment revisions so saved plans can require rechecking. Operational settings also need review: group capacity, minimum age, visit/wait duration, sessions and extra fees cannot be made correct by a publication toggle.

### Building the real first-city database

- Define launch neighbourhoods, categories, budget bands and minimum useful coverage before claiming city coverage.
- Gather permitted leads from search/social/maps, merchant submissions and direct local research.
- Deduplicate and confirm branches; preserve source identity and collection dates.
- Obtain essential prices, hours, offerings, constraints and booking links through usable evidence.
- Inspect representative venues directly or with trusted local contributors; record observations, not unsupported endorsements.
- Run wrong-branch, wrong-hours, price and accessibility checks against a human-labelled sample.
- Publish only eligible records; retain unresolved leads separately.
- Start continuous refresh and correction handling before serving customer recommendations.

No fixed venue count, “hidden gem” quota or old reference seed list has been accepted as a launch-quality standard. The twelve current demo records and historical example CSV rows are fictional fixtures.

## 8. Freshness and continuous operation

The requirement is a continuously maintained database with demonstrable freshness, not continuous model calls for their own sake. Use push updates where available, change-aware polling elsewhere, and request-time checks for facts that affect a pending outing.

### Existing scheduler defaults

| Mechanism | Current value / behavior | Limitation |
|---|---|---|
| Worker polling | 5 seconds | Local process, not production uptime proof |
| Scheduler pass | Once per minute | Queue capacity still matters |
| Regular refresh | Every 24 hours by default | Not every field is reverified |
| Upcoming saved plans | Hourly refresh for relevant venues within the upcoming-day window | Does not guarantee real price/session inventory |
| Job lease | 10 minutes; recover expired leases | Distributed scale/stress behavior not fully proven |
| Retries | Backoff, default maximum 3 attempts | Failed work needs operator attention |
| Priority | Analysis 90; urgent correction 85; active-plan refresh 80; discovery 50; regular refresh 20 | Fairness/starvation policies need scale evaluation |
| Provider budget | Default 100 calls/day | Call cap is not a monetary ceiling |
| Merchant push | Signed HMAC webhook with replay protection | No real merchant connected |
| Saved-plan validity | Venue revision/critical expiry and age can trigger recheck | Customer-facing end-to-end freshness still needs live verification |

Current live refresh mainly checks Google operating status; it does not reverify every menu price, dish, accessibility condition, wait or activity slot. A demo refresh inspects fixtures and must not appear to be a live source update.

### Target freshness improvements

- Define expiry/check policies per field, source and volatility; use upcoming customer demand and contradictions to raise priority.
- Store last attempted check separately from last successful verification; record what was checked.
- Use source change signals, authorized webhooks, incremental cursors and deduplicated jobs to avoid unnecessary repeated fetches.
- Track launch-area/category gaps; reserve capacity for new discovery as well as popular existing venues.
- Recheck live-critical opening/session/routing facts before finalizing a plan; recheck price/availability through appropriate sources.
- Degrade safely during outages: show uncertainty or exclude an unsupported candidate, with a useful explanation.
- Alert on stale critical facts, delayed queues, failed/expired credentials, repeated provider errors, quota exhaustion and suspicious changes.
- Propagate accepted corrections to affected saved plans; implement user notifications only as an explicit additional product decision.
- Measure provider cost per useful verified update and latency from correction to affected-plan recheck.

Do not invent refresh SLAs. Establish actual budgets, access quotas, coverage and field volatility, then set measurable targets. “Always accurate” is an ambition; the product earns trust by promptly checking and correcting facts and visibly distinguishing what it knows.

## 9. LLMs, deterministic logic and learning

**Gemini is not required by the product concept.** It was selected as a replaceable multimodal provider. An alternative hosted or local model can fulfill the role if it passes the same quality, cost, language and latency evaluations. A model API key does not grant access to Instagram videos or comments.

| Work | Appropriate method | Current state |
|---|---|---|
| Natural-language intent, captions, translation, ambiguous evidence | LLM with structured validated outputs | Multimodal/text adapter exists; conversational discovery missing |
| Speech/OCR/scene observations | Multimodal LLM and/or specialized speech/OCR/vision tools | One broad provider request, not a complete staged pipeline |
| Arithmetic, routes, hard filters, time/cost feasibility | Deterministic code and routing service | Baseline implemented and locally tested |
| Job execution, retries, deduplication, scheduling | Durable deterministic worker | Implemented baseline |
| Personalized recommendations initially | Editable profile, explicit feedback, bounded scoring | Implemented simple tag-weight baseline |
| Later ranking/novelty learning | Evaluated ML when enough representative outcomes exist | No trained recommendation model |
| Reliability assessment | Evidence history, source identity, corroboration, calibrated models where justified | Basic counts only; full system missing |

Current feedback learning must not be described as a sophisticated trained model. Confirmed visits update limited tag preferences; clicks and saves are not visits. Richer feedback dimensions and notes are recorded but not fully interpreted. Session mood must not overwrite lasting preference, and positive feedback must not silently increase the next request's hard budget.

Before adding trained ML: collect consented outcomes, define the prediction/ranking task, split evaluation by time/user to prevent leakage, compare against the simple baseline, measure subgroup/cold-start performance and keep correction/deletion possible. Training a model is conditional on measurable value, not a mandatory prerequisite to a useful first product.

## 10. Current architecture and code map

`React PWA → FastAPI → SQLAlchemy database` with a separate database-backed worker/scheduler. Live external calls use provider adapters. Local demo uses SQLite and labelled fixtures; intended live storage/auth uses PostgreSQL/Supabase. No Redis or vector database is currently required.

| Path | Responsibility |
|---|---|
| [backend/app/main.py](backend/app/main.py) | API routes and application orchestration |
| [backend/app/schemas.py](backend/app/schemas.py) | Validated request/data schemas |
| [backend/app/db.py](backend/app/db.py) | Persistence and schema/migration support |
| [backend/app/auth.py](backend/app/auth.py) | Demo sessions, live token validation and admin checks |
| [backend/app/planner.py](backend/app/planner.py) | Feasibility, ranking and plan construction |
| [backend/app/providers.py](backend/app/providers.py) | Google, Gemini, Brave and YouTube adapters |
| [backend/app/resolver.py](backend/app/resolver.py) | Candidate venue matching, not full visual geolocation |
| [backend/app/evidence.py](backend/app/evidence.py) | Claims, acceptance/review, publication and revisions |
| [backend/app/jobs.py](backend/app/jobs.py) | Queue, worker, retry/lease/refresh behavior |
| [backend/app/ingest.py](backend/app/ingest.py) | Signed merchant ingestion |
| [backend/app/config.py](backend/app/config.py) | Environment configuration |
| [backend/app/manage.py](backend/app/manage.py) | Migration and local backup commands |
| [backend/app/seed.py](backend/app/seed.py) | Fictional demo inventory |
| [backend/app/research.py](backend/app/research.py) / [research_api.py](backend/app/research_api.py) | Durable specialist coordinator, evidence review and private investigation APIs |
| [backend/app/social.py](backend/app/social.py) / [web_evidence.py](backend/app/web_evidence.py) | Configurable social connectors and bounded official-page collection |
| [backend/app/analysts.py](backend/app/analysts.py) / [media.py](backend/app/media.py) | Typed specialist model outputs and local video frame extraction |
| [backend/app/discovery.py](backend/app/discovery.py) / [operations.py](backend/app/operations.py) | Guided preference conversation, data readiness and launch review gates |
| [resources/coimbatore-launch-leads.json](resources/coimbatore-launch-leads.json) | Nine unverified official-source research leads; not published inventory |
| [web/src](web/src) | Discover, details, saved library, tastes, sources and admin UI |
| [web/public](web/public) | PWA manifest, icons and service worker |
| [backend/tests](backend/tests) / [web/tests](web/tests) | Backend/provider and browser/accessibility/PWA verification |
| [scripts](scripts) | Windows start/stop/check commands |
| [Dockerfile](Dockerfile) / [compose.yaml](compose.yaml) | Container definitions; not yet runtime verified |

Important current limits: one to four stops; up to three alternatives; small candidate pools (demo up to 18 stored candidates, live up to 10 nearby published candidates); basic intent parsing. Discovery jobs produce leads but do not autonomously complete lead → media → exact branch → accepted claims → new venue publication. The request planner does not initiate a complete external investigation when its inventory cannot answer.

The resolver compares a small number of model-proposed names with stored venues and Google name/address candidates. String similarity is not exact-branch proof. There is no Google Lens integration. Bounded ffmpeg frame extraction and model-based text/sign inspection now exist, alongside human-reviewed creator history; their real-world accuracy remains unverified.

## 11. Completion register

Additional precisely scoped completions, 4 November 2026:

- [x] U01 ? Meta and saved-task third-party connector implementations with placeholders, bounded collection and resumable runs. **Implemented/mock-tested**, not live verified (C05 remains open).
- [x] U02 ? Typed caption/comment/video outputs and actual local ffmpeg frame extraction. **Locally verified extraction/contract boundaries**; multilingual model quality remains F03.
- [x] U03 ? Source branch review, pending-venue creation, dated social claim proposals, creator factual outcomes and copy/sample accounting. **Locally verified baseline**; advanced identity/reliability quality remains C08/C09.
- [x] U04 ? Selectable one-to-four-stop plans, dated sessions, person/group packages, per-companion interests and occasion preference updates. **Locally verified baseline**; broader optimization and partner feeds remain B09/B10.
- [x] U05 ? Internal-first release gate, invited account allowlist, data-review workflow, quality dashboard and configurable estimated INR spending reservations. **Locally verified**; reservations are not invoice guarantees.
- [x] U06 ? Nine researched official-source Coimbatore leads and idempotent review import. **Documented/local import tested**; no real venues auto-published, DTA07 remains open.


All completed implementation entries below reflect recorded work through **4 November 2026**. Evidence comes from the linked source files, [verification report](docs/VERIFICATION.md), backend tests and browser tests. No live-provider or production completion is implied.

### A. Scope and documentation

- [x] A01 — Record confirmed scope, exclusions and initial architecture. **Documented.** [Plan](docs/PLAN.md), [architecture](docs/ARCHITECTURE.md).
- [x] A02 — Selectively inspect user reference project, PROJ documents and Claude OS archive. **Documented.** [Reference review](docs/REFERENCE_REVIEW.md); no executable reference code copied.
- [x] A03 — Create this canonical full-scope knowledge record, evidence-level checklist and remaining execution procedure. **Documented.** This file.
- [ ] A04 — Keep the register synchronized after each subsequent completed implementation/validation step. **Ongoing obligation**, not permanently completable.
- [ ] A05 — Dated FavHiker matrix completed in FAVHIKER_DEEP_REVIEW.md; broader market and customer differentiation validation remain open.

### B. App and planning baseline

- [x] B01 — English responsive PWA with Discover, Places, Saved, Taste, Sources and Admin surfaces. **Locally verified.** Browser suite and web build.
- [x] B02 — Practical request inputs, group/per-person budgets, baseline hard filtering and one/two-stop plans without return calculations. **Locally verified.** Planner/backend tests.
- [x] B03 — Cost/time breakdown, reserve, full opening-window/movie checks, lock/swap/replan and infeasible states. **Locally verified baseline.** Not arbitrary-length optimization or live seat availability.
- [x] B04 — Saved plans/places, revision rechecks, private profile/visit history and bounded taste updates. **Locally verified.** Core journeys.
- [x] B05 — Data export/erase, preference editing and history clearing. **Locally verified baseline.** Production retention/backup deletion policy still needed.
- [x] B06 — Public-shell PWA caching, install icons, offline reconnect behavior and desktop/mobile automated accessibility checks. **Locally verified.** Not a full manual accessibility audit.
- [ ] B07 — Guided undecided choices and independent mood/novelty controls implemented/local tested (FH06); fully adaptive conversation and real-user usefulness remain unvalidated.
- [ ] B08 — Reversible visit/dish taste and occasion rebuilding, cuisine/spice controls implemented/local tested (FH04/FH09); deeper reason-aware interpretation and real group suitability remain open.
- [ ] B09 — Broader multi-stop planning, variable activity packages, mixed pricing and uncertainty-aware costs.
- [ ] B10 — Live cinema/activity sessions, prices and availability integrations where access exists.

### C. Social discovery and investigation

- [x] C01 — Accept supported reference links, supplied text/comments/transcripts and small permitted video uploads; persist processing status. **Locally verified.** Upload limit/signature and URL validation tests.
- [x] C02 — Write structured Gemini text/video analysis adapter, including text-only “video not analyzed” handling. **Implemented; mocked/local contract checks.** No live multilingual quality validation.
- [x] C03 — Write Brave/YouTube/Google discovery and simple candidate resolver adapters. **Implemented; mocked/local contract checks.** Not a complete Instagram agent.
- [x] C04 — Display explicit missing-source/provider states rather than inventing analysis. **Locally verified baseline.**
- [ ] C05 - Broad Instagram location/keyword/hashtag discovery and complete access evaluation. **Partial live evidence:** public keyword discovery, newest-known-date ordering, all-found-source retention, actual video/caption/loaded-comment collection. Meta cursor pagination is implemented/mock-tested; access and exhaustive coverage are not verified.
- [x] C06 - Shared investigation cases, specialist dependencies, durable batches, retries, quota deferral and completion gates. **Implemented/local tests and real 15-source completed workflow.**
- [ ] C07 - Speech/scene/keyframe/OCR processing and targeted reinspection with multilingual evaluation. **Implemented:** local ASR, scene-cut and fallback sampling, all-frame-group analysis and requested follow-up inspection. **Actual execution:** two real eight-frame reel results now exist. **Unfinished:** representative language/OCR accuracy; private labelling and error metrics are implemented in L19.
- [ ] C08 — Implement exact-branch investigation from multiple visual/text/geographic clues and independent confirmation.
- [ ] C09 — Implement meaningful comment evidence classification, creator identity/history, repost independence and source reliability evaluation.
- [x] C10 - Connect discovery, collection, analysis, branch hypotheses, identified-spots storage and explicit review/publication gates. **Implementation/local publication-boundary tests and real collection-to-draft evidence.** No real location has been approved or published.
- [x] C11 - Connect relevant inventory gaps in user requests to external investigation, with honest partial/unavailable outcomes. **Implemented and locally tested; live inventory/route quality remains unverified.**

### D. Data and freshness

- [x] DTA01 — SQLAlchemy schema, SQLite persistence and twelve labelled fictional fixtures. **Locally verified.** No real inventory completion.
- [x] DTA02 — Claim provenance/dates, ordinary acceptance, unusual-case review, duplicate/old-fact handling and revision invalidation. **Locally verified baseline.**
- [x] DTA03 — Admin venue/operational settings, branch confirmation, publish/pause and audit controls. **Locally verified baseline.**
- [x] DTA04 — Durable queue, deduplication keys, atomic leases, retries, restart recovery, priorities and heartbeat. **Locally verified.** Distributed production load unverified.
- [x] DTA05 — Scheduled refresh, upcoming-plan priority and request-time Google status/opening/route adapter paths. **Implemented/local contract verified.** Real freshness not verified.
- [x] DTA06 — HMAC merchant ingestion with timestamp/replay checks and unusual-update review. **Locally verified.** No real partners onboarded.
- [ ] DTA07 — Build and independently verify the real Coimbatore launch inventory across required categories and needs.
- [ ] DTA08 — Typed menu/review evidence and private dish/visit relationships expanded in schema 7 (FH02/FH07); the full pipeline's verified real price/session/creator dataset remains incomplete.
- [ ] DTA09 — Operate actual source updates, per-field adaptive freshness, coverage checks, correction handling and failure alerts.
- [ ] DTA10 — Demonstrate that accepted corrections recheck affected live recommendations promptly under expected load.

### E. Accounts, providers and deployment

- [x] E01 — Isolated opaque local demo sessions and server-side live admin allowlist logic. **Locally verified.** Demo admins are intentionally different from live admin authorization.
- [x] E02 — Supabase email/Google auth integration and PostgreSQL/RLS migration code. **Implemented.** Real Supabase/PostgreSQL account behavior unverified.
- [x] E03 — Placeholder configuration and provider/key setup guides. **Documented.** Secrets absent from committed files.
- [x] E04 — Windows dependency/build/start/stop flow and hidden API/worker operation. **Locally verified.** Current running state must be checked, not inferred from past startup.
- [x] E05 — SQLite online backup and integrity check. **Locally verified.** Full production restore drill remains.
- [x] E06 — Container build/deployment definitions. **Implemented only.** Docker Linux engine was unavailable for execution.
- [ ] E07 — Configure real credentials/account permissions and validate each actual provider integration with bounded usage.
- [ ] E08 — Validate Supabase login/authorization, PostgreSQL migration/RLS, backup and restore on staging.
- [ ] E09 — Validate container build/run if using containers; select and deploy production hosting, HTTPS and process supervision.
- [ ] E10 — Enable production monitoring, alerts, cost controls, retention rules and operational ownership.

### F. Quality and launch

- [x] F01 — Recorded backend suite: **36 passed**, plus static checks. **Locally verified.** Isolated SQLite and mocked providers.
- [x] F02 — Recorded browser suite: **10 passed**, strict TypeScript/production build, automated accessibility and PWA checks. **Locally verified.**
- [ ] F03 — Build human-labelled multilingual/video/location/comment/evidence evaluation cases and pass agreed quality gates.
- [ ] F04 — Test the full live discovery-to-recommendation chain, source outages, quota failures and correction propagation.
- [ ] F05 — Evaluate production concurrency, latency, queue fairness, cost and outage recovery against the actual launch workload.
- [ ] F06 — Run representative customer outings and measure usefulness, wrong-place/hours/price rates and budget/time compliance.
- [ ] F07 — Pass all customer-launch gates and record the release decision. **Not currently customer ready.**

## 12. Remaining execution sequence

This is the implementation order, not a claim that supplying keys finishes the app. Much of the missing coordinator, data model, connectors, analysis, learning and pipeline code can be built with fixtures before live credentials arrive.

| Phase | Actions and dependencies | Required output / definition of done |
|---|---|---|
| X01 Preserve scope and baseline | Keep this register, reproducible local checks and existing data boundaries | Full requirements mapped to tasks; baseline failures fixed before integration work |
| X02 Source access contracts | Determine usable Instagram/search/video/merchant/cinema routes; document fields, permissions, limits, retention and costs | Concrete connector contracts and representative test fixtures; unavailable capabilities explicitly identified |
| X03 Investigation data/orchestrator | Add shared cases, tasks, evidence references, hypotheses, budgets, cancellation and completion rules | Restartable bounded workflow; no duplicate execution or fabricated success; tests cover interrupted and partial cases |
| X04 Collection and media analysis | Implement actual source connectors plus speech/OCR/scenes/keyframes/targeted reinspection | Modality coverage reported accurately; timestamped structured observations; test multilingual/ambiguous inputs |
| X05 Resolution and trust | Branch hypotheses, independent confirmation, source canonicalization, comment/creator history | Wrong-branch examples rejected; copies do not multiply confidence; unknowns and conflicts survive |
| X06 Full evidence pipeline | Connect leads to claims, human review and publication; extend offering/session schema | A supported lead can become a verified eligible venue; weak/conflicting evidence cannot silently publish |
| X07 Discovery experience and learning | Conversational uncertainty handling, meaningful novelty, group tradeoffs, richer feedback | New and returning users receive useful choices; hard constraints preserved and inferences correctable |
| X08 Planner completion | Extend multi-stop/package/group pricing; integrate real session/availability where accessible | Feasible schedules and cost ranges evaluated against representative scenarios; no invented inventory |
| X09 Live activation and inventory | Supply local secrets, verify account access, build real city records, validate provider outputs | Real examples pass each connector and publication gate; demo/live datasets remain separate |
| X10 Continuous operations | Per-field freshness, push/poll strategies, coverage, alerts, quotas and cost tracking | Sustained data maintenance and correction propagation demonstrated with outages and load |
| X11 Staging and customer evaluation | Auth/DB/restore, deployment, privacy, load, labelled evidence evaluation, real outings | Recorded release evidence and operational owner; remaining limitations explicitly accepted |

Phases can overlap where dependencies allow. For example, fixture-based coordinator work need not wait for an Instagram token, but live collection cannot be declared complete until the actual access path works. Do not silently replace an unavailable access path with fabricated results.

## 13. Credentials and external dependencies

Put actual values in ignored local `.env` or the production secret store. Never paste private values into this file, source code, browser bundles, screenshots or logs. See [KEYS.md](docs/KEYS.md) and [.env.example](.env.example).

| Setting | Purpose / requirement |
|---|---|
| `APP_MODE` | `demo` locally; `live` only with separate real setup |
| `DATABASE_URL` | SQLite demo or backend-only PostgreSQL connection; TLS in live setup |
| `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` | Live account project/public browser credential; not a server secret |
| `ADMIN_USER_IDS` | Server-controlled allowed Supabase UUIDs |
| `GOOGLE_MAPS_API_KEY` | Enabled Places/Routes services, account access, restrictions and billing configuration |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Chosen analysis provider/model; model placeholder is now blank and requires actual account selection/testing |
| `BRAVE_SEARCH_API_KEY` | Web search access |
| `YOUTUBE_API_KEY` | YouTube metadata/search/comment access subject to availability |
| `META_ACCESS_TOKEN`, `META_INSTAGRAM_ACCOUNT_ID` | Implemented Meta connector also needs `META_GRAPH_VERSION`, provider selection and actual permissions; alternative Apify saved-task connector exists |
| `MERCHANT_WEBHOOK_SECRET` | At least 32 random characters for an approved signed partner integration |
| `WEB_ORIGIN` | Actual frontend origin, HTTPS in production |
| `MAX_PROVIDER_CALLS_PER_DAY` | Default 100; supplement with provider-specific monetary controls |
| `MAX_MEDIA_MB` | Default 12 |
| `WORKER_POLL_SECONDS`, `REFRESH_INTERVAL_HOURS`, `MAX_ATTEMPTS` | Defaults 5, 24 and 3; tune against real workload |

Google OAuth client credentials belong in the Supabase dashboard; configure redirects and email/SMTP there. Provider permissions, application review, contracts, content rights, regional support and partner feeds may be dependencies beyond API keys. Cinema seats and activity slots are not unlocked by an unrelated Google key.

No Redis/vector database/payment/app-store credential is currently required. Credentials must not trigger uncontrolled recurring paid work merely by existing: configure enabled jobs, geographic scope, provider limits and budgets before live activation.

## 14. Verification and release gates

### Evidence already recorded

The existing [verification report](docs/VERIFICATION.md), dated 4 November 2026, records 55 passing backend tests and 12 passing browser tests, strict build/static checks, automated desktop/mobile accessibility checks, PWA behavior, Windows launcher/stop/restart, worker heartbeat and SQLite backup integrity. These checks were executed during the investigation implementation update; earlier documentation-only consolidation did not rerun application tests.

Provider tests used mocks. Live Supabase/PostgreSQL, Google, Gemini, Brave and YouTube account checks have not passed because they have not been run with the actual configured accounts. Docker runtime was not verified because its Linux engine was not running. A non-failing Starlette TestClient deprecation warning was recorded; it is not evidence of provider health.

### Required evaluation dataset

Include specific and vague requests, new/returning users, food-only/activity-only/combined outings, restrictive budgets, multiple party sizes, dietary/access needs, overnight hours, late arrivals, uncertain waits, movie sessions, unavailable routes and impossible plans. Include Tamil and other-language media, mixed-language speech, ambiguous signs, misleading captions, copied posts, sponsored content, unavailable comments, wrong branch names, stale prices and conflicting sources. Label correct entities, supported facts, unknowns and required review outcomes with human evidence.

Model evaluation must distinguish extraction quality from truth verification: correctly transcribing a false price claim does not verify the price.

### Customer-launch gate checklist

- [ ] L01 — Launch geography/category coverage defined and independently checked; no fictional records eligible in live mode.
- [ ] L02 — Every published branch has usable essential evidence and appropriate source dates; critical unknowns handled honestly.
- [ ] L03 — Actual permitted social/video/search source paths work; full investigation workflow demonstrates success and partial failure.
- [ ] L04 — Human-labelled media/location/evidence evaluation passes agreed thresholds; branch mistakes and unsupported claims measured.
- [ ] L05 — Google/other route and operating checks work for real launch geography/dates; missing route elements are not zero-time legs.
- [ ] L06 — Required merchant pricing, session/package and capacity information is current enough for supported recommendations.
- [ ] L07 — Separate users cannot access each other's plans/visits/submissions; real admin access requires the server allowlist.
- [ ] L08 — PostgreSQL migration, RLS assumptions, backup/restore and worker resumption pass on staging.
- [ ] L09 — HTTPS, OAuth/email redirects, process supervision, alerts and incident recovery operate on the chosen host.
- [ ] L10 — Queues, provider quotas and monetary budgets sustain intended freshness and request latency under expected demand.
- [ ] L11 — Data retention, source attribution, user deletion/export and operational access are checked for the actual production setup.
- [ ] L12 — Representative people complete real outings and provide outcome feedback; usefulness and practical errors are measured.

Track wrong-place/branch rate, wrong-hours rate, actual-vs-estimated price/time error, constraint violations, freshness coverage, correction latency, useful recommendation rate, discovery diversity, repeat usefulness, queue latency/failures and cost per useful plan/update. Define thresholds using actual launch needs and evidence; no unsupported numeric accuracy promise has been agreed.

## 15. Operating procedures

### Local development and checks

From the project root:

```powershell
.\scripts\start.ps1
```

Open `http://127.0.0.1:8000`. The launcher installs locked dependencies, builds the client and starts hidden API/worker processes. Existing `.env` is preserved. Use `-SkipBuild` only when the existing client build is current. Stop with:

```powershell
.\scripts\stop.ps1
```

Run appropriate baseline checks:

```powershell
.\scripts\check.ps1
```

With the built app running, run browser checks from `web/`:

```powershell
npm run test:e2e
```

Backend tests use an isolated temporary database. Browser tests create demo accounts and can replace ignored `web/test-results/`. Logs/database live under ignored `data/`. A previously recorded running app does not guarantee it is running now; inspect health and worker heartbeat when reporting current operation.

### Live setup sequence

1. Use a separate PostgreSQL/Supabase environment; keep demo storage isolated.
2. Configure secrets, permitted sources, provider quotas and monetary limits locally/server-side.
3. Configure auth redirects/SMTP/Google login, live origin and server admin UUIDs.
4. From `backend/`, run `uv run python -m app.manage migrate`; validate the schema/RLS using staging.
5. Run bounded smoke checks for actual auth, places, dated hours, routes, search, available comments and multilingual analysis.
6. Verify fixture/live separation and unavailable/partial-provider outcomes.
7. Load independently sourced venue evidence, confirm branches and review publication eligibility.
8. Run the worker under supervision with enabled-source scope, monitoring and budget controls.
9. Pass the release gates before making customer-ready claims.

Detailed commands and caveats: [setup](docs/SETUP.md), [operations](docs/OPERATIONS.md), [integrations](docs/INTEGRATIONS.md).

### Review/correction procedure

Inspect the source and applicable date → confirm venue/branch and unit/package → compare existing evidence → accept ordinary supported facts or route unusual/conflicting facts to review → record decision and reason → increment affected venue revision → recheck affected plans → verify the customer-visible result. Do not overwrite provenance or mark a failed refresh as successful.

### Worker failure procedure

Inspect job kind, attempts, lease, sanitized error and provider health. Distinguish missing access from transient failure. Recover/retry within limits; avoid duplicate side effects. Keep last successful fact timestamp unchanged. Escalate repeatedly failed critical checks and show affected facts as uncertain/unavailable. Prioritize upcoming plans and material corrections without indefinitely starving discovery.

### Merchant integration

Current `/api/ingest/merchant` verifies HMAC-SHA256 over timestamp and raw body, a five-minute timestamp window, replay identity/payload handling and bounded batches. It supports an approved operator/partner integration, not self-service per-merchant authorization. Full protocol: [MERCHANT_UPDATES.md](docs/MERCHANT_UPDATES.md). Onboarding real partners and defining scoped credentials remain tasks.

### Backup and privacy

From `backend/`, `uv run python -m app.manage backup-demo` creates a SQLite online snapshot including committed WAL data. For restore, stop this app's processes, retain the current database and restore a tested snapshot to the configured location. Do not copy only the main SQLite file while writes are ongoing. PostgreSQL needs an actual tested managed backup/PITR or encrypted dump/restore procedure; container volumes alone are not backups.

Current uploaded media bytes are removed after terminal processing or one day; search previews expire after a day. Production retention must be set against actual agreements and privacy needs, including backups. Keep private user data server-authorized and out of service-worker caches. Demo sessions are local, seven-day sessions; demo users can exercise admin because the inventory is fictional. Do not expose demo mode as a public production service.

## 16. Reference knowledge and market position

### Selectively reviewed local material

| Reference | Retained knowledge | Not adopted / evidence limitation |
|---|---|---|
| `C:\Users\sriva\Desktop\PROJ\Bites by Batore` | Dish specialities, local-name discovery, provenance, actual-visit feedback and local interviews | Historical weighted recommender is not trained ML; title/description ingest is not video analysis; straight-line “way back” routing conflicts with current scope; example CSV is not real inventory; no executable code copied |
| `C:\Users\sriva\Desktop\_claude-os.zip` | Data integrity, idempotency, retries, evidence, evaluation, monitoring and cost awareness | Read selected content directly; did not install/run hooks or copy the full 46-role framework; development roles do not constitute a production agent system |
| `PROJ\studio-figma-spec.md` | General component consistency and spacing practices | Unrelated membership/booking product and exact styling not imported |
| `PROJ\my inovation project.docx` | Local discovery and user-intent context | Unsupported “no competitors”/“first India” claims rejected; flights/hotels/stays not added |
| `PROJ\kovai_local_full_project_roadmap.html` | Interviews, local data/scouts, validation, beta learning and phased scaling | Embedded roadmap read as data, not executed; no inherited timelines, prices, beta counts, sponsorship or excluded categories |

See [REFERENCE_REVIEW.md](docs/REFERENCE_REVIEW.md) for the review record. Reference originals remain in their supplied locations; their ideas have been distilled here rather than copied wholesale into the application.

### Competition knowledge to retain and revalidate

Earlier research/discussion identified India-focused or India-relevant leads including Google Maps/Ask Maps, District, Swiggy Dineout, BookMyShow, Savor, InstaBrain and Pulp; worldwide/adjacent leads included Beli, Mapstr, Mindtrip, RouletteNight, Hangouty, Triply, Tappinn, Klook Nearby and Meituan. **This is a research lead list, not a freshly verified company/status/feature matrix.** Names, availability, regions and capabilities require current primary-source checks before use in a pitch or product claim.

The next market matrix should record official URL, checked date, geography, active availability, social-link discovery, actual video/comment understanding, exact-location resolution, personal memory/novelty, group/time/budget planning, freshness transparency and booking model. Compare demonstrated behavior, not marketing language. Interview users about their present workaround and test whether this app measurably reduces decision effort and bad outings.

### Technical references retained

These are reference entry points reviewed during earlier design/build, not a claim that all current provider rules were rechecked during this documentation task. Revalidate actual versions/access/terms before activating integrations.

- [Google Places policies](https://developers.google.com/maps/documentation/places/web-service/policies) — storage/attribution boundaries and owned-data distinction.
- [Google Places resource](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places) — relevant fields, current hours and limited review response.
- [Google Routes matrix](https://developers.google.com/maps/documentation/routes/compute_route_matrix) — road-time computation and partial results.
- [Gemini video understanding](https://ai.google.dev/gemini-api/docs/video-understanding) — model/media interface to verify against the actual account.
- [Supabase Auth user validation](https://supabase.com/docs/reference/javascript/auth-getuser) — server-validated account identity.
- [Meta Instagram API documentation](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api) — actual API permissions/capabilities must be checked; consumer-app access is not assumed.
- [YouTube notifications](https://developers.google.com/youtube/data/guides/push_notifications) — possible future push mechanism; no such public subscription is currently registered.

### Supporting project documents

[README](README.md) · [Original plan](docs/PLAN.md) · [Architecture](docs/ARCHITECTURE.md) · [Acceptance criteria](docs/ACCEPTANCE.md) · [Verification](docs/VERIFICATION.md) · [Setup](docs/SETUP.md) · [Operations](docs/OPERATIONS.md) · [Keys](docs/KEYS.md) · [Integrations](docs/INTEGRATIONS.md) · [Merchant protocol](docs/MERCHANT_UPDATES.md) · [Reference review](docs/REFERENCE_REVIEW.md)

## 17. Risks, unresolved decisions and change log

| Issue | Required action / owner role | Current disposition |
|---|---|---|
| Instagram access and completeness | Integration work must establish a real usable access route and sample limitations | Unresolved; reserved Meta keys are not implementation |
| Unsupported full-product completion claims | Development must report exact evidence level per task | Corrected in this master; full product remains incomplete |
| Model hallucination/translation errors | Evaluation and verification must check timestamped observations against human evidence | Live evaluation missing |
| Similar-name/branch mistakes | Location resolver must retain alternatives and require confirmation | Simple matching only |
| Stale or misleading source content | Evidence system must track applicability, independence and expiry | Baseline exists, full pipeline missing |
| Provider storage/access changes | Integration owner must check current permitted use and retention before activation | Reference links retained, live review required |
| Cost and queue saturation | Operations must define monetary budget, quotas, alerting and fair scheduling | Default call cap only; no production workload established |
| Launch coverage and quality threshold | Product/data owner must choose measurable first-city scope and evaluate it | No agreed inventory count or numeric quality SLA |
| Hosting and operational ownership | Select runtime, monitoring, backups and response responsibility | Local Windows path tested; public deployment absent |
| Commercial demand | Product research must test actual usefulness and alternatives | Differentiation hypothesis unvalidated |

These are recorded dependencies and decisions to resolve at the appropriate stage, not a fresh questionnaire to the user. Routine implementation can continue with sensible documented assumptions; external account permissions, source availability and real-world quality must be evidenced rather than assumed.

### Change log

| Date | Change | Evidence / consequence |
|---|---|---|
| 2026-11-04 | Consolidated full discussion, user corrections, selected references, implementation state, data contracts and remaining procedure into this canonical file | Workspace documents/source and recorded verification; no new live verification claimed |
| 2026-11-04 | Explicitly separated local app completion from original autonomous-agent scope | Earlier implementation stopped at a smaller release; missing keys explain untested integrations, not missing coordinator/collector/analysis code |
| 2026-11-04 | Added stable checklist IDs and evidence levels | Future completed steps must update this file and relevant verification record |
| 2026-11-04 | Checked this document's local links, contents anchors and task IDs; linked it from README and the earlier plan | All local targets and section links resolve; no duplicate task IDs. Documentation-only verification; application tests were not rerun for this change |

### Future completion entry template

```text
Date/time:
Task ID(s):
Change completed:
Evidence level: documented / implemented / locally verified / live verified / customer validated
Files or evidence:
Validation and result:
Remaining limitation/dependency:
Checklist and verification report updated:
```

**Next release focus:** configure and smoke-test actual sources, evaluate the implemented investigation chain on labelled multilingual evidence, build/verify the real Coimbatore inventory, and complete staging/operational gates before invited testers. Advanced geolocation/reliability and owned models remain separate unfinished work; credentials alone do not establish their quality.


### Latest implementation change record

2026-11-04: added investigation implementation U01?U06, marked the precisely scoped C06/C10/C11 and guided B07 work, recorded the user's budget/rollout/ownership decisions, and retained live-data/evaluation gaps. See [build update](docs/BUILD_UPDATE_2026-11-04.md), [verification](docs/VERIFICATION.md) and [source leads](resources/coimbatore-launch-leads.json). No public release, paid provider call or live Instagram success is claimed.


2026-11-04 final regression record: 55 backend tests and 12 browser tests passed;
19 investigation tests passed again after the final identity/import fixes. The
legacy model-name default was removed: `GEMINI_MODEL` must be selected for the actual
account. Live keys/accounts, actual data quality, partner connections, production
restore/deployment and invited-user outcomes remain unchecked.

Final runtime check: local API healthy, schema 3, worker heartbeat current, zero
failed jobs. Demonstration mode remains active, Instagram collection disabled and
release stage internal. There are **zero verified live inventory records**; the nine
official-source leads await the documented investigation and publication gates.


2026-11-04 local research update: L01-L08 implemented and checked at the stated scope. Public Instagram caption collection succeeded; actual video/comments were unavailable from tested pages. Models/database/storage run locally. The previous demo-only final runtime entry is superseded.

Local backup follow-up: a consistent SQLite research snapshot was created at data/backups/batore-20261104T155248Z.db and opened read-only. PRAGMA quick_check returned ok; six source records and zero venues were present. This verifies snapshot readability, not a production disaster-recovery exercise.

Final connector regression: public caption metadata must not prevent a configured full provider from retrieving video/comments. Provider-sample markers prevent duplicate paid recollection. Covered by an isolated mocked-provider test; no paid connector was called.

Final runtime evidence (4 November 2026): API healthy in local mode; Qwen3-VL instruct installed; public search and autonomous discovery enabled; worker heartbeat 1 second old; zero failed jobs; six source records/four distinct Instagram links; two review cases and one unavailable query; zero published venues. Full Instagram provider is still disabled. Report saved locally as data/local-final-status.json.


### 5 November 2026 - direct public Instagram collector

Implemented Python Playwright Chromium collection, exact-shortcode association, visible-comment sampling, clear DASH audio retrieval/joining, bounded downloads and media receipts. Live investigation `e4f4578d-3999-4450-9c7b-c4c372d00a22` selected its own three sources and collected all three videos plus 32 comments. No login or paid API was used. Text-model failures exposed by this batch led to constrained timestamps/output, non-price filtering and commenter-candidate exclusion. Caption/comment repairs are recorded in an audit entry. Local frame sampling is spread across clip duration. Source speech text/segments share 24-hour retention; audio failure remains a verification gap unless the source explicitly has no audio. No sources were promoted to verified venue facts. See [DIRECT_INSTAGRAM.md](docs/DIRECT_INSTAGRAM.md) for setup, steps, exact evidence and remaining limits.

Final verification, 5 November: 86 backend tests, Ruff checks, production web build and four desktop/mobile local checks pass. All nine specialist analyses for the recorded three-reel batch are saved as observations; case remains review. API/worker restored to local mode, direct browser enabled, zero failed jobs and zero published venues. Final snapshot `data/backups/batore-20261105T120451Z.db` passed read-only SQLite quick_check. Current DB totals and precise limits are in VERIFICATION.md; no customer or model-accuracy validation is claimed.


### 5 November 2026 - itinerary inventory, all-source queue and approval gate

Latest user decisions: newest-first before selection; do not stop at two or three reels; save discovered locations after each investigation; collect Coimbatore maps, menus and vibes for a small food/entertainment itinerary planner; operator approves every location before suggestions. These supersede the old result cap and automatic-publication policy.

Implemented schema 5 identified spots and its admin UI; automatic candidate insertion during each streamed source and final verification; first-party menu/park/activity collection; private web-enrichment jobs; date probing/ranking and all-found-source retention; durable batch pacing; Meta discovery cursors; scene-cut frame selection, grouped local inference and follow-up frames. Removed automatic venue publication from accepted facts. Source text retention now follows the latest valid fetch, allowing unfinished old sources to be recollected instead of losing their new data immediately.

Actual expanded case `64ae5da9-a63c-40e3-9367-1c4acf2dffa2`: 15 sources retained/processed, 14 videos downloaded, 83 loaded comments, 15 caption + 12 comment + 13 video analyses saved. End state review. Inventory checkpoint: 66 unapproved candidate records, 120 first-party menu pairs, nine first-party targets, two coordinate leads. Candidate count includes uncertain names/branches and is not a count of verified venues. 99 backend checks, production build and six local desktop/mobile checks passed. Read INVENTORY_COLLECTION.md for remaining original Instagram requirements rather than assuming the entire vision is finished.
