# Project continuity

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
