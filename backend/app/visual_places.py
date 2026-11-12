"""Local reference-image matching. A visual match is a clue, never place approval."""

import base64
import hashlib
import ipaddress
import os
import socket
from urllib.parse import urlparse
import httpx
from sqlalchemy import select
from .db import IdentifiedSpot, now
from .providers import quota, Unavailable

os.environ.setdefault("OPENCV_IO_MAX_IMAGE_PIXELS", "16000000")


MAX_POINTS = 500


def signature(raw):
    import cv2
    import numpy as np

    if not raw or len(raw) > 4 * 1024 * 1024:
        raise ValueError("Image exceeds the local reference limit")
    try:
        image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    except cv2.error as exc:
        raise ValueError("Unreadable or oversized reference image") from exc
    if image is None or image.size > 16000000:
        raise ValueError("Unreadable or oversized reference image")
    height, width = image.shape
    scale = min(1, 800 / max(height, width))
    image = cv2.resize(image, (max(1, int(width * scale)), max(1, int(height * scale))))
    points, descriptors = cv2.ORB_create(nfeatures=500).detectAndCompute(image, None)
    # OpenCV can return one or two more than requested; keep the stored size bounded.
    points = points[:MAX_POINTS]
    descriptors = descriptors[:MAX_POINTS] if descriptors is not None else None
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "width": image.shape[1],
        "height": image.shape[0],
        "points": [[round(p.pt[0], 2), round(p.pt[1], 2)] for p in points],
        "descriptors": base64.b64encode(descriptors.tobytes()).decode() if descriptors is not None else "",
    }


def compare(query, reference):
    import cv2
    import numpy as np

    if min(len(query.get("points", [])), len(reference.get("points", []))) < 20:
        return {"matched": False, "reason": "Too few distinctive visual features"}

    def decode(item):
        raw = base64.b64decode(item["descriptors"], validate=True)
        if len(raw) != len(item["points"]) * 32:
            raise ValueError("Invalid local visual descriptor")
        # References indexed before the bound existed may hold a few extra points.
        return np.frombuffer(raw[: MAX_POINTS * 32], dtype=np.uint8).reshape(-1, 32)

    pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(decode(query), decode(reference), k=2)
    good = [pair[0] for pair in pairs if len(pair) == 2 and pair[0].distance < 0.70 * pair[1].distance]
    # Repeated signs/tiles must not count as many independent correspondences.
    good = list({p.trainIdx: p for p in sorted(good, key=lambda p: -p.distance)}.values())
    if len(good) < 20:
        return {"matched": False, "matches": len(good), "reason": "Insufficient unique feature matches"}
    a = np.float32([query["points"][p.queryIdx] for p in good])
    b = np.float32([reference["points"][p.trainIdx] for p in good])
    matrix, mask = cv2.findHomography(a, b, cv2.RANSAC, 4)
    if matrix is None or mask is None:
        return {"matched": False, "reason": "No consistent image geometry"}
    keep = mask.ravel().astype(bool)
    count, ratio = int(keep.sum()), float(keep.mean())

    def coverage(points, shape):
        return float(cv2.contourArea(cv2.convexHull(points))) / (shape["width"] * shape["height"])

    covered = min(coverage(a[keep], query), coverage(b[keep], reference)) if count >= 3 else 0
    return {
        "matched": count >= 20 and ratio >= 0.6 and covered >= 0.08,
        "inliers": count,
        "inlier_ratio": round(ratio, 3),
        "covered_fraction": round(covered, 3),
        "reason": "Local ORB/geometry comparison; logos, reused photos and different branches still require review",
    }


def fetch_reference(db, url, page_url):
    parsed, page = urlparse(url), urlparse(page_url)
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.port not in {None, 443}
        or parsed.hostname != page.hostname
    ):
        raise Unavailable("Reference images must use the same public HTTPS host as the evidence page")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise Unavailable("Reference image host must be public")
        quota(db)
        with httpx.Client(timeout=15, trust_env=False, follow_redirects=False) as client:
            with client.stream("GET", url) as response:
                if response.status_code != 200 or not response.headers.get("content-type", "").startswith(
                    "image/"
                ):
                    raise Unavailable("Reference image unavailable")
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 4 * 1024 * 1024:
                        raise Unavailable("Reference image too large")
        return {
            "url": url,
            "page_url": page_url,
            "collected_at": now(),
            "signature": signature(raw),
            "basis": "Page image; exact branch and whether it depicts a storefront remain unverified",
        }
    except (OSError, httpx.HTTPError, ValueError) as exc:
        raise Unavailable("Reference image could not be processed locally") from exc


def match_frames(db, user_id, frames):
    rows = list(db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == user_id)))
    references = [
        (r, ref)
        for r in rows
        if r.status not in {"merged", "quarantined", "rejected"}
        for ref in r.data.get("visual_references", [])
        if ref.get("signature")
    ]
    matches, unusable = [], set()
    for frame in frames:
        query = frame["signature"]
        for row, ref in references:
            try:
                result = compare(query, ref["signature"])
            except (ValueError, KeyError, TypeError):
                # One damaged reference image must not fail the whole reel analysis.
                unusable.add(ref.get("url", ""))
                continue
            if result["matched"]:
                matches.append(
                    {
                        "spot_id": row.id,
                        "reference_url": ref["url"],
                        "page_url": ref["page_url"],
                        "timestamp_seconds": frame["seconds"],
                        **result,
                    }
                )
    return {
        "reference_count": len(references),
        "frame_count": len(frames),
        "unusable_reference_count": len(unusable),
        "matches": matches,
        "status": "candidate_matches" if matches else "no_match" if references else "no_references",
        "limitation": "Only indexed page images were compared. This is not worldwide visual geolocation or independent venue confirmation.",
    }
