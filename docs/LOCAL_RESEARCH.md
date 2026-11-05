> Latest update: [INVENTORY_COLLECTION.md](INVENTORY_COLLECTION.md) supersedes the old total-source limit. Three is a batch size; all found sources are retained. Schema 5 adds identified spots and explicit per-location approval. Current local frame budget is eight and browser pacing is thirty visits/day.

# Local Instagram research

Updated 5 November 2026. This supersedes the earlier requirement for Supabase and hosted Gemini during internal research. Production deployment is a separate phase.

## Confirmed workflow

The operator supplies no example reels. The agent chooses Coimbatore food/entertainment topics and neighbourhoods, searches public sources, collects accessible evidence and stores an investigation. The operator reviews its findings, confirms the correct branch with independent evidence, corrects errors, and approves facts. Future investigations retrieve relevant corrections. Fictional demo venues never enter this database.

The first metadata-only runs saved six source records for four distinct links. The newer direct-browser batch independently discovered three reels and retrieved all three videos, three captions and 32 loaded comments. Two separate audio tracks were joined locally. This extends the earlier metadata-only result; see [DIRECT_INSTAGRAM.md](DIRECT_INSTAGRAM.md) for the live evidence and collection procedure. Search snippets, captions, video and comments remain separate evidence types. There are no verified published venues yet.

## Local configuration

The current ignored `.env` uses:

```dotenv
APP_MODE=local
DATABASE_URL=sqlite:///./data/local-research.db
ANALYSIS_PROVIDER=ollama
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3-vl:2b-instruct
WHISPER_MODEL=base
LOCAL_SEARCH_ENABLED=true
AUTONOMOUS_DISCOVERY=true
RESEARCH_MAX_SOURCES=3
RESEARCH_DAILY_LIMIT=3
MEDIA_MAX_FRAMES=4
INSTAGRAM_BROWSER_ENABLED=true
INSTAGRAM_PROVIDER=disabled
BROWSER_DAILY_LIMIT=12
BROWSER_MAX_COMMENTS=30
BROWSER_TIMEOUT_SECONDS=35
RELEASE_STAGE=internal
```

Local mode forces local inference even if the provider setting says Gemini. It requires SQLite and accepts loopback connections only. A persistent local operator session replaces cloud authentication. This is a single-operator research workstation; do not expose it as a multi-user deployment.

The existing `data/batore.db` demo database remains separate. A consistent snapshot was made under `data/backups/` before activation. Schema version 4 adds reversible research corrections; existing tables are retained.

Run `scripts/setup-local.ps1` to install locked Python dependencies, Chromium and the vision/speech models. Ollama must be installed and running. Then use `scripts/start.ps1`; stop the app and worker with `scripts/stop.ps1`. Setup does not rewrite existing secrets. For another machine, copy the settings above into its ignored `.env`.

Open http://127.0.0.1:8000/admin and choose **Investigations**. Use **Find the next examples for me** to start a topic without providing a link. Open an investigation to inspect the original source, collected metadata, specialist output and missing modalities. **Use extracted candidate** prefills a draft; it does not verify the branch. **Teach the agent a correction** records feedback; **Stop reusing this correction** revokes it.

## What runs where

| Component | Execution/storage | Current method |
| --- | --- | --- |
| Discovery | Local Python worker; internet searches | DDGS public search with bounded subprocess time; topic relevance filtering and broader-city fallback |
| Caption collection | Local HTTP client; internet source page | Anonymous public Instagram metadata; explicit errors for unavailable/redirected/limited pages |
| Direct public reel collection | Local clean Chromium; internet source page/CDN | Exact-post captions, loaded visible comments, video and optional separate audio; no login used |
| Alternative social access | Optional configured provider | Existing Meta and saved Apify task adapters; credentials still blank |
| Caption/comments interpretation | Local Ollama | Qwen3-VL 2B **instruct**, constrained English JSON; output remains observations |
| Video | Local ffmpeg and Ollama | Bounded sampled frames, with timestamps; requires retrievable video bytes |
| Speech | Local CPU | faster-whisper base multilingual model, int8, cached weights; automatic language detection |
| Feedback | Local SQLite | Private, scoped, revocable examples retrieved into later analysis |
| Jobs and evidence | Local SQLite | Durable specialist stages, results, errors and review records |
| Venue publication | Local database with review gates | Independent branch confirmation and accepted current essential facts |

