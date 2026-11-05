> Later 5 November update: [INVENTORY_COLLECTION.md](INVENTORY_COLLECTION.md) records the completed 15-source run, all-source batching, identified-spots inventory, and current eight-frame/thirty-browser-visit configuration. The three-reel evidence below remains historical.

# Direct local Instagram collection

Updated 5 November 2026. This extends the local research workflow; it does not establish exhaustive Instagram coverage or recommendation accuracy.

## What is implemented

The agent discovers public Instagram permalinks through its existing public-search frontier. A clean local Chromium process then opens each selected reel. It reads publicly delivered, rendered-page evidence for that exact post. No supplied example URLs, API token, paid data provider, account login or imported browser session was used in the recorded live batch.

1. **Discover:** choose a Coimbatore topic, search, deduplicate and save source leads. Search snippets remain leads, not captions.
2. **Collect:** try public HTML metadata, then the optional direct browser. Match embedded page records to the exact post shortcode; exclude recommended posts. Read the caption, publisher, available integer engagement counts and loaded visible comments. Do not store commenter account metadata.
3. **Retrieve media:** use only a video reference delivered for the target post and accepted by the existing CDN/network/size checks. If its clear DASH manifest exposes a separate audio track, download and join it locally with ffmpeg. Record byte count, SHA-256, collection method and time. An inaccessible track leaves a visible gap.
4. **Analyse locally:** Qwen3-VL instruct handles caption/comment interpretation and up to four video frames spread across the clip. Faster-whisper transcribes available audio and records machine-detected language and timed segments. English output is required. Sampled frames are not exhaustive frame-by-frame analysis; speech language detection is not a transcription accuracy score.
5. **Check evidence:** reject unsupported modality attributions, invalid structures, unknown placeholder venue names and descriptive non-prices. Commenter mentions do not generate venue candidates. Preserve model observations separately from verified facts. Exact location, current prices and hours require independent evidence and review.
6. **Store/review:** retain sources, processing results, receipts and gaps in the private local investigation. Raw media and signed download URLs are removed after verification/cancellation. Source text, comment text and machine transcripts expire after 24 hours. Existing export/erasure includes the source records. Local review corrections are retrieved into later investigations; no model weights are trained by this process.

## Configuration and operation

Run `scripts/setup-local.ps1` once to install locked Python dependencies, Chromium and the selected local models. Ollama must be installed/running. The current ignored local `.env` includes:

```dotenv
APP_MODE=local
INSTAGRAM_BROWSER_ENABLED=true
INSTAGRAM_PROVIDER=disabled
BROWSER_DAILY_LIMIT=12
BROWSER_MAX_COMMENTS=30
BROWSER_TIMEOUT_SECONDS=35
```

The provider setting controls the optional Meta/Apify connector independently from the browser switch. `.env.example` leaves the browser disabled until explicitly enabled. Meta/Apify remain alternative collection paths when configured, not prerequisites for the demonstrated public-page route.

Use `scripts/start.ps1` and open http://127.0.0.1:8000/admin. The Investigations panel reports the direct-browser switch separately from optional API connectors. Choose **Find the next examples for me**, or provide a topic such as **Coimbatore sushi Tamil food review**. The normal worker performs the stages. **Evidence** displays collection reports, media receipts, specialist observations and gaps. Draft candidates still require review before venue publication.

The worker operates while the computer and processes are running. It has the existing three-investigation daily budget and four-hour autonomous cooldown; the browser additionally has a durable twelve-visit daily budget. Each browser page permits at most 160 allowlisted requests, with public-IP checks and a bounded timeout. Login/challenge/rate-limit failures remain explicit. A challenge or HTTP 429 sets a one-hour collection cooldown. No account prompts or challenges are solved. A signup panel that coexists with publicly readable content does not itself mean authentication occurred.

## Recorded real test

Investigation: `e4f4578d-3999-4450-9c7b-c4c372d00a22`.
Query: `Coimbatore sushi Tamil food review`. The app selected the URLs itself.

| Instagram shortcode | Loaded comments | Video downloaded | Separate audio joined | Media bytes | SHA-256 |
|---|---:|---|---|---:|---|
| `Db3HJGTMKIN` | 11 | Yes | No; source reported no audio | 3,978,975 | `54d3ef9efaf7fc25670b27542ff918c6b6de6d686d3baf139973a3af9f2d5806` |
| `CelhYMUJ41l` | 12 | Yes | Yes | 3,994,498 | `c7a3c0e55cb59845e5427d80ebeb84d9877c5e421d0e3cba5cd9f7ab4534dc9f` |
| `DaAyXh-p1ta` | 9 | Yes | Yes | 3,701,587 | `026e8df19e31fa6ae15c1ffe469537f8abf6b727e9932465b6606444bfaedc90` |

After the text-model fixes, all three caption passes, all three comment passes and all three video passes have stored `observations_only` results. The case remains `review` with three exact-branch confirmation gaps and zero eligible venues. One audio track yielded a machine transcript detected as Tamil; the other yielded no speech segments. Neither is a manually labelled speech-quality evaluation.

These are **32 loaded comments**, not a complete comments archive. Further comment pages and replies are not fetched. Missing or hidden counts are unknown, never zero. Instagram dislikes are not invented. Public-page success may vary by post, network, region and time.

The initial live pass exposed text-model output truncation and invalid evidence structures. A diagnostic reproduced calendar timestamps in a clip-timestamp field. The fix constrains text timestamps to null, bounds output fields, and applies a larger but bounded output budget. Further checks remove descriptive text from price fields, remove commenter mentions from candidate discovery, and distinguish different emoji comments. Earlier failed text-analysis results are preserved in an audit entry when repaired. None of these checks establishes factual model accuracy.

## Automated verification procedure

- Parser fixtures include the target and an unrelated recommended post; assert that captions, comments and media are associated only with the target.
- Actual headless Chromium renders a local JavaScript fixture with all network access blocked; assert the snapshot reader sees rendered text and embedded JSON.
- Verify unsupported URLs, media hosts, challenge cooldown, durable daily budget and demo-mode disabling.
- Generate synthetic video and audio separately, join locally, and check that ffmpeg detects both streams.
- Check source receipts, private media exclusion from API/export, transcript persistence, retention deletion and audio-gap reporting.
- Check cancelled local jobs stop before inference and local inference renews the job lease without charging external-provider quota.
- Run backend regression tests and the web production build; run local desktop/mobile UI and accessibility checks against the restored local app. UI correction mutations use fixtures so they do not teach the real agent fictional feedback.

Current check counts and final runtime evidence are in [VERIFICATION.md](VERIFICATION.md).

## Remaining work and honest completion levels

- **Implemented and live exercised:** direct public-page collection of the three sampled real reels, loaded comments and downloadable media; local interpretation pipeline.
- **Not established:** exhaustive hashtags/creators/city coverage, every comment/reply, durable anonymous access, reliable OCR/location matching, or representative multilingual accuracy.
- **Needs human evaluation:** compare transcripts, sampled visual observations and candidate locations with the actual sources; record corrections and an independently labelled held-out set.
- **Before invited testers:** independently verify Coimbatore branches and current essential venue facts, evaluate freshness and recommendation quality, and pass the existing release gates. No venue from these reels is automatically published.
- **Later:** owned-model training and production hosting/restore evaluation. The current models are locally running third-party open weights.

Implementation: `backend/app/browser_sources.py`, `browser_media.py`, `research.py`, `local_models.py`, `analysts.py`. Playwright's [network documentation](https://playwright.dev/docs/network) and [browser-context API](https://playwright.dev/docs/api/class-browsercontext) describe the underlying browser controls.
