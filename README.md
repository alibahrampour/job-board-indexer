# Job Board Indexer — Phase 1 + 2

78 platform-specific connectors → Pipeline → PostgreSQL → Search API → Next.js UI

## اجرا

```bash
cp .env.example .env            # ADMIN_API_KEY را عوض کنید
docker compose up --build -d
docker compose exec api python -m scripts.seed_sources   # ثبت چند برد Greenhouse
```

- سایت: http://localhost:3000 (جست‌وجو، جزئیات آگهی، صفحه شرکت)
- داشبورد ادمین: http://localhost:3000/admin (با `ADMIN_API_KEY` وارد شوید؛ کلید فقط در sessionStorage همان تب می‌ماند)
- مستندات API: http://localhost:8000/docs
- Scheduler هر ۵ دقیقه منابع سررسیدشده را صف می‌کند (پیش‌فرض: هر ۶ ساعت برای هر منبع).
- اجرای دستی یک منبع:

```bash
curl http://localhost:8000/api/v1/sources                      # شناسه منبع را بردارید
curl -X POST -H "X-Admin-Key: change-me" \
     http://localhost:8000/api/v1/admin/sources/<SOURCE_ID>/run
docker compose logs -f worker
```

- جست‌وجو:

```bash
curl "http://localhost:8000/api/v1/jobs/search?q=qa+engineer&location=Amsterdam&remote_type=HYBRID"
```

- افزودن منبع جدید Greenhouse:

```bash
curl -X POST http://localhost:8000/api/v1/admin/sources \
  -H "X-Admin-Key: change-me" -H "Content-Type: application/json" \
  -d '{"name":"greenhouse:figma","connector":"greenhouse","config":{"board_token":"figma"}}'
```

هر ۷۸ پلتفرم فایل و کلاس Connector مستقل و کلید Registry دارند. چهارده پلتفرم
از Connectorهای دارای پیاده‌سازی قبلی استفاده می‌کنند. برای ۶۴ پلتفرم باقی‌مانده
کلاس اختصاصی scaffold وجود دارد؛ این کلاس‌ها عمداً ثبت Source را رد و اجرای Crawl
را با خطای روشن متوقف می‌کنند تا قبل از پیاده‌سازی و اعتبارسنجی endpoint/tenant
داده‌ی نادرست یا وضعیت موفقیت کاذب تولید نشود. اضافه شدن Stub به معنی قابل‌خزش
بودن پلتفرم نیست.

هر ATS یا Job Board ممکن است به URL، tenant، board slug یا تنظیمات اختصاصی نیاز
داشته باشد. کشف خودکار شرکت‌ها و پشتیبانی اجرایی از ۷۸ پلتفرم هنوز پیاده نشده است.

تنظیمات لازم برای Connectorهای دارای پیاده‌سازی:

| Connector | کلیدهای `config` لازم |
|---|---|
| Ashby | `board` |
| BambooHR | `company` |
| Breezy HR | `company` |
| Greenhouse | `board_token` |
| Lever | `company` |
| Personio | `tenant` |
| Pinpoint | `tenant` |
| Recruitee | `tenant` |
| Rippling | `company` |
| SmartRecruiters | `company_id` |
| Teamtailor | `tenant` |
| Workable | `subdomain` |
| Workday | `tenant`؛ `instance` و `site` اختیاری |
| WP Job Manager | `feed_url` (آدرس RSS عمومی) |

`company_name` برای اکثر Connectorها اختیاری است و در صورت نبود، نام از board یا
tenant حدس زده می‌شود. برای نمونه، منبع Ashby را با
`"connector":"ashby"` و `"config":{"board":"linear"}` ثبت کنید. هر Source معرف
یک board/tenant/feed مشخص است؛ اجرای همه‌ی شرکت‌های هر پلتفرم نیازمند کشف و ثبت
جداگانه‌ی آن Sourceها است.

## تست

```bash
docker compose exec api pytest
```

## ساختار

| مسیر | نقش |
|---|---|
| `app/connectors/base.py` | قرارداد Connector، `NormalizedJob`، retry/backoff |
| `app/connectors/greenhouse.py` | Connector اول |
| `app/connectors/registry.py` | ثبت صریح کلاس‌های Connector پلتفرم‌ها |
| `app/connectors/unavailable.py` | رفتار مشترک Stubها؛ بدون Crawl عمومی یا fallback |
| `app/services/normalization.py` | توابع خالص استانداردسازی (محلی، نوع استخدام، URL، HTML…) |
| `app/services/ingestion.py` | Pipeline و منطق Expiration |
| `app/services/search_service.py` | جست‌وجوی Full-Text با رتبه‌بندی |
| `app/workers/` | Celery، قفل اجرای تکراری، Scheduler |
| `app/api/` | Jobs، Companies، Sources، Admin، Health |
| `frontend/app/` | صفحات Next.js: `/`، `/jobs`، `/jobs/[id]`، `/companies/[id]`، `/admin` |
| `frontend/components/` | SearchForm، JobCard، Pagination |
| `backend/data/platforms.csv` | رجیستری ۷۸ پلتفرم با دسته‌بندی روش استخراج |

## تصمیم‌های طراحی

- **Expiration محافظه‌کار:** آگهی فقط وقتی `EXPIRED` می‌شود که چند اجرای کامل و موفق متوالی (`EXPIRE_AFTER_MISSED_RUNS`) آن را نبیند. اجرای ناموفق، ناقص (خطای Parse)، یا پاسخ خالی برای منبعی که قبلاً آگهی داشته، هرگز آگهی‌ها را منقضی نمی‌کند.
- **Dedup فاز ۱:** فقط تطبیق دقیق `source_id + external_job_id` (قید یکتا در دیتابیس). تطبیق URL و شباهت، فاز بعد؛ و طبق سند، شباهت فقط پیشنهاد می‌دهد و خودکار ادغام نمی‌کند.
- **Migration اولیه** از روی metadata مدل‌ها ساخته می‌شود؛ تغییرات بعدی با `alembic revision --autogenerate`.
- جست‌وجو از پیکربندی `simple` استفاده می‌کند تا برای زبان‌های مختلف (هلندی، انگلیسی…) بدون Stemming خطا ندهد.

## هنوز پیاده نشده (فاز بعد)

Rate Limit مشترک در Redis بین Workerها، تطبیق URL/Similarity، پارس حقوق،
تکمیل ۶۴ Connector Stub شده، کشف tenantها، پشتیبانی Playwright،
Prometheus/Sentry و تست‌های Integration با Postgres واقعی.

## Frontend (فاز ۲)

- صفحات سمت سرور رندر می‌شوند و فرم جست‌وجو یک فرم GET ساده است؛ پس URL هر جست‌وجو قابل اشتراک‌گذاری است و بدون JavaScript هم کار می‌کند.
- صفحه آگهی JSON-LD از نوع `JobPosting` تولید می‌کند (برای آگهی‌های Expired/Closed تولید نمی‌شود). نمایش Rich Result تضمین‌شده نیست.
- آگهی‌های `PENDING_EXPIRATION` با هشدار نمایش داده می‌شوند.
- لینک‌های Apply با `rel="noopener noreferrer nofollow"` باز می‌شوند.
- اجرای محلی بدون Docker: `cd frontend && npm install && npm run dev` (با `API_URL` و `NEXT_PUBLIC_API_URL` اشاره‌کننده به بک‌اند).
- محدودیت فعلی: کلید ادمین در مرورگر وارد می‌شود (کافی برای MVP؛ برای Production باید احراز هویت واقعی با نقش‌ها جایگزین شود).
