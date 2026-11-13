# Agent-approved test inventory, categories and collector tuning

12 November 2026. Written for whoever continues this project. It records an owner
decision that changes an earlier rule, what was done, and what is still unverified.

## Owner decision

Until now every location needed the owner's personal Maps review and approval
before the planner could suggest it. On 12 November the owner asked to skip that
for the data collected so far, so the itinerary planner can be tested: the agent
removes duplicates and approves locations itself, and missing prices and hours may
be filled with category estimates.

This applies to the **local test inventory only**. Each such venue carries
`details.test_inventory` and its facts are stored as claims with
`source_group = "test-inventory"`. Nothing here is verified, and it must not be
treated as a verified city guide or released to testers as one.

## What the test inventory contains

Snapshot at publication (12 November, 11:39 UTC), from `data/city-collection/test-inventory-20261112.json`:

| | Count |
|---|---|
| Venues published | 559 |
| Price is a category estimate | 533 |
| Opening hours are a category estimate | 383 |
| Hours parsed from collected text | 176 |
| Skipped: no coordinates | 597 |
| Skipped: same name within 250 m of a published venue | 5 |

By category: restaurants 291, desserts 72, cafÃ©s 61, parks 52, street food 43,
cinemas 28, adventure 6, bars 4, bowling 1, theme parks 1. There are no gaming,
workshop, sports or attraction venues yet, because none of those drafts has
coordinates.

Every venue is assumed open. Cinemas have four placeholder show times
(10:30, 14:00, 18:15, 21:30) because the planner needs sessions to schedule a film.
Vegetarian is set only when the name or a directory cuisine tag says so, which is
why vegetarian-only requests find few places.

## Commands

Run from `backend/` in local mode, with the worker stopped and a backup taken.

| Command | Effect |
|---|---|
| `python -m app.manage retune-drafts` | Re-runs the name gate and category rules over unprepared drafts |
| `python -m app.manage geocode-drafts` | Sets coordinates from Maps links already collected for a draft, when all its links agree within 300 m |
| `python -m app.manage test-inventory-publish` | Publishes eligible drafts as test venues. Safe to repeat |
| `python -m app.manage test-inventory-revert` | Deletes the test venues and their claims and returns the drafts to review |

`geocode-drafts --limit N` also tries the public OpenStreetMap geocoder for N
drafts. In a 40-draft rehearsal it matched 3 and one was wrong, so it is off by
default.

Backup taken before any change: `data/backups/local-research-20261112T111443Z-pre-test-inventory.db`.

## Planner in local mode

Local mode has no Google key, so `/api/plans` previously returned nothing. It now
uses stored hours and travel estimated from straight-line distance. Each plan
carries two warnings saying so. Candidates are the nearest and most relevant
places, at most six per category.

Planner scoring changes that also apply in demo mode:

- A repeated kind of stop (two meals, two parks) costs 12 points per repeat.
- The three options prefer to share at most one stop with each other.
- Everyday words map to categories ("movie" to cinema, "dinner" to restaurants).

## Seeing every plan and every unpublished place

Added later on 12 November at the owner's request.

- **All plans.** `max_options` on a plan request (default 3, up to 400) returns
  that many distinct stop sets, best first, and `total_options` gives how many
  fit. The Discover page asks for 400 and shows 24 at a time with "Show 24 more"
  and "Show all". "All" means every combination of the shortlisted places: the
  planner still shortlists the 18 nearest and most relevant places for one or two
  stops, and 10 for three or four. Measured locally: 120 plans in about 3 seconds
  for two stops, 92 in 5 seconds for three, 162 in 24 seconds for four.
- **Unpublished places.** Admin, "Unpublished places" tab, backed by
  `GET /api/admin/spots/unpublished`. It lists every draft the planner cannot use
  with the reason: no coordinates, held name, possible duplicate, ready but not
  yet published, or merged. Filters: reason, search, category, area, source, and
  whether coordinates exist. At the time of writing: 1,012 unpublished, of which
  609 lack coordinates, 275 are held for their name and 106 as possible duplicates.

