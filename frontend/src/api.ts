import type { Health, RecommendResponse, RegistryResponse, TenderResponse } from "./types";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    throw new Error(typeof detail === "string" ? detail : `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  health: () => request<Health>("/api/health"),
  recommend: (query: string, output_language: "en" | "hi") =>
    request<RecommendResponse>("/api/recommend", json({ query, top_k: 5, output_language })),
  analyseTender: (file: File, output_language: "en" | "hi") => {
    const form = new FormData();
    form.append("file", file);
    return request<TenderResponse>(`/api/tender/analyse?output_language=${output_language}`, { method: "POST", body: form });
  },
  registry: () => request<RegistryResponse>("/api/standards"),
  feedback: (request_id: string, standard_id: string, decision: "accept" | "reject") =>
    request<{ recorded: string }>("/api/feedback", json({ request_id, standard_id, decision })),
};

export const CATEGORY_LABELS: Record<string, string> = {
  product: "Product specification",
  test_method: "Test method",
  terminology: "Terminology",
  safety: "Safety",
  installation: "Installation / code of practice",
  normative: "General requirement",
};

export const ALLIED_LABELS: Record<string, string> = {
  normative_ref: "Normative references",
  test_method: "Test methods",
  terminology: "Terminology",
  safety: "Safety",
  installation: "Installation",
  related_product: "Related products",
  referenced_by: "Referenced by",
};
