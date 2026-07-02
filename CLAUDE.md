# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

钉钉工作汇报统计系统 — a standalone web app (not embedded in DingTalk) for parsing DingTalk work reports, aggregating work hours by project/employee/department, and enforcing role-based data access. Python full stack: Django 6.0 + DRF backend, Vue 3 + Element Plus frontend.

See `设计方案.md` for the full design document (13 sections) and `工程日志.md` for the implementation log.

## Common Commands

```bash
# Development server (uses SQLite, DEBUG=True, Demo mode)
python manage.py runserver

# Database
python manage.py makemigrations
python manage.py migrate

# Seed data — always run seed_demo first, then seed_reports
python manage.py seed_demo                      # 3 departments + 5 users (one per role), passwords "admin123"
python manage.py seed_demo --password custompass
python manage.py seed_reports                   # ~30 reports + ~97 work entries, last 10 working days
python manage.py seed_reports --days 5           # Fewer days span

# Testing
python manage.py test tests.test_infrastructure  # 27 infrastructure tests (DB, auth, API, ORM, roles)
python manage.py test apps.accounts              # Single app

# Shell (IPython installed)
python manage.py shell

# Install deps
pip install -r requirements/dev.txt              # base + pytest/factory-boy/ipython
pip install -r requirements/prod.txt             # base + psycopg2 + gunicorn

# Create a new app (always use apps. prefix)
python manage.py startapp <name> apps/<name>

# ---- Frontend (Vue 3 + Vite) ----
cd frontend
npm install                                      # Install dependencies
npm run dev                                      # Dev server on :5173, proxies /api to :8000
npm run build                                    # Production build
```

## Architecture

### Settings hierarchy

Three-layer `from .base import *` pattern:
- `config/settings/base.py` — shared config via `python-decouple` with sensible defaults (SQLite, Demo mode on)
- `config/settings/dev.py` — `DEBUG=True`, SQLite, CORS for `localhost:5173`
- `config/settings/prod.py` — `DEBUG=False`, PostgreSQL, HTTPS security headers

`manage.py` defaults to `config.settings.dev`; WSGI/ASGI default to `config.settings.prod`.

All config values read via `decouple.config("KEY", default=...)` — no `.env` file needed to start.

### App organization

All apps live under `apps/` and use the `apps.xxx` naming convention in `AppConfig.name`. Active apps: `accounts`, `dingtalk`, `reports`, `projects`, `stats`. `exports` is commented out until its models are created.

### Key models

- **`accounts.Department`** — tree via `parent` self-FK; `manager` FK → User; `dingtalk_dept_id`
- **`accounts.User`** (extends `AbstractUser`) — `AUTH_USER_MODEL`. Five roles via `TextChoices`: admin, executive, dept_manager, product_manager, employee. Has `is_admin`/`is_executive` etc. properties, plus `can_view_department(dept)` and `can_view_project(project)`.
- **`projects.Project`** — name/code/aliases (JSON), product_managers M2M → User, `match_text()` for log parsing
- **`reports.WorkReport`** — raw DingTalk log JSON in `raw_contents`, linked to creator (User)/department/sync_log. Reverse: `work_entries` (from WorkEntry.report) and `contents` (from ReportContent.report).
- **`reports.ReportContent`** — per-field content split (今日完成工作, 明日计划, etc.) under a WorkReport
- **`stats.WorkEntry`** — parsed work-hour record (the core analytic unit). FK to report/employee/department/project. Has confidence score (0-100), `is_categorized` flag, 4 DB composite indexes on `(employee, date)`, `(department, date)`, `(project, date)`, `(is_categorized,)`.
- **`dingtalk.SyncLog`** — sync operation audit trail

### API endpoints

URL chain: `config/urls.py` → `config/api_urls.py` → per-app `urls.py`

| Method | Endpoint | View | Access |
|--------|----------|------|--------|
| POST | `/api/auth/demo-login/` | `DemoLoginView` | AllowAny |
| GET | `/api/auth/me/` | `CurrentUserView` | IsAuthenticated |
| GET | `/api/reports/` | `ReportListView` | IsAuthenticated + role filter |
| GET | `/api/reports/{id}/` | `ReportDetailView` | IsAuthenticated + role filter |
| GET | `/api/stats/dashboard/` | `DashboardView` | IsAuthenticated + role filter |
| GET | `/api/stats/entries/` | `WorkEntryListView` | IsAuthenticated + role filter |

Views use DRF `APIView` / `generics.ListAPIView` / `generics.RetrieveAPIView`. Serializers in per-app `serializers.py`.

**Report list query params**: `page`, `page_size`, `date_from`, `date_to` (default 30-day window), `username`, `department`, `search` (icontains in ReportContent values).

**Dashboard response**: `total_hours_this_month`, `total_hours_last_month`, `total_reports_this_month`, `active_projects`, `active_employees`, `avg_daily_hours` (hours ÷ days with data), `project_breakdown[]`, `employee_breakdown[]`, `daily_trend[]`.

### Role-based permissions (fully enforced)

Permission filtering is in `apps/accounts/permissions.py` — all report/stats endpoints call these functions at the QuerySet level (not via DRF Permission classes):

- `get_visible_department_ids(user)` — returns visible department IDs; dept_manager gets own dept + recursive sub-departments
- `apply_report_access_filter(qs, user)` — filters WorkReport queryset by role
- `apply_work_entry_access_filter(qs, user)` — filters WorkEntry queryset by role

