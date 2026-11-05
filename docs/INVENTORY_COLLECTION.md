# Coimbatore itinerary inventory and Instagram work queue

Updated 5 November 2026. This is an itinerary-planning product: food and/or entertainment within the user's time and budget. Investigation supplies its database; investigation is not the customer-facing goal.

## Confirmed latest rules

- Search newest-first, using publication dates rather than likes or collection time. An unknown date remains unknown.
- Retain every relevant source returned by the configured discovery paths. Do not discard everything after the first two or three.
- Process sources in durable batches. A processing batch is not a cap on the investigation total. Resource/access limits can delay work, and must remain visible.
- Add extracted places to a private **identified spots** database after each source completes, and reconcile the inventory again when an investigation completes.
- Collect map/branch leads, menus or activity offerings, item/package prices, vibe evidence, hours and practical details for Coimbatore.
- The operator approves each location before it can appear in itinerary suggestions. Neither a model result nor acceptance of a venue fact grants publication permission.

## Pipeline and stored outputs

| Step | Method | Stored output / boundary |
|---|---|---|
| Topic selection | Existing local frontier rotates food/entertainment topics and neighbourhoods | Private investigation and durable tasks |
| Recent discovery | Public search tries month, year and broader available results; configured YouTube uses date order; official Meta recent-media cursors persist between worker deliveries | Every returned candidate is retained after URL deduplication; provider search windows and limits do not establish exhaustive Instagram coverage |
| Date checking | Bounded public-metadata probes resume in groups of eight before collection | Known dates ranked newest-first; unknown dates last; relevance breaks ties. Browser timestamps can refine the order later |
| Collection and interpretation | Anonymous browser, available provider alternatives, local speech/model processing | Each source is collected and analysed before moving to the next; completed outputs survive retries |
| Long investigations | Three-source processing batch, durable queue, lease renewal and deferred quota errors | Remaining sources stay in the same case; an hourly retry checks whether capacity/access has recovered |
| Identified spots | Candidate extraction from caption/video results, owner-scoped identity keys | Names, area/address clues, sources, dish/activity mentions and explicitly unverified atmosphere observations; no invented coordinates |
| First-party enrichment | Bounded HTML collection from documented Coimbatore targets; literal source checks for configured branch facts; structured menu-item parsing and source direction links | Item prices retain `item` units; park entry prices retain their units; source links, collection times, unknown publication dates and review gaps are preserved |
| Further enrichment | Local public-web search for newly identified names; two pages per job delivery | Search-discovered pages remain unverified candidates, never automatically labelled official. Missing/blocked pages are retained as gaps |
| Operator review | Identified spots panel, branch-evidence form, existing fact review and Venue desk | Preparing a venue creates a pending record. Explicit location approval plus current essential facts is required before publication |
| Planning | Existing budget/time/preferences itinerary engine | Drafts and venues lacking operator location approval cannot become live itinerary candidates |

The latest local configuration uses `RESEARCH_STREAMING=true`, `RESEARCH_MAX_SOURCES=3` as the batch size, `BROWSER_DAILY_LIMIT=30`, `MAX_PROVIDER_CALLS_PER_DAY=200`, `MEDIA_MAX_FRAMES=8` and `INVENTORY_COLLECTION_ENABLED=true`. Optional paid providers remain disabled; paid-provider reservations retain the INR 3,000 monthly target. The higher free-source allowances are pacing limits, not purchased quotas or a promise of 30 successful reels.

The scheduler refreshes the first-party target inventory daily and queues enrichment for newly identified spots. It runs only while the workstation and worker remain on. The local job database retains pending work across restarts. This is not a claim of continuous city-wide coverage or instant detection of every menu change.

## Video processing scope

The updated local extractor combines clip endpoints, detected scene transitions and evenly spaced fallback frames within the configured frame budget. All selected frames are sent to the local model in groups of four; frames after the first group are no longer silently omitted. Speech is transcribed once per video. The model can request bounded follow-up timestamps, which are inspected as another view of the same source, not independent corroboration.

This is bounded scene/frame sampling, not exhaustive decoding and interpretation of every video frame. A real two-scene generated clip verifies scene-cut selection; an eight-frame test verifies all groups reach analysis. The earlier real 15-source run used the previous four-frame configuration. A new real eight-frame replay was deferred by the configured daily browser limit, so that newest live smoke is **not yet verified**. Raw failures remain visible, and available-modality limitations are retained.