## Owner edits, learning, relevance and wider sources (13 November)

Requested by the owner on 13 November.

**Place manager.** The "Unpublished places" tab is now "Place manager". Per place
the owner can edit the name, category, area and coordinates (by pasting a Google
Maps link that contains them), confirm a held name is real, remove a place with a
reason, and restore a removed one. "Add places you know" takes names one per line;
an owner-typed name is trusted and skips the name gate, and the agent can be asked
to research each one. "Publish ready places" adds ready drafts to the test
inventory. Endpoints are under `/api/admin/spots`: `add`, `{id}/edit`,
`{id}/reject`, `{id}/restore`, `publish-ready`, `learned`.

**What is learned from edits** (`backend/app/learned.py`). No model is trained.
The decisions stay on the place records and are read back as rules:

- A name removed as not a real place, out of scope or wrong city is never
  proposed again, and other drafts with that name are held.
- A category the owner set is reused for that name. When two edited names share
  a distinctive word and agree, that word maps to the category for new names.
- A rename keeps the old spelling as an alias, so later reels attach to the
  corrected place, and it is stored as a reviewed example for the caption model.
- A creator the owner blocks while removing a place is skipped in future.
- Restoring a removed place removes its rule.

**Relevance gate** (`backend/app/relevance.py`). Before any model time is spent,
a reel is skipped unless its caption, creator handle or location tag ties it to
Coimbatore, and it is skipped when the caption is plainly about property, jobs or
similar with no food or entertainment word. Sources the owner supplied directly
are never skipped. Measured on stored data: 33 of 691 analysed reels had no
Coimbatore signal, and 26 of those had produced drafts.

**Video names need backing.** A venue name proposed from video analysis is kept
only if it appears in a sign read from the frames, in the speech transcript, or
among the caption names. Measured on stored data: of 870 names that video
analysis added beyond the caption, 498 had no such backing. The retune applies
the same test to existing drafts where the stored evidence allows; it held 90,
which includes some real places whose evidence text had already been purged.

**Planner searches.** A plan request that finds nothing no longer starts research
unless the request names something specific. A test request for "dinner and a
movie" had started a search that collected unrelated reels.

**Wider directory.** The OpenStreetMap query now also asks for bars, pubs,
bakeries and sweet shops, tea and coffee shops, gardens, trampoline and play
areas, sports centres and named pitches, museums, zoos and galleries. It returned
628 objects (474 before), created 149 drafts and 141 were published. The test
inventory is now 700 venues.

**Not done: Overture Maps.** The best free source for missing places is the
Overture Maps places dataset (open licence, built from Meta and Microsoft data).
Reading it needs a new package (`overturemaps` or `duckdb`), and installing one
was blocked by the session's permission rules, so it awaits the owner's approval.

## Categories

The list grew from seven to fourteen and is defined once in
`backend/app/categories.py`. The seven original ids are unchanged.

| Eat | Do |
|---|---|
| `food` Restaurants | `cinema` Movies |
| `street_food` Street food and messes | `gaming` Gaming and arcades |
| `cafe` CafÃ©s | `bowling` Bowling |
| `dessert` Desserts and bakeries | `adventure` Adventure |
| | `amusement` Theme and water parks |
| | `park` Parks and lakes |
| | `workshop` Creative workshops |
| | `attraction` Museums and sights |
| | `sports` Turfs and courts |
| | `nightlife` Bars and lounges |

Classification is keyword rules on the venue name, then on the dish or activity
text. For directory imports the OpenStreetMap tag decides food versus activity and
the name only refines the kind. The retune moved about 280 drafts, mostly
restaurants to desserts (118) and to street food (76).

Search topics changed too (`backend/app/frontier.py`). Sixteen city-wide topics,
mostly activities, are searched once before the area grid. In the grid, "sushi
restaurants" became "new restaurants" and "go karting adventure" became "rooftop
restaurants bars"; the grid is still 14 areas by 12 topics.

## Name gate

