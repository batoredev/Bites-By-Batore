"""Durable investigation coordinator and specialist stages.

Each stage has an inspectable task, each source retains its own observations.
Unknowns and failed modalities survive to the final review gate.
"""

from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from urllib.parse import urlparse
from sqlalchemy import select, delete
from .config import settings
from .db import (
    Investigation,
    ResearchTask,
    ResearchSource,
    Submission,
    Venue,
    Claim,
    Job,
    SourceAssessment,
    now,
)
from .providers import (
    DeferredCollection,
    Unavailable,
    web_search,
    youtube_discover,
    youtube_context,
    youtube_id,
    google_search,
    renew_job,
)
from .social import (
    canonical_url,
    instagram_discover,
    apify_start,
    apify_poll,
    collect_meta_comments,
    download_media,
)
from .analysts import analyze, comment_sample, evidence_fingerprint
from .media import extract_frames
from .web_evidence import read_official_page
from .resolver import normalized, source_track_record
from .recency import recency_key

ROLES = ["discovery", "collection", "caption", "comments", "video", "location", "reliability", "verification"]
TERMINAL = {
    "review",
    "complete",
    "complete_with_limits",
    "insufficient_evidence",
    "unavailable",
    "cancelled",
    "failed",
}


class PendingSource(Exception):
    """A remote async operation is still running; reschedule, do not busy wait."""

    def __init__(self, retry_seconds=20):
        self.retry_seconds = retry_seconds


def case_sources(db, case):
    rows = list(
        db.scalars(
            select(ResearchSource)
            .where(ResearchSource.case_id == case.id)
            .order_by(ResearchSource.created_at)
        )
    )
    return sorted(rows, key=lambda source: recency_key(source.content), reverse=True)


def creator_key(source):
    provider_id = str(source.content.get("creator_id") or "")[:100]
    if provider_id:
        return f"{source.platform}:id:{provider_id}"
    return f"{source.platform}:{source.creator.casefold()}" if source.creator else ""


def start_case(db, user_id, query, context=None, seed_sources=None):
    from .jobs import enqueue

    case = Investigation(user_id=user_id, query=query, context=context or {})
    db.add(case)
    db.flush()
    for ordinal, role in enumerate(ROLES):
        db.add(ResearchTask(case_id=case.id, role=role, ordinal=ordinal))
    for item in seed_sources or []:
        source_add(db, case, item)
    db.commit()
    enqueue(db, "investigation", {"case_id": case.id}, f"case:{case.id}:0", priority=90)
    return case


def source_add(db, case, item):
    url = item.get("url", "")
    platform = item.get("platform", "web")
    if platform in {"instagram", "youtube"}:
        try:
            url = canonical_url(url)
        except ValueError:
            return None
    existing = db.scalar(
        select(ResearchSource).where(ResearchSource.case_id == case.id, ResearchSource.canonical_url == url)
    )
    if existing:
        # Do not replace supplied content with a poorer search snippet.
        existing.content = {**item, **{k: v for k, v in existing.content.items() if v not in (None, "", [])}}
        return existing
    source = ResearchSource(
        case_id=case.id, canonical_url=url, platform=platform, creator=item.get("creator", ""), content=item
    )
    db.add(source)
    db.flush()
    return source


