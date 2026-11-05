# Acceptance and verification plan

These are requirements to test, not claims of completed verification.
See VERIFICATION.md for the executed checks and remaining external launch gates.

## Core journeys

- Specific cuisine request produces relevant supported options.
- 'Something different' works with a new user and an existing preference history.
- Food-only, activity-only, and combined plans work.
- Group totals include correct per-person/shared pricing and applicable travel.
- Duration covers the first travel leg through the final stop; no return leg exists.
- Open-at-arrival is insufficient when a venue closes before the activity finishes.
- Movie planning checks showtime, runtime, and applicable availability status.
- A request with no supported feasible option returns an honest explanation.
- Changing one stop or a constraint recomputes affected costs/timings.
- Saved plans persist across reloads and belong to the correct account.
- Feedback updates the relevant preferences; session mood and hard budget stay separate.
- Users can correct and clear stored preferences and history.

## Evidence and freshness

- Duplicate posts/jobs do not multiply independent evidence or overwrite records twice.
- Similar venue names do not silently merge branches.
- Old content cannot overwrite newer applicable information on arrival order alone.
- Conflicting prices retain their source/context and enter resolution.
- An integration timeout does not advance successful-check timestamps.
- Unsupported links/absent APIs report unavailable access without fabricated analysis.
- Critical stale facts trigger refresh or a provisional result.
- Accepted fact changes invalidate affected recommendations.
- Partial source failure does not crash unrelated refresh jobs.
- Jobs survive worker restart; retry exhaustion is inspectable.

## Privacy and security

- Cross-user requests cannot read/write another user's private plans or preferences.
- Admin endpoints require the admin role, including direct API calls.
- Demo identities and fixture data cannot silently appear in live mode.
- Secrets remain server-side and are redacted from logs.
- Arbitrary supplied URLs cannot access local/private network services.
- Third-party content cannot issue tool instructions or change agent permissions.
- Inputs, file types/sizes, timeouts, and costly request paths have limits.

## UI and operations

- Keyboard operation, readable contrast, clear labels, and mobile layouts.
- Explicit loading, empty, failed, partial, and unavailable states.
- No dead controls or fake completed background jobs.
- API/frontend builds and relevant type/lint checks pass.
- Browser checks cover request -> plan -> save -> reload -> feedback and admin review.
- Web/PWA is the confirmed platform; native builds are outside this release.
- Fresh clone setup, environment templates, database migrations, and worker startup
  are documented and exercised locally where tools permit.
- Provider-specific live smoke checks are listed for execution after key setup.

## Report format

For each verification: command or flow, result, evidence location, and limitations.
Do not reuse historical test counts from the reference project as new evidence.
