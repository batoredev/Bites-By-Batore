"""Score a reader on the frozen test, field by field.

A reader is any function text -> dict of Reading fields. For each field we report:
- when mentioned: how often the reader got it right when the request says it;
- stayed empty: how often it left the field at its default when the request doesn't say it
  (a reader that invents details fails here);
- overall: right across every request.
Critical fields (party size, budget, unit, vegetarian) must reach 100% before release.

Usage (from backend/):  python -m app.understand.evaluate [--reader keyword] [--show 15]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .reading import CRITICAL, FIELDS, LIST_FIELDS, Reading, expected

FROZEN = Path(__file__).with_name("frozen_test.jsonl")
# Written after v1's mistakes on FROZEN were studied, before v2 was trained, so it stays blind.
FROZEN_B = Path(__file__).with_name("frozen_test_b.jsonl")
# Written before the final v1 training run and scored once, with no changes after: the honest number.
FROZEN_C = Path(__file__).with_name("frozen_test_c.jsonl")


def load(path: Path = FROZEN) -> list[dict]:
    cases = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        case = json.loads(line)
        cases.append({"line": number, "text": case["text"], "expect": expected(case["expect"])})
    return cases


def _norm(field: str, value):
    if field in LIST_FIELDS:
        return sorted({str(v).strip().casefold() for v in (value or [])})
    if isinstance(value, str):
        return value.strip().casefold()
    return value


def score(reader, cases: list[dict]) -> dict:
    default = Reading().as_dict()
    fields = {f: {"mentioned": 0, "mentioned_right": 0, "silent": 0, "silent_right": 0} for f in FIELDS}
    exact, failures = 0, []
    for case in cases:
        got = {**default, **(reader(case["text"]) or {})}
        all_right = True
        for f in FIELDS:
            want, have = _norm(f, case["expect"][f]), _norm(f, got.get(f))
            right = want == have
            bucket = "mentioned" if want != _norm(f, default[f]) else "silent"
            fields[f][bucket] += 1
            fields[f][bucket + "_right"] += right
            if not right:
                all_right = False
                failures.append({"line": case["line"], "text": case["text"], "field": f,
                                 "expected": case["expect"][f], "got": got.get(f)})
        exact += all_right
    total = len(cases)
    report = {}
    for f, c in fields.items():
        report[f] = {
            "when_mentioned": round(c["mentioned_right"] / c["mentioned"], 3) if c["mentioned"] else None,
            "mentioned": c["mentioned"],
            "stayed_empty": round(c["silent_right"] / c["silent"], 3) if c["silent"] else None,
            "overall": round((c["mentioned_right"] + c["silent_right"]) / total, 3) if total else None,
        }
    right_fields = sum(c["mentioned_right"] + c["silent_right"] for c in fields.values())
    return {
        "cases": total,
        "field_accuracy": round(right_fields / (total * len(FIELDS)), 3) if total else None,
        "mentioned_accuracy": round(
            sum(c["mentioned_right"] for c in fields.values()) / max(1, sum(c["mentioned"] for c in fields.values())), 3),
        "exact_requests": round(exact / total, 3) if total else None,
        "critical": {f: report[f]["overall"] for f in CRITICAL},
        "fields": report,
        "failures": failures,
    }


def readers() -> dict:
    from .baseline import keyword_reading

    found = {"keyword": keyword_reading}
    try:
        from .model import read as model_read

        found["model"] = model_read
    except ImportError:
        pass
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a reader on the frozen test")
    parser.add_argument("--reader", default="keyword")
    parser.add_argument("--show", type=int, default=10, help="how many failures to print")
    args = parser.parse_args()
    result = score(readers()[args.reader], load())
    print(f"reader={args.reader}  cases={result['cases']}  field accuracy={result['field_accuracy']}  "
          f"when mentioned={result['mentioned_accuracy']}  exact requests={result['exact_requests']}")
    print(f"{'field':<17}{'when said':>10}{'(n)':>6}{'kept empty':>12}{'overall':>9}")
    for f, r in result["fields"].items():
        said = "-" if r["when_mentioned"] is None else f"{r['when_mentioned']:.0%}"
        empty = "-" if r["stayed_empty"] is None else f"{r['stayed_empty']:.0%}"
        print(f"{f:<17}{said:>10}{r['mentioned']:>6}{empty:>12}{r['overall']:>9.0%}")
    print("critical:", {k: f"{v:.0%}" for k, v in result["critical"].items()})
    for fail in result["failures"][: args.show]:
        print(f"  line {fail['line']}: {fail['field']} expected {fail['expected']!r} got {fail['got']!r} :: {fail['text']}")


if __name__ == "__main__":
    main()
