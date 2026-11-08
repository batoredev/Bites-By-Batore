> Latest continuation: [STAGES_1_2_3_6.md](STAGES_1_2_3_6.md) adds the real evaluation queue, holdout correction exclusion, source monitoring and approval packets. Six reference images are now indexed, but no independently verified visual branch match or accuracy result is claimed. Zero human evaluation labels and zero approved venues at this checkpoint.

> 7 November: [PERFORMANCE_IMPLEMENTATION.md](PERFORMANCE_IMPLEMENTATION.md) records completed speed/coverage mechanisms, local test receipts and remaining real quality validation. This is not a claim of complete Instagram access, independent accuracy or approved customer inventory.

# Instagram implementation and validation record — 6 November 2026

This supplements PROJECT_MASTER.md. The local collector operates independently of Codex while the workstation, API, worker and Ollama are running. Completing code is different from demonstrating factual accuracy, exhaustive Instagram access or a verified Coimbatore inventory.

## Scope and current status

| Capability | Implemented and locally tested | Actual execution evidence | Outstanding validation |
|---|---|---|---|
| Discovery | Public keyword discovery, newest-known-publication ordering, all discovered relevant sources retained, resumable processing batches | Prior 15-source run; existing sources selected by the agent | Search coverage, hidden/unindexed posts and representative access rates |
| Direct collection | Anonymous public Instagram page/video/caption/visible comment extraction; exposed reply controls; cooldown and quota deferral | New collector retrieved 12 comments from C7sl-Wloucq on 6 November, without login or Meta/Apify credentials | That page exposed no eligible expansion controls; successful live expansion is not established |
| Comments | Source-bound visible replies, batches of five, persisted progress, per-comment classes and text hashes; explicit unclear fallback | Local Qwen classified 12 collected real comments | Independent labels and agreement; sampled comments are not a representative poll |
| Video/language | Local Whisper transcription, sampled scene/keyframe groups, original-language visible lettering, follow-up inspection | Prior actual eight-frame results on two reels | English/Tamil representative word/character error rates; additional languages separately |
| Visual matching | Local ORB features, unique correspondences, homography/inlier and coverage checks; owner-scoped reference library | One first-party WAGHOBA page image indexed with 500 features | No successful independently confirmed real reel-to-branch visual match yet; shared logos/photos can mislead |
| Branch identity | Name/alias, area, address/house/postcode conflict checks, visual clues; ambiguity preserved; optional fresh Places results ranked | Real review queue available | Places connector not live verified/configured; exact Maps identities require review |
| Reliability | Owner-scoped, deduplicated 180-day human outcomes; uncertainty intervals; prospective prediction timestamps and Brier score | Calculation/ownership regression tests | No adequate prospective review sample; likes do not establish truth and dislikes are not invented |
| Correction learning | Existing scoped correction retrieval; paired local baseline/with-correction jobs; excludes same-source origins; checks revocation/input changes | Isolated leakage/ownership tests | No independent human-labelled A/B result yet; no trained owned weights |
| Inventory | Duplicate/relevance checks; maps/menu/vibe drafts; provenance and explicit location approval | First-party refresh: eight pages, nine targets, zero publication | Verified hours, prices, branches, suitability and user approval for every location |
| Evaluation | Operator-labelled names, transcription, visible text and comment classes; grouped development/holdout reports; release gates | Isolated API tests and browser review flow | Real gold labels, representative sampling and customer outcomes |

## How the added work runs

1. Existing discovery retains the full discovered set and orders known publication dates before processing. `RESEARCH_MAX_SOURCES` remains a batch size, not a total source cap.
2. Public collection only retains source-bound visible data. Reply/comment expansion is limited to controls associated with the exact post. Missing controls, login barriers, challenges and quota waits remain explicit. The configured local comment sample limit remains 30; the implementation supports up to 100. Neither setting promises all Instagram comments.
3. Collected comments are classified five at a time as `firsthand_claim`, `question`, `promotion`, `correction`, `opinion`, `unrelated` or `unclear`. Claims remain unverified. Each completed batch is committed; changed comment text invalidates previous batch reuse. The scheduler queues versioned upgrades for older sources whose raw comments remain available.
4. Local video observations include exact original-language lettering where readable. Frame signatures are compared against locally stored first-party/page-image signatures. Only matching clues and timestamps are attached to the source; comparison does not approve a branch.
5. First-party collection and web enrichment can index same-host HTTPS images. Images are size-limited; descriptors and evidence URLs are stored locally. A page image is not assumed to depict the exact storefront. Cross-host images are currently skipped and recorded as gaps. This is a small local reference library, not global visual geolocation.
6. Branch ranking combines available evidence and exposes house-number/area conflicts. Fresh Google Places candidates, when configured, are filtered for Coimbatore proximity and shown as candidates. Neither similarity scores nor model output count as independent confirmation. Existing operator Maps review and explicit location approval remain mandatory.
7. Creator statistics use distinct human-reviewed evidence groups within 180 days. Unresolved and outdated evidence does not enter the factual-support denominator. Wilson intervals describe the selected sample only. Prospective calibration uses predictions recorded before judgements; insufficient samples remain explicitly uncalibrated.
8. Accuracy labels are stored in the private source record. Export and erasure include them, comparisons and related jobs. No synthetic fixture or model answer is written as a real human reference label.