`quality_issues` now also holds names that are only descriptive words plus a
locality ("Pet Friendly Cafe in Coimbatore"), names starting with an article
("a local food spot"), and landmarks ("Coimbatore Corporation Bus Stand").
The retune held 188 existing drafts. A short allowlist keeps real businesses with
ordinary-word names, such as Cafe Coffee Day. Held drafts are retained, not deleted.

Known limit: a single unusual word that is not a venue ("Biscoff", "Veranda")
still passes. Only a better extraction model or Maps lookup fixes that.

## Collector fixes

- **Failed reel analyses.** 163 jobs failed with `Invalid local visual
  descriptor`. OpenCV returned 501 feature points for six reference images, one
  over the 500 the size check allowed. The count is now bounded, older references
  are read safely, and one bad reference is skipped instead of failing the reel.
  The jobs were requeued; in the next half hour 57 completed and none failed.
- **Video over the size limit.** 151 sources were rejected at 12 MB. The collector
  now keeps the smaller streams it already sees and falls back to them; the limit
  is 20 MB. Not yet exercised on a live over-limit reel. Existing rejected sources
  need recollection because their links have expired.
- **Duplicate scans.** The scheduler re-ran a multi-minute scan after every
  inventory change (914 runs). It now waits 30 minutes between scheduled scans.
- **Model reloads.** Text and vision calls asked Ollama for different context
  sizes, which reloads the model. Both now load with 8192; the stricter 4096
  evidence budget for text is unchanged.

## Model choice

Machine: RTX 3050 Laptop GPU with 4 GB of video memory, 16 GB RAM. Vision and
frame analysis stay on `qwen3-vl:2b-instruct`. Measured from recorded job
metrics, a model call takes about 11 seconds at the median and a reel about one
minute of processing; the earlier "7.5 minutes per reel" figure was queue wait.

The caption specialist was compared on 24 stored captions, judged by reading
each caption (small sample, one judge, no hand-labelled set):

| Caption model | Captions fully right, raw | After the two checks below | Median time |
|---|---|---|---|
| `qwen3-vl:2b-instruct` (was in use) | about 14 of 24 | about 17 of 24 | 3.6 s |
| `qwen3:4b` (already installed) | about 16 of 24 | about 19 of 24 | 6.9 s |

Both models fail the same way: when a caption names no venue they return the
creator's handle, the area, a film title, or a phrase copied from the prompt.
Two deterministic checks now handle most of that for either model:

- **Written-name check** (`analysts.ground_candidates`). A caption candidate is
  kept only if its name is written in the caption. A name that is only the
  creator's handle needs a separate written mention. Dropped names are stored in
  `analysis.caption.ungrounded_candidates`.
- **Instagram location tag.** The public page data carries the creator's location
  tag, with coordinates, when one was set. The collector now stores it as
  `content.location_tag`, and draft creation uses it for the venue name and
  coordinates. In a live check of five reels, one had a tag.

Decision: captions now use `qwen3:4b` through the new `OLLAMA_TEXT_MODEL`
setting; leave it empty to return to one model. The two models cannot both stay
in 4 GB, so Ollama swaps them about twice per reel. That cost is not yet measured.

The stronger option is a hosted model for the caption step only. It needs an API
key, a spending decision and a change to the "keep models local for now" rule, so
it was not done.

## Verification

- 413 backend tests pass; the new ones are in `tests/test_test_inventory.py` and
  `tests/test_owner_edits.py`.
- `ruff check app tests --select F` is clean; the production web build passes.
- Live local checks through `/api/plans`: default outing, "biryani", "dinner and a
  movie", an entertainment-only morning, and "go karting" each returned three
  plans. A vegetarian "dosa" request returned none, as explained above.
- The new page and the plan list were checked in a headless browser at desktop
  and phone widths with no page errors. The existing browser end-to-end suite was
  **not** re-run after these changes.

## Still unverified or unfinished

- No extraction accuracy number exists; there is still no hand-checked set.
- Test venues may be closed, misnamed or at the wrong branch.
- 597 active drafts have no coordinates and cannot be planned with.
- The stream fallback and the context-size change have not been measured live.
- A machine reboot stops the API, worker and Ollama; none restart on their own.
