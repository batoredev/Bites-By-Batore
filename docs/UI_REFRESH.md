# UI refresh and interaction review — 7 November 2026

The shared capabilities recorded in [FAVHIKER_DEEP_REVIEW.md](FAVHIKER_DEEP_REVIEW.md) remain implemented. Their previous backend run passed 202 tests. This update reorganizes the interface and fixes interactions; it does not turn unreviewed venue data into verified facts. English UI, Coimbatore, local storage/inference and explicit operator approval remain unchanged.

## Design and arrangement

The existing green Bites brand now uses a forest-green navigation rail, clear active destinations, white work surfaces and a consistent spacing/control scale. Navigation descriptions explain where a feature lives. The header names the current screen, and browser titles follow navigation. Decorative hero tiles were replaced with a compact introduction so the planner receives more attention.

The `emil-design-eng` skill guided interaction and accessibility polish. No new UI library, font service, paid service or external image source was required. Font files remain self hosted. Styles for shared surfaces are grouped in `web/src/interface.css`; existing domain-specific styles remain in `style.css`.

| Before | After | Why |
|---|---|---|
| Small text and inconsistent controls across screens | Larger labels/body text, shared control sizes, consistent panel/button radii | Improve readability and predictable interactions |
| Decorative hero dominated the planner | Compact introduction and clearly grouped craving/mood/practical details | Make the primary planning task easier to find |
| Long unstructured My taste page | Preferences grid, visible learning/privacy panels, direct links to diary/history/privacy | Help people reach the feature they need |
| Menu content buried below venue facts | Dedicated Menu & dishes tab; compact heading outside the overview | Reduce scrolling to dish suggestions |
| Transformed mobile sidebar could leave offscreen links focusable | Closed sidebar inert/hidden; open menu traps focus, locks body scrolling and supports Escape | Keep keyboard and screen-reader navigation within visible UI |
| Dialog unmount did not reliably return focus | Explicit restoration to its trigger | Preserve keyboard position after closing |
| Venue tabs lacked a complete keyboard interaction | Arrow keys, Home/End, roving tab stops and labelled tab panel | Support standard keyboard expectations |
| Search errors could resemble an empty result | Explicit error, retry and loading state; reset action for active filters | Distinguish unavailable results from no matching venues |
| Legacy mobile image height rules conflicted with the new card layout | Fixed art height, complete visible card body and properly sized bookmark | Prevent clipped names/descriptions/prices |
| Mobile operator tabs used cramped text | Wrapped two-column operation controls and larger status/table text | Keep review tools readable on small screens |
| Saved/operations buttons had a visual selection only | Selected views announce pressed state | Expose state to assistive technologies |

## Where each feature lives

| Destination | Main actions |
|---|---|
| Discover | Enter a craving or use guided discovery; choose mood and novelty separately; set starting point/time/people/budget; fine-tune and generate/revise an outing |
| Explore places | Search dishes, cuisines, places and areas; expand reviewed practical/diet/price filters; retry failures; open and save places |
| Place details | Overview, Menu & dishes for food/cafes, Sources, I visited, Report a change |
| Saved for later | Switch between saved plans and saved places; revisit/recheck an outing |
| My taste | Edit preferences, cuisine/spice/diet/access; inspect learning; manage private dish diary and visits; export or erase private data |
| From my feed | Share a source/text/media for the existing analysis workflow |
| Operations | Review queue, Investigations, Identified spots, Data readiness, Venue desk, Background work, Integrations and Audit trail |

Menu controls appear for food/cafe venues. Activity details do not show an irrelevant food-menu tab. Unknown/expired menu information remains unavailable; no placeholder price is promoted as real. Real venue suggestions still require the user's explicit approval. The redesign does not copy FavHiker's social network, public awards or other unconfirmed product categories.

## Checks and artifacts

- [x] Review the six primary screens before changes at desktop and phone widths.
- [x] Strict TypeScript and production build after changes.
- [x] New checks for menu keyboard navigation, focus restoration, mobile menu focus trap/Escape, retry recovery and taste shortcuts.
- [x] Responsive geometry matrix at 360, 600, 768, 900, 1024 and 1440 CSS pixels across Discover, Places, Taste, Sources and Operations.
- [x] Existing core journeys, private diary/visit learning and automated accessibility checks passed in the first complete redesign run: 26 passed, two viewport-specific skips.
- [x] Final expanded browser run after the compact-menu/selected-state adjustments: **30 passed**, two intentional viewport-specific skips, in 1.7 minutes. Includes core, guided research, product parity, accessibility, PWA and new UI checks.
- [x] Actual local operator regression run: **12 passed in 37.3 seconds**. Mutations were intercepted; no fixture labels/approvals entered the research DB.
- [x] Actual local app still runs in local mode; stopped only the separate demo review API/worker. Local health `ok`; updated UI observed at port 8000, English UI, 1440px document/viewport width.

Screenshots and structured geometry/page-error results are in ignored `data/ui-redesign/before/` and `data/ui-redesign/after/`. These contain labelled fictional demo venues, not approved real inventory. Reusable capture tool: `web/scripts/ui-review.mjs`, restricted to a separate demo instance (default port 8001). Run from `web/` with `node scripts/ui-review.mjs after` while that isolated instance serves the production build. The script creates only isolated demo sessions/plans; it cannot run against the actual local operator instance.

Browser checks use Chromium desktop/mobile emulation. They are not proof of physical-device behavior, all browser engines, a complete assistive-technology audit or real-world recommendation accuracy. No backend feature/connector/model completion is inferred from visual polish. Real data approval and matched outing evaluation remain pending.

The expanded run initially found the separate demo worker was missing; it was started with discovery/browser collection disabled. The existing source-result assertion now allows the page's documented 15-second polling interval rather than requiring completion inside five seconds. The final run passed with that worker present. Other corrected issues included a route-location variable shadowing the browser location during strict compilation, legacy mobile card sizing and dialog focus restoration. Failed attempts were not counted as passes. Backend code was unchanged in this UI task; the earlier 202-test backend result is retained as prior evidence, not presented as a new run.
