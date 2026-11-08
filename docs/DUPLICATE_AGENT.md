# Dedicated duplicate agent — 8 November 2026

This continuation fixes repeating identified-spot drafts. It does not establish
physical branch accuracy or approve locations for itinerary suggestions.

## Why some duplicates survived

- Caption handles, sign lettering and speech/OCR variants had different name keys.
  Real retained examples include `laffinage.coimbatore`, `l'affinage` and a partial
  `l'affin`, plus `Cosmos Cinemas` versus sign lettering `Cosmo Cinemas`.
- The old cleanup merged only when exactly one counterpart matched. A group of
  three could leave each row with two matches and consequently merge none.
- Duplicate-only held proposals were excluded from automatic reconsideration and
  the manual merge interface rejected held source records.
- A legacy identity-hash/merged-record lookup could bypass newer conflicting
  branch clues. Concurrent reciprocal manual merges also needed serialization.
- Search enrichment can attach one generic menu URL to different branches. A
  shared search-result page must never establish that the branches are identical.

## Current workflow

1. The local scheduler checks the inventory version when it runs (normally about
   once a minute; source/control delays can extend this). An unchanged completed
   version does not cause another full scan. An existing queued/running scan is
   reused. Failed terminal scans can retry after a cooldown; manual scan is also
   available.
2. A dedicated `batore-duplicates` worker thread claims durable
   `spot_deduplicate` jobs, independently of the collection/control and single
   model lane. It uses local SQL and deterministic evidence rules, no new AI
   provider, GPU inference or external requests. This is a separate responsibility
   inside the existing worker process, not a second LLM or separate server.
3. It reads owner-scoped unprepared drafts and duplicate-only held proposals.
   Unrelated relevance/geography holds, merged/rejected originals and prepared
   venues are not automatically consolidated.
4. Broad name/token, stable-reference, source and nearby-coordinate blocks find
   candidate pairs without a top-three prune. Candidate retrieval is not proof.
   Comparisons are planned outside the inventory writer lock; job leases renew.
5. Automatic decisions require compatible evidence. Anchors include an exact
   Maps identity, exact OSM object, compatible detailed own-address, or compatible
   names/aliases with coordinates within 25 metres. Concrete conflicting Maps
   identities, streets, house/unit numbers, postcodes, neighbourhoods, invalid
   coordinates or points over 150 metres apart block automatic merging.
6. A narrowly scoped caption/sign rule can consolidate extraction variants within
   the same owned source: a single caption entity must agree with recorded visual
   lettering, neither role may be a failed/skipped output, all recorded video
   candidates must account for that entity, and comparison/multi-venue captions
   are excluded. Limited repeated-vowel/plural normalization and sufficiently
   long partial OCR prefixes are allowed only under that source context. Obvious
   promotional dish titles remain raw model outputs, not new identity proof.
   These are still unverified model observations, not independent Maps checks.
7. Every pair in an automatic merge group must agree. A–B and B–C do not justify
   merging A–C when their evidence conflicts. The group is reloaded and checked
   again under a short serialized inventory lock immediately before writes.
8. A suitable active survivor is retained, preferring reviewed/first-party records
   and complete recorded sign lettering over a handle or partial OCR variant.
   Aliases and evidence are combined; originals retain `merged_into`, their prior
   status and audit history. Original source timestamps remain. The technical
   row-update time is not evidence of newly checked facts.
9. Uncertain pairs enter the private review desk. They are possible duplicates,
   not confirmed errors. Manual merge requires choosing an active survivor,
   checking the exact branch and recording an explicit reason. Different explicit
   Maps identities require correction before merge. Held sources can now be
   merged after review; reciprocal requests cannot create a merge cycle.
10. New insert/hash-redirect and legacy cleanup paths also check concrete branch
    conflicts. Search-only/monitored/lead URLs are excluded as identity anchors.
    Nothing in this workflow accepts facts, confirms a Maps name or publishes a
    venue. Each location still needs the operator's final approval.

