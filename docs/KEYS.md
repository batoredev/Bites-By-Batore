> Current internal research uses local SQLite, Ollama and faster-whisper. Gemini and Supabase keys are not required in local mode. See [LOCAL_RESEARCH.md](LOCAL_RESEARCH.md). Direct public-browser collection retrieved videos and loaded comments without credentials in the recorded sample. Meta/Apify are optional alternative paths when public access is insufficient; neither is currently live verified. See [DIRECT_INSTAGRAM.md](DIRECT_INSTAGRAM.md). The cloud setup below applies to a later live deployment.

# Credential checklist — fill locally at the end

Update: [investigation activation guide](BUILD_UPDATE_2026-11-04.md). New variables:
`INSTAGRAM_PROVIDER`, `META_GRAPH_VERSION`, `APIFY_API_TOKEN`,
`APIFY_INSTAGRAM_TASK_ID`, `APIFY_MAX_CHARGE_USD`, `AUTONOMOUS_DISCOVERY`,
`RELEASE_STAGE`, `TEST_USER_IDS`, `MONTHLY_BUDGET_INR`, `PROVIDER_RESERVE_INR`,
`RESEARCH_MAX_SOURCES`, `RESEARCH_DAILY_LIMIT`, `MEDIA_MAX_SECONDS`,
`MEDIA_MAX_FRAMES`, optional `FFMPEG_BINARY` and `WEB_EVIDENCE_HOSTS`.
Both Instagram connector paths now exist; configuration and actual access still
need testing. Default live access is internal admins only. Keep real values local.

All entries are placeholders in `.env.example`. Demo mode works with them blank.
Never put secret values in web source or commit `.env`.

| Variable | Needed for | Source / notes |
|---|---|---|
| `DATABASE_URL` | Live persistence | Supabase PostgreSQL; `postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres?sslmode=require`. URL-encode password special characters. Backend owner role, not anon/authenticated. |
| `SUPABASE_URL` | Live account validation | Supabase project HTTPS URL. |
| `SUPABASE_PUBLISHABLE_KEY` | Email / Google login | Supabase public publishable or legacy anon key. Private tables use RLS with no direct client policies. |
| `ADMIN_USER_IDS` | Live administration | Comma-separated Supabase user UUIDs. Assign after accounts exist. Never rely on editable user metadata. |
| `GOOGLE_MAPS_API_KEY` | Places and Routes | Google Cloud key with Places API (New), Routes API, billing and server restrictions. |
| `GEMINI_API_KEY` | Multilingual video/text analysis | Google AI Studio key with access to the chosen model. |
| `GEMINI_MODEL` | Model selection | Now blank intentionally: choose a supported multimodal model in the actual account. The earlier `gemini-2.5-flash` placeholder is not an availability guarantee. No live model call has been verified. |
| `BRAVE_SEARCH_API_KEY` | Web discovery | Brave Search API subscription key. Results are leads, not verified facts. |
| `YOUTUBE_API_KEY` | Video discovery/metadata/comments | Google Cloud YouTube Data API v3 key and quota. Comments may be unavailable. |
| `MERCHANT_WEBHOOK_SECRET` | Optional fast merchant push | Generate at least 32 random characters and share only with an approved integration; see MERCHANT_UPDATES.md. |
| `WEB_ORIGIN` | CORS / deployment | Actual HTTPS app origin; development uses the configured local origin. |

Google sign-in also requires a Google OAuth client ID/secret configured in the
**Supabase dashboard**, plus callback and allowed redirect URLs. Production email
login needs working SMTP. Neither secret belongs in browser code. The API checks
the user's access token with Supabase Auth on every authenticated request.

Optional future source access:

- `META_ACCESS_TOKEN`, `META_INSTAGRAM_ACCOUNT_ID` and `META_GRAPH_VERSION` configure
  the implemented Meta connector when `INSTAGRAM_PROVIDER=meta`. Actual public-content
  permissions must be validated. Alternatively select `apify` with its tested saved-task
  ID/token. Neither path implies unrestricted or complete reel/comment access.
- Cinema/activities live inventory needs partner access. Current release supports
  admin-confirmed screenings and external booking links, not seats or payments.

No Redis key, vector database key, payment key, native app-store account or
Supabase service-role browser key is required. The queue is database-backed.
The taste baseline does not need a pretrained recommendation model.

Set provider-side billing limits alongside `MAX_PROVIDER_CALLS_PER_DAY`. The latter
limits calls, not currency: different provider operations have different costs.
