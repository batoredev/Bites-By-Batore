# Operations and launch gates

## The continuing loop

1. Discover through configured web/YouTube/Places sources. A discovery result is
   a lead, not a published fact. Review exact venue and branch identity.
2. Analyze supplied media and available source context. Keep unknown location,
   prices, sponsorship and translation ambiguity explicit.
3. Record source evidence. Confirm provenance and distinguish copied material
   from independent corroboration. Use the review queue for unusual changes.
4. Schedule regular venue checks (default 24 hours), hourly checks for places in
   saved upcoming plans, and request-time status/opening/routing checks.
5. Apply accepted changes, increment venue revisions and recheck affected plans.
6. Watch failed jobs, queue delay, source access, expired facts and coverage. New
   discovery has reserved priority above routine refresh; interactive analysis and
   upcoming plans take precedence. This is a bounded initial workload, not a
   guarantee that an overwhelmed queue stays current.

The worker schedules once per minute and polls jobs every five seconds by default.
Approved partners can also push signed updates immediately through the
[merchant ingestion endpoint](MERCHANT_UPDATES.md). No real partner is connected yet.
A database lease prevents two workers claiming the same available job. Expired
leases can be recovered. Failures retry with exponential backoff, at most three
attempts by default, then need operator attention. Missing credentials do not
advance verification timestamps. A venue is never closed merely because it was
absent from a search result.

Uploaded bytes expire on completion/final failure or after one day. Search
previews expire after a day. Keep private DB backups secure and define the final
production retention policy with the actual source agreements.

## Admin workflow

- Add a venue with its own-source name/address/coordinates and optional Google ID.
- Edit planning details: visit/wait time, fees, group capacity, age/child suitability,
  screening times, external booking URL and exact-branch confirmation.
- Add price per person, weekly hours and closed status with traceable evidence.
  Monday is day 0; hours are minute ranges (10:00–22:00 = `[600,1320]`). Overnight
  ranges can cross midnight. Unusual claims stay in review.
- When essential current facts and branch identity are established, publish. A
  confirmed pending branch can auto-publish after ordinary authoritative updates.
- Pausing a venue removes it from future candidate selection. Changed revisions
  mark saved plans for a recheck.

## Before customers

Define a launch area and category coverage target. Verify a representative set
covering different budgets, neighbourhoods, vegetarian needs, access requirements
and group sizes. Inspect every published branch's essential facts and source dates.
Do not claim a complete city database merely because a list of names was imported.

Release only after:

- Live auth works for two separate users and a server-approved admin; one user
  cannot read another's plans, visits or submissions.
- Database migration, backup and restore are exercised on a staging PostgreSQL DB.
- Real Places details and Routes matrix work for launch geography; failures and
  partial matrix errors produce honest exclusions.
- A permitted Tamil video, another language video, ambiguous signage, a misleading
  caption and conflicting comments are assessed against human-labelled evidence.
- A known venue/branch mismatch is caught; no model-inferred price is marked verified.
- Merchant hours, total price/fees, capacity and cinema sessions are current.
- Providers, actual bills, API quotas, worker latency and operational staffing
  support the intended refresh frequency. A call cap is not a money cap.
- HTTPS, origins, OAuth/email redirects, uptime monitoring and failure alerting are
  active in the real deployment. Test outage recovery and rejected credentials.
- The user completes a plan and actual outing, then confirms whether the suggestion
  met their expectation. Measure wrong-place, wrong-hours, price-error and useful
  recommendation rates rather than promising perfection.

## Backup and restore

For local SQLite: from `backend/`, run `uv run python -m app.manage backup-demo`.
It uses SQLite's online backup API, including committed WAL data. To restore, stop
API/worker, retain the current database, and restore a tested snapshot to the
configured database location. Never copy just the main SQLite file while writes
are running. Do not remove unrelated files.

For PostgreSQL: use the managed provider's backups/PITR or an encrypted `pg_dump`
with a tested restore into a separate staging database. Confirm migration version,
row counts, representative private records, RLS and worker resumption before a
cutover. Container volumes alone are not backups. Deployment and restore have
not been performed against the user's Supabase account.

## Provider smoke checks after keys arrive

Use a dedicated staging account and small explicit provider budgets. Confirm:

1. Email and Google login, logout, expired-token rejection and admin allowlist.
2. Exact Google place lookup and fresh dated opening windows for known venues.
3. Route matrix for walking/driving with at least one unavailable element.
4. Brave search result pointers and YouTube search plus enabled/disabled comments.
5. Gemini structured output for short permitted multilingual media; no video
   analyzed flag when only text was supplied; no prompt instructions from content.
6. Candidate branch matching and human review; no automatic price inference.
7. Worker timeout/retry/dead-letter behaviour without timestamp fabrication.

Do not automatically run these paid/network tests simply because keys exist.
The local build/test path uses fixtures and mocked provider contracts.
