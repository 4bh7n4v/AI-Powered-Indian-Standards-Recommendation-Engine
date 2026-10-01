"""Retrieval evaluation: Recall@5, MRR, abstention accuracy and false-recommendation rate.

Usage (from backend/):  python -m eval.run_eval
"""
import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("ISRE_VAR_DIR", tempfile.mkdtemp(prefix="isre-eval-"))

from app.knowledge import load_kb
from app.pipeline.retrieve import Retriever


def main() -> None:
    golden = json.loads((Path(__file__).parent / "golden.json").read_text(encoding="utf-8"))["queries"]
    r = Retriever(load_kb())
    pos = [g for g in golden if g["expected"]]
    neg = [g for g in golden if not g["expected"]]
    hits5 = mrr = 0.0
    misses = []
    for g in pos:
        ids = [h.id for h in r.search(g["q"], 5).hits]
        rank = next((i for i, sid in enumerate(ids) if sid in g["expected"]), None)
        if rank is not None:
            hits5 += 1
            mrr += 1 / (rank + 1)
        else:
            misses.append((g["q"], ids[:3]))
    abstain_ok = sum(1 for g in neg if r.search(g["q"], 5).abstained)
    print(f"Retrieval mode      : {r.mode}")
    print(f"Queries             : {len(pos)} with an answer, {len(neg)} with no applicable IS")
    print(f"Recall@5            : {hits5 / len(pos):.2f}")
    print(f"MRR                 : {mrr / len(pos):.2f}")
    print(f"Correct abstentions : {abstain_ok}/{len(neg)}")
    print(f"False recommendations on no-answer queries: {len(neg) - abstain_ok}/{len(neg)}")
    for q, ids in misses:
        print(f"  MISS  {q!r} -> {ids}")


if __name__ == "__main__":
    main()
