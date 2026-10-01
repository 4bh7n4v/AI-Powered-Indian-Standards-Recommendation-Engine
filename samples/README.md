# Sample tenders

Demonstration tenders for the Tender Health Check. Each file is available as `.txt`, `.docx` and `.pdf`. The scanned tender is PDF only.
They are fictional and written for this prototype.

| File | Project and scenario | Expected overall status | What it shows |
|---|---|---|---|
| `01_office_complex_construction` | Administrative Block, Central Government Office Complex: complete specification | **Acceptable** | Current editions, test methods, safety standards and certification clauses all present. |
| `02_district_hospital_electrification` | Electrification and Water Supply Works, District Hospital: mixed quality | **Partially acceptable** | Items 1 and 4 are clean. Item 2 lacks test methods. Item 3 cites an outdated edition. Item 5 lacks safety and test standards and the CRS clause. |
| `03_engineering_college_hostel` | Boys Hostel, State Engineering College: poor specification | **Not acceptable** | Outdated editions (IS 1786:1985, IS 2062:1999, IS 694:1990), a missing standard for the street light, an unknown IS number, and no certification clauses. |
| `04_regional_office_facility_services` | Facility Management Services, Regional Office: services only | **No Indian Standard applies** | The engine abstains on services and items outside the registry instead of guessing. |
| `05_government_school_building` | Government School Building (सरकारी विद्यालय भवन): Hindi-language tender | **Partially acceptable** | Hindi items matched through the glossary. Item 1 is complete; items 2 and 3 cite no standard. |
| `06_engineering_college_hostel_scanned.pdf` | Image-only scan of tender 03 | **Warning** | No text layer. The engine reports that OCR (PaddleOCR) is needed rather than giving an empty "all clear". |

## How statuses are decided

- **Item status:**
  - any *high* finding (missing standard or outdated edition) → **Not acceptable**;
  - any *medium* finding (missing test-method or safety standard, certification not stated) → **Needs revision**;
  - only minor or no findings → **Acceptable**;
  - no applicable IS → **No applicable IS**.
- **Tender status** (items with no applicable IS are ignored):
  - every item acceptable → **Acceptable**;
  - no acceptable item and at least one not-acceptable item → **Not acceptable**;
  - otherwise → **Partially acceptable**.

Regenerate the DOCX and PDF files after editing a `.txt` file:

```bash
python generate_samples.py   # needs pymupdf and python-docx (backend/requirements.txt)
```
