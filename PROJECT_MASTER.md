# Bites by Batore — master project record and completion tracker

Last consolidated: **6 November 2026 (Asia/Calcutta)**.

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
- [ ] A05 — Complete a dated, sourced competitor capability matrix and validate differentiation with customers. Prior research leads are not a finished current market assessment.

### B. App and planning baseline

- [x] B01 — English responsive PWA with Discover, Places, Saved, Taste, Sources and Admin surfaces. **Locally verified.** Browser suite and web build.
- [x] B02 — Practical request inputs, group/per-person budgets, baseline hard filtering and one/two-stop plans without return calculations. **Locally verified.** Planner/backend tests.
- [x] B03 — Cost/time breakdown, reserve, full opening-window/movie checks, lock/swap/replan and infeasible states. **Locally verified baseline.** Not arbitrary-length optimization or live seat availability.
- [x] B04 — Saved plans/places, revision rechecks, private profile/visit history and bounded taste updates. **Locally verified.** Core journeys.
- [x] B05 — Data export/erase, preference editing and history clearing. **Locally verified baseline.** Production retention/backup deletion policy still needed.
- [x] B06 — Public-shell PWA caching, install icons, offline reconnect behavior and desktop/mobile automated accessibility checks. **Locally verified.** Not a full manual accessibility audit.
- [ ] B07 — Adaptive conversational “I don't know what I want” flow with useful contrasting choices.
- [ ] B08 — Deeper reason/occasion-aware preference learning and group suitability evaluation.
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
- [ ] DTA08 — Expand offering/source/creator/investigation/evidence relationships and applicable price/session records as needed for the full pipeline.
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
