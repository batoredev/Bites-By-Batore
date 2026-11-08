"""Bounded first-party inventory collection into private, unapproved spot drafts."""

import json
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from .config import ROOT
from .db import now
from .providers import Unavailable, DeferredCollection
from .spots import upsert_spot, unique
from .web_evidence import read_official_html, VisibleText


def save_target(db, user_id, seed, data):
    """Explicit configured cross-reference joins evidence, never confirms identity or facts."""
    if seed.get("target_source_url"):
        from sqlalchemy import select
        from .db import IdentifiedSpot
        from .spots import INACTIVE, merge_data
        from .spot_identity import name_key

        matches = [
            r
            for r in db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == user_id))
            if r.status not in INACTIVE
            and name_key(r.name) == name_key(seed["name"])
            and r.area == seed.get("area", "")
            and any(s.get("url") == seed["target_source_url"] for s in r.data.get("sources", []))
        ]
        if len(matches) == 1:
            matches[0].data = merge_data(matches[0].data, data)
            matches[0].updated_at = now()
            return matches[0]
    return upsert_spot(db, user_id, seed["name"], seed["category"], seed.get("area", ""), data)


class Document(HTMLParser):
    def __init__(self, url):
        super().__init__()
        self.url, self.links, self.items = url, [], []
        self.capture, self.parts, self.last_name = "", [], ""
        self.images = []
        self.ld_active, self.ld_parts, self.ld_documents = False, [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self.ld_active, self.ld_parts = True, []
        if tag == "meta" and attrs.get("property") in {"og:image", "og:image:url"} and attrs.get("content"):
            self.images.append(urljoin(self.url, attrs["content"]))
        if tag == "a" and attrs.get("href"):
            url = urljoin(self.url, attrs["href"])
            if urlparse(url).scheme == "https" and not urlparse(url).username:
                self.links.append(url)
        hook = attrs.get("data-hook")
        if hook in {"item.name", "item.price"}:
            self.capture, self.parts = hook, []

    def handle_data(self, value):
        if self.ld_active:
            self.ld_parts.append(value)
        if self.capture:
            self.parts.append(value)

    def handle_endtag(self, tag):
        if tag == "script" and self.ld_active:
            try:
                self.ld_documents.append(json.loads("".join(self.ld_parts)))
            except (ValueError, RecursionError):
                pass
            self.ld_active, self.ld_parts = False, []
        if self.capture and tag == "span":
            text = "".join(self.parts).strip()
            if self.capture == "item.name":
                self.last_name = text
            elif self.last_name and re.fullmatch(r"[₹]\s*[\d,]+(?:\.\d{1,2})?", text):
                self.items.append(
                    {
                        "name": self.last_name,
                        "price_inr": float(re.sub(r"[^\d.]", "", text)),
                        "unit": "item",
                        "source_url": self.url,
                        "basis": "First-party menu item and displayed price; current availability/taxes unconfirmed",
                    }
                )
            self.capture = ""


def structured_observations(documents, url):
    """Literal schema.org observations only; never infer prices/hours or approve facts."""
    result = {"offerings": [], "hours_candidates": [], "vibes": [], "menu_links": [], "structured_venues": []}
    pending = list(documents)
    while pending:
        value = pending.pop()
        if isinstance(value, list):
            pending.extend(value)
            continue
        if not isinstance(value, dict):
            continue
        pending.extend(v for v in value.values() if isinstance(v, (list, dict)))
        kind = value.get("@type", [])
        kinds = set(kind if isinstance(kind, list) else [kind])
        if "MenuItem" in kinds and isinstance(value.get("name"), str):
            offers = value.get("offers", [])
            for offer in offers if isinstance(offers, list) else [offers]:
                if not isinstance(offer, dict) or offer.get("priceCurrency") != "INR":
                    continue
                price = str(offer.get("price", "")).replace(",", "")
                if re.fullmatch(r"\d+(?:\.\d{1,2})?", price):
                    result["offerings"].append(
                        {
                            "name": value["name"],
                            "price_inr": float(price),
                            "unit": "item",
                            "source_url": url,
                            "basis": "Literal JSON-LD MenuItem/INR offer; branch, taxes and current availability unverified",
                        }
                    )
        if kinds & {
            "Restaurant",
            "CafeOrCoffeeShop",
            "FoodEstablishment",
            "LocalBusiness",
            "MovieTheater",
            "BowlingAlley",
            "AmusementPark",
        }:
            if value.get("name"):
                result["structured_venues"].append({"name": value["name"], "address": value.get("address")})
            raw_hours = value.get("openingHours", [])
            for hours in raw_hours if isinstance(raw_hours, list) else [raw_hours]:
                if isinstance(hours, str) and hours.strip():
                    result["hours_candidates"].append(
                        {
                            "value": hours,
                            "source_url": url,
                            "basis": "Literal website JSON-LD; current opening hours unverified",
                        }
                    )
            specifications = value.get("openingHoursSpecification", [])
            for spec in specifications if isinstance(specifications, list) else [specifications]:
                if isinstance(spec, dict) and spec.get("opens") and spec.get("closes"):
                    result["hours_candidates"].append(
                        {
                            "value": json.dumps(spec, ensure_ascii=False, sort_keys=True),
                            "source_url": url,
                            "basis": "Literal website hours specification; dates/branch/current applicability unverified",
                        }
                    )
            menu = value.get("hasMenu") or value.get("menu")
            if isinstance(menu, str):
                target = urljoin(url, menu)
                if urlparse(target).scheme == "https" and urlparse(target).hostname == urlparse(url).hostname:
                    result["menu_links"].append(target)
            amenities = value.get("amenityFeature", [])
            for feature in amenities if isinstance(amenities, list) else [amenities]:
                if not isinstance(feature, dict) or feature.get("value") not in (True, "true"):
                    continue
                label = str(feature.get("name", "")).casefold()
                tag = {"outdoor seating": "outdoor", "rooftop": "rooftop", "live music": "live_music"}.get(
                    label
                )
                if tag:
                    result["vibes"].append(
                        {
                            "tag": tag,
                            "evidence": feature["name"],
                            "source_url": url,
                            "basis": "Explicit website amenity statement; current branch/vibe unverified",
                        }
                    )
    return result


def parse_document(html, url):
    document, visible = Document(url), VisibleText()
    document.feed(html)
    visible.feed(html)
    structured = structured_observations(document.ld_documents, url)
    links = unique(document.links)
    maps = [
        u
        for u in links
        if urlparse(u).hostname in {"www.google.com", "maps.google.com", "goo.gl", "maps.app.goo.gl"}
        and ("maps" in u or "goo.gl" in u)
    ]
    menu = [
        u
        for u in links
        if urlparse(u).hostname == urlparse(url).hostname and re.search(r"/menu(?:[/?#]|$)", u, re.I)
    ]
    coordinates = None
    for link in maps:
        match = re.search(r"/maps/dir//(-?\d+\.\d+),(-?\d+\.\d+)(?:[/?#]|$)", link)
        if match:
            lat, lng = float(match[1]), float(match[2])
            if 10.6 <= lat <= 11.4 and 76.5 <= lng <= 77.4:
                coordinates = {
                    "lat": lat,
                    "lng": lng,
                    "source_url": url,
                    "basis": "Destination coordinates in first-party directions link; entrance unconfirmed",
                }
    return {
        "maps_links": maps,
        "menu_links": unique(menu + structured["menu_links"]),
        "coordinates": coordinates,
        "offerings": unique(document.items + structured["offerings"]),
        "hours_candidates": unique(structured["hours_candidates"]),
        "vibes": unique(structured["vibes"]),
        "structured_venues": unique(structured["structured_venues"]),
        "image_links": unique(document.images)[:2],
        "text": "\n".join(visible.parts),
    }


def collect_inventory(db, user_id):
    seeds = json.loads((ROOT / "resources" / "coimbatore-spot-seeds.json").read_text(encoding="utf-8"))[
        "spots"
    ]
    cache, rows, gaps = {}, [], []
    for seed in seeds:
        url = seed["url"]
        try:
            if url not in cache:
                cache[url] = parse_document(read_official_html(db, url), url)
            doc = cache[url]
            if "visual_references" not in doc:
                from .visual_places import fetch_reference

                doc["visual_references"] = []
                for image_url in doc["image_links"]:
                    try:
                        doc["visual_references"].append(fetch_reference(db, image_url, url))
                    except DeferredCollection:
                        raise
                    except Unavailable as exc:
                        gaps.append({"name": seed["name"], "field": "visual_reference", "reason": str(exc)})
            text = doc["text"]
            data = {
                "sources": [
                    {
                        "url": url,
                        "type": "official",
                        "collected_at": now(),
                        "published_at": None,
                        "basis": "First-party page fetched; undated unless explicitly stated",
                    }
                ],
                "maps_links": doc["maps_links"],
                "menu_links": doc["menu_links"],
                "coordinates": doc["coordinates"],
                "visual_references": doc["visual_references"],
                "offerings": doc["offerings"],
                "review_notes": [
                    "Current branch, operation, menus, vibes and fees still require operator review. Collection does not establish customer suitability."
                ],
            }
            # Each configured fact is tied to a literal, branch-specific phrase on
            # the freshly fetched first-party page. Missing/changed text is a gap.
            for fact in seed.get("facts", []):
                needles = fact.get("requires", [])
                if all(" ".join(n.casefold().split()) in " ".join(text.casefold().split()) for n in needles):
                    field, value = fact["field"], fact["value"]
                    if field in {"vibes", "offerings"}:
                        value = [
                            {**v, "source_url": url, "basis": "First-party description; unapproved"}
                            for v in value
                        ]
                    data[field] = value
                else:
                    gaps.append(
                        {
                            "name": seed["name"],
                            "field": fact["field"],
                            "reason": "Expected first-party text was not found",
                        }
                    )
            for menu_url in doc["menu_links"][:2]:
                if menu_url == url:
                    continue
                try:
                    if menu_url not in cache:
                        cache[menu_url] = parse_document(read_official_html(db, menu_url), menu_url)
                    data["offerings"] = unique(data.get("offerings", []) + cache[menu_url]["offerings"])
                    data["sources"].append(
                        {
                            "url": menu_url,
                            "type": "official_menu",
                            "collected_at": now(),
                            "published_at": None,
                            "basis": "Menu prices are item prices, not a per-person outing cost",
                        }
                    )
                except DeferredCollection:
                    raise
                except Unavailable as exc:
                    gaps.append({"name": seed["name"], "url": menu_url, "reason": str(exc)})
            row = save_target(db, user_id, seed, data)
        except DeferredCollection:
            db.commit()
            raise
        except Unavailable as exc:
            gaps.append({"name": seed["name"], "url": url, "reason": str(exc)})
            row = upsert_spot(
                db,
                user_id,
                seed["name"],
                seed["category"],
                seed.get("area", ""),
                {
                    "sources": [
                        {
                            "url": url,
                            "type": "official_lead",
                            "collected_at": now(),
                            "basis": "Page unavailable; no page facts accepted",
                        }
                    ]
                },
            )
        if row:
            rows.append(row.id)
        db.commit()
    return {"identified_spots": len(set(rows)), "pages_read": len(cache), "gaps": gaps, "published": 0}
