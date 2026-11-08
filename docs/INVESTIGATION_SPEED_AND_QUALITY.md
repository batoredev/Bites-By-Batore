# Investigation speed and quality plan — 7 November 2026

Implementation follow-through: [PERFORMANCE_IMPLEMENTATION.md](PERFORMANCE_IMPLEMENTATION.md) records delivered mechanisms, local tests, model/browser receipts, enabled local switches and remaining independent validation. The inspection below is the historical basis, not a claim that all measurements are complete. Local-only models/storage, Coimbatore food/entertainment, newest-known-publication dispatch, all-relevant-source retention and explicit location approval remain required.

## What is slowing the current system

Read-only receipt: `data/investigation-speed-audit.json`, 7 November 2026 at 19:43 IST.

| Inspected fact | Implication |
|---|---|
| Local Qwen3-VL 2B instruct; Whisper base | No hosted inference is active |
| Ryzen 5600H, six physical cores/twelve logical processors; RTX 3050 Laptop, 4,096 MiB VRAM | Plan conservative CPU work and one GPU inference lane first; do not assume many parallel models fit |
| Shared call counter 300/300; Instagram browser counter 30/30; 55 queued jobs, no running job at the snapshot | Current queued delays include exhausted access allowances; faster inference alone cannot release those deferred calls |
| `stream_source` runs caption, comments and video sequentially, and collection waits for each source's analysis | Network collection and inference are coupled; a slow source delays subsequent ones |
| Browser launched through a subprocess per reel, with a 4.5-second page settle wait | Browser startup and fixed waits are candidates for measurement and optimization, not yet proven dominant |
| Up to eight sampled frames, processed in groups of four; comments in groups of five | Up to two vision calls and six comment calls for a fully collected 30-comment sample, plus one caption call |
| Chat request uses `keep_alive=2m`; 4,096 text / 8,192 image context; output cap 1,536 tokens; 240-second request timeout | Cold loads, prompt processing, generation and retries need separate measurements; configured timeout is not observed runtime |
| Whisper already cached within its process, CPU int8/four threads, VAD enabled, beam size one | These existing optimizations must not be claimed as new work; English-only replacement would violate multilingual intent |
| Job records have creation/due/completion but no execution start or stage duration | Creation-to-completion includes queue/quota time. A credible per-reel inference median/p95 cannot be derived from these fields |
| Zero saved human-labelled tasks or reviewer corrections at inspection | There is no independent accuracy baseline with which to certify "no accuracy loss" |

For an illustrative reel with 30 collected comments and eight frames, current batching permits approximately `1 + ceil(30/5) + ceil(8/4) = 9` local model calls before follow-up work. This is a code-derived example, **not** a measured count or duration for every source. Local Ollama calls do not use the external `quota()` path; the shared external call allowance must not be described as 300 LLM calls/day.

Browser watches share browser allowance with new collection. If six watches each consume one of thirty slots, twenty-four slots remain before new-collection retries or other browser work. This is capacity arithmetic, not a guaranteed number of new reels/day; cached and alternative access paths differ. Do not bypass access barriers, reset counters or automatically raise caps to manufacture throughput.

## Accuracy issues to fix before aggressive speed changes

Code inspection found three risks, not measured error rates:

1. Frame selection sorts the combined frame candidates and truncates to the budget. When there are more candidates than the limit, the ending frame can be dropped despite a comment saying both ends are preserved. Add explicit beginning/end retention, temporal coverage and scene selection tests, especially a final-frame shop name/address.
2. Local input is serialized then sliced at 18,000 characters. Chunking by evidence boundary should replace blind truncation so late addresses, exceptions, negation and offer conditions do not disappear. Preserve original-language text, source links and offsets.
3. Prompts request at most three venue candidates and multi-pass merge keeps at most five. Multi-venue reels need evidence segments and aggregation that retains all supported entities, rather than a hidden place-count cutoff. Existing "all discovered reels retained" is not the same as all places inside a reel being extracted.

These fixes can increase processing for difficult sources. Speed must be judged together with evidence coverage, recall and wrong-branch/unsupported-fact rates. A faster result obtained by discarding hard cases is not an improvement.

## Proposed architecture

