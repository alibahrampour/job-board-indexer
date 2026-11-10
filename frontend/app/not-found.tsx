import Link from "next/link";

export default function NotFound() {
  return (
    <div className="py-16 text-center">
      <h1 className="text-2xl font-semibold">Not found</h1>
      <p className="mt-2 text-slate-600">This page or job does not exist (or is no longer indexed).</p>
      <Link href="/jobs" className="mt-4 inline-block text-blue-700 hover:underline">Browse jobs</Link>
    </div>
  );
}
