"use client";

import { useCallback, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Metrics = {
  sources_total: number;
  sources_active: number;
  sources_failing: number;
  companies_total: number;
  jobs_by_status: Record<string, number>;
  jobs_active: number;
};
type Source = {
  id: string; name: string; connector: string; is_active: boolean; schedule_minutes: number;
  last_run_at: string | null; last_success_at: string | null; last_error_at: string | null;
  last_error_message: string | null;
};
type Run = {
  id: string; source_id: string; trigger: string; status: string; started_at: string;
  jobs_found: number; jobs_created: number; jobs_updated: number; jobs_failed: number;
  jobs_expired: number; error_message: string | null;
};

const when = (iso: string | null) => (iso ? new Date(iso).toLocaleString("en-GB") : "—");
const statusColor: Record<string, string> = {
  SUCCESS: "text-green-700", PARTIAL: "text-amber-700", FAILED: "text-red-700", RUNNING: "text-blue-700",
};

export default function AdminPage() {
  const [key, setKey] = useState("");
  const [input, setInput] = useState("");
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const call = useCallback(
    async (path: string, init: RequestInit = {}, k = key) => {
      const res = await fetch(`${API}${path}`, { ...init, headers: { ...(init.headers ?? {}), "X-Admin-Key": k } });
      if (res.status === 401) throw new Error("Invalid admin key");
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      return res.json();
    },
    [key],
  );

  const refresh = useCallback(async () => {
    if (!key) return;
    try {
      const [m, s, r] = await Promise.all([
        call("/api/v1/admin/metrics"),
        call("/api/v1/sources"),
        call("/api/v1/admin/ingestion-runs?limit=20"),
      ]);
      setMetrics(m); setSources(s); setRuns(r); setError(null);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to load";
      setError(msg);
      if (msg === "Invalid admin key") { sessionStorage.removeItem("adminKey"); setKey(""); }
    }
  }, [call, key]);

  useEffect(() => {
    const saved = sessionStorage.getItem("adminKey");
    if (saved) setKey(saved);
  }, []);

  useEffect(() => {
    if (!key) return;
    refresh();
    const t = setInterval(refresh, 15000);
    return () => clearInterval(t);
  }, [key, refresh]);

  async function action(path: string, okMessage: string) {
    try {
      await call(path, { method: "POST" });
      setNotice(okMessage); setError(null);
      setTimeout(refresh, 1500);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    }
  }

  if (!key) {
    return (
      <div className="mx-auto max-w-sm space-y-3 rounded-xl bg-white p-6 shadow-sm">
        <h1 className="text-lg font-semibold">Admin sign-in</h1>
        <p className="text-sm text-slate-600">Enter the ADMIN_API_KEY from your .env. It is kept only for this browser tab.</p>
        <input type="password" value={input} onChange={(e) => setInput(e.target.value)}
               className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" placeholder="Admin key" />
        <button className="w-full rounded-md bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700"
                onClick={() => { sessionStorage.setItem("adminKey", input); setKey(input); }}>
          Continue
        </button>
        {error && <p className="text-sm text-red-700">{error}</p>}
      </div>
    );
  }

  const stat = (name: string, value: number | string) => (
    <div className="rounded-lg bg-white p-4 shadow-sm">
      <div className="text-xs uppercase tracking-wide text-slate-500">{name}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
    </div>
  );
  const btn = "rounded border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50";
  const byStatus = metrics?.jobs_by_status ?? {};

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Admin dashboard</h1>
        <div className="flex gap-2">
          <button className={btn} onClick={refresh}>Refresh</button>
          <button className={btn} onClick={() => { sessionStorage.removeItem("adminKey"); setKey(""); setMetrics(null); }}>Sign out</button>
        </div>
      </div>
      {error && <p className="rounded-md bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      {notice && <p className="rounded-md bg-green-50 p-3 text-sm text-green-800">{notice}</p>}

      {metrics && (
        <section className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {stat("Sources", metrics.sources_total)}
          {stat("Active sources", metrics.sources_active)}
          {stat("Failing", metrics.sources_failing)}
          {stat("Companies", metrics.companies_total)}
          {stat("Active jobs", byStatus.ACTIVE ?? 0)}
          {stat("Expired", byStatus.EXPIRED ?? 0)}
        </section>
      )}

      <section>
        <h2 className="mb-3 text-lg font-semibold">Sources</h2>
        <div className="overflow-x-auto rounded-lg bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-slate-50 text-xs uppercase text-slate-500">
              <tr><th className="p-3">Name</th><th className="p-3">Every</th><th className="p-3">Last success</th><th className="p-3">Last error</th><th className="p-3">Actions</th></tr>
            </thead>
            <tbody>
              {sources.length === 0 && <tr><td colSpan={5} className="p-3 text-slate-500">No sources yet. Run the seed script.</td></tr>}
              {sources.map((s) => (
                <tr key={s.id} className="border-b last:border-0 align-top">
                  <td className="p-3">
                    <div className="font-medium">{s.name}</div>
                    <div className="text-xs text-slate-500">{s.connector}{s.is_active ? "" : " · disabled"}</div>
                  </td>
                  <td className="p-3">{s.schedule_minutes} min</td>
                  <td className="p-3">{when(s.last_success_at)}</td>
                  <td className="p-3">
                    {when(s.last_error_at)}
                    {s.last_error_message && <div className="max-w-xs truncate text-xs text-red-700" title={s.last_error_message}>{s.last_error_message}</div>}
                  </td>
                  <td className="space-x-1 p-3 whitespace-nowrap">
                    <button className={btn} onClick={() => action(`/api/v1/admin/sources/${s.id}/run`, `Queued ${s.name}`)}>Run now</button>
                    <button className={btn} onClick={() => action(`/api/v1/admin/sources/${s.id}/${s.is_active ? "disable" : "enable"}`, `${s.is_active ? "Disabled" : "Enabled"} ${s.name}`)}>
                      {s.is_active ? "Disable" : "Enable"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Recent ingestion runs</h2>
        <div className="overflow-x-auto rounded-lg bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-slate-50 text-xs uppercase text-slate-500">
              <tr><th className="p-3">Started</th><th className="p-3">Source</th><th className="p-3">Status</th><th className="p-3">Found</th><th className="p-3">New</th><th className="p-3">Updated</th><th className="p-3">Failed</th><th className="p-3">Expired</th></tr>
            </thead>
            <tbody>
              {runs.length === 0 && <tr><td colSpan={8} className="p-3 text-slate-500">No runs yet.</td></tr>}
              {runs.map((r) => (
                <tr key={r.id} className="border-b last:border-0">
                  <td className="p-3">{when(r.started_at)}<div className="text-xs text-slate-500">{r.trigger}</div></td>
                  <td className="p-3">{sources.find((s) => s.id === r.source_id)?.name ?? r.source_id.slice(0, 8)}</td>
                  <td className={`p-3 font-medium ${statusColor[r.status] ?? ""}`} title={r.error_message ?? ""}>{r.status}</td>
                  <td className="p-3">{r.jobs_found}</td><td className="p-3">{r.jobs_created}</td>
                  <td className="p-3">{r.jobs_updated}</td><td className="p-3">{r.jobs_failed}</td><td className="p-3">{r.jobs_expired}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