## Operator procedure

Open `http://127.0.0.1:8000/admin`.

1. **Investigations** shows examples the agent found, its evidence and gaps. Correct an interpretation through the existing scoped correction form; revoke an incorrect correction when necessary.
2. **Data readiness → Instagram accuracy review** lists collected sources. Open the original source, select the modality and language code (`en`, `ta`, or the actual language), then enter independently checked names, transcript, lettering or comment categories. Empty names can deliberately label a source with no venue. Missing original text must not be guessed.
3. The transcript and lettering reference must cover the same analysed material as the prediction. The current review contract is limited to 2,000 characters. This needs careful alignment; a long-video transcript cannot be compared to a short analysed clip as if they were identical inputs.
4. Saving labels records an immutable prediction snapshot inside the current label, reviewer, time, input fingerprint and deterministic origin-based development/holdout split. Re-saving replaces that task's current label. The report deduplicates origin/task pairs and uses labels from the last 90 days. Labels can be revoked.
5. **Compare with independent corrections** queues local caption/comment baseline and correction-assisted runs on the same unchanged input. A source's own correction or a repeated origin cannot serve as its learning example. Revoked corrections and changed labels/inputs cause results to be discarded. One paired result is not general improvement or weight training.
6. **Identified spots** exposes drafts, duplicate holds, map/menu/vibe evidence and missing fields. Confirm the exact Maps branch, prepare the pending venue, review essential facts and approve the location explicitly. An accuracy label or accepted individual fact does not publish a venue.
7. **Background work** shows retries and deferrals. Quota waits retain pending work. Keep the workstation and Ollama running. Start/stop with the existing `scripts/start.ps1` and `scripts/stop.ps1`; no startup task has been installed.

## Evaluation thresholds and remaining work

The initial engineering gates require at least 30 distinct held-out origins, ten English and ten Tamil task labels, 20 name cases with precision >=95% and recall >=90%, ten transcription cases with aggregate word error <=20%, ten visible-text cases with aggregate character error <=10%, and 100 comment labels with >=85% agreement. These are provisional targets, not measured accuracy or a statistical sampling guarantee. Other languages need their own evaluations before making quality claims about them.

- [x] Implement the local matching, comment classification, review statistics, evaluation and comparison mechanisms above.
- [x] Exercise real local comment inference and first-party reference indexing.
- [x] Exercise the revised public collector; report its unexpanded sample honestly.
- [ ] Independently label a representative set across cuisines, categories, creators, languages, ambiguous branches and negative examples.
- [ ] Demonstrate real branch visual matches and measure false matches, including reused photos/logos.
- [ ] Demonstrate correction-assisted improvement on held-out independent sources.
- [ ] Accumulate prospective human outcomes before claiming calibrated creator reliability.
- [ ] Validate optional official Meta/third-party/Places paths with configured access; public collection itself needs none of those credentials.
- [ ] Verify and approve each location, current critical facts and practical planning suitability.
- [ ] Conduct invited-user evaluation, then public launch only after successful validation.
- [ ] Train and evaluate owned model weights as a later funded/data-backed stage.

Live receipts are in ignored local `data/structured-comments-live-smoke.json`, `data/comment-expansion-live-smoke.json` and `data/visual-reference-live-smoke.json`. Exact test and runtime results are recorded in VERIFICATION.md. Current source availability and inventory counts will change as the worker runs.

Technical references: [OpenCV feature matching and homography](https://docs.opencv.org/4.13.0/d1/de0/tutorial_py_feature_homography.html) and [Google Places Text Search](https://developers.google.com/maps/documentation/places/web-service/text-search). Neither technique guarantees branch identity; Maps ranking is candidate assistance with separate operator review.