def discover_stage(db, case, task):
    cfg = settings()
    if task.result.get("search_complete"):
        return rank_discovery(db, case, task)
    if case.context.get("curated_leads"):
        return {
            "source_count": len(case_sources(db, case)),
            "basis": "Manually researched official-source leads; no automatic verification",
        }
    submission_id = case.context.get("submission_id")
    if submission_id:
        sub = db.get(Submission, submission_id)
        if not sub or sub.user_id != case.user_id:
            raise Unavailable("The original submission is no longer available")
        source_add(
            db,
            case,
            {
                **sub.content,
                "url": sub.url or f"submission:{sub.id}",
                "platform": "instagram"
                if "instagram.com/" in sub.url
                else "youtube"
                if youtube_id(sub.url)
                else "supplied",
            },
        )
        return {"sources": 1, "basis": "Owner-supplied evidence"}
    if case.context.get("url"):
        url = canonical_url(case.context["url"])
        source_add(db, case, {"url": url, "platform": "youtube" if youtube_id(url) else "instagram"})
        return {"sources": 1, "basis": "Supplied permalink; collection access still required"}
    if cfg.app_mode == "demo":
        return {"unavailable": "Live discovery is disabled in demo; no real source has been searched"}
    errors = {}
    if cfg.local_search_enabled and not task.result.get("public_search_done"):
        from .public_sources import public_search

        try:
            for row in public_search(db, case.query):
                source_add(db, case, row)
        except DeferredCollection as exc:
            raise PendingSource(exc.retry_seconds) from exc
        except Unavailable as exc:
            errors["public_search"] = str(exc)
        task.result = {**task.result, "public_search_done": True}
        db.commit()
    # Persist a provider run ID before polling; a retry resumes the same run.
    if cfg.instagram_provider == "apify":
        state = dict(task.result)
        if not state.get("apify_run"):
            try:
                if state.get("apify_start_requested"):
                    raise Unavailable(
                        "A prior provider start has no confirmed run ID; inspect the provider dashboard before starting another investigation"
                    )
                state["apify_start_requested"] = True
                task.result = dict(state)
                db.commit()
                state["apify_run"] = apify_start(db, case.query)
                task.result = state
                db.commit()
            except Unavailable as exc:
                errors["instagram"] = str(exc)
        if state.get("apify_run") and not state.get("apify_done"):
            try:
                rows = apify_poll(db, state["apify_run"])
                if rows is None:
                    state["polls"] = state.get("polls", 0) + 1
                    task.result = state
                    db.commit()
                    if state["polls"] < 10:
                        raise PendingSource()
                    raise Unavailable("Data-provider run exceeded the investigation wait budget")
                for row in rows:
                    source_add(db, case, row)
                task.result = {**state, "apify_done": True}
                db.commit()
            except Unavailable as exc:
                errors["instagram"] = str(exc)
    else:
        state = dict(task.result.get("meta_discovery", {}))
        try:
            for row in instagram_discover(db, case.query, state):
                source_add(db, case, row)
            task.result = {**task.result, "meta_discovery": state}
            db.commit()
            if not state.get("done"):
                raise PendingSource()
        except DeferredCollection as exc:
            raise PendingSource(exc.retry_seconds) from exc
        except Unavailable as exc:
            errors["instagram"] = str(exc)
    for name, fetch in [("web", web_search), ("youtube", youtube_discover)]:
        try:
            query = case.query + (" site:instagram.com/reel/" if name == "web" else "")
            for row in fetch(db, query):
                url = str(row.get("url") or "")
                platform = (
                    "instagram" if urlparse(url).hostname in {"instagram.com", "www.instagram.com"} else name
                )
                source_add(
                    db,
                    case,
                    {**row, "platform": platform, "access": "search_lead", "snippet_is_not_caption": True},
                )
        except Unavailable as exc:
            errors[name] = str(exc)
    db.commit()
    task.result = {**task.result, "search_complete": True, "search_errors": errors}
    db.commit()
    return rank_discovery(db, case, task)


def rank_discovery(db, case, task):
    cfg, errors = settings(), task.result.get("search_errors", {})
    # Date probes are resumable; no discovered source is discarded.
    sources = case_sources(db, case)
    from .known_spots import try_skip

    for source in sources:
        if not source.content.get("streamed"):
            try_skip(db, case, source, stage="before_recency_probe")
    if cfg.local_search_enabled:
        from .public_sources import public_instagram

        # Probe dates before selecting expensive browser/video work. Reuse captions
        # returned by this bounded metadata pass in the later collection stage.
        pending = [
            source
            for source in sources
            if source.platform == "instagram"
            and not source.content.get("streamed")
            and not source.content.get("recency_checked_at")
            and not source.content.get("published_at")
        ]
        for source in pending[:8]:
            try:
                metadata = public_instagram(db, source.canonical_url)
                source.content = {**source.content, **metadata, "recency_checked_at": now()}
            except DeferredCollection as exc:
                db.commit()
                raise PendingSource(exc.retry_seconds) from exc
            except Unavailable as exc:
                source.content = {**source.content, "date_gap": str(exc), "recency_checked_at": now()}
        db.commit()
        if len(pending) > 8:
            raise PendingSource()

    def source_priority(source):
        identity = creator_key(source)
        history = creator_assessment(db, identity, case.user_id)
        reviewed = history.get("supported", 0) + history.get("refuted", 0)
        # Shrink small review histories toward neutral; never use likes as truth.
        accuracy = (history.get("supported", 0) + 2) / (reviewed + 4)
        text = normalized(str(source.content.get("caption", "")) + " " + str(source.content.get("title", "")))
        terms = set(normalized(case.query).split())
        relevance = len(terms & set(text.split())) / max(1, len(terms))
        return (*recency_key(source.content), relevance + (accuracy - 0.5) * min(reviewed / 5, 1))

    sources.sort(key=source_priority, reverse=True)
    for rank, source in enumerate(sources):
        source.content = {**source.content, "selection_rank": rank + 1}
    db.commit()
    return {
        **task.result,
        "source_count": len(case_sources(db, case)),
        "unavailable_sources": errors,
        "note": "Search snippets are leads, not verified source content",
        "selection_order": "Newest known publication first; undated sources last. Relevance breaks ties.",
    }