The version saved as scanned is the input version, not a claim that concurrent
new rows were checked. Own merges or new evidence can cause a follow-up scan.
Reports are private and included in account export/erasure. Separate backups,
CSV exports and rehearsal files remain offline copies with their own retention.

## Operator controls

Open <http://127.0.0.1:8000/admin> → **Identified spots** → **Duplicate review desk**.
Refresh the saved report, filter/paginate possible pairs, inspect the original
spot/source records, then explicitly review a pair. **Run duplicate scan** queues
work; it does not silently merge the displayed uncertain pairs.

From `backend`, the equivalent queue-only command is:

```powershell
uv run python -m app.manage duplicates-run
```

The normal `scripts/start.ps1` launcher starts the worker and its duplicate lane.
The workstation must stay awake for background work. This is local internal
research, not a hosted production deployment.

## Verification and actual application

- [x] Implemented policy, durable scheduling, dedicated lane, group validation,
  conflict guards, manual held-source merge, review UI and private export/erasure.
- [x] **345 backend tests passed**; **20 isolated desktop/mobile checks passed**,
  including explicit branch confirmation, no merge on page load, held-source
  handling, pagination, accessibility, read retry and no mutation replay. Strict
  web build, new-module Ruff checks and repository unused-name checks passed.
  Broader optional lint selection also reports pre-existing style findings in
  unrelated files; it is not claimed clean.
- [x] Separate actual-inventory snapshot rehearsal: 989 eligible originals, 6,965
  candidate pairs, three merges in 20.095s; second pass zero in 20.786s. This is a
  consistency/safety rehearsal using existing evidence, not human gold labels.
- [x] Fresh consistent pre-apply backup:
  `data/backups/batore-20261108T142244Z.db`.
- [x] Real tracked local pass: 1,007 eligible originals, 7,150 candidate pairs;
  **three merged source drafts**, 12.961s job execution. Partial/handle L'affinage
  records consolidated into the full sign-name draft, and the Cosmos caption
  variant into the Cosmo sign-name draft. Second real pass made **zero** additional
  merges. All originals retained; zero venue/claim records created.
- [x] API/worker restarted locally. One interrupted owned analysis job was
  requeued with its committed source checkpoints/counters retained. A worker-run
  scan completed without foreground orchestration, with **zero model calls**;
  authenticated duplicate status returned HTTP 200. Initial unlimited-count
  collection remains enabled, with source pacing and monetary controls retained.
- [x] At 14:26 UTC / **19:56 IST**: **948 active unapproved drafts, 144 held,
  16 merged originals; 1,108 total**, 372 research sources. **215 possible review
  pairs** at the earlier stable scan, not 215 proven duplicates. Structural SQL
  audit healthy, integrity `ok`, no audited orphan or duplicate identity-key
  groups. Zero venues/claims and zero approvals. Counts change during collection.
- [ ] Human verification of uncertain branch pairs and real automatic-merge
  accuracy; broader multilingual/source accuracy; sustained concurrent growth;
  complete Coimbatore coverage and explicit location/fact approvals.
- [ ] Customer validation/public release. No model-weight training occurred.

Ignored evidence receipts are in `data/duplicate-agent/`: rehearsal/pass reports,
real pass reports, API/lane checks and controlled restart recovery. Collection CSVs
and current point-in-time gaps are in `data/city-collection/`.

## Meaning of the collection labels

**Vibe evidence** means retained source observations about ambience, such as
seating, music, lighting, crowd levels or an activity setup. A missing-vibe count
is the number of active drafts without that evidence. It is not a rating or a
verified fact; inferred atmosphere and venue attribution still need review.

**41 of 168 area/topic searches** means investigations have been created for 41
combinations in the current grid of **14 areas × 12 topics**. For example,
Peelamedu cafés and RS Puram sushi are two different combinations. Queued, running,
review, failed or cancelled cases can all count as previously scheduled; the
counter does not report completed searches, verified venues or city completeness.
The other 127 combinations had no investigation in that snapshot. Other queries
and directory imports can discover places outside those exact combinations.
The UI now calls these **search topics queued or started** and explains the
distinction directly.
