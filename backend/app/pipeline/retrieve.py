"""Stage 3 - Retrieve: hybrid lexical + dense search, fusion, rerank, abstention.

* Lexical: BM25 over title, scope and keywords, with exact IS-number matching.
* Dense (optional): BGE-M3 embeddings on the ORIGINAL query text, so Hindi works
  without translation. Enabled automatically when sentence-transformers is installed.
* Fusion: Reciprocal Rank Fusion; optional cross-encoder rerank.
* Abstention: below the confidence threshold the engine says "no applicable IS found".
"""
import hashlib
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from ..citations import CITATION_RE, find_citations
from ..config import ABSTAIN_THRESHOLD, DATA_DIR, DENSE_MODE, EMBED_MODEL, RERANK_MODEL
from ..knowledge import KnowledgeBase

log = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"[a-z][a-z0-9]*|[ऀ-෿]+")
STOPWORDS = set("""
a an the and or of for to in on at by with from as is are be shall should must will may can this that these those
it its into per all any each other such than then there their used use using up including include includes
supply supplying supplied providing provide delivery deliver install installation_work item items qty quantity nos no
number specification specifications spec specs required requirement requirements conform conforming confirm
standard standards indian bis is tender make brand approved equivalent good quality new complete set type
suitable general need needed want looking find recommend recommendation please procurement procure purchase buy
""".split())
# words that say the user wants a specific kind of standard, not the product spec
INTENT = {
    "test_method": {"test", "testing", "method", "assay", "measurement", "measure"},
    "installation": {"installation", "install", "laying", "code", "practice", "fixing", "erection"},
    "terminology": {"glossary", "term", "terminology", "definition", "vocabulary"},
    "safety": {"safety", "safe", "hazard"},
}
DENSE_FLOOR, DENSE_SPAN = 0.35, 0.35  # cosine -> confidence mapping for BGE-M3


def stem(tok: str) -> str:
    if not tok.isascii() or len(tok) <= 3:
        return tok
    if tok.endswith("ies") and len(tok) > 4:
        return tok[:-3] + "y"
    if tok.endswith(("ches", "shes", "sses", "xes")):
        return tok[:-2]
    if tok.endswith("s") and not tok.endswith("ss"):
        return tok[:-1]
    return tok


def tokenize(text: str) -> list[str]:
    return [stem(t) for t in TOKEN_RE.findall(text.lower()) if len(t) > 1 and t not in STOPWORDS]


@dataclass
class Hit:
    id: str
    score: float
    confidence: float
    matched_terms: list[str] = field(default_factory=list)
    lexical_rank: int | None = None
    dense_rank: int | None = None
    dense_similarity: float | None = None
    cited: bool = False


@dataclass
class RetrievalResult:
    hits: list[Hit]
    abstained: bool
    reason: str | None
    expanded_terms: list[str]
    mode: str


class BM25:
    def __init__(self, docs: dict[str, list[str]], k1: float = 1.5, b: float = 0.75):
        self.docs = {d: Counter(toks) for d, toks in docs.items()}
        self.len = {d: len(t) for d, t in docs.items()}
        self.avg = sum(self.len.values()) / max(len(docs), 1)
        n = len(docs)
        df = Counter(t for toks in docs.values() for t in set(toks))
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.mean_idf = sum(self.idf.values()) / max(len(self.idf), 1)
        self.k1, self.b = k1, b

    def score(self, q: list[str], d: str) -> float:
        tf, s = self.docs[d], 0.0
        for t in q:
            if t in tf:
                f = tf[t]
                s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[d] / self.avg))
        return s

    def coverage(self, q: list[str], d: str) -> tuple[float, list[str]]:
        """Lexical confidence (0..1): the larger of
        - the IDF-weighted share of query terms found in the document (short queries), and
        - the absolute IDF mass matched, saturating at ~4 distinctive terms (long tender items)."""
        uniq = list(dict.fromkeys(q))
        if not uniq:
            return 0.0, []
        total = sum(self.idf.get(t, self.mean_idf) for t in uniq)
        matched = [t for t in uniq if t in self.docs[d]]
        mass = sum(self.idf[t] for t in matched)
        return max(mass / total, min(1.0, mass / (4 * self.mean_idf))), matched


class DenseIndex:
    """BGE-M3 dense embeddings, cached on disk. Disabled when the library is missing."""

    def __init__(self, texts: dict[str, str]):
        self.ids = list(texts)
        self.model = None
        self.status = "off"
        if DENSE_MODE == "off":
            return
        try:
            import numpy as np
            from sentence_transformers import SentenceTransformer
        except ImportError:
            self.status = "not installed (pip install -r requirements-ml.txt)"
            return
        try:
            self.np = np
            self.model = SentenceTransformer(EMBED_MODEL)
            key = hashlib.sha256((EMBED_MODEL + "".join(texts.values())).encode()).hexdigest()[:16]
            cache = Path(DATA_DIR) / "cache" / f"emb_{key}.npy"
            if cache.exists():
                self.matrix = np.load(cache)
            else:
                self.matrix = self.model.encode(list(texts.values()), normalize_embeddings=True)
                cache.parent.mkdir(exist_ok=True)
                np.save(cache, self.matrix)
            self.status = f"on ({EMBED_MODEL})"
        except Exception as exc:  # model download or load failure
            log.warning("Dense retrieval disabled: %s", exc)
            self.model, self.status = None, f"failed to load: {exc}"

    def search(self, query: str, k: int = 20) -> list[tuple[str, float]]:
        if not self.model:
            return []
        q = self.model.encode([query], normalize_embeddings=True)[0]
        sims = self.matrix @ q
        order = self.np.argsort(-sims)[:k]
        return [(self.ids[i], float(sims[i])) for i in order]