def stream_source(db, case, source):
    from types import SimpleNamespace
    from .spots import identify_from_source
    from .known_spots import try_skip

    if try_skip(db, case, source):
        return
    roles = (
        ("caption", "video", "comments")
        if settings().known_spot_skip_enabled
        else ("caption", "comments", "video")
    )
    for role in roles:
        analysis_stage(db, case, SimpleNamespace(role=role), only_source=source)
        if role in {"caption", "video"}:
            candidates = [
                c
                for r in ("caption", "video")
                for c in source.analysis.get(r, {}).get("venue_candidates", [])
            ]
            if try_skip(db, case, source, candidates=candidates, stage="after_" + role):
                return
            identify_from_source(db, case, source)
            db.commit()  # Save each newly identified place before remaining specialist work.
    from .providers import renew_job

    renew_job(db)
    identify_from_source(db, case, source)
    source.content = {
        **{
            k: v
            for k, v in source.content.items()
            if k not in {"media", "media_url", "media_alternatives", "video_url", "audio_url"}
        },
        "streamed": True,
        "analysis_pending": False,
    }
    db.commit()


def collect_stage(db, case, task):
    errors, processed = [], 0
    streaming = settings().research_streaming and settings().app_mode != "demo"
    pipeline = streaming and settings().research_pipeline_enabled

    def dispatch(source):
        if pipeline:
            from .jobs import enqueue

            source.content = {**source.content, "analysis_pending": True}
            db.commit()
            enqueue(
                db,
                "source_analysis",
                {"case_id": case.id, "source_id": source.id},
                f"source-analysis:{source.id}",
                priority=90,
            )
        else:
            stream_source(db, case, source)

    for source in case_sources(db, case):
        from .known_spots import try_skip

        if source.state == "lead" and try_skip(db, case, source):
            continue
        if source.state != "lead":
            if streaming and not source.content.get("streamed"):
                dispatch(source)
            continue
        if processed >= max(1, settings().research_max_sources):
            raise PendingSource()
        if pipeline:
            from .db import Job

            backlog = list(
                db.scalars(
                    select(Job.id)
                    .where(Job.kind == "source_analysis", Job.state.in_(["queued", "running"]))
                    .limit(max(2, settings().research_max_sources * 2))
                )
            )
            if len(backlog) >= max(2, settings().research_max_sources * 2):
                raise PendingSource(5)  # Bound retained media/preparation backlog without dropping leads.
        content = dict(source.content)
        try:
            if settings().app_mode == "demo":
                content["collection_note"] = "Only supplied content is available in demonstration mode"
            elif source.platform == "youtube":
                video_id = youtube_id(source.canonical_url)
                if video_id:
                    content.update(youtube_context(db, video_id))
                    content["video_url"] = "https://www.youtube.com/watch?v=" + video_id
            elif source.platform == "instagram":
                if settings().local_search_enabled and not content.get("caption"):
                    from .public_sources import public_instagram

                    try:
                        content.update(public_instagram(db, source.canonical_url))
                    except DeferredCollection:
                        raise
                    except Unavailable as exc:
                        content["public_collection_gap"] = str(exc)
                if (
                    settings().instagram_browser_enabled
                    and not content.get("browser")
                    and not content.get("provider_collected")
                ):
                    from .browser_sources import browser_instagram

                    try:
                        browser_content = browser_instagram(db, source.canonical_url)
                        if content.get("comments") and not browser_content.get("comments"):
                            browser_content.pop("comments_coverage", None)
                        # A failed browser pass must not erase already retrieved text.
                        content.update({k: v for k, v in browser_content.items() if v not in (None, "")})
                    except DeferredCollection:
                        raise
                    except Unavailable as exc:
                        content["browser"] = {
                            "status": "unavailable",
                            "reason": str(exc),
                            "authenticated": False,
                        }
                if (
                    settings().instagram_provider == "apify"
                    and not content.get("provider_collected")
                    and not content.get("media")
                ):
                    if not content.get("apify_run"):
                        if content.get("apify_start_requested"):
                            raise Unavailable(
                                "Provider start outcome is unknown; inspect the provider dashboard before recollecting"
                            )
                        content["apify_start_requested"] = True
                        source.content = dict(content)
                        db.commit()
                        content["apify_run"] = apify_start(db, case.query, [source.canonical_url])
                        source.content = content
                        db.commit()
                    rows = apify_poll(db, content["apify_run"])
                    if rows is None:
                        content["polls"] = content.get("polls", 0) + 1
                        source.content = content
                        db.commit()
                        if content["polls"] < 10:
                            raise PendingSource()
                        raise Unavailable("Source collection exceeded wait budget")
                    matching = [row for row in rows if row["url"] == source.canonical_url]
                    if matching:
                        content.update(matching[0])
                elif settings().instagram_provider == "meta" and content.get("external_id"):
                    content = collect_meta_comments(db, content)
                if content.get("media_url") and not content.get("media"):
                    # Largest stream first; fall back to a smaller one when it is over the limit.
                    streams = [content["media_url"], *content.get("media_alternatives", [])]
                    for position, stream in enumerate(streams):
                        try:
                            content["media"] = download_media(db, stream)
                            content["media_stream_rank"] = position
                            break
                        except DeferredCollection:
                            raise
                        except Unavailable as exc:
                            if "download limit" not in str(exc) or position + 1 == len(streams):
                                raise
                if content.get("media") and not content.get("media_receipt"):
                    if content.get("audio_url"):
                        from .browser_media import download_audio, join_tracks

                        try:
                            content["media"] = join_tracks(
                                content["media"], download_audio(db, content["audio_url"])
                            )
                            content["browser"] = {**content.get("browser", {}), "audio_track_joined": True}
                        except DeferredCollection:
                            raise
                        except Unavailable as exc:
                            content["browser"] = {**content.get("browser", {}), "audio_track_gap": str(exc)}
                    import hashlib
                    import base64

                    raw = base64.b64decode(content["media"]["base64"])
                    content["media_receipt"] = {
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "bytes": len(raw),
                        "mime": content["media"]["mime"],
                        "downloaded_at": now(),
                        "method": content.get("collection_method", "configured_provider"),
                    }
                    if content.get("browser", {}).get("video_reference_found"):
                        content["browser"] = {**content["browser"], "video_downloaded": True}
                if not any(content.get(k) for k in ["caption", "comments", "transcript", "media"]):
                    raise Unavailable(
                        "Public collection could not retrieve this reel; configure a supported source connector for video/comments"
                    )
            elif source.platform == "web":
                content["transcript"] = read_official_page(db, source.canonical_url)
                content["collection_note"] = (
                    "Readable official-page text; site boilerplate may be included and facts require contextual verification"
                )
                content["fetched_at"] = now()
            source.state = "collected"
        except DeferredCollection as exc:
            source.content = {**content, "deferred_reason": str(exc)}
            db.commit()
            raise PendingSource(exc.retry_seconds) from exc
        except Unavailable as exc:
            errors.append({"source_id": source.id, "reason": str(exc)})
            content["collection_error"] = str(exc)
            source.state = "partial"
        source.content = content
        if evidence_fingerprint(content):
            source.content = {**content, "content_fingerprint": evidence_fingerprint(content)}
        source.creator = str(content.get("creator", ""))[:100]
        db.commit()
        if streaming:
            dispatch(source)
        processed += 1
    return {"source_count": len(case_sources(db, case)), "gaps": errors}


