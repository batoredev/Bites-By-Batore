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


class Document(HTMLParser):
    def __init__(self, url):
        super().__init__()
        self.url, self.links, self.items = url, [], []
        self.capture, self.parts, self.last_name = "", [], ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            url = urljoin(self.url, attrs["href"])
            if urlparse(url).scheme == "https" and not urlparse(url).username:
                self.links.append(url)
        hook = attrs.get("data-hook")
        if hook in {"item.name", "item.price"}:
            self.capture, self.parts = hook, []

    def handle_data(self, value):
        if self.capture:
            self.parts.append(value)

    def handle_endtag(self, tag):
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


def parse_document(html, url):
    document, visible = Document(url), VisibleText()
    document.feed(html)
    visible.feed(html)
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
        "menu_links": menu,
        "coordinates": coordinates,
        "offerings": unique(document.items),
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
            row = upsert_spot(db, user_id, seed["name"], seed["category"], seed.get("area", ""), data)
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
