import Link from "next/link";

type Props = {
  basePath: string;
  params: Record<string, string | undefined>;
  page: number;
  pageSize: number;
  total: number;
};

export default function Pagination({ basePath, params, page, pageSize, total }: Props) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (pages <= 1) return null;
  const href = (p: number) => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) if (v && k !== "page") qs.set(k, v);
    qs.set("page", String(p));
    return `${basePath}?${qs.toString()}`;
  };
  const btn = "rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-50";
  const off = "rounded-md border border-slate-200 px-3 py-1.5 text-sm text-slate-400";
  return (
    <nav className="mt-6 flex items-center justify-between" aria-label="Pagination">
      {page > 1 ? <Link href={href(page - 1)} className={btn}>← Previous</Link> : <span className={off}>← Previous</span>}
      <span className="text-sm text-slate-600">Page {page} of {pages}</span>
      {page < pages ? <Link href={href(page + 1)} className={btn}>Next →</Link> : <span className={off}>Next →</span>}
    </nav>
  );
}