def analysis_stage(db, case, task, only_source=None):
    from .performance import span
    from .analysis_reuse import analysis_key, reusable, mark, model_digest, valid_result

    role, gaps, completed, skipped_known = task.role, [], 0, 0
    for source in [only_source] if only_source else case_sources(db, case):
        skipped = source.analysis.get("discovery_skip")
        if skipped:
            skipped_known += 1
            gaps.append(
                {
                    "source_id": source.id,
                    "reason": "Remaining evidence skipped: location already in private inventory",
                }
            )
            continue
        if not only_source and source.content.get("analysis_pending"):
            from .db import Job

            pending = db.scalar(select(Job).where(Job.key == f"source-analysis:{source.id}"))
            if pending and pending.state in {"queued", "running"}:
                raise PendingSource(5)
            if pending and pending.state == "failed":
                result = source.analysis.get(role) or {
                    "status": "unavailable",
                    "reason": "Source analysis failed; retry the recorded job",
                    "video_analyzed": False,
                }
                gaps.append(
                    {"source_id": source.id, "reason": result.get("reason", "Source analysis incomplete")}
                )
                source.analysis = {**source.analysis, role: result}
                db.commit()
                continue
        if source.analysis.get(role, {}).get("status") == "observations_only" and not source.analysis[
            role
        ].get("reuse"):
            completed += 1
            continue
        content = source.content
        available = (
            bool(content.get("media") or content.get("video_url"))
            if role == "video"
            else bool(
                content.get("comments")
                if role == "comments"
                else content.get("caption") or content.get("transcript")
            )
        )
        if not available or settings().app_mode == "demo":
            result = source.analysis.get(role) or {
                "status": "unavailable",
                "reason": "No accessible modality or live analysis is disabled",
                "video_analyzed": False,
            }
        else:
            try:
                data = {"source_url": source.canonical_url}
                from .learning import relevant_examples

                data["reviewed_examples"] = relevant_examples(db, case.user_id, source, role)
                keys = {
                    "caption": ["caption", "transcript"],
                    "comments": ["comments", "comments_coverage"],
                    "video": [],
                }[role]
                data.update({k: content[k] for k in keys if k in content})
                if role == "caption" and content.get("machine_transcript"):
                    data.pop("transcript", None)
                digest = model_digest(role) if settings().app_mode == "local" else None
                key = analysis_key(role, data, content, digest)
                existing = source.analysis.get(role, {})
                if valid_result(existing, key) and (digest or not settings().analysis_reuse_enabled):
                    completed += 1
                    continue
                result = reusable(db, case, source, role, key, digest)
                if result is not None:
                    pass
                elif role == "comments":
                    from .comment_analysis import analyze_comments

                    with span("comments"):
                        result = mark(
                            analyze_comments(db, source, data, analyze, context_version=digest), key, digest
                        )
                else:
                    options = {}
                    if role == "video":
                        from .known_spots import allowed, decision

                        if allowed(case, source):

                            def stop_known(partial):
                                candidates = [
                                    *source.analysis.get("caption", {}).get("venue_candidates", []),
                                    *partial.get("venue_candidates", []),
                                ]
                                return bool(
                                    decision(db, case, source, candidates=candidates, stage="during_video")
                                )

                            options["on_pass"] = stop_known
                    with span(role):
                        result = mark(
                            analyze(
                                db,
                                role,
                                data,
                                content.get("media") if role == "video" else None,
                                content.get("video_url") if role == "video" else None,
                                **options,
                            ),
                            key,
                            digest,
                        )
                renew_job(db)
                if role == "caption":
                    from .analysts import ground_candidates

                    result = ground_candidates(
                        result,
                        " ".join(str(data.get(k, "")) for k in ("caption", "transcript")),
                        content.get("creator", ""),
                    )
                speech = result.pop("_transcription", None)
                signatures = result.pop("_visual_signatures", [])
                if role == "video" and not result.get("reuse", {}).get("reused"):
                    from .visual_places import match_frames

                    result["visual_reference_matches"] = match_frames(db, case.user_id, signatures)
                if speech:
                    source.content = {
                        **source.content,
                        "transcript": speech.get("text", ""),
                        "speech_segments": speech.get("segments", []),
                        "speech_language": speech.get("language"),
                        "speech_language_probability": speech.get("language_probability"),
                        "speech_model": speech.get("model"),
                        "machine_transcript": True,
                    }
                if role == "video":
                    requested = list(result.get("followup_seconds", []))
                    requested += [
                        o["timestamp_seconds"]
                        for o in result.get("observations", [])
                        if o.get("uncertainty") and o.get("timestamp_seconds") is not None
                    ]
                    result["followup_seconds"] = list(dict.fromkeys(requested))[:4]
                    result["attention"] = {
                        "baseline_sampling_retained": True,
                        "requested_seconds": result["followup_seconds"],
                        "reason": "Model-requested or explicitly uncertain timestamped clues; no location approval inferred",
                    }
                if (
                    role == "video"
                    and content.get("media")
                    and not result.get("reuse", {}).get("reused")
                    and not result.get("early_exit")
                    and (
                        result.get("followup_seconds")
                        or (settings().app_mode != "local" and settings().analysis_provider != "ollama")
                    )
                ):
                    try:
                        frames = extract_frames(content["media"], result.get("followup_seconds") or None)
                        result["frame_times"] = [f["seconds"] for f in frames]
                        if frames:
                            result["frame_inspection"] = analyze(db, "reinspect", data, frames=frames)
                            result["observations"] = [
                                *result.get("observations", []),
                                *result["frame_inspection"].get("observations", []),
                            ]
                            result["venue_candidates"] = [
                                *result.get("venue_candidates", []),
                                *result["frame_inspection"].get("venue_candidates", []),
                            ]
                    except Unavailable as exc:
                        result["frame_inspection"] = {"unavailable": str(exc)}
                completed += 1
            except Unavailable as exc:
                result = {"status": "unavailable", "reason": str(exc), "video_analyzed": False}
        if role == "comments":
            result["sample"] = comment_sample(content.get("comment_texts", content.get("comments", "")))
        if result["status"] == "unavailable":
            gaps.append({"source_id": source.id, "reason": result["reason"]})
        source.analysis = {**source.analysis, role: result}
        db.commit()
    return {"analyzed_sources": completed, "skipped_known_sources": skipped_known, "gaps": gaps}


