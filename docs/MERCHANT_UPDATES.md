# Fast merchant updates

The signed `POST /api/ingest/merchant` endpoint gives an approved data partner a
push path for price, hours and other supported factual changes. It uses the same
evidence policy as the admin desk: ordinary authoritative updates can apply;
unusual prices, closures and access changes require human review.

Set a server-only `MERCHANT_WEBHOOK_SECRET` of at least 32 random characters and
share it only with an approved integration. The endpoint is disabled without it.
This is a trusted operator/partner integration, not a public merchant self-signup
system. If independent merchant accounts are introduced, provision per-merchant
keys and scope each one to its own venue IDs before exposing it to them.

Headers:

- `Content-Type: application/json`
- `X-Batore-Timestamp`: current Unix seconds (five-minute acceptance window).
- `X-Batore-Signature`: lowercase hex HMAC-SHA256 of `timestamp + "." + exact_raw_body`,
  using the webhook secret. Never log or put the secret into the body.

Body example (replace IDs, timestamps, URLs and values with real approved evidence):

```json
{
  "event_id": "merchant-menu-revision-001",
  "facts": [{
    "venue_id": "your-canonical-venue-id",
    "field": "price_per_person",
    "value": {"value": 490},
    "source_url": "https://merchant.example/menu",
    "source_type": "merchant",
    "source_group": "merchant.example",
    "observed_at": "2026-11-04T09:00:00+05:30",
    "expires_at": "2026-11-05T09:00:00+05:30"
  }]
}
```

The service validates up to 50 facts per event and records a persistent event ID.
Retry the identical event/body with a fresh signature timestamp after a transient
failure; accepted facts are deduplicated. A reused ID with changed content is
rejected. Concurrent processing uses a recoverable lease. Review-needed updates
queue a high-priority verification job. Successful application invalidates saved
plan revisions. This endpoint has contract tests; no external merchant has been
onboarded or sent a request as part of this build.
