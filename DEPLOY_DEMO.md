# SKILLSETRA — FINAL DEMO DEPLOYMENT

## Goal

This package is the **demo-first** version. The website is configured to run with:

- `DEMO_MODE=true`
- no Supabase login required
- bundled demo SQLite workspace
- bundled roadmap/materials
- Puter as the primary AI provider
- Ollama as an optional secondary/local provider
- optional GitHub/Supabase integrations

## Option A — one-container deployment (recommended)

Use the root `Dockerfile` and `docker-compose.yml`.

```bash
docker compose up --build
```

Open:

`http://localhost:3000`

Only port **3000** is public. FastAPI runs inside the same container on port **8000**. Next.js proxies `/api/v1/*` to FastAPI, so the browser never has to know the backend URL.

This is the simplest deployment because the frontend and backend are packaged together.

## Option B — Vercel/hosted Next.js + separate FastAPI

The frontend now uses the same-origin `/api/v1` proxy. Set one server-side Next.js variable:

```env
BACKEND_INTERNAL_URL=https://YOUR-FASTAPI-HOST
```

You do not need to expose the FastAPI URL as a `NEXT_PUBLIC_*` browser variable.

Keep:

```env
NEXT_PUBLIC_DEMO_MODE=true
NEXT_PUBLIC_API_BASE_URL=
```

Backend environment:

```env
DEMO_MODE=true
ENVIRONMENT=demo
CORS_ORIGINS=https://YOUR-FRONTEND-HOST
```

## Optional keys

Only enter keys for features you actually use:

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_TOKEN=
```

The core demo does not require these to load the dashboard, roles, roadmap or bundled learning catalog.

## Demo database

The demo workspace is in:

`backend/data/skillsetra_demo.db`

It contains the seeded `demo-user` workspace and is automatically used whenever `DEMO_MODE=true`.

Supabase setup is kept as an optional future authenticated database layer; it is not on the critical path for the demo.