## What has actually been collected

The first inventory pass fetched eight distinct first-party pages across nine named targets. It stored **120 menu item/price pairs** from [The French Door's menu](https://www.thefrenchdoorindia.com/menu), source map links, activity offerings and atmosphere descriptions. It also stored destination-coordinate leads, hours and listed entry fees from the district administration's [Semmozhi Poonga](https://coimbatore.nic.in/tourist-place/semmozhi-poonga/) and [Nilgiri Biosphere Nature Park](https://coimbatore.nic.in/tourist-place/nilgiri-biosphere-nature-park/) pages. All remain unapproved. Availability, taxes, entrance position and current conditions need review; listed dish prices are not per-person meal budgets.

The broader live Instagram case `64ae5da9-a63c-40e3-9367-1c4acf2dffa2` searched **Coimbatore cafes latest menus ambience** without supplied example links. It retained and processed **15 sources**, downloaded **14 videos**, and collected **83 loaded comments**. Stored analyses: **15 captions, 12 comment samples, 13 videos**. Remaining modalities have explicit gaps. All eight workflow stages finished and the case ended in `review`.

At that checkpoint the database held **66 identified candidate records**, combining earlier source extractions, new source extractions and the nine first-party targets. These are not 66 verified unique operating venues; spelling variants, uncertain branch associations and false candidates require review and deduplication. No venue was published or approved on the user's behalf.

Source publication dates were refined by browser data after the initial ranking. Three sources initially lacking a usable date consequently appear at different positions in the final dated view. `selection_rank` records the original selection order; it is not rewritten to falsely imply that the more precise date was known earlier.

## Review procedure

1. Open http://127.0.0.1:8000/admin and choose **Identified spots**.
2. Inspect each source, date, branch clue, map lead, menu/activity price and vibe statement. Unknowns and contradictory proposals remain separate from accepted facts.
3. Use **Prepare location for approval** only after checking its exact address and coordinates against independent evidence. The form saves a pending venue.
4. In **Venue desk**, review current price, hours and operating-status evidence. Explicitly approve that location when ready. Accepted facts alone no longer trigger automatic publication.
5. Use investigation corrections to teach source-interpretation mistakes. This retrieves examples into future analysis; it is not weight training or proven improvement in model accuracy.

## Storage, ownership and retention

Schema 5 adds `identified_spots` with owner-scoped identities, draft data, status and the eventual venue ID. Export includes owned spots. Erasure removes owned spots and their queued inventory/enrichment jobs; another owner's records are unaffected. Published city inventory has its separate review/audit lifecycle.

Raw Instagram source text/transcripts expire 24 hours after the latest valid fetch; receipts and derived observations persist. Re-fetching an expired pending source establishes a new retention window. Media is removed after streamed analysis; private signed media URLs are excluded from normal API/export views. Point-in-time SQLite backups can contain source data from their snapshot time and need separate retention handling.

## Completion register

| Requirement | Current evidence level | Remaining work |
|---|---|---|
| Newest-known-first selection | Implemented; ordering/probe-resume tests; live dates recorded | Providers can omit dates or return incomplete search results |
| More than 2–3 relevant sources | Implemented; six/ten-source retention tests; real 15-source completed case | No claim of every Instagram post worldwide being discoverable |
| Resumable source processing | Implemented and tested; live per-source results persisted | Longer operation and varied access-failure evaluation |
| Official Meta pagination | Implemented, mock cursor tests | Credentials/permissions and live access verification |
| Direct video/comments collection | Live exercised on real public pages | Public comment replies/pages remain a bounded sample; access varies |
| Scene selection, all frame groups, follow-up inspection | Implemented; local extraction/grouping tests | New eight-frame live replay and representative multilingual/OCR evaluation |
| Automatic identified-spots DB | Implemented; live records; owner/export/erasure tests | Branch deduplication and operator verification |
| Menu/map/vibe inventory | First real batch stored and review UI tested | Broad category/neighbourhood coverage, current facts, manual map/vibe checks |
| Explicit location approval | Implemented and tested; auto-publication path removed | Operator has not approved any real locations |
| Full original Instagram vision | **Not fully complete** | Advanced visual reference-image geolocation, calibrated creator reliability, representative labelled accuracy evaluation, broader source/comment access, and verified city inventory remain open |

Code/tests being complete for a listed subtask does not close the final row. Model quality cannot be certified from successful JSON output or a few accessible pages.
