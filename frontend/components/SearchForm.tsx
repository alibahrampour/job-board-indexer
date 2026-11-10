type Props = { values?: Record<string, string | undefined>; compact?: boolean };

const field = "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none";

export default function SearchForm({ values = {}, compact = false }: Props) {
  const v = (k: string) => values[k] ?? "";
  return (
    <form action="/jobs" method="get" className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-[2fr_1fr_auto]">
        <input name="q" defaultValue={v("q")} placeholder="Job title, skill or keyword" className={field} aria-label="Search" />
        <input name="location" defaultValue={v("location")} placeholder="City or country (e.g. Amsterdam, NL)" className={field} aria-label="Location" />
        <button type="submit" className="rounded-md bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700">
          Search
        </button>
      </div>
      {!compact && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <select name="remote_type" defaultValue={v("remote_type")} className={field} aria-label="Work type">
            <option value="">Any work type</option>
            <option value="REMOTE">Remote</option>
            <option value="HYBRID">Hybrid</option>
            <option value="ONSITE">On-site</option>
          </select>
          <select name="employment_type" defaultValue={v("employment_type")} className={field} aria-label="Employment type">
            <option value="">Any employment type</option>
            <option value="FULL_TIME">Full-time</option>
            <option value="PART_TIME">Part-time</option>
            <option value="CONTRACT">Contract</option>
            <option value="INTERNSHIP">Internship</option>
            <option value="TEMPORARY">Temporary</option>
          </select>
          <select name="seniority" defaultValue={v("seniority")} className={field} aria-label="Seniority">
            <option value="">Any seniority</option>
            <option value="JUNIOR">Junior</option>
            <option value="SENIOR">Senior</option>
            <option value="LEAD">Lead</option>
            <option value="STAFF">Staff</option>
            <option value="PRINCIPAL">Principal</option>
            <option value="MANAGEMENT">Management</option>
          </select>
          <select name="posted_within_days" defaultValue={v("posted_within_days")} className={field} aria-label="Posted">
            <option value="">Any time</option>
            <option value="1">Last 24 hours</option>
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
          </select>
          <select name="sort" defaultValue={v("sort") || "relevance"} className={field} aria-label="Sort">
            <option value="relevance">Most relevant</option>
            <option value="newest">Newest</option>
          </select>
        </div>
      )}
    </form>
  );
}