def location_stage(db, case, task):
    from .db import IdentifiedSpot
    from .branch_matching import branch_match, rank_google

    spots = list(db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == case.user_id)))
    inventory = list(db.scalars(select(Venue).where(Venue.is_demo == (settings().app_mode == "demo"))))
    count = 0
    for source in case_sources(db, case):
        hypotheses = []
        candidates = []
        for role in ["caption", "video"]:
            candidates.extend(source.analysis.get(role, {}).get("venue_candidates", []))
        seen = set()
        for candidate in candidates:
            name = normalized(candidate.get("name", ""))
            clues = normalized(" ".join(candidate.get("address_clues", [])))
            identity = (name, clues)
            if not name or identity in seen:
                continue
            seen.add(identity)
            matches = []
            for venue in inventory:
                similarity = SequenceMatcher(None, name, normalized(venue.name)).ratio()
                if similarity < 0.7:
                    continue
                # A precise independently maintained full address, not an area name, is needed.
                address_match = len(normalized(venue.address)) >= 15 and normalized(venue.address) in clues
                confirmed = similarity == 1 and address_match and venue.details.get("branch_confirmed", False)
                matches.append(
                    {
                        "venue_id": venue.id,
                        "name_similarity": round(similarity, 2),
                        "address_match": address_match,
                        "status": "confirmed" if confirmed else "candidate",
                    }
                )
            if sum(x["status"] == "confirmed" for x in matches) > 1:
                for row in matches:
                    row["status"] = "candidate"
            hypothesis = {"observed": candidate, "inventory_matches": matches, "google_place_ids": []}
            visual = source.analysis.get("video", {}).get("visual_reference_matches", {}).get("matches", [])
            ranked = [
                branch_match(candidate, s, visual)
                for s in spots
                if s.status not in {"merged", "quarantined", "rejected"}
            ]
            ranked = sorted(
                [r for r in ranked if r], key=lambda r: (not r["conflicts"], r["score"]), reverse=True
            )
            if len(ranked) > 1 and ranked[0]["score"] - ranked[1]["score"] < 2:
                for r in ranked:
                    if r["status"] == "corroborated_candidate":
                        r["status"] = "ambiguous_candidate"
                        r["conflicts"].append("Multiple branches have similar support")
            hypothesis["spot_matches"] = ranked
            if settings().app_mode == "local":
                hypothesis["lookup_gap"] = (
                    "Exact branch requires independent address and coordinate verification; source captions alone do not confirm a location"
                )
            if settings().app_mode != "demo":
                try:
                    places = google_search(db, f"{name} {clues} Coimbatore", 11.0168, 76.9558)
                    hypothesis["google_place_ids"] = [
                        p["id"] for p in rank_google(candidate, places) if p.get("id")
                    ]
                except Unavailable as exc:
                    hypothesis["lookup_gap"] = str(exc)
                if not any(m["status"] == "confirmed" for m in matches):
                    try:
                        clues_from_video = source.analysis.get("video", {}).get("observations", [])
                        clue_text = " ".join(
                            o.get("text", "")[:120]
                            for o in clues_from_video
                            if o.get("basis") in {"visual", "speech"}
                        )[:300]
                        leads = web_search(db, f"{name} {clues} {clue_text} Coimbatore address")
                        hypothesis["independent_lookup_leads"] = [{"url": x.get("url")} for x in leads[:3]]
                    except Unavailable as exc:
                        hypothesis["independent_lookup_gap"] = str(exc)
            hypotheses.append(hypothesis)
        source.analysis = {
            **source.analysis,
            "location": {
                "hypotheses": hypotheses,
                "rule": "Similar name or Maps result alone is not branch confirmation",
            },
        }
        count += len(hypotheses)
        db.commit()
    return {"hypotheses": count, "review_required_for_ambiguous_branches": True}