```text
Newest-first discovery and durable source queue
        |
        +--> Paced Instagram collection (initially one lane)
        +--> Bounded first-party HTTP collection (initial experiment: two lanes)
                    |
              Immutable source version / content fingerprint
                    |
           +--------+---------------------+
           |                              |
     CPU audio/OCR/frame preparation      Caption/comment preparation
     (bounded, measured contention)       and changed-input detection
           +------------------------------+
                    |
           One local GPU inference lane
           with independent specialist outputs
                    |
        Cross-source branch/conflict/provenance checks
                    |
         Transactional deduplication and identified-spots update
                    |
             Your explicit location approval
                    |
             Eligible itinerary inventory
```

Collect the next source while the current source uses the GPU. Start CPU overlap cautiously (one ASR lane, one other preparation lane as an experiment); benchmark CPU contention before increasing it. Do not run four independent vision models at once on the present 4 GB GPU simply because there are four agent roles. The roles can share one loaded model while keeping tasks, evidence attribution and outputs separate.

Each worker needs its own database session. Keep transactional source/owner identity, leases, cancellation, idempotent stage results and duplicate protection. Prefer one controlled insertion lane initially. Distinguish "first provisional draft available" from "investigation coverage complete"; UI progress must never call a partial source pass completed. Keep all discovered relevant sources queued, dispatch newest known dates first, and preserve each source's evidence when results complete out of order.

## Changes in execution order

| ID | Change | Accuracy protection | Acceptance evidence |
|---|---|---|---|
| P01 | Add stage timing and queue/quota reason reporting | Record failures, retries, unavailable sources and omissions, not just successful fast calls | Load/prompt/generation/download/ASR/frame/DB times; median/p95; cold/warm runs |
| P02 | Fix sampling/truncation/multi-venue coverage | Explicit ending-frame tests, original offsets, full entity retention | Synthetic edge regressions plus independently checked real examples |
| P03 | Versioned analysis reuse across repeat investigations | Key by owner, source content, modality, model, prompt/schema and correction versions; preserve independent provenance | Cache hits match valid outputs; misses for changes/revocation/holdout/privacy boundaries |
| P04 | Separate collection, CPU preparation and GPU queues | Durable bounded jobs; no shared SQL session; cancellation and lease checks retained | Failure/restart/concurrent-delivery tests and real memory/latency measurements |
| P05 | Reduce model startup/overhead | Keep model warm during active work; bound idle residency; preserve needed context and output completeness | Ollama load/token timings and `ollama ps` during actual inference |
| P06 | Reuse a clean browser process where appropriate; replace fixed sleeps with bounded readiness checks | Fresh isolated contexts, exact-post matching, timeout/cooldown behavior and source coverage retained | Same accessible captions/media/comment sample; no cross-source leakage; restart recovery |
| P07 | Refresh only changed components | Compare caption, comments, media and source assertions separately; fetch fresh evidence as required | Changed comments do not repeat unchanged audio; changed clip does repeat affected visual/ASR work |
| P08 | Escalate difficult segments rather than repeat everything | Uniform/scene coverage baseline retained; unreadable/conflicting clues trigger higher-resolution/reinspection or human review | No measurable branch/name/OCR/comment regression on independent holdout |
| P09 | Serve outing requests from approved local inventory | Enforce expiry/approval/revision checks; missing/stale data produces an honest partial/unavailable result | Fast plans with fresh eligible facts; no silent use of unapproved drafts |
| P10 | Pilot the full system and roll back regressions | Versioned code/model/prompt/config, retained baseline, independent labels | Measured speed/quality/cost report, then sustained operation |

P03 is beyond the existing within-source completed-stage/comment-batch checkpoints. Stable media/ASR/frame results may be reused only within existing retention permissions; this plan does not extend raw-video or transcript retention. Expired cache entries must be deleted or invalidated in line with owner erasure and source retention. Reusing interpretation does not renew a menu's freshness, establish a new independent source or grant approval.

P05 should first test residency and actual GPU placement. Longer context, more concurrent requests and heavier quantization can change memory and quality. Do not shrink away evidence, cut required visual coverage, silently truncate outputs, use an English-only speech model or switch to a weaker model to advertise speed. A larger local GPU or a paid-model benchmark can be evaluated later if measurements justify it; no purchase or cloud inference is authorized by this document.

