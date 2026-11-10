import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { apiGet, NotFoundError, type JobDetail } from "@/lib/api";
import { label, salaryRange, timeAgo } from "@/lib/format";

async function load(id: string): Promise<JobDetail> {
  try {
    return await apiGet<JobDetail>(`/api/v1/jobs/${id}`);
  } catch (e) {
    if (e instanceof NotFoundError) notFound();
    throw e;
  }
}

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  try {
    const job = await apiGet<JobDetail>(`/api/v1/jobs/${params.id}`);
    return {
      title: `${job.title} at ${job.company.name}`,
      description: (job.description ?? "").slice(0, 160) || undefined,
    };
  } catch {
    return { title: "Job" };
  }
}

function jsonLd(job: JobDetail) {
  if (job.status === "EXPIRED" || job.status === "CLOSED") return null;
  return {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    title: job.title,
    description: job.description ?? job.title,
    datePosted: job.posted_at ?? job.first_seen_at,
    hiringOrganization: { "@type": "Organization", name: job.company.name, sameAs: job.company.website ?? undefined },
    jobLocation: job.location
      ? { "@type": "Place", address: { "@type": "PostalAddress", addressLocality: job.city ?? job.location, addressCountry: job.country_code ?? undefined } }
      : undefined,
    jobLocationType: job.remote_type === "REMOTE" ? "TELECOMMUTE" : undefined,
  };
}

export default async function JobPage({ params }: { params: { id: string } }) {
  const job = await load(params.id);
  const salary = salaryRange(job.salary_min, job.salary_max, job.salary_currency);
  const facts: [string, string][] = [
    ["Location", job.location ?? ""],
    ["Work type", label(job.remote_type)],
    ["Employment", label(job.employment_type)],
    ["Seniority", label(job.seniority)],
    ["Department", job.department ?? ""],
    ["Salary", salary],
    ["Posted", timeAgo(job.posted_at ?? job.first_seen_at)],
    ["Last checked", timeAgo(job.last_seen_at)],
  ];
  const ld = jsonLd(job);
  const inactive = job.status !== "ACTIVE";

  return (
    <article className="space-y-6">
      {ld && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(ld).replace(/</g, "\\u003c") }}
        />
      )}
      <Link href="/jobs" className="text-sm text-blue-700 hover:underline">← Back to search</Link>

      <header className="rounded-xl bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold">{job.title}</h1>
        <p className="mt-1 text-slate-600">
          <Link href={`/companies/${job.company.id}`} className="font-medium hover:underline">{job.company.name}</Link>
        </p>
        {inactive && (
          <p className="mt-4 rounded-md bg-amber-50 p-3 text-sm text-amber-800">
            {job.status === "PENDING_EXPIRATION"
              ? "This job was not seen in the latest check and may no longer be available."
              : "This job is no longer listed by its source."}
          </p>
        )}
        {job.apply_url && (
          <a href={job.apply_url} target="_blank" rel="noopener noreferrer nofollow"
             className="mt-5 inline-block rounded-md bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700">
            Apply on {job.platform ?? "source site"} ↗
          </a>
        )}
      </header>

      <dl className="grid gap-4 rounded-xl bg-white p-6 shadow-sm sm:grid-cols-2">
        {facts.filter(([, v]) => v).map(([k, v]) => (
          <div key={k}>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{k}</dt>
            <dd className="mt-0.5 text-sm">{v}</dd>
          </div>
        ))}
      </dl>

      <section className="rounded-xl bg-white p-6 shadow-sm">
        <h2 className="mb-3 text-lg font-semibold">Description</h2>
        {job.description ? (
          <div className="whitespace-pre-line text-sm leading-relaxed text-slate-800">{job.description}</div>
        ) : (
          <p className="text-sm text-slate-500">No description was provided by the source.</p>
        )}
      </section>

      <section className="rounded-xl bg-white p-6 shadow-sm">
        <h2 className="mb-3 text-lg font-semibold">Sources</h2>
        <ul className="space-y-2 text-sm">
          {job.sources.map((s) => (
            <li key={s.id} className="flex flex-wrap items-center justify-between gap-2">
              <a href={s.source_url} target="_blank" rel="noopener noreferrer nofollow" className="text-blue-700 hover:underline">
                {s.platform} ↗
              </a>
              <span className="text-slate-500">{s.source_status.toLowerCase()} · seen {timeAgo(s.last_seen_at)}</span>
            </li>
          ))}
        </ul>
      </section>
    </article>
  );
}
