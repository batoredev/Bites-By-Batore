# FavHiker: deep public review and shared-feature implementation

Reviewed and implemented **7 November 2026**, Asia/Kolkata. This expands [the first comparison](FAVHIKER_COMPARISON.md). Project decisions remain in [PROJECT_MASTER.md](../PROJECT_MASTER.md).

## Result and evidence boundary

FavHiker is a direct competitor in deciding where and what to eat, remembering tastes and finding something suitable when the user is undecided. It also advertises day/trip planning. **Coimbatore, mood, personalization, budgets, AI review analysis and human review are not exclusive differentiators for us.** Public Coimbatore restaurant, cuisine and dish pages were found in this review.

This task adds working shared capabilities to our local app: typed reviewed menus, dish search and suggestions, practical filters, private dish history, cuisine/spice preferences, reversible feedback and independent novelty controls. It strengthens evidence handling and preserves explicit location approval. It does not establish that either product always gives correct recommendations, that we match their inventory breadth, or that our recommendations outperform theirs.

Evidence vocabulary:

| Level | Meaning in this review |
|---|---|
| Advertised | First-party product or store description; not independently executed |
| Public page observed | Text/controls returned through web retrieval or indexed first-party content; may be a cached version |
| Browser attempted | Actual anonymous Chromium request; four routes returned CloudFront HTTP 403 |
| Implemented | Our code and UI exist |
| Locally tested | Isolated database, assertions and browser checks passed |
| Live verified | A particular real source/runtime path actually executed; not general accuracy |
| Customer validated | Real users completed independently checked outings; **not established here** |

The web retrieval tool returned different cached versions of some URLs. For example, a newer indexed restaurant page exposed menu/review detail while an older direct-open snapshot exposed only a shell. Collection counts, marketing rules and page layouts are therefore observations of returned versions, not a guarantee about every current session. No account was created, subscription purchased, message sent, app installed, protection bypassed or private implementation accessed. No competitor content was inserted as an approved venue fact in our DB.

## What was learned from official sources

