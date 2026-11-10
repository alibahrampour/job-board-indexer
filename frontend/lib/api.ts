// Server-side API access (server components only). Browser code uses BROWSER_API.
export const SERVER_API = process.env.API_URL ?? "http://localhost:8000";
export const BROWSER_API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Company = {
  id: string;
  name: string;
  website: string | null;
  logo_url: string | null;
  industry: string | null;
  active_jobs?: number;
};

export type JobSource = {
  id: string;
  platform: string;
  source_url: string;
  apply_url: string | null;
  source_status: string;
  last_seen_at: string;
};

export type JobSummary = {
  id: string;
  title: string;
  company: Company;
  location: string | null;
  city: string | null;
  country_code: string | null;
  remote_type: string | null;
  employment_type: string | null;
  seniority: string | null;
  department: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  posted_at: string | null;
  first_seen_at: string;
  last_seen_at: string;
  status: string;
  apply_url: string | null;
  platform: string | null;
};

export type JobDetail = JobSummary & {
  description: string | null;
  quality_score: number;
  sources: JobSource[];
};

export type SearchResponse = {
  total: number;
  page: number;
  page_size: number;
  results: JobSummary[];
};

export class NotFoundError extends Error {}

type Params = Record<string, string | number | undefined>;

export async function apiGet<T>(path: string, params: Params = {}): Promise<T> {
  const url = new URL(path, SERVER_API);
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") url.searchParams.set(k, String(v));
  }
  const res = await fetch(url, { cache: "no-store" });
  if (res.status === 404 || res.status === 422) throw new NotFoundError(path);
  if (!res.ok) throw new Error(`API ${res.status} for ${path}`);
  return res.json() as Promise<T>;
}

export const SEARCH_KEYS = [
  "q", "location", "remote_type", "employment_type", "seniority",
  "company", "posted_within_days", "sort",
] as const;

export function searchJobs(raw: Record<string, string | undefined>, page: number, pageSize = 20) {
  const params: Params = { page, page_size: pageSize };
  for (const key of SEARCH_KEYS) params[key] = raw[key];
  return apiGet<SearchResponse>("/api/v1/jobs/search", params);
}
