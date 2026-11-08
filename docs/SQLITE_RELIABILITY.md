# Local collection contention repair — 8 November 2026

The user authorized continuing the database fill and finishing the remaining work.
The collector stays local, with initial daily count caps removed, existing spending
reservations/source cooldowns and every factual/location approval gate retained.

## Cause and changes

The status audit found SQLite `database is locked` exceptions in API request
counting, worker claiming, lease renewal and job-completion writes. SQLite already
used WAL and a 30-second busy timeout. The principal code-level bottleneck was
`reconcile_spots`: it held `BEGIN IMMEDIATE` while repeatedly comparing the whole
inventory, including Unicode name normalization and expensive fuzzy comparisons.
Each investigation verification stage calls that cleanup. A limited read-only
50×679 comparison sample took 4.438s for the old fuzzy pass alone; its full-inventory
60s extrapolation is an estimate, **not a measured old full cleanup duration**.

Changes:

- Transaction-local name/signature/character-count caches and conservative alias,
  name, Maps-ID and source indexes reduce unnecessary comparisons. Canonical
  branch predicates remain authoritative; directional fuzzy-match thresholds,
  row order, merge-target alias reindexing, ownership, held originals and evidence
  attribution stay intact. The serialized identity transaction is retained;
  there is no unlocked stale-snapshot writeback.
- SQLite lock errors receive a distinct `database_busy` wait reason. A busy claim
  executes no source work. Busy execution/completion writes keep committed source
  checkpoints and queue a retry without consuming a normal failure attempt.
  A failed recovery write leaves the existing lease recoverable. Completion
  recovery checks the durable state/attempt before updating it; deleted/cancelled
  or subsequently claimed work is not overwritten by that recovery path.
- API lock conflicts return sanitized HTTP 503 with `Retry-After: 2`. The web app
  retries only reads, twice at most, honoring short Retry-After values and aborts.
  Mutations are not repeated automatically; an earlier write may have committed.
- The Windows launcher now uses a per-workspace start mutex, a real loopback TCP
  probe, exact workspace Python/module ownership, process-exit checks and compatible
  PID records. Repeated starts reuse the existing API/worker instead of trusting
  a missed CIM port result or another listener's health response.

No schema migration, source approval, new trained model, provider activation,
model precision change or daily request-cap restoration was introduced.

## Verification

- **292 backend tests passed in 37.24s**, required Ruff passed. New regressions
  check exhaustive-reference reconciliation parity, directional fuzzy equivalence,
  comparison complexity, lock-error classification, transient claim/execution/
  completion recovery, saved checkpoints and sanitized API retry responses.
- Strict production web build passed; **12 isolated desktop/mobile browser checks
  passed in 17.9s**. They include GET recovery and no automatic POST repetition,
  initial-mode usage, attribution/coverage and known-location controls. Fixtures
  stayed in a separate test DB or intercepted responses.
- A separate copy of the **811-original snapshot** completed two full cleanup/
  commit passes in **3.7926s / 3.6023s**, with zero merge/hold/evidence changes and
  SQLite `quick_check=ok`. A concurrent probe write completed after 7.425s across
  the back-to-back passes, with zero probe errors. It is a limited contention
  rehearsal; it does not establish a universal maximum lock duration.
- Live restart: consistent pre-change backup
  `data/backups/batore-20261108T093634Z.db`; four owned jobs interrupted/stale at the
  controlled stop were requeued after checking that the workspace worker was
  stopped and holding the launcher mutex. Source checkpoints and request/spending
  counters were preserved; only the interrupted claim attempt was refunded.
- Re-running the actual launcher reused API **23848** and worker **18256** (Python
  redirector PIDs), with stop-compatible parent/child records unchanged.
- Live API probe: duplicate cleanup HTTP 200 in **7.063s**, zero data changes;
  all **24 concurrent reads HTTP 200**, longest 7.435s. No new lock errors appeared
  in the restarted API/worker logs at this check. This is a short smoke, not proof
  of sustained error-free operation or a response-time SLA.
- 09:43 UTC checkpoint: **692 active drafts / 111 held / 12 merged**, 168 research
  sources, zero real venues/accepted claims. API/worker running; initial request/
  browser/investigation count caps still unlimited. Counts will keep changing.
- 09:45 UTC follow-up: schema-7 integrity/structural audit healthy, unchanged 692/
  111/12 draft states and 168 sources, worker heartbeat 0.38s old. No new error/
  traceback/lock matches in either restarted log at final check. Consistent
  post-change backup created: `data/backups/batore-20261108T094543Z.db`.

Evidence in `data/reliability/`: archived old logs, `reconcile-rehearsal.json`,
separate rehearsal DB, `restart-recovery.json`, `launcher-live.json` and
`live-probe.json`. Offline snapshots/backups need separate erasure when deleting
offline copies of private records.

## Still open

Monitor sustained collection for recurring contention and expired leases, especially
as the inventory grows. Current tests/smokes demonstrate the repair at the measured
scope, not arbitrary city-scale capacity. Database structural health and successful
HTTP responses do not verify venue identity, menus/hours/vibes or human accuracy.
Complete the first-city evidence work and obtain explicit location approvals before
recommendations; invited testing/public release remains gated.
