import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Job Board Indexer", template: "%s · Job Board Indexer" },
  description: "Search job postings aggregated from ATS platforms and job boards in one place.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
            <Link href="/" className="text-lg font-bold text-blue-700">Job Board Indexer</Link>
            <nav className="flex gap-5 text-sm font-medium text-slate-700">
              <Link href="/jobs" className="hover:text-blue-700">Jobs</Link>
              <Link href="/admin" className="hover:text-blue-700">Admin</Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
