# Investigation improvements: implementation and verification

Latest 8 November implementation: [KNOWN_LOCATION_EARLY_EXIT.md](KNOWN_LOCATION_EARLY_EXIT.md)
supersedes the earlier always-complete-discovery sampling policy for known places
and records full GPU placement tests, actual local backfill and duplicate holds.

Updated 7 November 2026. This is the implementation record for P01–P10 in
[INVESTIGATION_SPEED_AND_QUALITY.md](INVESTIGATION_SPEED_AND_QUALITY.md).
`PROJECT_MASTER.md` remains the canonical project record.

## 8 November observational speed follow-up

Read-only worker receipt: `data/performance/speed-audit-20261108.json`. The newly
recorded workload is more useful than the earlier caption smoke, but remains a
small unlabelled sample. No code, model, allowance or runtime setting changed.

- Eight completed source-analysis jobs: median **144.15 seconds**, observed range
  **34.29–595.16 seconds**. This is execution after collection; queue, quota/access
  and approval waits are excluded. Jobs can have missing modalities, and their
  completion does not establish factual correctness.
- Forty-six measured model responses/calls: 1,162.32 seconds local-model phase;
  generation 926.78 seconds (**79.7%**), load 101.42 seconds, prompt evaluation
  123.76 seconds. Generation is the main observed model-time cost.
- Six measured speech passes: 200.82 seconds total, **33.47 seconds/pass**; frame
  preparation 45.16 seconds total. Nested times must not be summed as wall time.
- Current UTC-day shared external counter 300/300; browser 14/30. Browser allowance
  remains, while the shared call budget can still defer required collection steps.

Next speed work, still proposals: preserve all facts while reducing repeated output;
avoid repeatedly interpreting the same transcript across visual passes while keeping
timestamp/branch attribution; overlap one bounded CPU preparation lane with GPU
inference; verify active-load GPU placement/backend acceleration before purchases;
pace shared provider calls around useful unfinished work; expose completed draft
components promptly while keeping incomplete-source status and publication holds.
Existing cache, ten-minute residency and browser/collection lanes are already on.

Changes to prompts, batching, precision, model, evidence sampling or ASR settings
need fixed-input regressions and representative independent labels. Neither a
smaller evidence sample nor extra unprofiled GPU concurrency is a demonstrated
speed improvement. Streaming partial progress changes time-to-first-result; it
does not by itself reduce full validated completion time.

## Scope retained

Local models, SQLite and storage; English interface and multilingual evidence;
Coimbatore food and entertainment; INR 3,000/month initial operating target.
All relevant discovered reels remain durable, ordered by newest known publication
before collection. Three sources is a processing batch, not a result cutoff.
Every location still needs the operator's explicit identity/fact/location review.
Interpretation reuse never accepts a fact, renews a menu's freshness, counts as
independent corroboration or publishes a venue. No cloud inference, purchase,
model-weight training or public release is part of this work.

## Delivered mechanisms

| ID | Implementation | Verification boundary |
|---|---|---|
| P01 | Per-job delivery/start/eligible queue wait/execution/retry reason; nested phase timings; Ollama load/prompt/generation/token counts; private report and UI | Isolated failure/retry/privacy tests and real local model receipts. Historical jobs have no invented timings. Delivery percentiles are not reel-completion percentiles. |
| P02 | Beginning/end plus distributed frame sampling; overlapping Unicode evidence segments with original offsets; context/output overflow splitting; all supported venue candidates retained through matching | Ending-frame/time-distribution, nested text-offset, multi-venue/branch and full-frame retry regressions. No independently measured real extraction accuracy yet. |
| P03 | Owner/source/input/role/pipeline/model-digest/correction-context keyed interpretation reuse; 24-hour interpretation validity; invalid/future timestamps, evaluation origins and deleted origins rejected | Owner, changed model/input/context, holdout, expiry and erasure regressions. No live cache-hit throughput claim. |
| P04 | Durable source-analysis jobs; collection/control and analysis lanes with separate SQL sessions; one GPU semaphore; bounded media backlog; missing-enqueue recovery; cancellation/erasure handling | Atomic filtered claiming and complete isolated case lifecycle tested. Additional CPU parallelism is deferred until real ASR contention is profiled. |
| P05 | Bounded configurable model residency and reusable loopback HTTP connections; unchanged model/context/output/temperature/frame budgets | Real installed Qwen caption cold/warm and final guarded-client measurements. These do not measure whole-reel throughput or prove universal speedup. |
| P06 | Reusable hidden browser helper; fresh context per source; idle/EOF/error restart; bounded readiness only when configured comment sample and caption/video reference already exist | Controlled real Chromium pages and process-controller failure tests. New reuse path has not been live verified against public Instagram. |
| P07 | Exact component signatures; unchanged analysis skipped; changed comment batches reclassified with stable indexes; changed corrections/model invalidate batches | Isolated component and correction-context tests. Stable raw collection is still refreshed normally; this is not permission to reuse expired input. |
| P08 | Explicitly uncertain timestamped clues join requested follow-up frames; baseline sampling retained; follow-up observations/candidates preserved | Full-frame overflow regression and existing reinspection coverage. Unreadable/no-access clues remain unknown and require review. Real branch accuracy still unmeasured. |
| P09 | Approved-inventory planner gates retained; Server-Timing on plan requests; no Instagram/model call added to request path | Existing expiry/approval/revision/route tests plus response timing regression. Current empty real published inventory cannot establish real itinerary latency or quality. |
| P10 | Reproducible local smoke CLI; private measurements; independently labelled, uncached caption/comment comparison jobs; explicit baseline timing absence; reversible flags | Tooling tested locally. Representative paired video/branch labels, matched baseline wall times, sustained operation and customer validation remain open. |

