from pathlib import Path

from app.citations import find_citations

SAMPLES = Path(__file__).resolve().parents[2] / "samples"


def top(client, query):
    r = client.post("/api/recommend", json={"query": query, "top_k": 3})
    assert r.status_code == 200
    return r.json()


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["standards"] > 30


def test_citation_parser():
    c = find_citations("conforming to IS 1554 (Part 1):1988 and IS: 1786-2008, IS/IEC 60529")
    assert [(x.number, x.part, x.year, x.iec) for x in c] == [
        ("1554", "1", 1988, False), ("1786", None, 2008, False), ("60529", None, None, True)]
    assert find_citations("IS 10322 (Part 5/Sec 3):2012")[0].candidate_ids[0] == "IS-10322-P5-S3"


def test_semantic_product_query(client):
    body = top(client, "TMT reinforcement bars Fe 500D for building construction")
    first = body["results"][0]
    assert first["standard"]["id"] == "IS-1786"
    assert first["certification"][0]["scheme"] == "BIS_ISI"
    assert {"test_method", "normative_ref", "installation"} <= set(first["allied"])
    assert "IS 1786:2008" in first["clause"]


def test_hindi_query(client):
    body = top(client, "बिजली के तार घरेलू वायरिंग के लिए")
    assert body["detected_language"]["code"] == "hi"
    assert body["results"][0]["standard"]["id"] == "IS-694"


def test_hindi_clause_output(client):
    r = client.post("/api/recommend", json={"query": "22 carat gold jewellery", "output_language": "hi"}).json()
    assert r["results"][0]["standard"]["id"] == "IS-1417"
    assert "हॉलमार्क" in r["results"][0]["clause"]


def test_abstains_on_services(client):
    body = top(client, "housekeeping services for office building")
    assert body["abstained"] and body["results"] == []


def test_exact_citation_and_outdated_edition(client):
    body = top(client, "cables as per IS 694:1990")
    first = body["results"][0]
    assert first["standard"]["id"] == "IS-694"
    assert first["version"]["cited_is_outdated"] is True


def test_test_method_intent(client):
    assert top(client, "tensile test method for steel bars")["results"][0]["standard"]["category"] == "test_method"


def analyse(client, name):
    with open(SAMPLES / name, "rb") as f:
        r = client.post("/api/tender/analyse", files={"file": (name, f)})
    assert r.status_code == 200, name
    return r.json()


def test_tender_health_check_formats(client):
    for ext in ("txt", "docx", "pdf"):
        body = analyse(client, f"03_engineering_college_hostel.{ext}")
        items = {i["index"]: i for i in body["items"]}
        assert len(items) == 5
        assert "outdated" in [f["kind"] for f in items[1]["findings"]]
        assert "missing" in [f["kind"] for f in items[3]["findings"]]
        assert "not_in_registry" in [f["kind"] for f in items[5]["findings"]]


def test_sample_tender_statuses(client):
    expected = {
        "01_office_complex_construction.pdf": "acceptable",
        "02_district_hospital_electrification.docx": "partially_acceptable",
        "03_engineering_college_hostel.txt": "not_acceptable",
        "04_regional_office_facility_services.pdf": "not_applicable",
        "05_government_school_building.docx": "partially_acceptable",
        "06_engineering_college_hostel_scanned.pdf": "unreadable",
    }
    for name, status in expected.items():
        assert analyse(client, name)["summary"]["status"] == status, name


def test_rejects_unsupported_file(client):
    r = client.post("/api/tender/analyse", files={"file": ("x.exe", b"MZ")})
    assert r.status_code == 415


def test_standard_lookup_and_feedback(client):
    assert client.get("/api/standards/IS-694").json()["label"] == "IS 694:2010"
    assert client.get("/api/standards/NOPE").status_code == 404
    rid = top(client, "LED street light")["request_id"]
    assert client.post("/api/feedback", json={"request_id": rid, "standard_id": "IS-10322-P5-S3",
                                              "decision": "accept"}).status_code == 200
    assert client.get("/api/audit/verify").json()["intact"] is True
