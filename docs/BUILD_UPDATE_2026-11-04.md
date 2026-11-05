# Investigation implementation and activation record

This update supersedes the initial build's narrower implementation descriptions.
The canonical requirements/checklist remain in [PROJECT_MASTER.md](../PROJECT_MASTER.md).

## Latest user decisions

- Initial total operating target: **INR 3,000/month**, including hosting/providers.
- Prepare both official Meta and a replaceable third-party Instagram collection path.
- Use placeholders until the user configures access; no paid activation performed.
- Work internally on Coimbatore data first. Verify the inventory before inviting
  test users. Public release follows successful invited testing.
- Long term: develop models owned by the product. This is a future development
  requirement, not a claim that current hosted model weights or source data are ours.

## Implemented in this update

### Investigation workflow

`investigations`, `research_tasks`, `research_sources` and `source_assessments`
extend schema version 3. The coordinator persists discovery, collection, caption,
comment, video, location, reliability and verification stages. Each stage is a
durable job; successful stages survive restart. The scheduler repairs a missing
successor job after a crash. Provider runs use stored IDs and bounded polling.
An uncertain provider-start outcome is not automatically started again.

Owner-private endpoints support creating/listing/reading/cancelling investigations
and resuming a failed step. Data export and erasure include investigations and
dependent records. Deleting a submission removes its related investigation data.
The Sources screen shows progress, evidence, source limitations and unresolved
checks. Demo mode does not claim external collection or model analysis.

Recovered queue deliveries are bound to their original stage, and provider activity
renews the active job lease. Cancellation is checked before further provider calls.
Admins can conclude insufficient evidence or use independently verified venues with
explicit retained limitations; a conclusion never accepts unverified claims.

Live social submissions now use this workflow. Scheduled discovery and inventory
gaps can launch it when `AUTONOMOUS_DISCOVERY=true`. The scheduled owner must be
a configured admin who has signed in. This switch is off until source access and
spending limits are configured.

### Collection and analysis

- Meta connector: bounded hashtag search/recent media with explicit account,
  token and Graph version; accessible comments are sampled. It does not bypass
  missing public-content permissions or resolve arbitrary private media.
- Third-party connector: an operator-configured Apify saved task, asynchronous
  run ID/poll/dataset retrieval, per-run charge setting, normalized reel records.
  The supplied contract targets Instagram Scraper-style inputs/outputs. The actual
  saved task and paid plan must be smoke tested; a placeholder is not proof of access.
- Bounded video downloads from approved Instagram CDN hosts; no arbitrary URL
  fetching, credentials in URLs, private-network media or redirects.
- YouTube metadata/comment sampling and supported video inputs.
- Web discovery leads and bounded readable HTML collection from explicitly
  configured official-source hosts. Redirects, PDFs and script-only pages require
  separate/manual review. Search snippets are not relabelled as page content.
- Typed caption/comment/video specialist outputs with observation basis and
  timestamps. Invalid modality attribution fails validation.
- Bundled ffmpeg frame extraction, uniform sampling or targeted timestamps,
  bounded frame count/size/timeouts, and a separate frame-inspection model pass.
  Raw media is removed after final processing or after one day. Retrieved text
  is also expired after one day; production source retention still needs review.

These are logical specialist roles, not a claim of independently trained models.
Actual multilingual speech, OCR, scene interpretation and model quality have not
been verified against live media/accounts. Sampling is not exhaustive frame-by-frame
inspection and visual location matching is not a Google Lens integration.

### Branch, source and publication review

The resolver retains alternate inventory/place-ID hypotheses. Matching a name alone
cannot confirm a branch. An exact stored name/full address plus an independently
confirmed inventory branch is stronger evidence; ambiguous cases remain for review.
Unresolved candidates can trigger additional web lookup using extracted clues.

Admin can link a source to an existing independently confirmed branch or create a
pending venue with independently supplied coordinates/address. Current essential
claims are still required before publication. Dated, branch-resolved social fact
extractions may create review claims; they never auto-accept themselves. Contradictory
reports remain visible in the verification result.

Repeated comment text and normalized caption copies are detected as limited
independence signals, not proof of bots. Creator identities have human-reviewed
supported/refuted/outdated/unresolved outcomes. Repeated evidence origins do not
inflate the historical sample. Outdated facts and personal taste do not count as
false claims. Historical support rate is descriptive, not a calibrated probability.

### Discovery, planning and feedback

A guided conversation narrows purpose, energy and desired novelty using explicit
answers and saved tastes. It does not change budget, starting point, party size or
available time. This is bounded guided dialogue, not an unrestricted chat model.

Planning supports one to four stops, using a bounded candidate pool; maximum is
selectable. Group/person packages include duration and expiry. Dated sessions include
runtime, price, optional available-place count and source/expiry. Signed merchant
updates can carry `packages` and `dated_sessions`. No commercial ticketing partner
is connected, and a result is not a booking or seat reservation. This bounded search
does not prove global optimality across every package/session combination.

Per-companion interests influence balance. Confirmed atmosphere ratings update
occasion-specific interests separately from food/activity preference weights.
Free-text feedback is retained without pretending its meaning was understood.
No trained recommendation model or cross-account group profile merger is claimed.

