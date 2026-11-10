const LABELS: Record<string, string> = {
  REMOTE: "Remote", HYBRID: "Hybrid", ONSITE: "On-site",
  FULL_TIME: "Full-time", PART_TIME: "Part-time", CONTRACT: "Contract",
  INTERNSHIP: "Internship", TEMPORARY: "Temporary",
  INTERN: "Intern", JUNIOR: "Junior", SENIOR: "Senior", LEAD: "Lead",
  STAFF: "Staff", PRINCIPAL: "Principal", MANAGEMENT: "Management",
};

export const label = (v: string | null | undefined) => (v ? LABELS[v] ?? v : "");

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(diff)) return "";
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${Math.max(minutes, 1)} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} day${days === 1 ? "" : "s"} ago`;
  const months = Math.floor(days / 30);
  return `${months} month${months === 1 ? "" : "s"} ago`;
}

export function salaryRange(min: number | null, max: number | null, currency: string | null): string {
  if (min == null && max == null) return "";
  const fmt = (n: number) =>
    new Intl.NumberFormat("en", {
      style: currency ? "currency" : "decimal",
      currency: currency ?? undefined,
      maximumFractionDigits: 0,
    }).format(n);
  if (min != null && max != null) return `${fmt(min)} – ${fmt(max)}`;
  return fmt((min ?? max) as number);
}
