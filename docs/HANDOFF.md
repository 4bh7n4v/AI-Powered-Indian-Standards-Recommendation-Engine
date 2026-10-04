# Developer Handoff: Indian Standards Recommendation Engine

**Smart India Hackathon · PS 26108** · Department of Consumer Affairs · Team N0TH1NG
**Handoff date:** 2026-10-01 · **Data as of:** 2026-09-30 · **Version:** 0.1.0 (baseline prototype)

This document is for the developer taking over the project. After reading it you should be able to run the app, demonstrate every feature, understand how each part of the code works, and know what to build next. Every output quoted below was produced by the running app on the handoff date.

---

## Contents

1. [What the project does](#1-what-the-project-does)
2. [Run it in 2 minutes](#2-run-it-in-2-minutes)
3. [The website, tab by tab](#3-the-website-tab-by-tab)
4. [Demo script (8–10 minutes)](#4-demo-script-810-minutes)
5. [Scenario catalogue with verified results](#5-scenario-catalogue-with-verified-results)
6. [Architecture and code map](#6-architecture-and-code-map)
7. [How a request flows through the code](#7-how-a-request-flows-through-the-code)
8. [Data files and how to extend them](#8-data-files-and-how-to-extend-them)
9. [REST API reference](#9-rest-api-reference)
10. [Configuration](#10-configuration)
11. [Tests, evaluation, logs and audit](#11-tests-evaluation-logs-and-audit)
12. [Local development without Docker](#12-local-development-without-docker)
13. [Known issues and limitations](#13-known-issues-and-limitations)
14. [Roadmap: what to build next](#14-roadmap-what-to-build-next)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. What the project does

A procurement official either **describes a product** ("LED street light 90 W, IP66") or **uploads a tender document**. The engine returns:

| Output | Example |
|---|---|
| Applicable **Indian Standard(s)**, ranked, with evidence | IS 1786:2008 for TMT bars, with the matched words highlighted in its scope |
| **Allied standards** in six types: normative reference, test method, terminology, safety, installation, related product | IS 1608 (Part 1) tensile test for IS 1786 |
| **Current edition**, and a flag when the input cites an old one | "Cited edition 1990 is outdated · current IS 694:2010" |
| **Certification** that applies: ISI Mark (QCO), CRS or Hallmarking, with the order it comes from | "CRS registration" for LED luminaires |
| A **ready-to-paste tender clause** in English or Hindi | "The product shall conform to IS 10322 (Part 5/Sec 3):2012 …" |
| **Abstention** when nothing applies | "No applicable Indian Standard found" for housekeeping services |

The **Tender Health Check** reads a PDF, DOCX or TXT tender, splits it into items, and flags missing standards, outdated editions, missing test-method or safety standards, and certification the tender does not ask for. It then grades each item and the tender as a whole.

**Main design principle:** the engine prefers saying "I don't know" or "to verify" over giving a confident wrong answer. All seed data is marked `verified: false`, and the UI shows this.

---

## 2. Run it in 2 minutes

**Requirement:** Docker Desktop (Windows with WSL 2 or macOS) or Docker Engine with the Compose plugin (Linux).

```bash
docker compose up -d --build      # first build takes a few minutes
```

| Open | What |
|---|---|
| <http://localhost:8000> | Web app |
| <http://localhost:8000/docs> | Interactive API docs (Swagger) |
| <http://localhost:8000/api/health> | Engine status as JSON |

Check that it is up:

```bash
docker ps                                   # STATUS should say (healthy)
curl -s localhost:8000/api/health
# {"status":"ok","retrieval_mode":"BM25 + exact IS number", ..., "standards":37,"edges":49,"data_as_of":"2026-09-30", ...}
```

Common commands:

| Task | Command |
|---|---|
| Live log | `docker compose logs -f app` |
| Log report | `docker compose exec app python -m app.log_report` |
| Tests | `docker compose run --rm app python -m pytest -q` |
| Evaluation | `docker compose run --rm app python -m eval.run_eval` |
| Rebuild after code change | `docker compose up -d --build` |
| Stop | `docker compose down` |

The web UI is built into the image, so **any frontend or backend change needs a rebuild** (or use the dev setup in §12).

---

## 3. The website, tab by tab

The page has a header, four tabs and a footer.

### Header (always visible)

- Title, subtitle and the SIH PS number.
- **Output language** selector: *English* or *हिन्दी (Hindi)*. This changes the language of the **generated tender clauses** in both the Find Standards and Tender Health Check tabs. The rest of the UI stays in English.
- **Engine status pill:** green "Engine online · 37 standards · data as of 2026-09-30" when `/api/health` responds, and red "Engine offline" when it doesn't. Hover to see the dense-retrieval status.

### Tab 1: Find Standards (default)

1. A text box (up to 5000 characters). The **Find standards** button stays disabled until there are at least 3 characters. **Ctrl+Enter** (or **Cmd+Enter**) also submits.
2. **Six example chips** run a search with one click:
   - `TMT reinforcement bars Fe 500D for building construction`
   - `LED street light 90 W, IP66, aluminium housing`
   - `PVC insulated copper house wiring cable 1.5 sq mm`
   - `1000 litre overhead water storage tank`
   - `बिजली के तार घरेलू वायरिंग के लिए` (Hindi)
   - `Housekeeping services for office building` (shows abstention)
3. **Meta row:** the detected language, extracted attributes (materials, grades, quantities), glossary terms (for Hindi or Hinglish input) and the retrieval mode.
4. **Result cards**, ranked. Each card shows:
   - IS number, category tag, domain tag, title, and a confidence bar (or "Cited in input" when the user typed the IS number);
   - badges: current edition (red if the cited edition is outdated), amendments ("to be verified"), and certification (amber; "· to verify" because the source is not yet verified);
   - **Show details / Hide details** (the first card opens automatically):
     - **Why this standard?** The scope text with matched terms highlighted.
     - **Certification:** the scheme name, the order and the effective date.
     - **Allied standards:** a table grouped by type.
     - **Suggested tender clause**, with a **Copy** button.
     - **Accept / Reject** buttons, which write to the hash-chained audit log and then show "Accepted · recorded in audit log".
5. **Abstention:** a blue notice reading "No applicable Indian Standard found …" instead of cards.

### Tab 2: Tender Health Check

1. A **drop zone** (drag and drop a file), a **Choose file** button (PDF, DOCX or TXT, up to 10 MB), and a **"Use a sample tender…"** dropdown with the six samples.
2. **Overall result banner**, colour-coded: Acceptable, Partially acceptable, Not acceptable, No Indian Standard applies, or Could not read document. It includes counts of items per status.
3. **Four stat tiles:** items found, missing or outdated (high severity), incomplete (medium), and no applicable IS.
4. A document line with the file name, type, pages, the first 12 characters of the SHA-256 hash and the data date, plus any warnings (for example "Page 1 looks scanned; install PaddleOCR to read it.").
5. **One card per item:** item number, title, status pill, primary IS tag, the item text, and a **findings table** (severity, finding, suggested fix). It ends with a **suggested clause** and a **Copy** button when there are findings.

### Tab 3: Standards Registry

- A table of all 37 standards: Standard, Title, Type, Domain.
- **Domain dropdown filter** (5 domains) and a **text filter** that matches the IS number or title (for example `1786`).
- The header line says the data is "not yet verified against the BIS portal".

### Tab 4: Portal Integration

- A table of the main REST endpoints, a `curl` example, and a link to `/docs` (Swagger UI, where every endpoint can be tried live).

### Deep links (useful in demos)

| URL | Effect |
|---|---|
| `/?q=LED%20street%20light%2090%20W` | Opens Find Standards and runs the search on load |
| `/?tab=tender&sample=02` | Opens Tender Health Check and analyses sample 02 (use `01`–`06`) |
| `/?tab=registry`, `/?tab=api` | Opens that tab directly |

### Footer

A disclaimer that this is not an official Government of India service, and that the data is an illustrative seed to be verified on the BIS Standards Portal.

---

## 4. Demo script (8–10 minutes)

Open these tabs in the browser beforehand to save time. Every step below was verified against the running app.

| # | Time | Do this | Say / point at |
|---|---|---|---|
| 1 | 0:00 | Open `http://localhost:8000` | The green status pill shows the engine is live with 37 standards. Data is marked unverified on purpose. |
| 2 | 0:30 | Click the chip **TMT reinforcement bars Fe 500D…** | Top result **IS 1786:2008** at 100%. Open the details: matched terms are highlighted, the certification is **ISI Mark (QCO)** under the Steel QCO, allied standards include test methods IS 1608, IS 1599 and IS 228, and there is a ready tender clause. |
| 3 | 1:30 | Click **Accept** on card 1 and **Reject** on card 2 | Each decision goes into a hash-chained audit log. You can show this later at `/api/audit/verify` → `{"intact": true}`. |
| 4 | 2:00 | Type `PVC insulated cable as per IS 694:1990` and search | The badge turns red: **"Cited edition 1990 is outdated · current IS 694:2010"**. The card shows "Cited in input". |
| 5 | 2:45 | Click the Hindi chip **बिजली के तार घरेलू वायरिंग के लिए** | Language is detected as **Hindi**. The glossary expands it to *electrical, wire, cable, wiring*, and the top result is **IS 694:2010**. |
| 6 | 3:15 | Switch **Output language → हिन्दी**, then search `LED street light 90 W, IP66` | The tender clause is now in Hindi. Top result is IS 10322 (Part 5/Sec 3):2012 with **CRS registration**. |
| 7 | 3:45 | Click the **Housekeeping services** chip | **Abstention**: services have no IS, so the engine says so instead of guessing. |
| 8 | 4:15 | Switch back to English. Go to **Tender Health Check** and pick **Office Complex** | **Acceptable**: 5/5 items clean. This is what a good tender looks like. |
| 9 | 5:00 | Pick **District Hospital** | **Partially acceptable**: 2 acceptable, 2 need revision, 1 not acceptable. Item 3 cites the outdated IS 4985:2000; item 5 lacks safety and test standards and the CRS clause. Show the suggested fix and **Copy**. |
| 10 | 6:00 | Pick **Engineering College – Boys Hostel** | **Not acceptable**: 5 high and 11 medium findings. Outdated IS 1786:1985, IS 2062:1999 and IS 694:1990, a missing IS for the street light, and an unknown "IS 99999" flagged *check manually*. |
| 11 | 7:00 | Pick **Regional Office – Facility Services** | **No Indian Standard applies**: all 4 service items abstain. |
| 12 | 7:20 | Pick **सरकारी विद्यालय भवन** | A Hindi tender: **Partially acceptable**. Item 1 (सरिया) is clean; items 2 and 3 don't cite their IS. |
| 13 | 7:45 | Pick **Boys Hostel (scanned copy)** | **Could not read document**, with the warning that OCR is needed. The engine never gives a false "all clear" on a blank scan. |
| 14 | 8:15 | Go to **Standards Registry**, choose domain *Gold jewellery*, type `1786` | The registry is transparent and filterable. |
| 15 | 8:45 | Go to **Portal Integration**, then open `/docs` | GeM or CPPP can integrate through the OpenAPI REST API. Try `POST /api/recommend` live. |

**Fallback if the network or UI fails:** run the `curl` commands in §9. They show the same results.

---

## 5. Scenario catalogue with verified results

### 5.1 Find Standards

| Input | Detected | Top results (confidence) | Certification | Notes |
|---|---|---|---|---|
| TMT reinforcement bars Fe 500D for building construction | English | **IS 1786:2008** (1.00), IS 2502:1963 (0.40), IS 456:2000 (0.35) | ISI Mark (QCO) | Allied: 1 normative, 3 test, 1 terminology, 2 installation, 1 related |
| LED street light 90 W, IP66, aluminium housing | English | **IS 10322 (Part 5/Sec 3):2012** (0.65), IS 16105:2012 (0.37), IS/IEC 60529:2001 (0.28) | CRS registration | Has 2 safety allied standards |
| PVC insulated copper house wiring cable 1.5 sq mm | English | **IS 694:2010** (1.00), IS 8130:2013 (1.00), IS 1554 (Part 1):1988 (0.61) | ISI Mark (QCO) | |
| 1000 litre overhead water storage tank | English | **IS 12701:1996** (1.00), IS 7634 (Part 3):2003 (0.39) | No mandatory scheme found | |
| बिजली के तार घरेलू वायरिंग के लिए | **Hindi** | **IS 694:2010** (0.74), IS 732:2019 (0.42) | ISI Mark (QCO) | Glossary: electrical, wire, cable, wiring |
| Housekeeping services for office building | English | **Abstained** | — | A service, so no IS applies |
| Armoured XLPE aluminium power cable, 3.5 core, 95 sq mm, 1.1 kV | English | **IS 7098 (Part 1):1988** (0.98), IS 1554 (Part 1) (0.93), IS 8130 (0.86) | No mandatory scheme found | |
| 22 carat gold jewellery bangles | English | **IS 1417:2016** (0.73), IS 15820, IS 1418 (test methods) | Hallmarking (HUID) | |
| PVC insulated cable as per **IS 694:1990** | English | **IS 694:2010**, *cited in input*, **outdated = true** | ISI Mark (QCO) | Red "outdated edition" badge |
| sariya Fe 500 for slab casting (Hinglish) | English | **IS 1786:2008** (1.00) | ISI Mark (QCO) | Glossary: reinforcement, bar, tmt |
| laptop computers with 16 GB RAM | English | **Abstained** | — | Outside the 5 seeded domains |
| test method for tensile strength of rebar | English | **IS 1608 (Part 1):2018** (0.67), IS 10810, IS 12235 | — | Intent detection boosts the *test method* category |

**Example clause (English, LED):**
> The product shall conform to IS 10322 (Part 5/Sec 3):2012 (Luminaires - Part 5: Particular requirements - Section 3: Luminaires for road and street lighting), latest edition with all amendments. Tests shall be carried out as per IS/IEC 60529:2001, IS 16105:2012, IS 16106:2012. The product shall be registered with the Bureau of Indian Standards under the Compulsory Registration Scheme …

**Same clause in Hindi:**
> उत्पाद भारतीय मानक IS 10322 (Part 5/Sec 3):2012 (…) के नवीनतम संस्करण, सभी संशोधनों सहित, के अनुरूप होगा। परीक्षण IS/IEC 60529:2001, IS 16105:2012, IS 16106:2012 के अनुसार किए जाएँगे। …

### 5.2 Tender Health Check (`samples/`)

| Sample | Overall | Items | High / Medium / Info | Per-item highlights |
|---|---|---|---|---|
| 01 Office Complex (PDF) | **Acceptable** | 5 | 0 / 0 / 0 | All 5 acceptable: IS 1786, IS 694, IS 10322-5-3, IS 12701, IS 4985 |
| 02 District Hospital (DOCX) | **Partially acceptable** | 5 | 1 / 5 / 0 | Items 1 and 4 OK · item 2 lacks a test method · item 3 cites outdated **IS 4985:2000** · item 5 lacks test and safety standards and the CRS clause |
| 03 Engineering College Hostel (PDF or TXT) | **Not acceptable** | 5 | 5 / 11 / 1 | Outdated IS 1786:1985, IS 2062:1999 and IS 694:1990 · street light and gold items cite no IS · no certification clauses · **IS 99999** "not in the verified registry; check it manually" |
| 04 Regional Office Facility Services (PDF) | **No Indian Standard applies** | 4 | 0 / 0 / 0 | Housekeeping, security, catering and AC maintenance all abstain |
| 05 Government School Building, Hindi (DOCX) | **Partially acceptable** | 3 | 2 / 3 / 0 | सरिया item OK · बिजली के तार and पानी की टंकी items don't cite IS 694 or IS 12701 |
| 06 Hostel scanned (image-only PDF) | **Could not read document** | 0 | — | Warning: "Page 1 looks scanned; install PaddleOCR to read it." |

**How statuses are decided** (`backend/app/pipeline/expand.py`):

- **Finding severities:**
  - `high`: the primary IS is missing, or the cited edition is outdated;
  - `medium`: no test-method or safety standard is cited, or certification applies but isn't stated;
  - `low`: an IS is cited without an edition;
  - `info`: the cited IS is not in the registry.
- **Item status:**
  - any high finding → *Not acceptable*;
  - else any medium finding → *Needs revision*;
  - else → *Acceptable*;
  - no IS and no findings → *No applicable IS*.
- **Tender status** (ignores *No applicable IS* items):
  - all items acceptable → *Acceptable*;
  - no acceptable items and at least one not-acceptable → *Not acceptable*;
  - otherwise → *Partially acceptable*;
  - no text → *Could not read document*.

### 5.3 Validation and error scenarios

| Scenario | Result |
|---|---|
| Query shorter than 3 characters | UI button disabled · API returns **422** "String should have at least 3 characters" |
| Upload of an unsupported type (`.png`, no extension) | **415** "Unsupported file type … Use PDF, DOCX or TXT." shown as a red alert |
| Upload larger than 10 MB | **413** "File is larger than 10 MB." |
| Unknown standard `GET /api/standards/does-not-exist` | **404** "Unknown standard 'does-not-exist'." |
| Feedback with `decision: "maybe"` | **422** "Input should be 'accept' or 'reject'" |
| Any unhandled server error | **500** with `request_id`; the traceback goes to `logs/server.jsonl` |
| Backend down | Header pill turns red: "Engine offline" |

---

## 6. Architecture and code map

![Architecture](architecture.png)

```
Browser (React + TS, Vite)  ──HTTP──▶  FastAPI (backend/app/main.py)  ──▶  Engine (engine.py)
                                                                            │
     1 Ingest ──▶ 2 Understand ──▶ 3 Retrieve ──▶ 4 Expand & Annotate ──▶ 5 Deliver
     ingest.py    understand.py    retrieve.py    expand.py                deliver.py + audit.py
                                        │               │
                                   KnowledgeBase (knowledge.py) ◀── backend/data/*.json, *.yaml
```

### Backend (`backend/app/`, about 1,100 lines of Python)

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app, request-logging middleware (adds `X-Request-ID`), Pydantic request models, all `/api/*` routes, serves the built SPA from `frontend/dist` |
| `engine.py` | `Engine.recommend()` and `Engine.analyse_tender()`: run the 5 stages and build the JSON response. A singleton via `get_engine()` |
| `knowledge.py` | Loads `standards.json`, `edges.json`, `glossary.json` and `certification_rules.yaml` into `KnowledgeBase`; `resolve(citation)` maps "IS 694:1990" to a record |
| `citations.py` | Regex parser for IS citations: `IS 694:1990`, `IS 10322 (Part 5/Sec 3)`, `IS/IEC 60529` |
| `pipeline/ingest.py` | Stores uploads by SHA-256 in `var/documents/`; extracts text from PDF (PyMuPDF), DOCX (python-docx, including tables) and TXT; detects scanned pages and runs PaddleOCR if installed |
| `pipeline/understand.py` | `split_items()` (numbered tender items with line ranges), `detect_language()` (Devanagari and 8 other Indic scripts), `extract_attributes()` (rule-based, or Qwen2.5 via Ollama if configured) |
| `pipeline/retrieve.py` | `BM25` + glossary expansion + exact-citation boost + optional `DenseIndex` (BGE-M3) → Reciprocal Rank Fusion → optional cross-encoder rerank → confidence → **abstain if below `ABSTAIN_THRESHOLD`** |
| `pipeline/expand.py` | `allied()` (graph edges by type), `version()` (current vs. cited edition), `certification()` (rule pack), `health_check()`, `item_status()`, `tender_status()` |
| `pipeline/deliver.py` | `tender_clause()`: English or Hindi clause templates |
| `audit.py` | Append-only `var/audit.jsonl`; each entry stores the previous entry's hash; `verify()` checks the chain |
| `logs.py`, `log_report.py` | JSON-lines logging with daily rotation; a CLI report of request counts, latency percentiles, uploads and errors |
| `config.py` | All environment variables (see §10) |

### Frontend (`frontend/src/`)

| File | Responsibility |
|---|---|
| `App.tsx` | Tabs, language state, health polling, deep-link parsing (`?tab`, `?q`, `?sample`) |
| `api.ts` | `fetch` wrappers and the display labels for categories and allied types |
| `types.ts` | TypeScript types that mirror the API JSON |
| `components/RecommendPanel.tsx` | Find Standards tab |
| `components/ResultCard.tsx` | One recommendation: badges, details, allied table, clause, Accept/Reject |
| `components/TenderPanel.tsx` | Tender Health Check tab, the sample list and status texts |
| `components/RegistryPanel.tsx` | Registry table and filters |
| `components/ApiPanel.tsx` | Portal Integration tab |
| `components/Header.tsx`, `CopyButton.tsx` | Header with language and status; clipboard button |
| `styles.css` | All styling |

Sample tenders are served to the UI from `frontend/public/samples/` (a copy of `samples/`). **If you edit a sample, update both folders.**

### Other folders

| Path | Contents |
|---|---|
| `backend/data/` | The knowledge base (see §8) |
| `backend/eval/` | `golden.json` (28 labelled queries) and `run_eval.py` |
| `backend/tests/` | 12 pytest tests (`test_api.py`) |
| `backend/var/` | Runtime: `audit.jsonl` and `documents/` (uploads). Git-ignored, mounted into Docker |
| `logs/` | `server.jsonl` (+ daily rotations). Mounted into Docker |
| `samples/` | 6 demo tenders (TXT, DOCX, PDF) + `generate_samples.py` |
| `docs/` | Architecture diagrams (`.mmd` sources + `.png`) and this file |

---

## 7. How a request flows through the code

### `POST /api/recommend`

1. `main.recommend()` validates `RecommendRequest` (3–5000 characters, `top_k` 1–10, `en`/`hi`).
2. `Engine.recommend()`:
   - `detect_language()` and `extract_attributes()`;
   - `Retriever.search()`:
     1. strips IS citations from the text and expands Hindi or Hinglish words through the glossary;
     2. resolves exact citations; these are always ranked first, with confidence 1.0;
     3. scores BM25 on title + scope + keywords (the keywords count twice);
     4. adds the dense BGE-M3 ranking if installed;
     5. fuses the rankings with RRF (`1/(60+rank)`), adding small boosts for the category the user asked about (e.g. "test method") or, by default, for product specifications;
     6. sets confidence to BM25 term coverage × query specificity (or the dense similarity, if higher);
     7. **abstains** if the top confidence is below `0.30`.
   - For each hit, `_card()` builds the version (outdated check), certification, allied groups and clause.
   - `audit.record("recommend", …)` returns the `request_id` used later by feedback.

### `POST /api/tender/analyse`

1. `main.analyse_tender()` reads the file (rejects it if over 10 MB) and calls `Engine.analyse_tender()`.
2. `ingest()` stores the file by hash and extracts text (or returns OCR warnings); `UnsupportedDocument` becomes a 415 response.
3. `split_items()` splits the text into numbered items. For each item:
   - search with `top_k=3`;
   - the *primary* standard is the first hit whose category is `product`;
   - run `health_check()` and `item_status()`, and build a clause when there is a primary standard.
4. Count findings, compute `tender_status()`, and add an audit record.

### `POST /api/feedback`

Checks that the standard exists, then appends `{request_id, standard_id, decision, comment}` to the audit chain.

---

## 8. Data files and how to extend them

All data is an **illustrative seed**: 37 standards in 5 domains, 49 graph edges, 4 certification rules. Every record is `verified: false`.

| Domain key | Name | Standards |
|---|---|---|
| `steel_reinforcement` | Steel reinforcement bars and structural steel | 9 |
| `power_cables` | Electrical wires and power cables | 10 |
| `led_street_lighting` | LED luminaires for road and street lighting | 8 |
| `water_storage_pipes` | Plastic water storage tanks and PVC water pipes | 7 |
| `gold_jewellery` | Gold jewellery and artefacts | 3 |

Categories: `product` (9), `test_method` (11), `normative` (6), `installation` (6), `terminology` (3), `safety` (2).

### `standards.json`: one record per standard

```json
{
  "id": "IS-1786", "number": "IS 1786", "year": 2008,
  "domain": "steel_reinforcement", "category": "product",
  "title": "High strength deformed steel bars and wires for concrete reinforcement - Specification",
  "scope": "Requirements for high strength deformed steel bars ... (team paraphrase, NOT BIS text)",
  "keywords": ["TMT bar", "rebar", "HYSD", "Fe 500D", "sariya", "..."],
  "superseded_editions": [1985, 1979],
  "amendments": []
}
```

- `id` must be unique and is used in edges and rules. The convention is `IS-<number>[-P<part>][-S<section>]`.
- `superseded_editions` drives the **outdated edition** check.
- `keywords` matter a lot for BM25 recall. Include trade names and Hinglish words.

### `edges.json`: the allied-standard graph

Typed links from a standard to another standard. The types are `normative_ref`, `test_method`, `terminology`, `safety`, `installation` and `related_product`. Reverse links appear in the API as `referenced_by`. The `test_method` and `safety` edges are what the health check uses to raise "No test method / safety standard cited".

### `certification_rules.yaml`: the rule pack

```yaml
rules:
  - id: crs-led
    scheme: CRS                      # BIS_ISI | CRS | HALLMARKING
    applies_to: [IS-10322-P5-S3, IS-15885-P2-S13]
    order: "Electronics and Information Technology Goods (Requirement for Compulsory Registration) Order, 2012"
    effective_from: null
    verified: false                  # the UI shows "· to verify" while this is false
```

### `glossary.json`: Hindi and Hinglish to English

`"सरिया": "reinforcement bar TMT"`. It is used only by the lexical retriever; BGE-M3 handles multilingual text natively.

### Adding a new product domain (checklist)

1. Add the domain key and name to `standards.json → meta.domains`.
2. Add the product standard and its test-method, safety and other allied standards to `standards.json`.
3. Add edges in `edges.json`.
4. Add a certification rule to `certification_rules.yaml` if a QCO or CRS order applies.
5. Add Hindi or regional terms to `glossary.json`.
6. Add 5–10 queries to `backend/eval/golden.json`, including at least one with no answer.
7. Run `pytest` and `eval.run_eval`, then rebuild Docker.

Data is loaded once at startup (`lru_cache`), so **restart or rebuild the container after any data change.**

---

## 9. REST API reference

The full interactive spec is at `/docs` (OpenAPI 3). Every response carries an `X-Request-ID` header that matches its log line.

| Method | Endpoint | Body or parameters | Returns |
|---|---|---|---|
| GET | `/api/health` | — | Status, retrieval mode, dense status, counts, data date, notice |
| POST | `/api/recommend` | `{"query", "top_k": 5, "output_language": "en"\|"hi"}` | `request_id`, `detected_language`, `attributes`, `expanded_terms`, `retrieval_mode`, `abstained`, `abstain_reason`, `results[]`, `data_as_of` |
| POST | `/api/tender/analyse?output_language=en` | multipart `file` | `document`, `summary`, `items[]` |
| GET | `/api/standards?domain=&category=` | — | `meta` + `standards[]` |
| GET | `/api/standards/{id}` | e.g. `IS-1786` | Full record + `version` + `certification` |
| GET | `/api/standards/{id}/allied` | — | Allied standards grouped by type |
| POST | `/api/feedback` | `{"request_id", "standard_id", "decision": "accept"\|"reject", "comment"?}` | `{"recorded": <entry hash>}` |
| GET | `/api/audit/verify` | — | `{"intact": true}` |

Ready-to-run examples:

```bash
curl -s -X POST localhost:8000/api/recommend -H 'Content-Type: application/json' \
     -d '{"query":"LED street light 90 W IP66","top_k":3}'

curl -s -X POST localhost:8000/api/recommend -H 'Content-Type: application/json' \
     -d '{"query":"PVC insulated cable as per IS 694:1990","output_language":"hi"}'

curl -s -X POST "localhost:8000/api/tender/analyse?output_language=en" \
     -F file=@samples/02_district_hospital_electrification.docx

curl -s localhost:8000/api/standards/IS-1786/allied
curl -s localhost:8000/api/audit/verify
```

---

## 10. Configuration

Copy `.env.example` to `.env` to override the defaults used by `docker-compose.yml`.

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `8000` | Host port |
| `INSTALL_ML` | `false` | `true` installs PyTorch + sentence-transformers for BGE-M3 (image about 2 GB larger, 2.5 GB model download on first run, cached in the `models` volume) |
| `PIP_INDEX_URL` | PyPI | Mirror for unreliable networks |
| `ISRE_DENSE` | `auto` | `off` forces lexical-only retrieval |
| `ISRE_EMBED_MODEL` | `BAAI/bge-m3` | Dense model |
| `ISRE_RERANK_MODEL` | empty | e.g. `BAAI/bge-reranker-v2-m3` (needs dense retrieval) |
| `ISRE_OLLAMA_MODEL` / `ISRE_OLLAMA_URL` | empty / `host.docker.internal:11434` | LLM attribute extraction via Ollama |
| `ISRE_ABSTAIN_THRESHOLD` | `0.30` | Raise it to abstain more often, lower it to answer more often |
| `ISRE_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` or `ERROR` |
| `ISRE_LOG_RETENTION_DAYS` | `30` | Daily log files kept |
| `ISRE_DATA_DIR`, `ISRE_VAR_DIR`, `ISRE_LOG_DIR`, `ISRE_FRONTEND_DIST` | see `config.py` | Paths (already set inside Docker) |

To demo with semantic retrieval:

```bash
INSTALL_ML=true docker compose up -d --build
curl -s localhost:8000/api/health   # retrieval_mode should include "dense BAAI/bge-m3"
```

---

## 11. Tests, evaluation, logs and audit

### Tests: 12 passed on the handoff date

```bash
docker compose run --rm app python -m pytest -q
```

They cover health, the citation parser, a semantic product query, a Hindi query, Hindi clause output, abstention on services, exact citation with an outdated edition, test-method intent, all three file formats, all sample tender statuses, rejection of unsupported files, and standard lookup with feedback.

**Rule of thumb:** if you change data or retrieval logic, `test_sample_tender_statuses` will tell you whether the demo samples still give their expected results.

### Evaluation (`backend/eval/golden.json`, 28 queries)

```
Retrieval mode      : BM25 + exact IS number
Queries             : 24 with an answer, 4 with no applicable IS
Recall@5            : 1.00
MRR                 : 0.98
Correct abstentions : 4/4
False recommendations on no-answer queries: 0/4
```

These numbers are **optimistic**: the team wrote the golden set against its own seed data. Grow it with independently labelled queries before quoting results.

### Logs

- `logs/server.jsonl` holds one JSON object per line: every request (method, path, status, latency, client, request ID), every upload (file name, size, result, SHA-256), and warnings and errors with tracebacks.
- `docker compose exec app python -m app.log_report` (add `--since 2026-10-01` or `--json`) prints request counts per endpoint, p50/p95/max latency, the upload breakdown, tender results and recent errors.
- Observed latency: `/api/recommend` p50 is about 20 ms; `/api/tender/analyse` p50 is about 35 ms (first PDF about 390 ms).
- To analyse in pandas: `pd.read_json("logs/server.jsonl", lines=True)`.

### Audit log

`backend/var/audit.jsonl` is append-only and hash-chained. It records every recommend, tender analysis and accept/reject decision. `GET /api/audit/verify` returns `{"intact": false}` if any line has been edited.

---

## 12. Local development without Docker

Requires Python 3.11+ and Node.js 18+.

```bash
pip install -r backend/requirements.txt          # optional: -r backend/requirements-ml.txt
cd frontend && npm install && npm run build && cd ..
cd backend && uvicorn app.main:app --reload --port 8000
```

For frontend hot reload, run this in a second terminal:

```bash
cd frontend && npm run dev     # http://localhost:5173, proxies /api to :8000 (vite.config.ts)
```

CORS allows `http://localhost:5173` only (`main.py`).

Run the tests and evaluation from `backend/`: `python -m pytest -q` and `python -m eval.run_eval`.

Regenerate the sample DOCX and PDF after editing a sample `.txt`: `cd samples && python generate_samples.py`. Then copy the files to `frontend/public/samples/`.

---

## 13. Known issues and limitations

| # | Issue | Impact | Where |
|---|---|---|---|
| 1 | **The seed data is unverified.** Scope texts are team paraphrases; editions, amendments and QCO dates are unchecked; amendment lists and `effective_from` are mostly empty | Not fit for real tenders yet; the UI says so | `backend/data/` |
| 2 | **Only 37 standards in 5 domains**; anything else abstains (e.g. laptops) | Demo scope only | `standards.json` |
| 3 | **No OCR in the default image.** Scanned PDFs return "Could not read document" | Sample 06 | `ingest.py` (PaddleOCR is optional and not in requirements) |
| 4 | **Dense retrieval is off by default.** Synonym-heavy or paraphrased queries depend on keywords and the glossary | Lower recall on unseen phrasings | `INSTALL_ML=true` |
| 5 | **Hindi output uses fixed templates** only for clauses; the rest of the UI is English | — | `deliver.py` |
| 6 | `HEAD /api/health` returns **405** (only GET is defined) | Some uptime monitors use HEAD; use GET | `main.py` |
| 7 | Running `pytest` inside the container warns that `.pytest_cache` is not writable (the container runs as non-root) | Harmless | Add `-p no:cacheprovider` to silence it |
| 8 | **No authentication**, rate limiting or API keys | Do not expose publicly | `main.py` |
| 9 | **Analysis is synchronous**: large tenders block a worker | Fine for the demo | — |
| 10 | The registry is loaded from JSON at startup | A restart is needed after data edits | `knowledge.py` |
| 11 | Sample tenders exist in **two places** (`samples/` and `frontend/public/samples/`) | Keep them in sync | — |
| 12 | Item splitting relies on numbered items (`1.`, `2.` …) | Unnumbered free-form tenders may become one item | `understand.split_items` |

---

## 14. Roadmap: what to build next

Listed in order of priority, matching the README's "Not in this baseline yet":

1. **Verify the data** against the BIS Standards Portal and official QCO notifications, fill in amendments and effective dates, and set `verified: true` per record.
2. **Grow the registry** beyond 5 domains, and add a **scheduled refresh from BIS**.
3. **PostgreSQL + pgvector** storage. Only the loader in `knowledge.py` needs to change.
4. **Turn on BGE-M3 + reranker** by default for the demo machine; re-run the evaluation and compare.
5. **PaddleOCR** in an optional image layer for scanned tenders.
6. **Authentication:** JWT for officials and per-portal API keys. Add rate limiting.
7. **Async job queue** (Celery + Redis) for large tenders.
8. **IndicTrans2** for free-form Hindi and regional-language output.
9. An **embeddable `<script>` widget** and a mock GeM page to show portal integration.
10. A larger **independent golden set** (30–50 queries per domain).

---

## 15. Troubleshooting

| Symptom | Fix |
|---|---|
| `SSLError … UNEXPECTED_EOF_WHILE_READING` during build | The network is dropping connections to PyPI. Re-run `docker compose build` (downloads are cached), turn off the VPN, or set `PIP_INDEX_URL` in `.env` |
| Header shows **Engine offline** | `docker ps` → is the container healthy? Check `docker compose logs app` |
| Port 8000 is busy | Set `PORT=8080` in `.env`, then `docker compose up -d` |
| UI changes don't appear | The UI is baked into the image: `docker compose up -d --build`, or use `npm run dev` |
| Data edits don't appear | Restart the container (data is cached at startup) |
| `Permission denied` on `logs/` or `backend/var/` | The container runs as UID 1000; `sudo chown -R 1000:1000 logs backend/var` |
| Audit verify returns `intact: false` | `audit.jsonl` was edited by hand. Back it up and start a fresh one for the demo |
| Results look different from §5 | Check `/api/health` for `retrieval_mode`. With dense retrieval or a reranker on, rankings and confidences change |
