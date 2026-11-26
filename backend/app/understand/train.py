"""Train the understanding model locally and score it on the frozen test.

Usage (from backend/):  python -m app.understand.train [--examples 12000] [--epochs 6]

Writes models/understand-v1.json (the weights) and models/understand-v1.report.json (scores
on generated held-out data and on the frozen test, next to the keyword baseline). Any
generated request identical to a frozen-test request is dropped before training.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

from . import evaluate, generate
from .baseline import keyword_reading
from .model import CURRENT, Understander
from .reading import expected


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Bites' understanding model")
    parser.add_argument("--examples", type=int, default=12000)
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    started = time.perf_counter()
    train = generate.dataset(args.examples, seed=args.seed)
    held_out = generate.dataset(2000, seed=args.seed + 1000)
    frozen = evaluate.load()
    frozen_b = evaluate.load(evaluate.FROZEN_B)
    frozen_c = evaluate.load(evaluate.FROZEN_C)
    frozen_texts = {c["text"].casefold().strip() for c in frozen + frozen_b + frozen_c}
    # Short requests ("surprise me", "bowling") can come out identical to a frozen request.
    # Those are dropped so the model never sees an exam sentence.
    before = len(train)
    train = [ex for ex in train if ex["text"].casefold().strip() not in frozen_texts]
    held_out = [ex for ex in held_out if ex["text"].casefold().strip() not in frozen_texts]
    dropped = before - len(train)
    print(f"dropped {dropped} generated requests identical to frozen-test requests")

    model = Understander(meta={"version": "understand-v1", "examples": args.examples, "epochs": args.epochs,
                               "seed": args.seed})
    model.train(train, epochs=args.epochs)
    trained_seconds = round(time.perf_counter() - started, 1)

    held_cases = [{"line": i, "text": ex["text"], "expect": expected(ex["reading"])} for i, ex in enumerate(held_out)]
    held = evaluate.score(model.read, held_cases)
    frozen_model = evaluate.score(model.read, frozen)
    frozen_keyword = evaluate.score(keyword_reading, frozen)
    blind_model = evaluate.score(model.read, frozen_b)
    blind_keyword = evaluate.score(keyword_reading, frozen_b)
    final_model = evaluate.score(model.read, frozen_c)
    final_keyword = evaluate.score(keyword_reading, frozen_c)
    t0 = time.perf_counter()
    for case in frozen:
        model.read(case["text"])
    ms_per_request = round((time.perf_counter() - t0) * 1000 / len(frozen), 2)

    model.meta.update({
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "train_seconds": trained_seconds,
        "frozen": {k: frozen_model[k] for k in ("field_accuracy", "mentioned_accuracy", "exact_requests", "critical")},
        "frozen_b": {k: blind_model[k] for k in ("field_accuracy", "mentioned_accuracy", "exact_requests", "critical")},
        "frozen_c": {k: final_model[k] for k in ("field_accuracy", "mentioned_accuracy", "exact_requests", "critical")},
    })
    model.save(CURRENT)
    report = {
        "meta": model.meta,
        "ms_per_request": ms_per_request,
        "held_out_generated": {k: held[k] for k in ("cases", "field_accuracy", "mentioned_accuracy", "exact_requests")},
        "frozen_model": {k: v for k, v in frozen_model.items() if k != "failures"},
        "frozen_keyword_baseline": {k: v for k, v in frozen_keyword.items() if k != "failures"},
        "frozen_failures": frozen_model["failures"],
        "frozen_b_model": {k: v for k, v in blind_model.items() if k != "failures"},
        "frozen_b_keyword_baseline": {k: v for k, v in blind_keyword.items() if k != "failures"},
        "frozen_b_failures": blind_model["failures"],
        "frozen_c_model": {k: v for k, v in final_model.items() if k != "failures"},
        "frozen_c_keyword_baseline": {k: v for k, v in final_keyword.items() if k != "failures"},
        "frozen_c_failures": final_model["failures"],
    }
    CURRENT.with_suffix(".report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    size_kb = round(CURRENT.stat().st_size / 1024)
    print(f"trained in {trained_seconds}s on {args.examples} examples; model {size_kb} KB; {ms_per_request} ms/request")
    print(f"held-out generated: when mentioned {held['mentioned_accuracy']:.1%}, exact {held['exact_requests']:.1%}")
    print(f"frozen test MODEL:   when mentioned {frozen_model['mentioned_accuracy']:.1%}, "
          f"exact {frozen_model['exact_requests']:.1%}, critical "
          + ", ".join(f"{k} {v:.0%}" for k, v in frozen_model["critical"].items()))
    print(f"frozen test KEYWORD: when mentioned {frozen_keyword['mentioned_accuracy']:.1%}, "
          f"exact {frozen_keyword['exact_requests']:.1%}")
    print(f"BLIND test B MODEL:  when mentioned {blind_model['mentioned_accuracy']:.1%}, "
          f"exact {blind_model['exact_requests']:.1%}, critical "
          + ", ".join(f"{k} {v:.0%}" for k, v in blind_model["critical"].items()))
    print(f"BLIND test B KEYWORD: when mentioned {blind_keyword['mentioned_accuracy']:.1%}, "
          f"exact {blind_keyword['exact_requests']:.1%}")
    print(f"BLIND test C MODEL:  when mentioned {final_model['mentioned_accuracy']:.1%}, "
          f"exact {final_model['exact_requests']:.1%}, critical "
          + ", ".join(f"{k} {v:.0%}" for k, v in final_model["critical"].items()))
    print(f"BLIND test C KEYWORD: when mentioned {final_keyword['mentioned_accuracy']:.1%}, "
          f"exact {final_keyword['exact_requests']:.1%}")


if __name__ == "__main__":
    main()
