export interface StandardSummary {
  id: string;
  label: string;
  number: string;
  year: number | null;
  title: string;
  category: string;
}

export interface Certification {
  scheme: string | null;
  label: string;
  name: string | null;
  basis: string;
  effective_from: string | null;
  status: "mandatory" | "likely_mandatory" | "none_found";
  verified: boolean;
}

export interface VersionInfo {
  current_edition: string;
  year: number | null;
  status: string;
  amendments: string[];
  amendments_note: string | null;
  superseded_editions: number[];
  cited_year: number | null;
  cited_is_outdated: boolean;
  as_of: string;
  verified: boolean;
}

export interface Recommendation {
  standard: StandardSummary & { scope: string; domain: string; domain_name: string };
  confidence: number;
  evidence: { matched_terms: string[]; cited_in_input: boolean; dense_similarity: number | null; scope_text: string };
  version: VersionInfo;
  certification: Certification[];
  allied: Record<string, StandardSummary[]>;
  clause: string;
}

export interface RecommendResponse {
  request_id: string;
  query: string;
  detected_language: { code: string; name: string };
  attributes: { materials: string[]; quantities: string[]; grades: string[]; product: string | null; source: string };
  expanded_terms: string[];
  retrieval_mode: string;
  abstained: boolean;
  abstain_reason: string | null;
  results: Recommendation[];
  data_as_of: string;
}

export interface Finding {
  severity: "high" | "medium" | "low" | "info";
  kind: string;
  message: string;
  fix?: string;
  citation?: string;
}

export type ItemStatus = "acceptable" | "needs_revision" | "not_acceptable" | "not_applicable";
export type TenderStatus = "acceptable" | "partially_acceptable" | "not_acceptable" | "not_applicable" | "unreadable";

export interface TenderItem {
  index: number;
  title: string;
  text: string;
  lines: [number, number];
  language: string;
  primary_standard: StandardSummary | null;
  confidence: number;
  matched_terms: string[];
  abstained: boolean;
  status: ItemStatus;
  status_label: string;
  findings: Finding[];
  suggested_clause: string | null;
  /** Picture of the item in the uploaded PDF; null for other formats or when it can't be located. */
  evidence: { image: string; page: number; highlights: number } | null;
}

export interface TenderResponse {
  request_id: string;
  document: {
    name: string; sha256: string; type: string; pages: number; characters: number; ocr_pages: number[];
    warnings: string[]; source?: "upload" | "link" | "sample";
  };
  summary: {
    items: number;
    findings: Record<Finding["severity"], number>;
    items_without_standard: number;
    status: TenderStatus;
    status_label: string;
    items_by_status: Record<ItemStatus, number>;
  };
  items: TenderItem[];
  data_as_of: string;
}

export interface Health {
  status: string;
  retrieval_mode: string;
  dense: string;
  standards: number;
  edges: number;
  data_as_of: string;
  data_verified: boolean;
  notice: string;
}

export interface CheckRow {
  id: string;
  time: string;
  kind: "tender" | "search";
  title: string;
  source: string;
  status: TenderStatus | "matched" | null;
  status_label: string | null;
  items: number | null;
  issues: number | null;
  standards: string[];
  reopen: boolean;
}

export interface Stats {
  checks: { total: number; tenders: number; searches: number };
  items: { total: number; by_status: Record<ItemStatus, number> };
  tenders_by_status: Record<TenderStatus, number>;
  findings: Record<Finding["severity"], number>;
  searches_without_match: number;
  feedback: { accept: number; reject: number };
  top_gaps: { label: string; count: number }[];
  top_standards: { label: string; count: number }[];
  first_check: string | null;
  last_check: string | null;
  recent: CheckRow[];
}

export interface RegistryResponse {
  meta: { as_of: string; verified: boolean; domains: Record<string, string>; categories: Record<string, string> };
  standards: (StandardSummary & { domain: string })[];
}
