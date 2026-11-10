import Link from "next/link";
import type { JobSummary } from "@/lib/api";
import { label, salaryRange, timeAgo } from "@/lib/format";

const badge = "rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700";

export default function JobCard({ job }: { job: JobSummary }) {
  const salary = salaryRange(job.salary_min, job.salary_max, job.salary_currency);
  const badges = [label(job.remote_type), label(job.employment_type), label(job.seniority)].filter(Boolean);
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold">
            <Link href={`/jobs/${job.id}`} className="hover:text-blue-700">{job.title}</Link>
          </h2>
          <p className="mt-0.5 text-sm text-slate-600">
            <Link href={`/companies/${job.company.id}`} className="font-medium hover:underline">{job.company.name}</Link>
            {job.location ? ` · ${job.location}` : ""}
          </p>
        </div>
        {job.apply_url && (
          <a href={job.apply_url} target="_blank" rel="noopener noreferrer nofollow"
             className="rounded-md border border-blue-600 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-50">
            Apply ↗
          </a>
        )}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {badges.map((b) => <span key={b} className={badge}>{b}</span>)}
        {salary && <span className={badge}>{salary}</span>}
      </div>
      <p className="mt-3 text-xs text-slate-500">
        {timeAgo(job.posted_at ?? job.first_seen_at)}
        {job.platform ? ` · via ${job.platform}` : ""}
        {job.status === "PENDING_EXPIRATION" ? " · may no longer be available" : ""}
      </p>
    </article>
  );
}
