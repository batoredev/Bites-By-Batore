> 7 November continuation: local SQL schema 6 is upgraded and structurally audited; see [DATABASE_SQL.md](DATABASE_SQL.md). Atomic quotas, priority reel watches, repeat-safe changed-caption reinvestigation and watched-text retention are now implemented/tested. A real watch attempt remains quota-deferred. The 49 drafts still require current facts, exact branch review and your approval; no stage is marked fully validated. [Model comparison](MODEL_OPTIONS_COMPARISON.md) confirms the current data lacks reviewed training targets. Latest verification supersedes the historical counts below.

# Stages 1, 2, 3 and 6: implementation and evidence

Updated 6 November 2026. This records the requested Instagram validation, Coimbatore inventory, location approval and ongoing maintenance work. It does not redefine the full product scope or treat the eight investigation processing steps as eight product release stages. All runtime data and inference remain local; owned-model training is outside this execution.

## Completion checklist

| Stage | Implemented and tested | Live evidence | Still needed for full completion |
|---|---|---|---|
| 1: validate Instagram extraction | Private multilingual evaluation, original-input snapshots, origin-separated holdout metrics, independent-correction comparisons; held-out source corrections now excluded from retrieval | 51 collected source records, 47 distinct source URLs, 26 video analyses, 196 classified comments, six indexed reference images | Independent representative English/Tamil labels and other-language samples; exact visual branch evaluation; measured correction improvement; prospective creator outcomes |
| 2: build Coimbatore inventory | 168 discovery topic/area combinations; first-party targets; conservative cross-reference merges; retained conflicts; per-page monitoring and missing-evidence counts | Expanded collection read 11 pages for 14 target entries; final active inventory 49 candidates, 10 merged and 24 held records retained | 38 active candidates lack menu/price evidence; 43 lack hours; 44 lack vibes; all 49 lack operator Maps identity review. No exhaustive city denominator exists |
| 3: approve each location | Private approval packets, explicit blockers, source/branch review, current essential claim requirements, alert resolution, final location approval, private export/erasure | Actual 49-location Markdown/JSON packet generated; zero ready for approval; zero published venues | Your independent branch/fact review and explicit approval of each location. No approval was entered on your behalf |
| 6: maintain current data | Durable recurring jobs; page observations and change alerts; weekly reel caption checks; retry checkpoints; expiry holds; revision invalidation; restore drill | 59 page-check records attached to active candidates, eight currently unavailable/overdue; one conflicting-hours alert; API/worker running | First successful new reel-watch execution (currently quota-deferred), sustained multi-day cadence/recovery measurements and real correction-propagation outcomes |

**The mechanisms above are implemented. These four stages are not fully validated or customer-ready.** Real labels, exact branch review, sufficient coverage, sustained operation and your approvals cannot be replaced by automated fixture tests.

## What runs automatically

- The worker checks its queue every five seconds while the machine and process are running. Its scheduler runs about once a minute. This is local operation, not an installed Windows startup service.
- Discovery rotates 12 topics across 14 areas. The existing four-hour spacing and three investigations/day remain; three sources is still a processing batch, never a total-result cutoff. All relevant discovered sources remain queued and known publication dates determine newest-first processing. Search access does not guarantee that every city venue or reel can be found.
- First-party inventory collection is scheduled daily. HTTPS page checks target 24 hours after successful observation, processing two due pages per job delivery with a saved checkpoint after each page.
- Failed page checks retain previous evidence, record the error and retry with increasing intervals up to 24 hours. Three consecutive failures create a review alert. A successful fetch is not independent factual verification.
- Completed web enrichment repeats after seven days. Older completed searches are adopted into this cycle without losing their original results. Pending results are completed before starting a new search cycle.
- Reel caption monitoring targets seven days and schedules at most six checks/day. It shares the normal provider and browser allowances. It compares available caption text, records a bounded observation and collected-comment count, and flags affected locations when the caption changes. It does not claim to detect edits to every video, all comment changes or deleted/private content. Changed evidence needs reinvestigation; it is not silently assigned to the old model analysis.
- A changed critical page observation or expired accepted hours, operating status or per-person price moves a published location back to review and increments its revision. Old plan revisions become stale. Open alerts block publication. Resolving an alert does not accept a claim or approve the location.

Page comparisons currently cover fields supported by the parser and literal configured evidence assertions: menus/offerings, map links and configured address/hours/vibes. They are not a universal webpage semantic change detector. Unavailable pages and unknown fields stay visible as gaps.

## Operating limits and current backlog

The ignored local configuration now allows **300 provider calls/day**, increased from 200 for the expanded local collection work. Browser pacing remains **30 Instagram visits/day**; the monthly operating target remains **INR 3,000**. No paid connector was enabled and no allowance counter was reset. At the final checkpoint both daily allowances were exhausted; the saved queue waits for the next allowance period. Counters use UTC calendar days, which reset at **05:30 IST**. Scheduling and retry delay can make actual resumption later than that time.

