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


def test_pptx_and_html_inputs(client):
    deck = analyse(client, "07_district_hospital_presentation.pptx")
    assert deck["document"]["type"] == "pptx" and deck["summary"]["status"] == "partially_acceptable"
    html = (b"<html><head><style>p{}</style><script>var x=1;</script></head><body><h1>Tender</h1>"
            b"<p>1. Reinforcement steel: TMT bars Fe 500, conforming to IS 1786:1985.</p>"
            b"<p>2. Housekeeping services for the office building, daily cleaning.</p></body></html>")
    body = client.post("/api/tender/analyse", files={"file": ("tender.html", html)}).json()
    assert body["summary"]["items"] == 2
    assert "var x" not in body["items"][0]["text"]
    assert body["items"][0]["status"] == "not_acceptable"


def test_evidence_snapshots(client):
    body = analyse(client, "03_engineering_college_hostel.pdf")
    first = body["items"][0]["evidence"]
    assert first and first["page"] == 1 and first["highlights"] >= 1
    img = client.get(first["image"])
    assert img.status_code == 200 and img.content[:4] == b"\x89PNG"
    assert client.get("/api/snapshots/..%2Faudit.jsonl").status_code == 404
    assert all(i["evidence"] is None for i in analyse(client, "03_engineering_college_hostel.docx")["items"])


def test_history_and_stats(client):
    body = analyse(client, "02_district_hospital_electrification.docx")
    rows = client.get("/api/history?kind=tender").json()["checks"]
    assert rows[0]["id"] == body["request_id"] and rows[0]["status"] == "partially_acceptable" and rows[0]["reopen"]
    saved = client.get(f"/api/history/{body['request_id']}").json()
    assert saved["summary"] == body["summary"]
    assert client.get("/api/history/000000000000").status_code == 404
    s = client.get("/api/stats").json()
    assert s["checks"]["tenders"] >= 1 and s["tenders_by_status"]["partially_acceptable"] >= 1
    assert s["items"]["total"] >= 5 and s["recent"]


def test_analyse_url(client):
    import functools
    import http.server
    import threading

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SAMPLES))
    handler.log_message = lambda *a: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/03_engineering_college_hostel.pdf"
        body = client.post("/api/tender/analyse-url", json={"url": url}).json()
        assert body["document"]["source"] == "link" and body["summary"]["status"] == "not_acceptable"
        missing = client.post("/api/tender/analyse-url", json={"url": url.replace("03_", "99_")})
        assert missing.status_code == 422
    finally:
        server.shutdown()
    assert client.post("/api/tender/analyse-url", json={"url": "ftp://example.com/x.pdf"}).status_code == 422


def test_demo_seed(client):
    before = client.get("/api/stats").json()["checks"]["total"]
    added = client.post("/api/demo/seed").json()["checks_added"]
    assert added == 12
    assert client.get("/api/stats").json()["checks"]["total"] == before + added


def test_standard_lookup_and_feedback(client):
    assert client.get("/api/standards/IS-694").json()["label"] == "IS 694:2010"
    assert client.get("/api/standards/NOPE").status_code == 404
    rid = top(client, "LED street light")["request_id"]
    assert client.post("/api/feedback", json={"request_id": rid, "standard_id": "IS-10322-P5-S3",
                                              "decision": "accept"}).status_code == 200
    assert client.get("/api/audit/verify").json()["intact"] is True