### Data readiness and costs

Admin Data readiness shows category coverage, missing essential facts, expired
evidence, delayed/failed jobs, worker heartbeat and provider spending reservations.
`MONTHLY_BUDGET_INR=3000` limits **configured estimated provider reservations**;
it cannot guarantee actual total bills. Hosting costs and provider-side ceilings
must be budgeted separately. Defaults reserve INR 10/model request, 2/Maps or search,
1/YouTube or other request, 200/third-party run. These are deliberately configurable
allowances, not a researched pricing table. Failed requests can retain a reservation
because whether a remote operation was billed is not reliably known.

Live default `RELEASE_STAGE=internal` permits admin access only. Test mode requires
a recorded data review and server-side `TEST_USER_IDS`. Public mode also requires
the data-review record. Admin signoff checks technical blockers and requires
attestations for coverage, actual providers, staging restore and labelled evaluation.
This gate is an operational control, not an automatic certification of every venue.

## Real-data starting pack

[coimbatore-launch-leads.json](../resources/coimbatore-launch-leads.json) contains
nine official-source research leads checked on 4 November 2026. The admin can
import them idempotently into investigations. Importing does not publish any venue.
The source URLs, collection/readability limits and missing facts are retained.

Examples include [The French Door](https://www.thefrenchdoorindia.com/),
[Annapoorna's restaurant directory](https://www.sreeannapoorna.com/pages/restaurants),
[Prozone's entertainment directory](https://coimbatore.prozonemalls.com/entertainment)
and [CoASTT Kartmania](https://coastt.in/kartmania/). A directory or an old page is
not proof of today's operational status. No complete Coimbatore inventory is claimed.

## Activation sequence — no more product questions needed now

1. Review the new placeholders in `.env.example`; existing `.env` is not overwritten.
2. Keep demo and live databases separate. Back up and migrate to schema 3 before live startup.
3. Configure Supabase auth/DB, admin UUIDs, Google services, the selected analysis
   model and any enabled discovery providers. Account permissions are separate from keys.
4. Select `INSTAGRAM_PROVIDER=meta` or `apify`; leave `disabled` until access is ready.
   For Meta set the version enabled in the actual app. For Apify create/test a saved
   Instagram task, then set its ID/token and appropriate run/cost limits.
5. Check actual provider quotas/prices. Adjust estimated reservations and provider-side
   billing controls to leave room within INR 3,000 for hosting and other costs.
6. Run the live smoke/evaluation matrix in OPERATIONS.md. Test Tamil, another language,
   ambiguous signage, wrong branches, missing comments and misleading captions.
7. Import research leads and expand Coimbatore coverage. Confirm branches, essential
   facts, dietary/access requirements and operational packages; resolve review items.
8. Enable supervised background work, source collection and automatic investigation
   only for the intended scope. Inspect failures, spending, freshness and quality.
9. Complete staging restore and actual labelled evaluations. Record the data review;
   set `RELEASE_STAGE=test` with invited UUIDs only after the data is ready.
10. Run real outings, measure failures/usefulness, fix findings, then separately decide
    on `RELEASE_STAGE=public` and production hosting.

## Owned-model path

Keep prompts, schemas, evaluation cases and deterministic planning owned by this
project. Build a consented/licensed dataset with provenance and deletion rules;
do not assume ownership of Instagram content or third-party model weights. Establish
human-labelled speech/OCR/entity/claim/ranking benchmarks, train or adapt eligible
models, compare quality/latency/compute costs against the current provider, and
replace adapters only after evaluation. Training from scratch is not assumed feasible
under the initial INR 3,000 monthly target. External venue/source information still
requires collection even when inference models are owned.

The old `gemini-2.5-flash` default was removed from the template/configuration.
`GEMINI_MODEL` is intentionally blank until an available multimodal model is chosen
and tested in the actual account. Model lifecycle changes are a separate dependency:
see the [provider lifecycle documentation](https://ai.google.dev/gemini-api/docs/deprecations).

## Still external or unfinished

- Actual keys, Meta approvals/data-provider task access and live contract testing.
- Verified launch inventory; nine research leads are not nine verified recommendations.
- Real multilingual/location/reliability evaluations and operational coverage targets.
- Live partner cinema/activity feeds and direct merchant onboarding.
- Production PostgreSQL/RLS/restore, hosting, monitoring alert delivery and workload validation.
- Docker execution: daemon pipe is unavailable; Docker Desktop was not found at the
  standard installation path. The tested runtime remains local Windows.
- Advanced visual-geolocation retrieval, calibrated creator reliability, unrestricted
  dialogue, fully learned ranking and owned models remain beyond the evaluated baseline.

## Reference contracts checked

- [Meta API](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api).
  A direct Meta hashtag documentation request was rate-limited during this session;
  the actual app version/permissions still need validation.
- [Apify API](https://docs.apify.com/api/v2),
  [saved task runs](https://docs.apify.com/api/v2/actor-task-runs-post),
  [Instagram Scraper](https://apify.com/apify/instagram-scraper/input-schema).
- [Gemini video interface](https://ai.google.dev/gemini-api/docs/video-understanding).
  The configured model has not been live tested; documented capabilities do not prove
  the quality of this application's results.