def reliability_stage(db, case, task):
    origins = {}
    for source in case_sources(db, case):
        fingerprint = source.content.get("content_fingerprint") or evidence_fingerprint(source.content)
        origin = origins.setdefault(fingerprint, source.id) if fingerprint else source.id
        identity = creator_key(source)
        source.analysis = {
            **source.analysis,
            "reliability": {
                "creator_identity": identity or "unknown",
                "same_content_origin": origin,
                "possible_copy": origin != source.id,
                "history": source_track_record(db, identity),
                "engagement": {
                    "likes": source.content.get("likes"),
                    "views": source.content.get("views"),
                    "dislikes": None,
                },
                "assessment": creator_assessment(db, identity, case.user_id),
                "assessed_at": now(),
                "reason": "Engagement and model agreement do not verify a claim",
            },
        }
    db.commit()
    return {
        "independence": "Exact normalized caption copies share an origin; other repost relationships remain uncertain"
    }


def creator_assessment(db, identity, user_id=None):
    if not identity:
        return {"status": "unestablished", "reason": "Creator identity unknown"}
    rows = list(
        db.scalars(
            select(SourceAssessment)
            .where(SourceAssessment.creator_identity == identity)
            .order_by(SourceAssessment.created_at.desc())
        )
    )
    if user_id:
        rows = [r for r in rows if r.actor == user_id]
    from .trust import review_statistics

    return review_statistics(rows)


