"""Knowledge base: IS registry, allied-standards edges and certification rule packs."""
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache

import yaml

from .citations import Citation
from .config import DATA_DIR


@dataclass
class KnowledgeBase:
    meta: dict
    standards: dict[str, dict]
    edges: list[tuple[str, str, str]]
    edge_meta: dict
    cert: dict
    glossary: dict[str, str]
    by_number: dict[str, list[str]] = field(default_factory=dict)

    def __post_init__(self):
        for sid, s in self.standards.items():
            num = re.search(r"\d{2,5}", s["number"]).group(0)
            self.by_number.setdefault(num, []).append(sid)

    def get(self, sid: str) -> dict | None:
        return self.standards.get(sid)

    def resolve(self, c: Citation) -> dict | None:
        """Map a citation to a registry record, falling back to 'all parts' records."""
        for cid in c.candidate_ids:
            if cid in self.standards:
                return self.standards[cid]
        ids = self.by_number.get(c.number, [])
        if len(ids) == 1:
            return self.standards[ids[0]]
        return None

    def label(self, s: dict) -> str:
        return f"{s['number']}:{s['year']}" if s.get("year") else s["number"]


def _load_json(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_kb() -> KnowledgeBase:
    std = _load_json("standards.json")
    edges = _load_json("edges.json")
    cert = yaml.safe_load((DATA_DIR / "certification_rules.yaml").read_text(encoding="utf-8"))
    glossary = _load_json("glossary.json")["terms"]
    standards = {s["id"]: s for s in std["standards"]}
    edge_list = [tuple(e) for e in edges["edges"]]
    for a, b, _ in edge_list:
        if a not in standards or b not in standards:
            raise ValueError(f"Edge refers to unknown standard: {a} -> {b}")
    return KnowledgeBase(std["meta"], standards, edge_list, edges["meta"], cert, glossary)