P08 does not allow an easy-looking caption to skip all visual analysis or ignore negative comments. Route additional attention using observed uncertainty, unreadable text, contradictory areas/addresses, missing modalities and multiple venues. Model confidence or agreement between models is not independent correctness. Unknown stays unknown; unusual facts and location publication retain human gates.

## How to prove speed without hiding accuracy loss

1. Agent selects representative real examples: English, Tamil, code-switching, other available source languages, multiple branches, multi-venue reels, late signage, sponsorship, wrong-city content, copied posts, missing audio and contradictory comments. The user need not supply seed examples.
2. Reviewers independently label the actual source evidence. Do not use an LLM's output as its own gold answer. Keep separate development and holdout sets grouped by creator/venue/repost origin; exclude held-out corrections from retrieval.
3. Start with a pilot of at least thirty diverse reels and one hundred independently checked field/item judgements, then expand for underrepresented languages and wide uncertainty. These are proposed starting sizes, not sufficient evidence for every task or a release guarantee.
4. Run the existing baseline and each change on the same permitted inputs. Measure source coverage, exact names, branch precision/recall, unsupported facts, OCR/transcription errors, comment classes, abstentions, failures and freshness. Low errors with many omitted venues does not pass.
5. Measure time separately for queue wait, quota delay, source access, load, prompt evaluation, generation, ASR, frame processing, first draft and complete case; include cold/warm and repeated-content cases. Report successful and failed runs with denominators and hardware/config.
6. Define acceptable accuracy differences before comparing, with strict review of any wrong-branch/unsupported-fact regression. Examine paired results and uncertainty; "same score on thirty clips" does not prove globally identical accuracy.
7. Enable independently tested changes in shadow operation and retain rollback. Measure backlog age, source freshness, memory, throughput and daily allowances over several days. Do not report a reset quota or smaller evidence sample as a speed improvement.

Timing model: `completed investigation time = queue wait + quota/access waits + execution time`. A pipeline improves overlapping execution and resource use; it does not eliminate access waits or approval time. Customer plan response time should be measured separately because it should use the reviewed DB instead of waiting for a new Instagram investigation.

## Other product improvements needed

- Verify a useful Coimbatore inventory, including exact branches, menu/unit prices, current hours/status, vibes, amenities and activity/session details, then obtain explicit user approvals.
- Improve a canonical dish/cuisine vocabulary and aliases; add properly sourced venue photos and rating/review-count capabilities where evidence/access exists.
- Validate actual taste learning, richer group/occasion reasoning, conversational discovery and full outing time/cost feasibility; do not claim customer benefit solely from screens or tests.
- Compare matched requests with FavHiker using independently checked outcomes, and run invited-user tests after adequate reviewed local coverage.
- Keep public deployment, broader geography and owned-model training as later phases under the established decisions.

## Primary technical references

[Ollama chat API](https://docs.ollama.com/api/chat) exposes timing/token fields and a per-request model residency control. Capture them rather than estimating inference speed from job creation timestamps.

[Ollama FAQ](https://docs.ollama.com/faq) documents GPU/CPU placement inspection, residency and memory implications of parallel requests. The suggested single GPU lane is our conservative inference from the inspected 4 GB machine, not a universal performance optimum. Cache quantization can affect quality and needs evaluation.

[Structured outputs](https://docs.ollama.com/capabilities/structured-outputs) supports schema-constrained generation; this already exists in our local path. Valid JSON does not establish factual truth.

[faster-whisper documentation](https://github.com/SYSTRAN/faster-whisper) documents int8, VAD and batching. The project already uses CPU int8/VAD. Published benchmarks use other hardware/settings; their speedups are not measurements of this laptop.

## Current checklist

- [x] Read actual pipeline/config/hardware and record quota/data/timing limitations.
- [x] Check primary runtime documentation; preserve local-only decisions.
- [x] Document P01–P10 and product priorities.
- [x] Implement P01–P09 mechanisms and P10 measurement/comparison/rollback tooling with isolated regressions and receipts; extra CPU concurrency is held pending profiling.
- [ ] Obtain representative independent labels and establish the baseline.
- [ ] Demonstrate faster execution with preserved evidence coverage and acceptable quality, then prove sustained operation.

No promised seconds-per-reel, multiplier, complete-city date or zero-accuracy-loss guarantee is justified yet.