def verification_stage(db, case, task):
    eligible, gaps = set(), []
    sources = case_sources(db, case)
    for source in sources:
        if source.analysis.get("discovery_skip"):
            gaps.append(
                {
                    "source_id": source.id,
                    "missing": [
                        "Remaining reel evidence skipped under known-location discovery policy; not a complete fresh investigation"
                    ],
                }
            )
        for role in ["caption", "comments", "video"]:
            corrections = source.analysis.get(role, {}).get("corrections", [])
            if corrections:
                gaps.append(
                    {
                        "source_id": source.id,
                        "missing": ["Resolve reported corrections/contradictions"],
                        "reports": corrections,
                    }
                )
        matches = [
            m
            for h in source.analysis.get("location", {}).get("hypotheses", [])
            for m in h["inventory_matches"]
        ]
        linked = source.analysis.get("human_resolution", {})
        if linked.get("venue_id"):
            matches.append({"venue_id": linked["venue_id"], "status": "confirmed"})
        confirmed = {m["venue_id"] for m in matches if m["status"] == "confirmed"}
        if not confirmed:
            gaps.append({"source_id": source.id, "missing": ["Independent exact-branch confirmation"]})
        for venue_id in confirmed:
            venue = db.get(Venue, venue_id)
            if not venue or venue.is_demo != (settings().app_mode == "demo"):
                continue
            # Extracted claims are review proposals, not facts. Only dated sources
            # with a resolved branch can create them; source time is not visit time.
            if len(confirmed) == 1 and source.content.get("published_at"):
                from .schemas import ClaimInput
                from .evidence import ingest_claim
                from pydantic import ValidationError

                proposed_ids = list(source.analysis.get("proposed_claim_ids", []))
                for candidate in source.analysis.get("caption", {}).get("venue_candidates", []):
                    if normalized(candidate.get("name", "")) != normalized(venue.name):
                        continue
                    for fact in candidate.get("facts", [])[:10]:
                        try:
                            observed = datetime.fromisoformat(
                                source.content["published_at"].replace("Z", "+00:00")
                            )
                            proposed = ClaimInput(
                                venue_id=venue_id,
                                field=fact["field"],
                                value=fact["value"],
                                source_url=source.canonical_url,
                                source_type="social",
                                source_group=creator_key(source) or source.canonical_url,
                                observed_at=observed,
                                expires_at=observed + timedelta(hours=24),
                            )
                            claim = ingest_claim(db, proposed, "investigation-proposal", trusted=True)
                            proposed_ids.append(claim.id)
                        except (ValueError, TypeError, KeyError, ValidationError):
                            gaps.append(
                                {
                                    "source_id": source.id,
                                    "missing": ["A proposed fact needs valid units/date/value before review"],
                                }
                            )
                source.analysis = {**source.analysis, "proposed_claim_ids": sorted(set(proposed_ids))}
            fields = set(
                db.scalars(
                    select(Claim.field).where(
                        Claim.venue_id == venue_id, Claim.status == "accepted", Claim.expires_at > now()
                    )
                )
            )
            missing = sorted({"price_per_person", "hours", "closed"} - fields)
            if missing or venue.status != "published" or not venue.details.get("branch_confirmed"):
                gaps.append(
                    {
                        "venue_id": venue_id,
                        "missing": missing
                        + (
                            ["Branch/publication review"]
                            if venue.status != "published" or not venue.details.get("branch_confirmed")
                            else []
                        ),
                    }
                )
            else:
                eligible.add(venue_id)
        for role in ["caption", "comments", "video"]:
            if source.analysis.get(role, {}).get("status") == "unavailable":
                gaps.append({"source_id": source.id, "missing": [f"{role} analysis unavailable"]})
        if (
            source.analysis.get("video", {}).get("audio_gap")
            and source.content.get("source_has_audio") is not False
        ):
            gaps.append(
                {
                    "source_id": source.id,
                    "missing": ["Speech unavailable; video inspection covers sampled visuals only"],
                }
            )
        source.content = {
            k: v
            for k, v in source.content.items()
            if k not in {"media", "media_url", "media_alternatives", "video_url", "audio_url"}
        }
    from .spots import identify_from_source, reconcile_spots

    for source in sources:
        identify_from_source(db, case, source)
    reconcile_spots(db, case.user_id)
    result = {
        "eligible_venue_ids": sorted(eligible),
        "gaps": gaps,
        "source_count": len(sources),
        "publication": "Only existing independently verified published venues are eligible; new observations require review",
        "next_action": "Replan with current venue facts"
        if eligible
        else "Review evidence, confirm a branch and obtain current essential facts",
    }
    case.state = "complete" if eligible and not gaps else "review" if sources else "unavailable"
    case.result = result
    sub = db.get(Submission, case.context.get("submission_id", ""))
    if sub and sub.user_id == case.user_id:
        sub.status = "review"
        sub.content = {k: v for k, v in sub.content.items() if k != "media"}
        sub.result = {
            "investigation_id": case.id,
            **result,
            "video": {"analyzed": any(s.analysis.get("video", {}).get("video_analyzed") for s in sources)},
            "summary": "Specialist investigation finished; see the investigation for source evidence and unresolved checks",
        }
    return result


def execute_case(db, case_id, expected_ordinal=None):
    from .jobs import enqueue

    case = db.get(Investigation, case_id)
    if not case or case.state in TERMINAL:
        return {"message": "Investigation is terminal or removed"}
    query = select(ResearchTask).where(ResearchTask.case_id == case.id)
    if expected_ordinal is not None:
        query = query.where(ResearchTask.ordinal == expected_ordinal)
    else:
        query = query.where(ResearchTask.state != "done")
    task = db.scalar(query.order_by(ResearchTask.ordinal))
    if not task:
        return {"message": "No pending specialist task"}
    if task.state == "done":
        return {"message": "This stage already committed; duplicate delivery skipped", "role": task.role}
    unfinished_predecessor = db.scalar(
        select(ResearchTask.id).where(
            ResearchTask.case_id == case.id, ResearchTask.ordinal < task.ordinal, ResearchTask.state != "done"
        )
    )
    if unfinished_predecessor:
        raise PendingSource()
    case.state, case.updated_at, task.state = "running", now(), "running"
    db.commit()
    stages = {
        "discovery": discover_stage,
        "collection": collect_stage,
        "location": location_stage,
        "reliability": reliability_stage,
        "verification": verification_stage,
    }
    try:
        from .performance import span

        with span("stage." + task.role):
            result = stages.get(task.role, analysis_stage)(db, case, task)
    except PendingSource:
        task.state = "waiting"
        db.commit()
        raise
    except Exception:
        task.state = "retrying"
        db.commit()
        raise
    # Cancellation/deletion is checked again after provider calls.
    db.refresh(case)
    if case.state == "cancelled":
        for source in case_sources(db, case):
            source.content = {
                k: v
                for k, v in source.content.items()
                if k not in {"media", "media_url", "media_alternatives", "video_url", "audio_url"}
            }
        db.commit()
        return {"message": "Cancelled; results not advanced"}
    if task.role == "verification":
        # Refresh discarded uncommitted attributes; reapply the gate result.
        case.result = result
        case.state = (
            "complete"
            if result["eligible_venue_ids"] and not result["gaps"]
            else "review"
            if result["source_count"]
            else "unavailable"
        )
    task.state, task.result, task.error, task.completed_at = "done", result, "", now()
    case.updated_at = now()
    db.commit()
    if task.ordinal + 1 < len(ROLES):
        enqueue(db, "investigation", {"case_id": case.id}, f"case:{case.id}:{task.ordinal + 1}", priority=90)
    return {"case_id": case.id, "role": task.role, "state": case.state}


