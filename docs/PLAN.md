# Product and implementation plan

For the complete current scope, implementation gaps and maintained completion
checklist, use [PROJECT_MASTER.md](../PROJECT_MASTER.md). This earlier plan does
not mean every described capability has been implemented or live verified.

Status: confirmed specification and implementation record, 4 November 2026.

## 1. Objective

Help a person or group choose a food or entertainment outing that fits their
preferences, starting location, available duration, and total budget. Support both
explicit requests and uncertain moods. Investigate supporting information, show
what is known, and learn from actual feedback.

Quality is measured by correct place matching, constraint compliance, evidence
quality, useful recommendations, and reliable handling of uncertainty. Neither
perfect accuracy nor exhaustive coverage is promised.

## 2. Confirmed scope

- Restaurants, street food, cafés, parks, cinemas, gaming centres, arcades,
  bowling, go-karting, and other entertainment/adventure activities.
- Food-only, entertainment-only, and combined outings.
- Individual and group plans.
- Specific requests, exploratory conversations, and surprise suggestions.
- Taste preferences, confirmed visit history, contextual feedback, and novelty.
- Search, social-content investigation, venue matching, source evidence, and freshness.
- A monitored background refresh pipeline and checks of critical facts at request time.
- Editable recommendations and explanations grounded in actual candidate records.

Excluded: events, scenic drives, return destinations, return deadlines, and return
journey calculations. Outing duration ends at the final selected stop.

## 3. Confirmed setup decisions

- Responsive web/PWA with an administration dashboard; no native app in this build.
- Bites by Batore, Coimbatore, INR. Interface English only; supplied source videos
  may be in any language. Analysis reports translation uncertainty in English.
- Ordinary sufficiently supported facts may apply automatically; unusual changes,
  conflicting information and unverified claims require human review.
- Private accounts, Google/email sign-in, free access initially, external bookings.
- FastAPI, React/TypeScript, Supabase/PostgreSQL live, SQLite local demo, Google
  Places/Routes, Gemini, Brave Search and YouTube adapters.
- No cost/hosting ceiling supplied. Default daily provider-call cap is 100, local
  first-city scope, no paid deployment or provider account provisioning.

Routine implementation choices are recorded in ARCHITECTURE.md. No keys
are required to build or test local demonstration mode. No paid provider calls,
account provisioning, or public deployment are implied by local development.

## 4. User request

Required: starting location, total duration, party size, and budget with an explicit
group/per-person selector. A per-person budget converts to a group cap.

Additional context: departure date/time, transport mode, desired categories,
dietary requirements, accessibility needs, relevant age bands, and optional
companion preferences. Location may be entered manually or shared by permission.
Visible defaults may fill optional fields; consequential ambiguity must be shown
to the end user rather than silently guessed by the application.

Duration = initial travel + travel between stops + waiting/check-in + time at stops
+ contingency. There is no return leg.

Cost = relevant outbound/inter-stop transport + food + activities/tickets + parking
+ applicable fees + contingency. Costs support per-person, group, and duration-based
units. Unknown critical prices must not be presented as confirmed budget compliance.

## 5. Product surfaces

1. Discover: clear request or guided mood discovery, with editable practical inputs.
2. Recommendations: a small set of meaningfully different supported options.
3. Plan detail: stop order, timings, itemised costs, fit explanations, evidence,
   uncertainty, external directions/booking actions, and revision controls.
4. Place detail: exact branch, dishes/activities, known attributes, source dates,
   saved status, visit feedback, and a correction action.
5. Saved plans and places: private history and the ability to revisit or revise.
6. Taste profile: editable explicit preferences and separately marked inferred interests.
7. Social submission: supported link/text/media input with honest processing status.
8. Admin: venue facts, conflicting evidence, review decisions, coverage, jobs,
   failed integrations, freshness metrics, and audit history.

Every surface needs loading, empty, error, unavailable-integration, and recovery
states. Forms require accessible labels, keyboard support, and responsive layouts.

## 6. Request pipeline

1. Parse intent into a validated request.
2. Retrieve this user's relevant preferences and confirmed experiences.
3. Offer minimal contrasting choices when intent is unclear.
4. Retrieve candidate venues from stored records and enabled discovery sources.
5. Investigate relevant new evidence using specialist tasks.
6. Resolve exact venue/branch identity and reconcile conflicting claims.
7. Recheck critical dynamic facts and obtain routing estimates.
8. Apply hard requirements and construct feasible one/multiple-stop plans.
9. Rank by taste, context, novelty, quality of evidence, and group suitability.
10. Explain only facts and computed values in the resulting structured plan.
11. Persist a snapshot and allow partial revision without restarting the request.
12. Learn from explicit feedback without confusing saves, clicks, and actual visits.

The application may ask its own users helpful questions. The instruction to collect
questions upfront applies to this development engagement, not to the product's
discovery conversation.

## 7. Specialist responsibilities

