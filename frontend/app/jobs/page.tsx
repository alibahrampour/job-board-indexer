import type { Metadata } from "next";
import JobCard from "@/components/JobCard";
import Pagination from "@/components/Pagination";
import SearchForm from "@/components/SearchForm";
import { searchJobs, type SearchResponse } from "@/lib/api";

type SP = Record<string, string | undefined>;
const PAGE_SIZE = 20;

export const metadata: Metadata = { title: "Search jobs" };

export default async function JobsPage({ searchParams }: { searchParams: SP }) {
  const page = Math.max(1, Number(searchParams.page) || 1);
  let data: SearchResponse | null = null;
  try {
    data = await searchJobs(searchParams, page, PAGE_SIZE);
  } catch {
    data = null;
  }
  return (
    <div className="space-y-6">
      <SearchForm values={searchParams} />
      {data === null ? (
        <p className="rounded-md bg-amber-50 p-4 text-sm text-amber-800">Search is unavailable right now. Please try again.</p>
      ) : (
        <>
          <p className="text-sm text-slate-600">{data.total.toLocaleString("en")} jobs found</p>
          {data.results.length === 0 ? (
            <p className="rounded-md bg-slate-100 p-4 text-sm">No jobs match these filters. Try fewer filters or a broader keyword.</p>
          ) : (
            <div className="space-y-3">{data.results.map((j) => <JobCard key={j.id} job={j} />)}</div>
          )}
          <Pagination basePath="/jobs" params={searchParams} page={page} pageSize={PAGE_SIZE} total={data.total} />
        </>
      )}
    </div>
  );
}