def public_case(db, case):
    from .performance import case_metrics

    tasks = list(
        db.scalars(select(ResearchTask).where(ResearchTask.case_id == case.id).order_by(ResearchTask.ordinal))
    )
    return {
        "id": case.id,
        "query": case.query,
        "state": case.state,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
        "result": case.result,
        "performance": case_metrics(db, case),
        "tasks": [{"role": t.role, "state": t.state, "result": t.result, "error": t.error} for t in tasks],
        "sources": [
            {
                "id": s.id,
                "url": s.canonical_url,
                "platform": s.platform,
                "state": s.state,
                "creator": s.creator,
                "analysis": s.analysis,
                "content": {
                    k: v
                    for k, v in s.content.items()
                    if k not in {"media", "media_url", "media_alternatives", "apify_run", "video_url", "audio_url"}
                },
            }
            for s in case_sources(db, case)
        ],
    }


def erase_cases(db, user_id):
    from .db import ResearchCorrection

    db.execute(delete(ResearchCorrection).where(ResearchCorrection.user_id == user_id))
    ids = list(db.scalars(select(Investigation.id).where(Investigation.user_id == user_id)))
    source_ids = list(db.scalars(select(ResearchSource.id).where(ResearchSource.case_id.in_(ids))))
    db.execute(delete(SourceAssessment).where(SourceAssessment.source_id.in_(source_ids)))
    for job in db.scalars(
        select(Job).where(
            Job.kind.in_(
                [
                    "investigation",
                    "source_analysis",
                    "evaluation_compare",
                    "source_quality_upgrade",
                    "source_watch",
                ]
            )
        )
    ):
        if job.payload.get("case_id") in ids or job.payload.get("source_id") in source_ids:
            db.delete(job)
    db.execute(delete(ResearchSource).where(ResearchSource.case_id.in_(ids)))
    db.execute(delete(ResearchTask).where(ResearchTask.case_id.in_(ids)))
    db.execute(delete(Investigation).where(Investigation.id.in_(ids)))


def purge_expired_sources(db):
    for source in db.scalars(select(ResearchSource)):
        watch = source.analysis.get("source_watch", {})
        if "observed_caption" in watch:
            try:
                watched_at = datetime.fromisoformat(watch.get("checked_at", ""))
                expired_watch = (
                    watched_at.tzinfo is None
                    or (datetime.now(timezone.utc) - watched_at).total_seconds() > 86400
                )
            except (ValueError, TypeError):
                expired_watch = True
            if expired_watch:
                source.analysis = {
                    **source.analysis,
                    "source_watch": {k: v for k, v in watch.items() if k != "observed_caption"},
                }
        try:
            fetched = datetime.fromisoformat(source.content.get("fetched_at") or source.created_at)
            if fetched.tzinfo is None or fetched > datetime.now(timezone.utc):
                fetched = datetime.fromisoformat(source.created_at)
        except (ValueError, TypeError):
            fetched = datetime.fromisoformat(source.created_at)
        age = (datetime.now(timezone.utc) - fetched).total_seconds()
        if age > 86400:
            fingerprint = source.content.get("content_fingerprint") or evidence_fingerprint(source.content)
            source.content = {
                k: v
                for k, v in source.content.items()
                if k
                not in {
                    "media",
                    "media_url",
                    "audio_url",
                    "video_url",
                    "description",
                    "title",
                    "transcript",
                    "speech_segments",
                    "caption",
                    "comments",
                    "comment_texts",
                    "search_preview",
                }
            }
            if fingerprint:
                source.content = {**source.content, "content_fingerprint": fingerprint}
            if settings().research_streaming and not source.content.get("streamed"):
                case = db.get(Investigation, source.case_id)
                if case and case.state in {"queued", "running"}:
                    source.state = "lead"
                    source.content = {
                        k: v for k, v in source.content.items() if k not in {"browser", "media_receipt"}
                    }