| Scope | admin | executive | dept_manager | product_manager | employee |
|-------|:-----:|:---------:|:------------:|:--------------:|:--------:|
| Own data | ✓ | ✓ | ✓ | ✓ | ✓ |
| Department data | all | all | own dept + subs | ✗ | ✗ |
| Project stats | all | all | dept projects | owned projects | ✗ |
| Manage users/roles | ✓ | ✗ | ✗ | ✗ | ✗ |
| Trigger sync | ✓ | ✓ | ✗ | ✗ | ✗ |

### Authentication modes

Three modes that coexist:
1. **JWT** (primary) — `rest_framework_simplejwt`, configured as default DRF auth
2. **Demo login** (active during dev) — `POST /api/auth/demo-login/` accepts username+password, returns JWT + user profile. Guarded by `DINGTALK_DEMO_MODE=True`
3. **DingTalk SSO** (designed, not yet built) — QR code OAuth2 flow

## Frontend Architecture

### Tech stack
Vue 3 (Composition API, `<script setup>`) + Vite + Element Plus + vue-router + Pinia + Axios + ECharts.

### Directory layout
```
frontend/src/
├── api/index.js           # Axios instance with JWT interceptor + 401 redirect
├── api/auth.js            # demoLogin(), getCurrentUser()
├── api/dashboard.js       # getDashboard(), getWorkEntries(params)
├── api/reports.js         # getReports(params), getReportDetail(id)
├── router/index.js        # /login (guest), / (Dashboard), /reports (Reports) + auth guard
├── stores/auth.js         # Pinia auth store (token in localStorage, login/logout/fetchUser)
├── views/LoginView.vue    # Demo login page (5 pre-filled accounts)
├── views/DashboardView.vue # Full dashboard: 5 KPI cards + 3 ECharts + project detail table
├── views/ReportsView.vue   # Report list with filters, pagination table, detail drawer
├── style.css              # Design tokens (CSS custom properties) + Element Plus overrides
├── App.vue                # Sidebar layout (200px fixed) + guest standalone mode
└── main.js                # createApp → Pinia → Router → ElementPlus → mount
```

### Design tokens (style.css)
"Precision Instrument" theme: `--steel: #1B1F2A`, `--steel-light: #262B38`, `--paper: #F5F3EE`, `--brass: #C8A45C`, `--blueprint: #4A90A4`, `--sage: #7D9B76`, `--vermilion: #D4695A`. Font stack: `"PingFang SC", "Microsoft YaHei", "Inter", sans-serif`.

### App.vue layout
Guest routes (login) render standalone `<RouterView />`. Authenticated routes wrap in a 200px fixed sidebar + main content area. Sidebar has brand mark, nav items (Dashboard / 工作日志 with Element Plus icons), user info footer, logout button. Responsive: collapses to 56px on ≤640px.

### ECharts dashboard (DashboardView.vue)
3 charts with "Precision Instrument" palette: daily trend bar (BRASS), project pie (donut with legend), employee horizontal bar. Charts initialize in `onMounted` after data loads, dispose in `onUnmounted`, resize on window resize. **Critical**: `loading.value = false` must be set BEFORE `renderCharts()` — otherwise the DOM containers won't exist yet (template still shows loading state).

### Report detail drawer (ReportsView.vue)
Uses `el-drawer` with `@row-click="(row) => openDetail(row.id)"` — Element Plus `el-table` passes the row object, NOT the id. Drawer content is teleported to `<body>`, so all drawer styles must be in a non-scoped `<style>` block (Vue scoped styles can't reach teleported DOM).

### API proxy
Vite dev server proxies `/api/*` → `http://127.0.0.1:8000`. `vite.config.js` uses `host: '0.0.0.0'` to bind both IPv4 and IPv6 (fix for `127.0.0.1` connection refused). In production, configure Nginx to serve frontend static files and proxy `/api/` to the Django backend.

## Conventions

- **All `verbose_name` values are in Chinese** — this is an internal tool for Chinese-speaking users
- **Unicode in management commands**: Avoid emoji/special Unicode in `stdout.write()` — Windows GBK terminals can't encode them. Use ASCII-safe alternatives (`[+]` instead of `✓`, `[OK]` instead of `✅`)
- **App naming**: Never name an app `statistics` — it conflicts with Python's stdlib module. The app is named `stats`
- **Custom User model timing**: `AUTH_USER_MODEL` must be enabled before the first `migrate`. If you get `InconsistentMigrationHistory`, delete `db.sqlite3` and re-migrate from scratch
- **Demo mode guard**: Always check `settings.DINGTALK_DEMO_MODE` before exposing local-auth endpoints

## Gotchas

- No `config/celery.py` exists yet — Celery is configured in settings but the Celery app instance hasn't been created. Add this before implementing sync tasks
- `db.sqlite3` is gitignored, so each clone needs `python manage.py migrate && python manage.py seed_demo && python manage.py seed_reports`
- `seed_reports` generates reports going back `--days` working days from today; on the 1st of a month, almost all data falls in the previous month. Run with a higher `--days` value to populate the current month
- `seed_reports` starts its report ID sequence at `max_existing_id + 1000` to avoid UNIQUE constraint collisions on `dingtalk_report_id`. If you delete reports manually and re-run, the IDs may still collide — check the max existing ID first
- Windows PowerShell blocks npm scripts by default; use cmd.exe or `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` in admin PowerShell
