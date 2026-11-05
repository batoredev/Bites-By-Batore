> Current internal research uses local SQLite, Ollama and faster-whisper. Gemini and Supabase keys are not required in local mode. See [LOCAL_RESEARCH.md](LOCAL_RESEARCH.md). Meta/Apify access is still needed to verify full Instagram video/comments when public pages do not expose them. The cloud setup below applies to a later live deployment.

# Integrations and source constraints

Provider selection is confirmed. Values belong in `.env`, never this document or
logs. See KEYS.md for the exact variables and SETUP.md for the live switch.

| Capability | Candidate | Needed later | Behaviour without configuration |
| --- | --- | --- | --- |
| Database/auth | Supabase/Postgres | Project URL, public client key, server-only DB connection; Google OAuth setup | Local labelled demo persistence/auth |
| Video/text understanding | Gemini, replaceable adapter | Server-side model API key and selected model IDs | Demo analysis only; live analysis unavailable |
| Venue search/details | Google Places | Restricted server API key, enabled service, billing/project setup | Demo venue data only; live discovery unavailable |
| Travel estimates | Google Routes | Restricted server key, enabled service | Labelled demo estimates; no pretend live routes |
| General web discovery | Brave Search | Search subscription key | Search integration unavailable |
| YouTube discovery | YouTube Data API | Key and permitted channel/source setup | Discovery unavailable |
| Instagram inputs | Supplied permitted video/text and source links | Approved connector needed for broader access | No automatic arbitrary-reel download; text/media path remains available |
| Movie sessions/availability | Cinema or ticketing provider | Partner/feed access if available | No invented showtimes or seat availability |
| Activity pricing/availability | Venue/booking partner | Provider account/feed access where available | Evidence-backed estimates only, unavailable slots labelled |
| Background operation | Durable worker/scheduler | Hosting runtime and queue/database settings | Local worker/scheduler commands |
| Maps display | External Google Maps links | No separate browser Maps key | No fictional demo directions |
| Email delivery | Auth/transactional provider | Email setup for production | Demo flow only |

An API key alone may not unlock a platform feature: account permissions, partner
agreements, regional availability, and application review are separate dependencies.

No billing activation, paid calls, public deployment, bookings, or messages will be
performed simply because a placeholder exists. User-authorised local build work
continues with deterministic fixtures and provider contract tests.

Primary documentation checked during design/build:

- [Google Places policies](https://developers.google.com/maps/documentation/places/web-service/policies): distinguish permanently stored identifiers from restricted place content. Do not mirror Google into a permanent owned dataset.
- [Places resource](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places): use dated current opening windows, operating status and explicit field masks. Returned reviews are not the complete review corpus.
- [Routes matrix](https://developers.google.com/maps/documentation/routes/compute_route_matrix): check per-element errors; one missing route is not a zero-minute trip.
- [Gemini video understanding](https://ai.google.dev/gemini-api/docs/video-understanding): configured multimodal media analysis; model/access availability must be tested in the actual account.
- [Supabase Auth](https://supabase.com/docs/reference/javascript/auth-getuser): server validation of live access tokens, not trust in client-stored identity fields.
- [Meta Instagram API](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api): account/permission limits differ from the Instagram consumer app. Universal reel/comment access is not assumed.
- [YouTube notifications](https://developers.google.com/youtube/data/guides/push_notifications): possible later channel push integration. Current implemented discovery is scheduled polling; no public webhook subscription has been registered.

Worker refresh success records a successful provider check, not re-verification of
every stored price, dish, accessibility fact or ticket slot. Critical owned facts
still need their own accepted current sources. All live integrations remain
unverified against the user's accounts until credentials and smoke checks exist.