The laptop has about 16 GB RAM and 4 GB NVIDIA VRAM. Jobs run serially. Models may partly use CPU and can be slow. The default `qwen3-vl:2b` tag used a thinking renderer and exhausted the response limit during testing; the explicit instruct variant is used instead. PyAV is pinned below 17 because PyAV 19 broke faster-whisper's audio decoder in the real smoke test.

Internet search/source collection and initial model downloads still need internet. Interpretation, feedback, databases and testing run locally; no cloud AI fallback occurs. Locally running third-party open weights are not our own trained model.

## Learning rules

Each correction records source ID, specialist, exact scope phrase, original error, corrected interpretation, reason, owner and time. Up to four active matching examples are supplied to future analysis. Matches are case-insensitive whole phrases in available source text/title, limited to the same owner and specialist. Examples expire from retrieval after 90 days. Analysis records the example IDs it used.

Corrections also contribute future discovery topics. They never automatically overwrite current prices, hours, addresses or venue truth. A correction may itself be wrong; it is reviewer guidance to check against the new source. Revocation stops future reuse but does not silently rewrite historical outputs. Export includes corrections; erasing research data deletes them. This is retrieval-based learning, not weight fine-tuning or measured model improvement. No user corrections have been supplied yet, so there is no honest claim of customer-trained accuracy.

The compact local model extracts candidate names, address clues, dishes/activities and raw price wording. It does not emit the broader hosted model's structured fact proposals. Essential venue facts still need the existing structured review flow. Duplicate candidates are collapsed and engagement counts are rejected as price claims. Unsupported modalities are rejected rather than relabelled.

## Autonomous operation and storage

The frontier covers seven topic groups across six Coimbatore neighbourhoods, plus reviewed correction scopes. It chooses the least recently investigated query. While the app and worker are running, the scheduler starts another investigation after a four-hour cooldown, subject to the daily limit and no active case. The operator must first open the local app to establish the persistent local account. A paused frontier starts no new cases; already-running cases must be cancelled separately. The worker cannot run when this computer is off or asleep; no Windows startup task has been installed.

Search results can contain stale, irrelevant or out-of-city material. Query relevance and publication gates limit their effect, but do not prove exhaustive coverage. Failed queries rotate and may be revisited; the agent does not hammer unavailable services. External calls retain the existing daily cap and paid-provider spending reservations. Free public collection/local inference do not reserve paid AI spending.

Source text/preview retention is currently 24 hours. Durable observations, provenance, fingerprints, review history and corrections remain. Video bytes are temporary and removed after verification/cancellation; ffmpeg temporary files are cleaned. Downloaded speech weights are in `data/models/`; Ollama manages its own model directory. Synthetic smoke media/results in `data/` are explicitly test artifacts, never database venues. A backup includes the SQLite evidence and learning records, not a portable copy of Ollama weights.

## Completion gates

- [x] Isolated real-data local mode, persistent local operator, no cloud auth requirement.
- [x] Self-selected discovery, public source collection, stored real examples and review UI.
- [x] Local model/speech dependencies installed; no hosted-AI fallback.
- [x] Correction persistence, retrieval, revocation, export and erasure covered by tests.
- [x] Desktop/mobile review and correction UI checks.
- [x] Direct public Instagram video and loaded-comment retrieval demonstrated on three agent-selected real reels.
- [ ] Representative collection/access coverage; complete comment retrieval is not implemented.
- [ ] Representative Tamil and other-language transcription/vision accuracy, manually labelled and measured.
- [ ] Advanced visual landmark/reference-image geolocation and exact-branch resolution evaluation.
- [ ] Human correction dataset sufficient for held-out quality evaluation or owned-model training.
- [ ] Verified Coimbatore inventory and current price/hours/closure coverage before invited testers.

Direct public browser access now works for the recorded sample, but it does not finish the full Instagram agent. Meta/Apify credentials are optional alternative paths; keep any configured secrets in their existing environment placeholders, not in chat. Google/Brave remain optional external verification adapters with their existing placeholders. Gemini is not needed for this local configuration.

## Primary references

- Ollama [chat API](https://docs.ollama.com/api/chat) for local JSON/image inference.
- Ollama [Qwen3-VL model library](https://ollama.com/library/qwen3-vl) for local model variants.
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) for multilingual local speech inference.
- [DDGS](https://github.com/deedy5/ddgs) for public search integration; availability is not guaranteed.