The pipeline version is `2026-11-07-coverage-v3`. No SQL migration was needed:
timings use existing `jobs.result`; component cache/checkpoints and evaluation
receipts use existing owner-scoped source analysis JSON. Schema remains 7.

## Evidence coverage and context handling

The previous frame selection could lose a closing sign when early scene changes
filled the sample budget. Endpoints now stay in the budget and remaining samples
spread across the inspected timeline. The configured eight-frame budget is retained;
this does not claim every frame in a reel was inspected. Existing clip-duration,
download and collected-comment bounds still apply and must be visible as limitations.

Long captions/transcripts are segmented with overlap and absolute offsets, including
recursive splits. No serialized JSON tail is silently cut. Every segment is either
processed or reported as incomplete. Output-length failures split text or frame
groups; comment batches can split down to individual collected comments, retaining
their original indices. Oversized unsplittable metadata remains unavailable rather
than being silently discarded. Different menu/price and branch clues survive merge.

The installed Qwen model's local GGUF vocabulary/merges supply a token budget check.
It reserves space for output, chat formatting and sampled images before inference.
The supported pre-tokenizer is Qwen2/GPT-2 BPE; a replacement with another tokenizer
needs its own verified adapter. A missing/unverifiable tokenizer produces an explicit
gap. Tokenization uses loopback Ollama metadata, downloads no models, and caches only
the vocabulary by actual model digest. This protects input coverage; it does not
prove the model understood or correctly extracted every clue.

## Queue and resource behaviour

With the pipeline flag enabled in local mode, one control thread discovers/collects
while one analysis thread prepares frames/audio and performs specialist inference.
One model semaphore prevents simultaneous GPU requests within that worker process.
Run one worker instance; a second independent process would have another semaphore.
The collection backlog is limited to twice the source processing batch before it
waits, preserving all remaining leads. This bounds retained media and prevents an
unbounded CPU preparation queue. CPU ASR remains one lane; no unsupported claim of
four parallel vision models is made.

Collection and analysis commit separate durable jobs. A restart recovers a pending
source whose enqueue was interrupted. Main case analysis waits for queued source
jobs; failures remain explicit gaps. Lease renewal and cancellation checks run before
model calls and before identified-spot insertion. Owner export/erasure includes
source jobs and their timings; interpretation data stays on the existing source.

The browser helper keeps one Chromium process, creates/closes a fresh context for
each URL and expires after 120 idle seconds. It retains the existing target-post,
network, comment visibility, cooldown and allowance checks. Early readiness requires
the configured sample to be present; partial/absent samples receive the bounded
settle window and exposed-control expansion. It does not claim all comments or a
representative sample. Provider/browser allowances are unchanged.

## Operating and rollback

The independent switches are documented in `.env.example`:

```dotenv
ANALYSIS_REUSE_ENABLED=true
RESEARCH_PIPELINE_ENABLED=true
BROWSER_REUSE_ENABLED=true
OLLAMA_KEEP_ALIVE=10m
```

These are opt-in in a fresh checkout. The existing local installation can use them
after its recorded checks. Keep APP_MODE=local, the current model, eight frames,
thirty collected-comment target and existing source/provider allowances.

