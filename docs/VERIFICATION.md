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