| Source | Observation | Limit |
|---|---|---|
| [Home](https://www.favhiker.com/) | Social diary, taste matching, choice comparison, mood-based day planning, broader categories and business updates | Marketing and visible page content; recommendation outcomes untested |
| [How it works](https://www.favhiker.com/how-favhiker-works) | Dish/cuisine/location filters, diary learning, community GoldenBites and AI Picks; a canonical dish vocabulary is described | Coverage and ranking claims not independently audited |
| [Trip planner](https://www.favhiker.com/plan-my-trip) | Public shell has destination, timing, participants, budget and Favio conversation | No generated itinerary was obtained or checked |
| [Dining formats](https://www.favhiker.com/dining-formats) | Eighteen formats in three tiers; described owner/editor priority, type/photo inference and uncertain-case review | Their actual classifier accuracy and review operations were not tested |
| [Periyar Restaurant, Kochi](https://www.favhiker.com/city/kochi-625/restaurants/periyar-restaurant-kochi-664c805d53e25743dd64b951) | Dish diary counts, amenities, directions and AI Picks explaining praise/complaint analysis of a recent review sample | Advertised latest-100 processing was not executed by us |
| [Takri Natives' Kitchen & Cafe](https://www.favhiker.com/city/nagrota-bagwan-506/restaurants/takri-natives-kitchen-cafe-nagrota-bagwan-69501b14790e15b680bdaeda) | Returned page includes 161 menu entries attributed to the restaurant website, with categories and prices | Menu completeness/current prices not independently checked; another section was an empty client shell |
| [Food categories](https://www.favhiker.com/categories) | Category search and dish discovery pages | Taxonomy counts vary by returned page/version |
| [Malls](https://www.favhiker.com/malls) | Mall discovery includes dining, cinema and children/family uses | Does not establish live activity capacity or seat availability |
| [Connect](https://www.favhiker.com/connect) | Premium MCP integration advertised for reading/writing permitted diary and preference information through assistants | Authentication, permissions and actual transactions untested |
| [Google Play](https://play.google.com/store/apps/details?id=com.delnie.favhiker) | Android product, cuisine/diet/spice personalization and social features; 50K+ cumulative downloads shown | Downloads are not active users, revenue or retained customers |
| [App Store](https://apps.apple.com/in/app/favhiker-find-must-try-dishes/id6466083218) | iOS product; description includes route-based food discovery, parking/washroom information and dish collections | No native app interaction or route quality benchmark |

Additional routes inspected/search-reviewed include AI Picks, What to Order, public explorers, collections, privacy/terms and business references. Older and newer pages differ in award limits and presentation; a single marketing sentence is not a stable technical specification. Public profile names were not imported into the real database.

Anonymous browser receipt: `data/favhiker-deep-review/anonymous-browser.json`, with four screenshots in the same folder. It records 403 responses for `/`, `/plan-my-trip`, `/search` and `/dining-formats`. Web-readable content does not mean those browser workflows passed.

## Coimbatore evidence changes the positioning

The indexed [Valarmathi Mess page](https://www.favhiker.com/city/coimbatore-2294/restaurants/valarmathi-mess-coimbatore-66b22690ba368cc4f6d0d378) contains Coimbatore address, dishes and diary signals. [Cuisine discovery](https://www.favhiker.com/city/coimbatore-2294/cuisines) includes local cuisine/restaurant associations. Their [Coimbatore restaurant listing](https://www.favhiker.com/city/coimbatore-2294/restaurants) also establishes local presence, although the returned listing version is older. These are enough to reject any claim that they do not cover Coimbatore; they do not establish an exhaustive current venue count.

The indexed [Nahdi Coimbatore page](https://www.favhiker.com/city/coimbatore-2294/restaurants/nahdi-kuzhimandi-coimbatore-66e8d036c095fa3b63e44715) exposes a menu attributed to the restaurant website; a different returned version is an older shell. The indexed [Gobi Sanda Vilas page](https://www.favhiker.com/city/coimbatore-2294/restaurants/gobi-sanda-vilas-kongunaatin-suvai-coimbatore-6a6827809f2e47c202baf07d) exposes dish praise/complaint counts and wait/service observations; its older retrieved version shows a generic AI Picks entry point. This demonstrates public feature evidence, not verified extraction accuracy.

A possible position for us is **a feasible, checked short Coimbatore food-and-entertainment outing**, with exact branches, honest freshness, group totals, useful novelty and fast correction. That is a hypothesis requiring actual outing results. Local models and autonomous reels are implementation choices; the customer benefit must be fewer bad recommendations and less planning effort. Their actual autonomous reel workflow, creator calibration and per-field freshness policies remain unknown. Unknown does not mean absent.

## Shared capability matrix and the work completed

| ID | Shared customer need | Our gap before this task | Result in our app | Verification / remaining boundary |
|---|---|---|---|---|
| FH01 | Find a named dish, cuisine or place | Browse mainly searched loaded place labels/tags | Server search includes current reviewed dishes, cuisines, names, tags and neighbourhoods | Boundary-aware matches; expired/unavailable dish evidence excluded; beyond-first-page test |
| FH02 | Know what to order | Offering/package support was not a complete menu experience | Typed menu, private preference ranking, reasons, source/date/expiry and explicit unknown fields | Invalid data and duplicate normalized dish names rejected; actual menus still need review |
| FH03 | Remember dishes to try and dishes enjoyed | Saved places and visits did not form a dish diary | Private want-to-try, tried, favourite and not-for-me states with dates/notes; edit/remove | Stable owner/place/dish identity, persistence, owner isolation and repeat-safe updates tested |
| FH04 | Learn taste without distorting it | Incremental visit contributions were difficult to reverse | Rebuild tastes from retained visit snapshots and dish feedback; cuisine/spice controls | Edit/delete/opt-out/reenable and normalized duplicate tags tested; no trained weights claimed |
| FH05 | Find an appropriate dining setting | Practical reviewed formats/amenities were not searchable | Reviewed dining-format, parking/washroom, vegetarian dish and price filters | Unknown/expired values fail required filters; human-reviewed evidence required |
| FH06 | Ask for something different while keeping the mood | Mood and novelty could be conflated | New place/new taste/familiar preference separate from quiet/social/etc.; combined food/activity guidance | Quiet plus new-taste, negation, word boundaries, party/time/budget preservation tested |
| FH07 | Use positive and negative review evidence | Reel comments existed but dish picks lacked a review-evidence display | Accepted current per-dish review samples show praise, complaint, mixed and source links | Origin/source duplicates collapse transitively; expired/unaccepted signals excluded; no fake stars |
| FH08 | Save and retrieve discoveries reliably | Saved records depended on the initially loaded browse list; toggle could flip on retry | Explicit desired-state bookmark API and separate complete owner saved-place retrieval | Repeat requests stable; saved place beyond first 300 results retained |
| FH09 | Correct personal history | Visits could be added but lacked full reversible editing | Owner-only visit editing/deletion, stable experience snapshot and recomputed taste | Date collisions, future dates and cross-account changes rejected; browser form checked |
| FH10 | Make a workable outing | Planner already existed; live candidate precheck favoured proximity before requested dish | Current menu vocabulary participates in selection; requested dish/locked stops get precheck priority | Budget/time/group tests retained; dish item price cannot replace outing per-person spend |
| FH11 | Find the right branch | Existing explicit Maps identity and location approval gates | Exact reviewed Maps URL preferred in details; menus never grant publication | Unapproved locations remain unavailable; real branch review still pending |
| FH12 | Trust information and control private data | New diary records needed lifecycle coverage | Diary added to export, erasure and taste-memory clearing; source expiry enforced | Isolated privacy/lifecycle regressions passed; no external customer validation |
| FH13 | Use the product on a phone | New forms needed mobile coverage | Responsive menu, filters, diary and visit editor; accessible source links | Desktop/mobile journeys, automated WCAG A/AA assertions and visual inspection |

Our eight supported dining-format values are `cafe`, `casual_dining`, `fine_dining`, `quick_service`, `street_food`, `food_court`, `bakery`, `dessert_shop`. They are a functional local taxonomy, **not** a claim to reproduce FavHiker's eighteen formats. No model assigns or publishes a format without the fact-review path. Cuisine and format remain separate.

Search combines cuisine, vegetarian and maximum-price criteria on the **same available reviewed dish**. It cannot satisfy a Japanese vegetarian query by combining a Japanese meat dish with an unrelated vegetarian dish. If a query matches only a dish name, the price/diet filters also apply to that matching dish. Place discovery is paginated only after filtering, with stable ordering. No public rating/review-count filter or community-award network is claimed to exist in our app.

## How our added flows work

### Menu evidence, review and publication

1. The existing agent finds relevant recent reels and first-party pages, retains evidence and populates owner-scoped identified spots. Website/menu text is a candidate observation, not a verified menu.
2. Operator checks exact branch identity and source. Prepare a venue through the existing review workflow; do not approve merely because it has a convincing name.
3. Add a structured `offerings` claim, using the source's observation time and a justified expiry. Set unknown fields to null or omit them. Do not infer vegetarian status, prices, availability or sentiment from popularity.
4. Review each entry against original evidence. `offerings`, `dining_format` and `amenities` use the existing proposed-claim and explicit acceptance workflow. Public submissions cannot self-assert official authority.
5. Final location approval remains a separate explicit operator decision, requiring exact Maps identity and current critical facts. Accepting a menu never automatically publishes the place.
6. Only current accepted menu evidence appears in dish search/picks. Expired menus display an unavailable message. History can still be edited after evidence expires or a venue becomes unavailable.

Example value for an `offerings` claim in the admin JSON field (**schema illustration only; never insert as a real venue**):

```json
[
  {
    "name": "Example reviewed dish",
    "category": "main",
    "cuisine": "Japanese",
    "tags": ["sushi"],
    "price_inr": 280,
    "unit": "item",
    "vegetarian": null,
    "spice": null,
    "available": null,
    "review_evidence": []
  }
]
```

The API wraps this in `{"value": [...]}`. Supported units are `item`, `person`, `group`; this field describes the menu, not a recalculation of itinerary spending. Booleans must be true/false/null, prices finite numeric values, dish names meaningful and unique after normalization. Limits prevent a claim from becoming an unbounded payload: up to 200 entries and up to 100 review observations per item. These are ingestion bounds, not a claim of complete menu access. Larger source menus require deliberate review/extension rather than silent truncation.

`amenities` example: `{"parking": null, "washroom": true, "indoor_seating": true}`. Allowed values are strict boolean or null. These are separately dated accepted facts; a filter does not treat a missing value as yes. Existing dietary/access/age/session constraints remain in the planner.

Optional `review_evidence` observations contain `source_url` (public HTTPS), `evidence_group`, `sentiment` (`praise`, `complaint`, `mixed`, `mention`), `observed_at` and `expires_at` (timezone-aware). Review originals before accepting. Shared origin groups or identical URLs are unioned transitively before counting. Conflicting sentiments in one group become mixed. Expired observations are excluded. Distinct labels do not prove distinct reviewers; counts are labelled **reviewed source groups in a bounded sample**, never the whole platform population. No blanket claim of fetching Google's latest 100 reviews is made for our connectors.

### Private diary and learning

1. Search Explore places and open a reviewed published venue.
2. Save a dish to try, or explicitly record that it was tried on a real date. A save is never a venue visit.
3. My taste contains private dish history with status filtering, editing and deletion, plus editable visits.
4. Favourites and not-for-me dishes contribute small positive/negative tag signals. Visit food/activity dimension scores contribute to those taste tags; atmosphere contributes separately to occasion context. Generic overall stars and free-text notes are not silently interpreted as food taste.
5. Every edit/removal recomputes from remaining history. Repeat saves do not amplify a preference. Case/spelling normalization prevents duplicate tags being counted twice. Visit snapshots preserve the experience context when venue tags later change.
6. Opt out to clear inferred signals; reenable to rebuild only from remaining records. Clear taste memory removes visits and the dish diary, while saved places/plans remain. Full private-data erasure includes the new records; export includes the diary. All history is owner scoped.

No public GoldenBite, taste-twin percentage, crowd badge, shared rating or model-training claim is manufactured from private records. A self-reported favourite does not independently prove a completed visit, a purchase or objective quality.

### Undecided discovery and itinerary

Users keep their starting point, departure, total time, group size and budget. Quiet/social/active describes the desired atmosphere. New place/new taste/familiar describes novelty independently. The guide offers direction without overwriting hard constraints. Current reviewed menu vocabulary can satisfy a dish query; stale menus cannot. Live precheck order prioritizes locked stops and relevant requested dishes before distance, then uses the existing bounded current-status/route adapter path. Real Maps/Routes/provider outcomes remain separately unverified when access is not configured.

## Scope maintained

This remains an English PWA/admin app for short food and entertainment outings in Coimbatore, with multilingual source analysis, local inference/storage and the INR 3,000/month operating target. No extra paid provider or cloud inference was activated for this task.

FavHiker also has social following/circles, public diaries/leaderboards, community awards, gamification, books, stays, worldwide discovery, native apps and assistant connectors. These were researched but are not automatically added to our confirmed private first release. Neither road-trip food discovery nor scenic drives are substituted for the user's short outing requirement. Events and return-trip planning remain excluded. A private taste profile is not equivalent to their cross-user Taste Match network.

## Verification and actual local data

- Backend: **202 passed in 31.74s**; required Ruff undefined/unused checks passed. Includes typed menu validation, freshness, joint filtering, pagination, private lifecycle, reversible learning, approval gates, live candidate ordering and balanced deduplicated review support.
- Web: strict TypeScript and production build passed. Final new-feature desktop/mobile run: **10 passed in 36.9s**. Existing core/accessibility run earlier in this task: **8 passed**. Local research desktop/mobile regressions: **12 passed in 52.3s**. See [VERIFICATION.md](VERIFICATION.md).
- Menu and diary desktop/mobile screenshots inspected in `data/parity-visual/`; no horizontal overflow in checked viewports. Source link underlining fixed after the new evidence panel's accessibility assertion found it.
- SQL: schema **7** adds private `dish_entries`, visit experience snapshots and unique owner/place/dish and owner/place/date protection. Rehearsal migrated a separate backup twice; active DB migrated twice with every existing table count preserved. SQLite/PostgreSQL empty-schema SQL exported; actual PostgreSQL deployment is not verified.
- Backup rehearsal: `data/parity-migration-rehearsal.json`. Active migration: `data/parity-live-schema7.json`. Final online snapshot and separate-file restored audit: `data/parity-final-status.json`. Live data was not replaced by the restore check.
- At **18:39 IST**, actual inventory was **56 active identified spots, 10 merged and 24 held originals, 61 source records, zero accepted venue claims and zero venues/approvals**. There were twelve stored successful `public_content` reel-watch receipts. This supersedes the earlier checkpoint at which watch execution was deferred; it is not evidence of universal comment access or sustained refresh accuracy.
- API restarted in local mode at `http://127.0.0.1:8000`; new private diary, saved-place and filtered browse routes returned 200. One local API and worker tree are restored. The worker heartbeat can age while a synchronous collection/inference job runs; the status receipt records the observed age rather than calling it continuous liveness proof.
- Private review packets exported to `data/review-packs/review-20261107T130632Z.md` and `.json`. They expose blockers; they do not approve any location. Ongoing collection can change counts.

Tests use an isolated demo database and temporary backend databases. The review-support browser example is an intercepted synthetic API response; it is not a real customer review or a live sentiment benchmark. Local research browser mutation fixtures are intercepted. Initial test failures included selector/fixture mistakes, a missing `km` import, normalized duplicate tag counting and source-link accessibility. These were fixed. Two concurrently invoked browser runs also collided on the shared trace directory; final runs are sequential with separate output directories. Failed attempts are not counted as passes.

## Completion checklist and remaining accuracy work

- [x] Deep public first-party/store research and direct browser attempt.
- [x] Establish Coimbatore presence and correct earlier uncertainty.
- [x] Implement FH01-FH13 engineering changes and owner/privacy coverage.
- [x] Run isolated backend, new desktop/mobile and required static/build checks.
- [x] Migrate actual local SQL with preserved data; verify a separate-file restore.
- [x] Restore local app/worker and export current private review packets.
- [ ] Independently review and approve real branch/menu/amenity/freshness facts. Currently no real published venue can demonstrate the new menu experience.
- [ ] Measure extraction and review-sentiment accuracy on independently labelled English/Tamil and other available multilingual evidence. No gold labels or corrections were invented.
- [ ] Run matched real requests through both products and independently verify outcomes. No authenticated competitor planner run or head-to-head quality result exists.
- [ ] Validate with invited users only after sufficient reviewed local coverage; public release remains gated.

Suggested comparative protocol (pending, **not completed**): use identical starting point, departure, budget unit, party, time, diet and novelty requests across dish-specific, undecided, quiet/new-taste, combined-activity, expired-fact and ambiguous-branch cases. Check exact venue/branch and current menu against originals; record total travel/wait/visit time and group spending, constraint violations, relevant alternatives and reasons. Reviewers independently label recommendations before seeing which system produced them. Report denominators, unavailable results, disagreement and uncertainty. Start with at least 30 distinct requests and 100 independently checked item/fact judgements for an initial directional evaluation; these are proposed evaluation sizes, not a statistical guarantee or changed release gate. Do not declare superiority from a single successful example.

Engineering delivery for these shared features is locally testable. **Perfect accuracy, complete city coverage and customer-ready competitive parity remain unproven.**
