# Platform coverage plan

Source of truth: `backend/data/platforms.csv` (58 ATS + 20 job boards).

Families: A = public JSON/XML/RSS API, B = unofficial tenant JSON / embedded data,
C = HTML or schema.org JobPosting JSON-LD, D = JS-heavy (Playwright), E = needs research.

All 78 platforms have a dedicated connector class and registry key. Fourteen
use their existing native implementations. The remaining 64 are explicit
unavailable stubs: they refuse source registration and fail clearly rather than
pretending to crawl through a generic adapter.

`confidence` and `endpoint_hint` are research notes and MUST be verified against a live
tenant before being used as production configuration. The `status` column is
planning metadata, not a measure of runnable connector support.

Key point: these are *platforms*, each hosting thousands of company boards. A connector alone
returns nothing until a source (tenant slug) is registered, so tenant discovery is a separate task.