class Retriever:
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        texts, toks = {}, {}
        for sid, s in kb.standards.items():
            kw = " ".join(s.get("keywords", []))
            texts[sid] = f"{s['number']} {s['title']}. {s['scope']} Keywords: {kw}"
            toks[sid] = tokenize(f"{s['title']} {s['scope']} {kw} {kw}")
        self.bm25 = BM25(toks)
        self.dense = DenseIndex(texts)
        self.texts = texts
        self.reranker = None
        if RERANK_MODEL and self.dense.model:
            try:
                from sentence_transformers import CrossEncoder
                self.reranker = CrossEncoder(RERANK_MODEL)
            except Exception as exc:
                log.warning("Reranker disabled: %s", exc)

    @property
    def mode(self) -> str:
        parts = ["BM25 + exact IS number"]
        if self.dense.model:
            parts.append(f"dense {EMBED_MODEL}")
        if self.reranker:
            parts.append(f"rerank {RERANK_MODEL}")
        return " + ".join(parts)

    def expand(self, text: str) -> tuple[list[str], list[str]]:
        """Tokenize and add English glossary terms for Hindi / Hinglish words."""
        raw = TOKEN_RE.findall(text.lower())
        extra = []
        for t in raw:
            if t in self.kb.glossary:
                extra.extend(self.kb.glossary[t].lower().split())
        for key, val in self.kb.glossary.items():  # Devanagari words attached to suffixes
            if not key.isascii() and key in text and key not in raw:
                extra.extend(val.lower().split())
        toks = tokenize(text) + [stem(t) for t in extra if t not in STOPWORDS]
        return toks, list(dict.fromkeys(extra))

    def search(self, text: str, top_k: int = 5) -> RetrievalResult:
        # citations are matched exactly below; drop them from the free-text query
        q, expanded = self.expand(CITATION_RE.sub(" ", text))
        # 1. exact citations of known standards always come first
        cited = []
        for c in find_citations(text):
            rec = self.kb.resolve(c)
            if rec and rec["id"] not in cited:
                cited.append(rec["id"])
        # 2. lexical ranking
        lex = sorted(((sid, self.bm25.score(q, sid)) for sid in self.kb.standards), key=lambda x: -x[1])
        lex = [(sid, s) for sid, s in lex if s > 0]
        lex_rank = {sid: i for i, (sid, _) in enumerate(lex)}
        # 3. dense ranking
        dense = self.dense.search(text)
        dense_rank = {sid: i for i, (sid, _) in enumerate(dense)}
        dense_sim = dict(dense)
        words = set(TOKEN_RE.findall(text.lower())) | set(q)
        wanted = {cat for cat, keys in INTENT.items() if words & keys}
        specificity = min(1.0, (len(set(q)) + 1) / 4)  # one-word queries are not "certain"
        # 4. reciprocal rank fusion
        fused: dict[str, float] = {}
        for ranks in (lex_rank, dense_rank):
            for sid, r in ranks.items():
                fused[sid] = fused.get(sid, 0.0) + 1.0 / (60 + r)
        hits = []
        for sid, score in fused.items():
            cov, matched = self.bm25.coverage(q, sid)
            conf = cov * specificity
            if sid in dense_sim:
                conf = max(conf, min(1.0, max(0.0, (dense_sim[sid] - DENSE_FLOOR) / DENSE_SPAN)))
            category = self.kb.standards[sid]["category"]
            if category in wanted:
                score += 0.003
            elif category == "product" and not wanted:
                score += 0.0001  # tie-breaker: product specifications are the primary answer
            hits.append(Hit(sid, score, round(conf, 3), matched, lex_rank.get(sid), dense_rank.get(sid),
                            round(dense_sim[sid], 3) if sid in dense_sim else None))
        hits.sort(key=lambda h: (-h.score, -h.confidence))
        if self.reranker and hits:
            top = hits[:10]
            scores = self.reranker.predict([(text, self.texts[h.id]) for h in top])
            top = [h for _, h in sorted(zip(scores, top), key=lambda x: -x[0])]
            hits = top + hits[10:]
        for sid in reversed(cited):
            hits = [h for h in hits if h.id != sid]
            hits.insert(0, Hit(sid, 1.0, 1.0, [], cited=True))
        hits = [h for h in hits if h.cited or h.confidence >= ABSTAIN_THRESHOLD * 0.75][:top_k]
        if not hits or hits[0].confidence < ABSTAIN_THRESHOLD:
            return RetrievalResult([], True, "No applicable Indian Standard found in the registry with "
                                   "enough confidence. The item may be a service, or outside the "
                                   "domains covered by the current data.", expanded, self.mode)
        return RetrievalResult(hits, False, None, expanded, self.mode)
