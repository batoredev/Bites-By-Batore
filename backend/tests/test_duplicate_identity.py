"""Pure evidence-policy fixtures. These names/addresses are invented."""

from types import SimpleNamespace

import pytest

from app.duplicate_identity import assess_pair, identity_conflicts, name_variant_key


def spot(name="Zircon Cafe", area="", **data):
    return SimpleNamespace(name=name, area=area, data=data)


def point(lat=11.01, lng=76.96):
    return {"lat": lat, "lng": lng, "basis": "Unverified fixture lead"}


def test_name_variants_preserve_order_and_remove_standalone_suffixes():
    assert name_variant_key("l'affinage") == name_variant_key("laffinage.coimbatore") == "laffinage"
    assert name_variant_key("Zircon Café, R.S. Puram") == "zircon"
    assert name_variant_key("CoASTT Kartmania") == "coastt kartmania"
    assert name_variant_key("Coast Kart Mania") == "coast kart mania"
    assert name_variant_key("Zircon Ember") != name_variant_key("Ember Zircon")
    assert name_variant_key("Café") == ""


@pytest.mark.parametrize(
    "extra",
    [
        {},
        {"area": "RS Puram"},
        {"sources": [{"url": "https://fixture.test/shared-chain-homepage"}]},
        {"sources": [{"url": "https://www.instagram.com/reel/fixture/"}]},
    ],
)
def test_name_area_and_shared_url_alone_are_review(extra):
    assert assess_pair(spot(**extra), spot(**extra))["decision"] == "review"


def test_maps_reference_is_strong_but_does_not_create_confirmation():
    data = {"maps_identity": {"place_key": "pid:fixture"}}
    a, b = spot(**data), spot("A renamed fixture", **data)
    result = assess_pair(a, b)
    assert result["decision"] == "merge"
    assert "confirmed_by" not in a.data["maps_identity"]
    assert "confirmed_by" not in b.data["maps_identity"]


def test_same_osm_object_strong_different_object_is_not_proof():
    assert (
        assess_pair(spot(directory_refs=["node/123"]), spot(directory_refs=["node/123"]))["decision"]
        == "merge"
    )
    assert (
        assess_pair(spot(directory_refs=["node/123"]), spot(directory_refs=["way/123"]))["decision"]
        == "review"
    )


@pytest.mark.parametrize(
    "address_a,address_b",
    [
        ("No. 14, Main Rd, R.S. Puram, Coimbatore 641002", "14 Main Road, RS Puram, 641002"),
        ("Door No 14A, Fixture St, 641002", "14A, Fixture Street, Coimbatore 641002"),
        ("14/1, Fixture Avenue, 641002", "No. 14/1 Fixture Ave, 641002"),
        ("D B Road, Coimbatore 641002", "D B Rd, 641002"),
    ],
)
def test_detailed_addresses_accept_safe_formatting_variants(address_a, address_b):
    result = assess_pair(spot(address=address_a), spot(address=address_b))
    assert result["decision"] == "merge", result


def test_directory_address_clues_and_structured_components():
    a = spot(address_clues=["14", "Fixture Road", "RS Puram", "641002"])
    b = spot(address_components={"house_number": "14", "street": "Fixture Rd", "postcode": "641002"})
    assert assess_pair(a, b)["decision"] == "merge"


@pytest.mark.parametrize(
    "address",
    [
        "RS Puram",
        "641002",
        "No 14",
        "Main Road",
        "Near No 14, Main Road, 641002",
        "Opposite Fixture Cafe, No. 14 Main Road, 641002",
        "Behind Fixture Park, Main Road 641002",
    ],
)
def test_short_addresses_and_landmarks_are_not_own_address_anchors(address):
    assert assess_pair(spot(address=address), spot(address=address))["decision"] == "review"


