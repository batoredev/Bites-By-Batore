"""Isolated reconciliation parity and bounded expensive identity comparisons."""

import hashlib
from copy import deepcopy
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app import spots
from app.db import Audit, Base, IdentifiedSpot, make_engine
from app.spot_identity import possible_match


class ExhaustiveReference:
    """The original all-pairs candidate selection and fuzzy predicate."""

    def __init__(self, rows):
        self.rows = rows

    def update(self, row):
        pass

    def branch_candidates(self, row):
        return self.rows

    duplicate_candidates = source_candidates = branch_candidates

    def possible_names(self, left, right):
        return possible_match(left, right)


@pytest.fixture
def isolated_sessions(tmp_path):
    engines = [make_engine("sqlite:///" + str(tmp_path / f"reconcile-{i}.db")) for i in range(2)]
    for engine in engines:
        Base.metadata.create_all(engine)
    yield [sessionmaker(engine, expire_on_commit=False) for engine in engines]
    for engine in engines:
        engine.dispose()


def varied_rows():
    fixtures = [
        ("Amber", "RS Puram", {"aliases": ["Jade"], "sources": [{"url": "https://fixture.test/a"}]}),
        ("Amber Cafe", "RS Puram", {"sources": [{"url": "https://fixture.test/a"}]}),
        ("Jade", "RS Puram", {"sources": [{"url": "https://fixture.test/a"}]}),
        ("Copper Kitchen", "", {"maps_identity": {"place_key": "pid:matching-identity"}}),
        ("Totally Different", "", {"maps_identity": {"place_key": "pid:matching-identity"}}),
        ("Copper Kitchen", "", {"maps_identity": {"place_key": "pid:different-identity"}}),
        ("Saffron Patio", "RS Puram", {"address": "No 17, Main Street"}),
        ("Saffron Patia", "RS Puram", {"address": "No 19, Main Street"}),
        ("Café Zircon", "Peelamedu", {}),
        ("Cafe Zircon", "Peelamedu", {}),
        ("Unresolved Banyan", "", {"sources": [{"url": "https://fixture.test/b"}]}),
        ("Unresolved Banyan", "", {"sources": [{"url": "https://fixture.test/c"}]}),
        ("Eden Eats", "", {"sources": [{"url": "https://fixture.test/shared"}],
                              "observations": [{"text": "A quiet dining room", "basis": "visual",
                                                "source_url": "https://fixture.test/shared"}]}),
        ("Ruby Bakes", "", {"sources": [{"url": "https://fixture.test/shared"}]}),
        ("new cafe", "", {}),
        ("நிலா உணவகம்", "", {}),
        ("The Copper Kitchen", "", {"strict_identity": True,
                                      "coordinates": {"lat": 11.0, "lng": 77.0}}),
        ("The Copper Kitchen", "", {"strict_identity": True,
                                      "coordinates": {"lat": 11.1, "lng": 77.1}}),
    ]
    rows = [
        IdentifiedSpot(id=f"row-{i:03}", identity_key=f"identity-{i}", user_id="owner", name=name,
                       area=area, category="food", data=deepcopy(data), status="identified", venue_id="",
                       created_at=f"2026-11-08T00:00:{i:02}+00:00")
        for i, (name, area, data) in enumerate(fixtures)
    ]
    rows.extend([
        IdentifiedSpot(id="retained-held", identity_key="held", user_id="owner", name="Amber",
                       data={"retained_evidence": True}, status="quarantined", venue_id=""),
        IdentifiedSpot(id="other-owner", identity_key="other", user_id="other", name="Amber",
                       data={"private_evidence": True}, status="identified", venue_id=""),
    ])
    return rows


def snapshot(db):
    return {
        row.id: (row.name, row.area, row.status, row.venue_id, deepcopy(row.data))
        for row in db.scalars(select(IdentifiedSpot))
    }


def test_indexed_reconciliation_matches_exhaustive_reference(isolated_sessions, monkeypatch):
    outputs = []
    for index, factory in enumerate(isolated_sessions):
        with factory() as db:
            db.add_all(varied_rows())
            db.commit()
            with monkeypatch.context() as patch:
                if index == 0:
                    patch.setattr(spots, "_ReconciliationIndex", ExhaustiveReference)
                counts = spots.reconcile_spots(db, "owner")
                db.commit()
                actions = [(a.action, a.target, a.detail) for a in db.scalars(select(Audit))]
                outputs.append((counts, snapshot(db), actions))
    assert outputs[0] == outputs[1]
    counts, rows, _ = outputs[1]
    assert counts["merged"] >= 4
    assert rows["row-002"][2] == "merged"  # Alias introduced by an earlier merge remains searchable.
    assert rows["row-003"][2] == "merged"  # Explicit matching Maps IDs bypass different names.
    assert rows["row-005"][2] != "merged"  # Conflicting Maps IDs remain separate.
    assert rows["row-012"][4]["unassigned_observations"]
    assert rows["retained-held"][4] == {"retained_evidence": True}
    assert rows["other-owner"][4] == {"private_evidence": True}
    assert all(row[3] == "" for row in rows.values())


def test_cached_fuzzy_matching_preserves_direction_and_normalization():
    names = ["Café Zircon", "Cafe Zircon", "Zircon restaurant", "The Zircon", "Zircon Patio",
             "Zircon Patia", "AB C", "A BC", "cafe", "restaurant", "", "&",
             "tide", "diet", "நிலா உணவகம்", "நிலா காபி"]
    index = spots._ReconciliationIndex([])
    for left in names:
        for right in names:
            assert index.possible_names(left, right) == possible_match(left, right)


def test_distinct_inventory_avoids_all_pairs_branch_normalization(isolated_sessions, monkeypatch):
    count = 160
    with isolated_sessions[0]() as db:
        db.add_all([
            IdentifiedSpot(id=f"distinct-{i}", identity_key=f"distinct-{i}", user_id="owner",
                           name="Merchant " + hashlib.sha256(str(i).encode()).hexdigest()[:12],
                           area="", data={"sources": [{"url": f"https://fixture.test/{i}"}]},
                           status="identified", venue_id="")
            for i in range(count)
        ])
        db.commit()
        calls = SimpleNamespace(branch=0)
        original = spots.same_branch

        def counted(*args):
            calls.branch += 1
            return original(*args)

        monkeypatch.setattr(spots, "same_branch", counted)
        counts = spots.reconcile_spots(db, "owner")
        db.commit()
        assert calls.branch < count * 4
        assert counts["merged"] == counts["quarantined"] == 0
        assert len(snapshot(db)) == count
