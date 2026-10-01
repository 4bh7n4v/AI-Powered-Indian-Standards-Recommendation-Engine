"""Stage 5 - Review & Deliver: recommendation cards and ready-to-paste tender clauses."""
from ..knowledge import KnowledgeBase
from ..pipeline.expand import certification

CERT_CLAUSE = {
    "en": {
        "BIS_ISI": "The product shall bear the Standard Mark (ISI Mark) under a valid licence from the Bureau of Indian Standards.",
        "CRS": "The product shall be registered with the Bureau of Indian Standards under the Compulsory Registration Scheme, and the registration number shall be marked on it.",
        "HALLMARKING": "The articles shall be hallmarked by a BIS-recognised Assaying and Hallmarking Centre and carry a valid HUID.",
    },
    "hi": {
        "BIS_ISI": "उत्पाद पर भारतीय मानक ब्यूरो के वैध लाइसेंस के अंतर्गत मानक चिह्न (आईएसआई मार्क) अंकित होना चाहिए।",
        "CRS": "उत्पाद भारतीय मानक ब्यूरो की अनिवार्य पंजीकरण योजना के अंतर्गत पंजीकृत होना चाहिए और उस पर पंजीकरण संख्या अंकित होनी चाहिए।",
        "HALLMARKING": "वस्तुओं पर बीआईएस-मान्यता प्राप्त परख एवं हॉलमार्किंग केंद्र द्वारा हॉलमार्क तथा वैध एचयूआईडी अंकित होना चाहिए।",
    },
}
TEST_CLAUSE = {
    "en": "Tests shall be carried out as per {tests}.",
    "hi": "परीक्षण {tests} के अनुसार किए जाएँगे।",
}
MAIN_CLAUSE = {
    "en": "The {item} shall conform to {std} ({title}), latest edition with all amendments.",
    "hi": "{item} भारतीय मानक {std} ({title}) के नवीनतम संस्करण, सभी संशोधनों सहित, के अनुरूप होगा।",
}
DEFAULT_ITEM = {"en": "product", "hi": "उत्पाद"}


def tender_clause(kb: KnowledgeBase, s: dict, allied_groups: dict, lang: str = "en", item: str | None = None) -> str:
    lang = lang if lang in MAIN_CLAUSE else "en"
    parts = [MAIN_CLAUSE[lang].format(item=item or DEFAULT_ITEM[lang], std=kb.label(s), title=s["title"])]
    tests = [a["label"] for a in allied_groups.get("test_method", [])]
    if tests:
        parts.append(TEST_CLAUSE[lang].format(tests=", ".join(tests)))
    for c in certification(kb, s):
        if c["scheme"]:
            parts.append(CERT_CLAUSE[lang][c["scheme"]])
    return " ".join(parts)
