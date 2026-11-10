import Link from "next/link";
import JobCard from "@/components/JobCard";
import SearchForm from "@/components/SearchForm";
import { apiGet, type SearchResponse } from "@/lib/api";

export default async function Home() {
  let latest: SearchResponse | null = null;
  try {
    latest = await apiGet<SearchResponse>("/api/v1/jobs/latest", { page_size: 10 });
  } catch {
    latest = null;
  }
  return (
    <div className="space-y-10">
      <section className="rounded-xl bg-white p-8 shadow-sm">
        <h1 className="text-3xl font-bold">Every job board, one search.</h1>
        <p className="mt-2 text-slate-600">
          Postings collected from company career sites and ATS platforms, normalized and de-duplicated.
          {latest ? ` ${latest.total.toLocaleString("en")} jobs indexed right now.` : ""}
        </p>
        <div className="mt-6"><SearchForm compact /></div>
      </section>

      <section>
        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="text-xl font-semibold">Latest jobs</h2>
          <Link href="/jobs?sort=newest" className="text-sm text-blue-700 hover:underline">See all →</Link>
        </div>
        {latest === null ? (
          <p className="rounded-md bg-amber-50 p-4 text-sm text-amber-800">
            The API is not reachable right now. Check that the backend is running.
          </p>
        ) : latest.results.length === 0 ? (
          <p className="rounded-md bg-slate-100 p-4 text-sm text-slate-700">
            No jobs yet. Seed sources and run an ingestion from the <Link href="/admin" className="underline">admin page</Link>.
          </p>
        ) : (
          <div className="space-y-3">{latest.results.map((j) => <JobCard key={j.id} job={j} />)}</div>
        )}
      </section>
    </div>
  );
}