These are target cadences, not guaranteed freshness deadlines. Network failures, access barriers, the shared daily allowance, queued local inference and a sleeping/off workstation can delay work. The dashboard reports overdue pages. There is no defensible date for a permanently complete Coimbatore DB; new venues, menus, prices and closures require ongoing coverage measurement.

At 22:58 IST on 6 November: 175 jobs completed, two cancelled, 51 queued, no active job at that snapshot; API healthy in local mode and worker heartbeat current. The 51 source records include repeated origins across investigations. Counts are evidence inventory, not verified venue totals or extraction accuracy.

## Review and correction procedure

1. Run `scripts/start.ps1` if the app is stopped; open http://127.0.0.1:8000/admin.
2. In **Data readiness**, inspect monitoring gaps, conflicts, source dates and a location's approval packet. The examples were discovered by the agent; you do not need to supply seed reels.
3. In **Instagram accuracy review**, inspect the original source and label the exact analysed names, transcript, visible text or comment classes. Keep model language guesses separate from your reference. Use genuinely independent examples for held-out evaluation and correction comparisons.
4. In **Identified spots**, check the precise Maps place, branch address and coordinates. Generic Maps search links are leads only. Resolve ambiguous duplicates conservatively; similar names are not proof of a shared branch.
5. Prepare the pending venue. In **Venue desk**, review current hours, operating status and per-person price against appropriate evidence. Menu item prices or package tariffs are not automatically a per-person budget. Resolve source conflicts with a recorded evidence URL and reason.
6. Explicitly approve that location only after its blockers are cleared. Individual accepted facts, a completed investigation, a reviewed alert or an evaluation label do not publish it.
7. Submit scoped corrections through Investigations; compare future independent examples through the evaluation tooling. This is correction retrieval, not trained model weights. Revocation and privacy erasure remain supported.

The operator site and mall site disagree on Fun Unlimited at Prozone hours: [operator page](https://fununlimited.co.in/coimbatore/) states 11:00–22:00; [mall page](https://coimbatore.prozonemalls.com/entertainment) states 09:00–23:00. Both observations and an unresolved alert are retained. They were associated through an explicit first-party Prozone cross-reference; a separate similarly named Instagram branch candidate was not merged without evidence.

[Cafe Totaram](https://cafetotaram.com/) supplied address/hours leads; its online cookie products were not treated as a cafe menu. [CSR Landmark day activities](https://csrlandmarkresorts.com/dayout.html) supplied package tariff leads with unknown units/taxes and inconsistent slot descriptions, not confirmed per-person prices or hours. Kites Cafe remains a lead because its page was unavailable. No source fetch or source pairing approves a location.

## Local artifacts and repeatable export

Private files under ignored `data/`:

- `review-packs/review-20261106T172728Z.md` and `.json`: all 49 active candidate packets with source URLs, observations, conflicts and approval blockers.
- `stages-1236-inventory.json`: actual first-party collection receipt.
- `stages-1236-refresh.json`: manual continuation that stopped at quota; do not read it as a successful full refresh. Subsequent persisted page-check evidence is in the final status/report.
- `stages-1236-final-status.json`: final local runtime, evaluation and inventory snapshot.
- `stages-1236-restore-drill.json`: separate-file restore and row-count/integrity receipt.
- `backups/batore-20261106T172729Z.db`: consistent snapshot; `restore-drill-20261106T172729Z.db`: separately restored copy. Live DB was not replaced.

Refresh the private packet at any time from `backend/`:

```powershell
uv run python -m app.manage review-pack
```

This command only reads the selected local owner's report and writes a timestamped local export. It performs no network fetch, evaluation labelling or publication. These exported files and backups are separate local copies; deleting an account through the app does not remove previously exported files from disk.

## Verification boundary

- Full backend run: 157 tests passed before the final generic-description and expiry-audit privacy fixes. Final affected maintenance/identity/inventory suites: 59 tests passed, including the new regression. All use isolated test databases.
- Ruff required undefined/unused checks passed; strict TypeScript and production build passed.
- Desktop/mobile checks cover the maintenance packet and alert-review flow, evaluation, investigation, correction and Maps/held-record UI. Mutations and invented fixtures are intercepted and never written to the real inventory. Final results are recorded in `VERIFICATION.md`.
- A live inventory cleanup held two generic activity descriptions, retained their original evidence and made zero changes on immediate repeat. It did not infer any exact Maps identity.
- Snapshot and restored copy each passed SQLite `quick_check`; selected counts matched: 83 identified-spot originals, 51 source records, 228 jobs, zero venues. This demonstrates a local separate-file restore, not disaster recovery on another machine.
- No independent evaluation labels, creator outcomes, exact branch confirmations, user approvals or customer results were fabricated. The new reel-watch path is implemented and fixture-tested but has no successful live watch receipt yet.

Final runtime check: after recovering stale workspace-owned process trees, one fresh API and one worker were confirmed at 23:04 IST; the authenticated maintenance report succeeded. The launcher stop routine now recovers this workspace's omitted redirector processes while preserving executable-path and creation-time checks. See the newest verification record.
