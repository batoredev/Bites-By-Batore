# Project continuity

Latest continuation: read docs/SQLITE_RELIABILITY.md. Duplicate-cleanup indexing/
cache repair, transient SQLite busy handling, API read-only retries and safer
Windows launcher are implemented. 292 backend tests/12 browser checks passed;
separate full-size copy cleanup ~3.6–3.8s, live cleanup plus 24 concurrent reads
returned 200. Four interrupted/stale jobs recovered with worker stopped. Initial
unlimited collection is running; 09:43 UTC snapshot 692 active/111 held/12 merged,
168 research sources, zero real venues/accepted claims. Short smoke has no new
locks; sustained/growing-inventory reliability and real accuracy remain unverified.

Latest user direction (8 November, after initial import): remove app daily request
caps until initial collection finishes and continue collection improvements. Read
docs/BULK_COLLECTION.md. LOCAL_BULK_COLLECTION=true is enabled locally: effective
request/browser/daily-case limits are zero (unlimited counts), counters retained.
Paid monetary guards, source pacing/cooldowns, caches, ownership and approval gates
remain. Zero monetary budget never means unlimited spending. This supersedes the
older daily/two-call app-count allowance statements below during initial mode.
283 backend tests and eight desktop/mobile checks passed. 541 queued waits resumed;
live aggregate count passed 300, sources grew 83 to 86 at the recorded snapshot.
Later 07:17 UTC: counter 410, sources 88, 574 active drafts / 98 held / 12 merged;
zero real venues/accepted claims. Final focused 12-test suite also covers HTTP-429
adapter Retry-After persistence. Counts are snapshots; use current DB/receipts.
No city completeness/accuracy or newly trained model/approval claim is justified.

Latest collection checkpoint (8 November): read docs/COIMBATORE_COLLECTION.md.
Local Overpass baseline is live fetched/imported, using Coimbatore administrative
areas clipped to the existing 40km radius; not a municipal census. Require district
boundary metadata, preserve ODbL attribution, cache seven days and keep the two-call
weekly allowance. Broad-radius Kerala leads were held, not deleted. Current private
SQL inventory: 568 active unapproved drafts, 98 held and 12 merged originals, 83
research sources, zero real venues/accepted claims. Six retained-caption jobs
completed locally. These counts supersede earlier checkpoints; facts/accuracy and
operator approvals remain unfinished. Public OSM listing pages are not daily HTML
maintenance targets. Do not reset shared external pacing or claim all city data is
collected; data/city-collection/PROGRESS.md and runtime/coverage/CSV snapshots retain
gaps. Existing autonomous worker runs separately while the computer stays awake.

Latest user direction (8 November): prioritize new locations. Stop remaining reel
processing when its previously recorded location(s) are matched, retain the source
and an explicit skipped-coverage receipt, and advance to the next reel. Preserve
ambiguous/new branches and unaccounted multi-venue candidates. Backfill existing
extractions into the canonical local identified_spots SQL inventory and persist
new discoveries immediately; operator location review happens later. This does
not approve facts/locations or publish suggestions. Maintenance/full-review paths
must bypass discovery skipping. GPU use is authorized; preserve model precision
and evidence requirements while verifying local memory and actual GPU placement.

Read `PROJECT_MASTER.md` before changing product scope. It is the canonical record
of user decisions, implementation status, evidence and unfinished work.

Update the master checklist and relevant verification document after completing a
step. Distinguish implemented, locally tested, live verified and customer validated.
Never mark a connector live merely because code or an environment variable exists.

Confirmed latest constraints: English UI; multilingual source analysis; Coimbatore
only initially; food and entertainment; no events/scenic drives/return planning.
Initial total operating target is INR 3,000/month. Both official Meta and replaceable
third-party source paths are authorized with placeholders. Work internally on data
first, then invited tests after verification, then public release after successful
evaluation. Owned models are a long-term requirement, not a claim that a trained
model already exists.

Keep secrets in ignored environment configuration. Use isolated data for tests.
Do not publish fictional venues or automatically accept model-extracted facts.
Preserve private investigation ownership and include new records in export/erasure.

Latest user requirement: the agent discovers examples itself. Keep models, testing,
DB and storage local for now. Read docs/LOCAL_RESEARCH.md. APP_MODE=local uses an
isolated SQLite DB and persistent loopback-only operator. Restore local mode after
tests. Reviewer correction retrieval is implemented; do not call it trained weights.

Direct public Instagram browser collection is implemented and live exercised on three
agent-selected reels (5 November 2026). Read docs/DIRECT_INSTAGRAM.md. Do not say
Meta/Apify credentials are mandatory for this public path. Loaded comments are a
bounded sample; model observations, branch locations and prices remain unverified.

Latest user decisions (5 November): itinerary planner first; newest-known-publication
ordering before collection; retain all relevant discovered reels, never top-3 prune.
RESEARCH_MAX_SOURCES is now a processing batch size. Stream each source through
analysis and identified-spots insertion; quota waits preserve pending sources.
Schema 5 adds owner-scoped identified_spots. Read docs/INVENTORY_COLLECTION.md.
Every location requires explicit operator approval before suggestions; accepting
facts must not auto-publish venues. Drafts/first-party menu pairs are unapproved.

Latest quality direction (6 November): check duplicates/relevance before spot inserts.
Read docs/SPOT_IDENTITY_QUALITY.md. Held and merged records retain their evidence;
do not silently delete or re-create them. Similar names alone do not confirm a
branch. Names remain Maps-unconfirmed until explicit operator identity review;
optional Places lookup is not live verified. Maps identity review is required for
non-demo venue publication; it does not replace current fact/location approval.

Latest continuation (6 November): read docs/INSTAGRAM_COMPLETION.md and the newest
VERIFICATION.md section. Local visual-reference matching, branch conflict ranking,
resumable structured comments, creator uncertainty/calibration metrics and private
accuracy-review/comparison tooling are implemented. Only one real reference image
and a 12-comment local inference smoke are verified; real accuracy, branch matching,
calibration and correction improvement remain unmeasured. Never fabricate gold
labels or operator approvals. Public comment expansion was unavailable on the
real test page; offline control-expansion tests are not live coverage evidence.
