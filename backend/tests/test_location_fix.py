"""The owner corrects a wrong location by pasting a Maps link, a share link or coordinates."""

import pytest
from fastapi import HTTPException

from app import spots_api


def test_typed_coordinates_are_accepted_inside_coimbatore():
    point = spots_api._link_point(" 11.0203, 76.9612 ")
    assert (point["lat"], point["lng"]) == (11.0203, 76.9612)
    assert point["source_url"] == "https://www.google.com/maps?q=11.0203,76.9612"
    with pytest.raises(HTTPException) as far:
        spots_api._link_point("13.0827, 80.2707")  # Chennai
    assert "40 km" in far.value.detail


def test_the_place_pin_wins_over_the_map_centre():
    link = ("https://www.google.com/maps/place/Brew+Corner/@11.0100,76.9500,17z/"
            "data=!3m1!4b1!4m6!3m5!1s0x0:0x0!8m2!3d11.0123!4d76.9567")
    point = spots_api._link_point(link)
    assert (point["lat"], point["lng"]) == (11.0123, 76.9567)


def test_share_links_are_followed_and_other_sites_refused(monkeypatch):
    monkeypatch.setattr(spots_api, "_resolve_short",
                        lambda url: "https://www.google.com/maps/place/X/@11.02,76.95,17z/data=!3d11.0211!4d76.9533")
    point = spots_api._link_point("https://maps.app.goo.gl/AbC123")
    assert (point["lat"], point["lng"]) == (11.0211, 76.9533)
    for bad in ("https://evil.example/maps/@11.0,76.9", "http://www.google.com/maps/@11.0,76.9,17z", "not a link"):
        with pytest.raises(HTTPException):
            spots_api._link_point(bad)


def test_short_link_resolver_never_leaves_google():
    with pytest.raises(HTTPException):
        spots_api._resolve_short("https://evil.example/x")