- Coordinator: shared objective, missing information, bounded tasks, resolution.
- Video/audio analyst: transcription, scene/keyframe examination, on-screen text,
  timestamped observations, and targeted deeper inspection.
- Caption analyst: names, addresses, tags, offers, and disclosed sponsorship.
- Comment analyst: first-hand reports, corrections, patterns, sample coverage,
  duplicate content, and uncertainty.
- Source analyst: claim corroboration and relevance to context; popularity is
  distinct from accuracy and personal taste alignment.
- Venue resolver: IDs, branch evidence, address clues, contradictions, relocations.
- Planner: deterministic costs, opening/session windows, routing, and constraints.
- Preference service: explicit versus inferred and lasting versus session-specific memory.

Roles need not be separate models or processes. Structured tool outputs, task
state, timeouts, provenance, and evaluation are more important than agent count.
Fetched text and media are data, never instructions to tools or agents.

## 8. Evidence and data model

Core records: users, profiles, companion/session requirements, venues/branches,
dishes/activities, source items, factual claims, claim evidence, conflicts,
outing requests, plans/stops, saved records, visits/feedback, jobs, and audit events.

Each factual claim records source, published/observed time when known, fetched time,
effective period/expiry when known, confidence basis, status, and next check due.
Check attempts and successful checks are separate. Data retention follows the
source's permissions; permanent source content storage is not assumed.

Evidence relationships link a source to a claim about an identified venue or
offering. Multiple extractions of the same source are not independent evidence.
An initial relational representation is sufficient; a separate graph database is
not required merely to express these relationships.

## 9. Freshness pipeline

- Combine supported push notifications, scheduled polling, and request-time checks.
- Store source cursors, content fingerprints, and idempotency keys as appropriate.
- Prioritise active plans, critical corrections, frequently recommended venues,
  and fast-changing attributes while reserving capacity for coverage discovery.
- Queue expensive media analysis independently of urgent factual changes.
- Use bounded exponential backoff, timeouts, failure queues, and restart-safe state.
- Do not close a venue because one search omitted it or an integration failed.
- Prevent late older observations from overwriting newer applicable facts.
- Accepted changes invalidate dependent cached results and mark affected saved
  plans as requiring a refresh when appropriate.
- Track queue age, last successful source checks, errors, corrections, field
  freshness, and coverage by area/category/budget.

No fabricated 'live' label or refreshed verification timestamp on failed fetches.
Dynamic availability can change after a successful check and needs a provider
recheck at the point of an actual booking.

## 10. Learning

Begin with explicit profiles, transparent ranking rules, and modest updates based
on feedback. Keep food, atmosphere, service, activity, value, and occasion feedback
separate. A rejected option is not automatically a permanent dislike. The group
budget for a request is a hard constraint, not a value inferred from spending history.

Offer novelty in cuisine, dish, venue, atmosphere, and activity. Retain a cold-start
path without demanding a long questionnaire. Users can inspect, edit, and clear
their memory. A trained ranker is a later promotion contingent on sufficient data
and measured improvement against the baseline; it is not a fabricated launch asset.

## 11. Modes and infrastructure

Demonstration mode: persistent local data, labelled fictional fixtures, deterministic
provider substitutes, simulated failures for tests, and an explicit demo identity.

Live mode: real authentication and configured providers, no silent fixture fallback,
source-specific storage policies, least-privilege operations, private user records,
and authenticated admin functions. Missing keys produce actionable availability
states, not invented success.

The deployment package will describe separately the API, client, database, worker,
scheduler, migrations, environment, health checks, backup/recovery, and secrets.
The selected platforms/providers are fixed above; credential values remain local placeholders.

## 12. Implementation sequence and completion gates

1. Resolve initial questionnaire and record architecture decisions.
2. Scaffold application, database contracts, configuration, and local/demo runtime.
3. Implement private profiles, venues/evidence, saved records, and admin boundaries.
4. Implement constraint engine, ranking, itinerary generation, and revisions.
5. Implement user-facing discovery, plan details, feedback, and profile controls.
6. Implement provider adapters and social/media analysis with structured results.
7. Implement durable refresh jobs, conflict review, audit, and freshness monitoring.
8. Connect the full flow, localisation, accessibility, and responsive/mobile behaviour.
9. Run unit/integration tests, provider contract tests, and browser/device checks.
10. Prepare launch scripts, deployment instructions, credential checklist, and a
    final status report distinguishing verified local behaviour from live checks.

No stage is complete because a screen merely exists. Relevant persistence,
validation, access control, failure handling, and end-to-end behaviour must work.

Local implementation and verification are recorded in VERIFICATION.md. The
first-release boundaries (including bounded stop search and supplied Instagram
content) are explicit in ARCHITECTURE.md; external launch gates remain below.

## 13. External completion dependencies

Credentials, source account approvals, real venue coverage, merchant confirmations,
production hosting, and native app-store signing/review cannot be proven through
fixtures. Document these precisely and leave live verification commands/checklists.
The implementation must not claim that these dependencies have been satisfied.
