import type { Metadata } from "next";
import { notFound } from "next/navigation";
import JobCard from "@/components/JobCard";
import Pagination from "@/components/Pagination";
import { apiGet, NotFoundError, type Company, type SearchResponse } from "@/lib/api";

const PAGE_SIZE = 20;

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  try {
    const c = await apiGet<Company>(`/api/v1/companies/${params.id}`);
    return { title: `${c.name} jobs` };
  } catch {
    return { title: "Company" };
  }
}

export default async function CompanyPage({
  params,
  searchParams,
}: {
  params: { id: string };
  searchParams: Record<string, string | undefined>;
}) {
  const page = Math.max(1, Number(searchParams.page) || 1);
  let company: Company;
  let jobs: SearchResponse;
  try {
    [company, jobs] = await Promise.all([
      apiGet<Company>(`/api/v1/companies/${params.id}`),
      apiGet<SearchResponse>(`/api/v1/companies/${params.id}/jobs`, { page, page_size: PAGE_SIZE }),
    ]);
  } catch (e) {
    if (e instanceof NotFoundError) notFound();
    throw e;
  }
  return (
    <div className="space-y-6">
      <header className="rounded-xl bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold">{company.name}</h1>
        <p className="mt-1 text-sm text-slate-600">
          {[company.industry, `${company.active_jobs ?? jobs.total} open jobs`].filter(Boolean).join(" · ")}
        </p>
        {company.website && (
          <a href={company.website} target="_blank" rel="noopener noreferrer nofollow" className="mt-2 inline-block text-sm text-blue-700 hover:underline">
            {company.website} ↗
          </a>
        )}
      </header>
      {jobs.results.length === 0 ? (
        <p className="rounded-md bg-slate-100 p-4 text-sm">No open jobs for this company right now.</p>
      ) : (
        <div className="space-y-3">{jobs.results.map((j) => <JobCard key={j.id} job={j} />)}</div>
      )}
      <Pagination basePath={`/companies/${params.id}`} params={searchParams} page={page} pageSize={PAGE_SIZE} total={jobs.total} />
    </div>
  );
}