To roll back scheduling/reuse, set the first three values to false and model
residency to 2m, then restart using `scripts/stop.ps1` and `scripts/start.ps1 -SkipBuild`.
Pending source jobs still execute in the ordinary single worker loop. Coverage fixes
remain; rolling back must not restore silent truncation or venue loss. There is no
schema downgrade or deletion of collected evidence. Restore a backup only for an
actual data recovery need.

Read timing details in Investigations and Data readiness. The authenticated operator
API is `GET /api/admin/research-performance`. A local report is available with:

```powershell
cd backend
uv run python -m app.manage performance-report
uv run python -m app.performance_smoke --model --browser --keep-alive 10m
```

The smoke CLI is explicitly opt-in. It reads one retained agent-collected real
caption for two local inference calls and writes measurements to ignored
`data/performance/`. Its browser examples are intercepted offline pages in actual
Chromium; they are not inserted into the inventory and are not live Instagram
evidence. It neither changes quotas nor downloads models. Run model measurement
while the worker is idle to avoid cross-process GPU contention.

In Data readiness, independently inspect and label a retained source first. Then
**Measure extraction against saved labels** enqueues an uncached local comparison.
Changed/expired inputs, missing labels and changed/revoked correction context block
it. It compares independently labelled names/comments with the stored prediction,
records current execution, and reports historical baseline wall time as unavailable.
It does not claim a measured speedup. Revoking labels removes associated benchmark
receipts. Video/branch accuracy needs its own paired original-media review.

## Measurements obtained

`data/performance/smoke.json`: actual agent-collected caption, model initially absent
from `/api/ps`; first call 18.026s, including 11.174s model load; repeated call 5.912s,
including 0.015s load. Same model/input and candidate count, but outputs are unlabelled
and not evidence of identical factual accuracy. Residency and prompt reuse both
contribute; this is not an end-to-end before/after benchmark.

Ollama reported 2,338,198,648 model bytes and 1,863,361,494 VRAM bytes with context
4,096 in that caption test: partial GPU placement. `nvidia-smi` subsequently reported
2,649 MiB used out of 4,096 MiB and 0% utilization at idle. Those figures are not peak
vision/ASR memory, sustained utilization or evidence that a GPU purchase is required.

The first guarded-client receipt is `data/performance/context-guard-smoke.json`;
the subsequent pooled-client receipt is `data/performance/pooled-client-smoke.json`.
Keep these distinct: context protection adds work and must be included in final
measurements, not omitted to advertise the earlier shorter result.
Final pooled-client calls were 7.401s with tokenizer initialization and 5.251s with
its vocabulary reused; budget-check time fell from 1.687s to 0.088s. These remain
unlabelled repeated-caption samples, not a general speed/accuracy comparison.

Controlled Chromium reused one browser across two pages: each began with zero
cookies and ended with its own one fixture cookie, retained both fixture comments
and the matching caption, and reached configured readiness. Recorded times are
offline harness times, not public website performance.

Final checks: 232 backend tests; required Ruff; strict web build; 16 local and 30
isolated-demo browser checks passed, with two intentional viewport-specific demo
skips. Real local API/worker remain running; temporary demo processes stopped.
Consistent SQLite restore audited healthy; 70 sources/111 spot originals and zero
real venue publications/human labels preserved. See the newest VERIFICATION entry.

## Remaining validation

- Independently label representative real English/Tamil/code-switched examples,
  late signs, several venues/branches, contradictions, missing modalities and wrong-city sources.
- Run matched old/new prediction and wall-time comparisons on retained permitted
  inputs; include omissions, failures and wrong-branch/unsupported-fact regressions.
- Exercise the new browser helper on accessible public reels when ordinary allowances
  permit; current exhausted allowances are not reset for a demonstration.
- Measure real frame/ASR/vision memory, cold/warm and queue behaviour over several days
  before increasing CPU/GPU parallelism or buying hardware.
- Obtain current independent venue facts and explicit approvals, then measure real
  outing feasibility, competitor comparisons and invited-user outcomes.

No zero-accuracy-loss guarantee, exhaustive city coverage, completion date or customer
readiness follows from code/tests alone.

Primary runtime references: [Ollama chat](https://docs.ollama.com/api/chat),
[Ollama residency/GPU guidance](https://docs.ollama.com/faq),
[Qwen2 tokenizer handling in llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/src/llama-vocab.cpp).