@pytest.mark.parametrize(
    "left,right,fragment",
    [
        ({"maps_identity": {"place_key": "pid:one"}}, {"maps_identity": {"place_key": "pid:two"}}, "Maps"),
        ({"branch_key": "north"}, {"branch_key": "south"}, "branch"),
        ({"address": "No 14, Fixture Road"}, {"address": "No 25, Fixture Road"}, "house"),
        ({"address": "Fixture Road, 641002"}, {"address": "Fixture Road, 641004"}, "postcode"),
        ({"address": "No 14, Fixture Road"}, {"address": "No 14, Another Road"}, "street"),
        ({"address": "Shop 2, No 14 Main Road"}, {"address": "Shop 3, No 14 Main Road"}, "unit"),
        ({"coordinates": point()}, {"coordinates": point(lat=11.1)}, "150"),
    ],
)
def test_conflicting_branch_evidence_blocks_merges(left, right, fragment):
    a, b = spot(**left), spot(**right)
    conflicts = identity_conflicts(a, b)
    assert any(fragment.lower() in c.lower() for c in conflicts)
    assert assess_pair(a, b)["decision"] == "separate"


def test_neighbourhood_conflicts_block_even_close_points():
    a = spot(area="RS Puram", coordinates=point())
    b = spot(area="Peelamedu", coordinates=point())
    assert assess_pair(a, b)["decision"] == "separate"


@pytest.mark.parametrize(
    "anchor",
    [
        {"maps_identity": {"place_key": "pid:fixture"}},
        {"directory_refs": ["node/123"]},
    ],
)
def test_stable_anchor_cannot_override_concrete_address_conflict(anchor):
    a = spot(address="No 14, Fixture Road", **anchor)
    b = spot(address="No 25, Fixture Road", **anchor)
    assert assess_pair(a, b)["decision"] == "separate"


def test_close_coordinates_require_names_or_explicit_aliases():
    assert assess_pair(spot(coordinates=point()), spot(coordinates=point(lat=11.0101)))["decision"] == "merge"
    assert (
        assess_pair(spot(coordinates=point()), spot("An unrelated business", coordinates=point()))["decision"]
        == "separate"
    )
    a = spot("Canonical Fixture", aliases=["Zircon Cafe"], coordinates=point())
    assert assess_pair(a, spot(coordinates=point()))["decision"] == "merge"
    assert "Compatible normalized names" in assess_pair(a, spot(coordinates=point()))["reasons"][0]


def test_coordinate_threshold_does_not_merge_a_spelling_guess():
    assert (
        assess_pair(spot("G Chat Corner", coordinates=point()), spot("G-Chaat Corner", coordinates=point()))[
            "decision"
        ]
        == "review"
    )
    assert (
        assess_pair(spot(coordinates=point()), spot(coordinates=point(lat=11.0105)))["decision"] == "review"
    )


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), "NaN", 999, True])
def test_invalid_coordinate_evidence_never_merges(invalid):
    a, b = spot(coordinates=point(lat=invalid)), spot(coordinates=point())
    assert identity_conflicts(a, b)
    assert assess_pair(a, b)["decision"] == "separate"


def test_cross_script_unknowns_remain_review_without_model_inference():
    assert assess_pair(spot("நிலா உணவகம்"), spot("Nila Restaurant"))["decision"] == "review"
    assert (
        assess_pair(
            spot("நிலா உணவகம்", aliases=["Nila Restaurant"], coordinates=point()),
            spot("Nila Restaurant", coordinates=point()),
        )["decision"]
        == "merge"
    )


def test_triads_require_all_pairs_not_transitive_bridge_merge():
    a = spot(address="No 14, Fixture Road", coordinates=point())
    bridge = spot(coordinates=point())
    c = spot(address="No 25, Fixture Road", coordinates=point())
    assert assess_pair(a, bridge)["decision"] == "merge"
    assert assess_pair(bridge, c)["decision"] == "merge"
    assert assess_pair(a, c)["decision"] == "separate"


def test_ambiguous_internal_address_cannot_be_repaired_by_shared_stable_id():
    a = spot(
        maps_identity={"place_key": "pid:fixture"},
        address_clues=["No 14, Fixture Road", "No 25, Fixture Road"],
    )
    b = spot(maps_identity={"place_key": "pid:fixture"}, address="No 14, Fixture Road")
    assert assess_pair(a, b)["decision"] == "review"


def test_flat_and_nested_candidate_dicts_are_supported_without_mutation():
    a = {"name": "Zircon Cafe", "coordinates": point()}
    b = {"name": "Zircon Cafe", "area": "", "data": {"coordinates": point()}}
    assert assess_pair(a, b)["decision"] == "merge"
    assert "maps_identity" not in a
