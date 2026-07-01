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

# Seed demo data — 3 departments + 5 users (one per role), all passwords default to "admin123"
python manage.py seed_demo
python manage.py seed_demo --password custompass

# Testing
python manage.py test                          # Run all tests
python manage.py test apps.accounts            # Single app
pytest                                         # If pytest-django configured

# Shell (IPython installed)
python manage.py shell

# Install deps
pip install -r requirements/dev.txt            # base + pytest/factory-boy/ipython
pip install -r requirements/prod.txt           # base + psycopg2 + gunicorn

# Create a new app (always use apps. prefix)
python manage.py startapp <name> apps/<name>

# ---- Frontend (Vue 3 + Vite) ----
cd frontend
npm install                                    # Install dependencies
npm run dev                                    # Dev server on :5173, proxies /api to :8000
npm run build                                  # Production build
```

## Frontend Architecture

### Tech stack
Vue 3 (Composition API, `<script setup>`) + Vite + Element Plus + vue-router + Pinia + Axios.

### Directory layout
```
frontend/src/
├── api/index.js       # Axios instance with JWT interceptor + 401 redirect
├── api/auth.js        # demoLogin(), getCurrentUser()
├── router/index.js    # /login (guest), / (requiresAuth) + navigation guard
├── stores/auth.js     # Pinia auth store (token in localStorage, login/logout/fetchUser)
├── views/LoginView.vue   # Demo login page
├── views/DashboardView.vue  # Placeholder dashboard
├── style.css          # Design tokens (CSS custom properties) + Element Plus overrides
├── App.vue            # Root: <RouterView />
└── main.js            # createApp → Pinia → Router → ElementPlus → mount
```

### Design tokens (style.css)
"Precision Instrument" theme: `--steel: #1B1F2A`, `--paper: #F5F3EE`, `--brass: #C8A45C`, `--blueprint: #4A90A4`, `--sage: #7D9B76`, `--vermilion: #D4695A`. Font stack: `"PingFang SC", "Microsoft YaHei", "Inter", sans-serif`.

### API proxy
Vite dev server proxies `/api/*` → `http://127.0.0.1:8000`. In production, configure Nginx to serve frontend static files and proxy `/api/` to the Django backend.

## Architecture

### Settings hierarchy

Three-layer `from .base import *` pattern:
- `config/settings/base.py` — shared config via `python-decouple` with sensible defaults (SQLite, Demo mode on)
- `config/settings/dev.py` — `DEBUG=True`, SQLite, CORS for `localhost:5173`
- `config/settings/prod.py` — `DEBUG=False`, PostgreSQL, HTTPS security headers

`manage.py` defaults to `config.settings.dev`; WSGI/ASGI default to `config.settings.prod`.

All config values read via `decouple.config("KEY", default=...)` — no `.env` file needed to start.

### App organization

All apps live under `apps/` and use the `apps.xxx` naming convention in `AppConfig.name`:

```python
# apps/accounts/apps.py
class AccountsConfig(AppConfig):
    name = "apps.accounts"
    verbose_name = "用户与部门"
```

`INSTALLED_APPS` = `DJANGO_APPS + THIRD_PARTY_APPS + PROJECT_APPS`. Active apps: `accounts`, `dingtalk`, `reports`, `projects`, `stats`. `exports` is commented out until its models are created.

### Authentication modes

Three modes that coexist:
1. **JWT** (primary) — `rest_framework_simplejwt`, configured as default DRF auth
2. **Demo login** (active during dev) — `POST /api/auth/demo-login/` accepts username+password, returns JWT + user profile. Guarded by `DINGTALK_DEMO_MODE=True`
3. **DingTalk SSO** (designed, not yet built) — QR code OAuth2 flow

### Key models

- **`accounts.Department`** — tree via `parent` self-FK; `manager` FK → User; `dingtalk_dept_id`
- **`accounts.User`** (extends `AbstractUser`) — `AUTH_USER_MODEL`. Five roles via `TextChoices`. Permission helpers: `can_view_department(dept)`, `can_view_project(project)`
- **`projects.Project`** — name/code/aliases (JSON), product_managers M2M, `match_text()` for log parsing
- **`reports.WorkReport`** — raw DingTalk log JSON in `raw_contents`, linked to creator/department/sync_log
- **`reports.ReportContent`** — per-field content split (今日完成工作, 明日计划, etc.)
- **`stats.WorkEntry`** — parsed work-hour record (the core analytic unit). Links to report/employee/department/project. Has confidence score (0-100) and `is_categorized` flag. 4 DB indexes for aggregation queries
- **`dingtalk.SyncLog`** — sync operation audit trail

### API pattern

URL chain: `config/urls.py` → `config/api_urls.py` → per-app `urls.py`

Current endpoints:
- `POST /api/auth/demo-login/` — Demo login (AllowAny, no auth classes)
- `GET /api/auth/me/` — Current user profile (IsAuthenticated)

Views use DRF `APIView` (class-based). Serializers in per-app `serializers.py`.

### Role-based permissions

| Scope | admin | executive | dept_manager | product_manager | employee |
|-------|:-----:|:---------:|:------------:|:--------------:|:--------:|
| Own data | ✓ | ✓ | ✓ | ✓ | ✓ |
| Department data | all | all | own dept | ✗ | ✗ |
| Project stats | all | all | dept projects | owned projects | ✗ |
| Manage users/roles | ✓ | ✗ | ✗ | ✗ | ✗ |
| Trigger sync | ✓ | ✓ | ✗ | ✗ | ✗ |

Permission enforcement via custom DRF Permission Classes at the QuerySet level (not yet implemented — designed, pending implementation).

## Conventions

- **All `verbose_name` values are in Chinese** — this is an internal tool for Chinese-speaking users
- **Unicode in management commands**: Avoid emoji/special Unicode in `stdout.write()` — Windows GBK terminals can't encode them. Use ASCII-safe alternatives (`[+]` instead of `✓`, `[OK]` instead of `✅`)
- **App naming**: Never name an app `statistics` — it conflicts with Python's stdlib module. The app is named `stats`
- **Custom User model timing**: `AUTH_USER_MODEL` must be enabled before the first `migrate`. If you get `InconsistentMigrationHistory`, delete `db.sqlite3` and re-migrate from scratch
- **Demo mode guard**: Always check `settings.DINGTALK_DEMO_MODE` before exposing local-auth endpoints

## Gotchas

- No `config/celery.py` exists yet — Celery is configured in settings but the Celery app instance hasn't been created. Add this before implementing sync tasks
- The `can_view_department()`/`can_view_project()` methods exist on the User model but are not yet enforced in DRF permission classes or QuerySet filtering
- The `frontend/` directory does not exist — Vue 3 frontend is planned but not started
- `db.sqlite3` is gitignored, so each clone needs `python manage.py migrate && python manage.py seed_demo`
