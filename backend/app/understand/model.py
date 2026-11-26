"""Bites' own understanding model, trained from scratch on the laptop, run on any CPU.

Two kinds of averaged perceptron, the classic fast linear learner:
- a word tagger that marks where a detail sits (PARTY, BUDGET, DURATION, AREA, INTEREST,
  AVOID, STOPS), reading each word with its neighbours, its shape and the word lists;
- small sentence classifiers for everything said in other ways: categories, veg, kids,
  wheelchair, surprise, out of scope, time of day, mood, novelty, transport, budget unit.
Numbers inside tagged spans are read by values.py, never learned. The trained weights are
one JSON file (models/understand-vN.json) loaded once; reading a request takes about a
millisecond and needs no GPU or cloud API.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

from . import values
from .lexicon import AREA_KEYS, CATEGORY_OF_WORD, INTERESTS, NUMBER_WORDS, normalize, phrase_hits
from .reading import MOODS, NOVELTY, TIMES, TRANSPORT, Reading

MODEL_DIR = Path(__file__).with_name("models")
CURRENT = MODEL_DIR / "understand-v1.json"
SPAN_TAGS = ("PARTY", "BUDGET", "DURATION", "AREA", "INTEREST", "AVOID", "STOPS")
TAGS = ["O"] + [f"{p}-{t}" for t in SPAN_TAGS for p in "BI"]
CATEGORY_IDS = ("food", "street_food", "cafe", "dessert", "nightlife", "cinema", "gaming", "bowling",
                "adventure", "amusement", "park", "workshop", "attraction", "sports")
CLASSIFIERS = {
    **{f"cat:{c}": ["no", "yes"] for c in CATEGORY_IDS},
    "vegetarian": ["no", "yes"], "children": ["no", "yes"], "wheelchair": ["no", "yes"],
    "surprise": ["no", "yes"], "out_of_scope": ["no", "yes"],
    "time_of_day": ["none", *TIMES], "mood": ["none", *MOODS], "novelty": ["none", *NOVELTY],
    "transport": ["none", *TRANSPORT], "budget_unit": ["none", "person", "group"],
}
UNITS = {
    "time": {"hours", "minutes"},
    "people": {"people", "of", "us", "friends", "peru", "per", "pax", "persons", "kids", "guys", "perukku"},
    "money": {"rupees", "each", "head", "person", "total", "overall", "budget", "max", "under", "within", "upto"},
    "stop": {"stop", "stops", "places", "place"},
    "neg": {"no", "not", "avoid", "without", "nothing"},
}
AREA_PHRASES = set(AREA_KEYS)
INTEREST_PHRASES = set(INTERESTS)
CATEGORY_PHRASES = set(CATEGORY_OF_WORD)


class Perceptron:
    """Averaged perceptron over string features. Ties go to the first (default) class."""

    def __init__(self, classes, weights=None):
        self.classes = list(classes)
        self.weights: dict[str, dict[str, float]] = weights or {}
        self._totals: dict = defaultdict(float)
        self._stamps: dict = defaultdict(int)
        self.i = 0

    def scores(self, feats):
        s = dict.fromkeys(self.classes, 0.0)
        for f in feats:
            w = self.weights.get(f)
            if w:
                for c, v in w.items():
                    s[c] += v
        return s

    def predict(self, feats):
        s = self.scores(feats)
        return max(self.classes, key=lambda c: (s[c], -self.classes.index(c)))

    def update(self, truth, guess, feats):
        self.i += 1
        if truth == guess:
            return
        for f in feats:
            w = self.weights.setdefault(f, {})
            for c, delta in ((truth, 1.0), (guess, -1.0)):
                key = (f, c)
                current = w.get(c, 0.0)
                self._totals[key] += (self.i - self._stamps[key]) * current
                self._stamps[key] = self.i
                w[c] = current + delta

    def average(self):
        for f, w in list(self.weights.items()):
            for c, v in list(w.items()):
                key = (f, c)
                total = self._totals[key] + (self.i - self._stamps[key]) * v
                avg = round(total / max(self.i, 1), 4)
                if avg:
                    w[c] = avg
                else:
                    del w[c]
            if not w:
                del self.weights[f]


def _shape(word: str) -> str:
    if word.isdigit():
        return "d"
    if word.endswith("k") and word[:-1].replace(",", "").replace(".", "").isdigit():
        return "dk"
    if any(ch.isdigit() for ch in word):
        return "dx"
    if word in NUMBER_WORDS:
        return "nw"
    return "x" if word.isalpha() else "p"


def gazetteer(words: list[str]) -> list[list[str]]:
    marks: list[list[str]] = [[] for _ in words]
    for name, phrases in (("AREA", AREA_PHRASES), ("INT", INTEREST_PHRASES), ("CAT", CATEGORY_PHRASES)):
        for start, end, _ in phrase_hits(words, phrases):
            for i in range(start, end):
                marks[i].append(f"{name}{'B' if i == start else 'I'}")
    for i, w in enumerate(words):
        for unit, vocab in UNITS.items():
            if w in vocab:
                marks[i].append("U:" + unit)
    return marks


def token_features(words, gaz, i, prev, prev2):
    def get(j):
        return words[j] if 0 <= j < len(words) else ("<s>" if j < 0 else "</s>")

    def gz(j):
        return "|".join(gaz[j]) if 0 <= j < len(words) else "-"

    w = words[i]
    feats = ["b", "w=" + w, "p1=" + prev, "p2=" + prev2 + ">" + prev, "w-1=" + get(i - 1), "w+1=" + get(i + 1),
             "w-2=" + get(i - 2), "w+2=" + get(i + 2), "w-1w=" + get(i - 1) + ">" + w, "ww+1=" + w + ">" + get(i + 1),
             "suf3=" + w[-3:], "pre3=" + w[:3], "shape=" + _shape(w), "shape-1=" + _shape(get(i - 1)),
             "shape+1=" + _shape(get(i + 1)), "p1w=" + prev + ">" + w, "g=" + gz(i), "g-1=" + gz(i - 1),
             "g+1=" + gz(i + 1), "g+2=" + gz(i + 2), "w+1g+1=" + get(i + 1) + gz(i + 1)]
    feats.extend("gm=" + m for m in gaz[i])
    return feats


def sentence_features(words, gaz):
    feats = ["b"] + ["u=" + w for w in words]
    feats += ["bi=" + a + "_" + b for a, b in zip(words, words[1:])]
    for _, _, phrase in phrase_hits(words, INTEREST_PHRASES):
        feats.append("int_cat=" + INTERESTS[phrase])
    for _, _, phrase in phrase_hits(words, CATEGORY_PHRASES):
        feats.append("cat_word=" + CATEGORY_OF_WORD[phrase])
    if any("AREAB" in g for g in gaz):
        feats.append("has_area")
    if any(_shape(w) in ("d", "dk", "nw") for w in words):
        feats.append("has_number")
    if words:
        feats.append("first=" + words[0])
    return feats


class Understander:
    def __init__(self, tagger: Perceptron | None = None, classifiers: dict | None = None, meta: dict | None = None):
        self.tagger = tagger or Perceptron(TAGS)
        self.classifiers = classifiers or {name: Perceptron(classes) for name, classes in CLASSIFIERS.items()}
        self.meta = meta or {}

    # ---- training ----
    def train(self, examples: list[dict], epochs: int = 6, seed: int = 7, log=print):
        rng = random.Random(seed)
        data = [(ex["words"], ex["tags"], gazetteer(ex["words"]), self._targets(ex["reading"])) for ex in examples]
        for epoch in range(epochs):
            rng.shuffle(data)
            wrong_tags = 0
            for words, tags, gaz, targets in data:
                prev, prev2 = "<s>", "<s>"
                for i in range(len(words)):
                    feats = token_features(words, gaz, i, prev, prev2)
                    guess = self.tagger.predict(feats)
                    self.tagger.update(tags[i], guess, feats)
                    wrong_tags += guess != tags[i]
                    prev2, prev = prev, guess
                feats = sentence_features(words, gaz)
                for name, clf in self.classifiers.items():
                    clf.update(targets[name], clf.predict(feats), feats)
            log(f"epoch {epoch + 1}/{epochs}: tagger mistakes {wrong_tags}")
        self.tagger.average()
        for clf in self.classifiers.values():
            clf.average()

    @staticmethod
    def _targets(r: dict) -> dict:
        t = {f"cat:{c}": "yes" if c in r["categories"] else "no" for c in CATEGORY_IDS}
        for name in ("vegetarian", "children", "wheelchair", "surprise", "out_of_scope"):
            t[name] = "yes" if r[name] else "no"
        for name in ("time_of_day", "mood", "novelty", "transport", "budget_unit"):
            t[name] = r[name] or "none"
        return t

    # ---- reading ----
    def tag(self, words: list[str]) -> list[str]:
        gaz = gazetteer(words)
        tags, prev, prev2 = [], "<s>", "<s>"
        for i in range(len(words)):
            guess = self.tagger.predict(token_features(words, gaz, i, prev, prev2))
            if guess.startswith("I-") and prev[2:] != guess[2:]:
                guess = "B-" + guess[2:]
            tags.append(guess)
            prev2, prev = prev, guess
        return tags

    def read(self, text: str) -> dict:
        words = normalize(text)
        tags = self.tag(words)
        spans: dict[str, list[list[str]]] = defaultdict(list)
        for w, t in zip(words, tags):
            if t.startswith("B-"):
                spans[t[2:]].append([w])
            elif t.startswith("I-") and spans[t[2:]]:
                spans[t[2:]][-1].append(w)
        feats = sentence_features(words, gazetteer(words))
        said = {name: clf.predict(feats) for name, clf in self.classifiers.items()}
        r = Reading()
        r.interests = list(dict.fromkeys(" ".join(s) for s in spans["INTEREST"]))
        r.avoid = list(dict.fromkeys(" ".join(s) for s in spans["AVOID"]))
        cats = [c for c in CATEGORY_IDS if said[f"cat:{c}"] == "yes"]
        # "meals" is served by restaurants and messes alike, so it doesn't name a category by itself.
        cats += [INTERESTS[i] for i in r.interests if i in INTERESTS and i not in {"meals"}]
        r.categories = list(dict.fromkeys(cats))
        r.party_size = next((v for v in (values.people(s) for s in spans["PARTY"]) if v), None)
        r.budget = next((v for v in (values.rupees(s) for s in spans["BUDGET"]) if v), None)
        r.duration_minutes = next((v for v in (values.minutes(s) for s in spans["DURATION"]) if v), None)
        r.max_stops = next((v for v in (values.stops(s) for s in spans["STOPS"]) if v), None)
        if spans["AREA"]:
            key = " ".join(spans["AREA"][0])
            r.area = AREA_KEYS.get(key, key.title())
        for name in ("vegetarian", "children", "wheelchair", "surprise", "out_of_scope"):
            setattr(r, name, said[name] == "yes")
        for name in ("time_of_day", "mood", "novelty", "transport"):
            setattr(r, name, None if said[name] == "none" else said[name])
        r.budget_unit = None if r.budget is None or said["budget_unit"] == "none" else said["budget_unit"]
        return r.as_dict()

    # ---- files ----
    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        blob = {"meta": self.meta, "tagger": self.tagger.weights,
                "classifiers": {name: clf.weights for name, clf in self.classifiers.items()}}
        path.write_text(json.dumps(blob, separators=(",", ":"), sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Understander":
        blob = json.loads(Path(path).read_text(encoding="utf-8"))
        tagger = Perceptron(TAGS, blob["tagger"])
        classifiers = {name: Perceptron(CLASSIFIERS[name], blob["classifiers"].get(name, {})) for name in CLASSIFIERS}
        return cls(tagger, classifiers, blob.get("meta", {}))


_loaded: Understander | None = None


def read(text: str) -> dict:
    """Read one request with the current shipped model."""
    global _loaded
    if _loaded is None:
        if not CURRENT.exists():
            raise FileNotFoundError(f"No trained model at {CURRENT}; run python -m app.understand.train")
        _loaded = Understander.load(CURRENT)
    return _loaded.read(text)
