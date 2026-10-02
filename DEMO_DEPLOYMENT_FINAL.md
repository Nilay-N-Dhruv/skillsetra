# SKILLSETRA — Final Demo Deployment Package

This package is intentionally configured for the **SKILLSETRA demo**:

- `DEMO_MODE=true` is the default.
- Supabase authentication is **not required** for the demo.
- The demo workspace uses the bundled SQLite database at `backend/data/skillsetra_demo.db`.
- The learning-material library and the supplied roadmap are included in the package.
- FastAPI and Next.js can run together through a same-origin `/api/v1` proxy, so the browser does not need a public backend URL in the normal bundled deployment.

## What you need to provide

For a standard demo, nothing is required beyond the hosting service's normal setup. Optional integrations accept their own keys:

- Puter: browser-side provider; no server API key is required by this package.
- Ollama: optional local/self-hosted secondary provider; no API key.
- GitHub: only required when using real GitHub connection features.
- Supabase: optional for future authenticated production mode.

## Easiest deployment: one Docker service

Build and run:

```bash
docker compose up --build
```

Open:

```text
http://localhost:3000
```

FastAPI is internal to the same container at port `8000`. The Next.js server proxies browser API calls from `/api/v1/*` to FastAPI, so no browser CORS or localhost API URL configuration is needed.

## Local Windows demo without Docker

Run:

```text
START_TEST_NO_SIGNIN.bat
```

or:

```text
START_DEMO.bat
```

Then open `http://localhost:3000`.

The script creates the local Python environment, installs backend/frontend dependencies, forces demo mode, starts FastAPI and Next.js, and opens the demo.

## Important environment behavior

Demo mode defaults:

```env
DEMO_MODE=true
ENVIRONMENT=demo
AI_PROVIDER=puter
NEXT_PUBLIC_DEMO_MODE=true
NEXT_PUBLIC_API_BASE_URL=
BACKEND_INTERNAL_URL=http://127.0.0.1:8000
```

Do not switch `DEMO_MODE` to `false` for the hackathon demo. That activates the Supabase-authenticated production path.

## Optional Supabase

The project includes Supabase setup files for a future authenticated deployment, but the final demo does not require them to render or use the seeded role/competency/material workflow.

## Optional API keys

Fill only the services you actually use. Keep server secrets out of all `NEXT_PUBLIC_*` variables.

## Demo verification

The final package should pass these smoke checks:

1. `GET /api/v1/health` returns `status=ok, mode=demo`.
2. `GET /api/v1/career/roles` returns the seeded roles.
3. `POST /api/v1/profile/goal` stores the selected target role in the demo workspace.
4. `GET /api/v1/dashboard` returns dashboard data.
5. `GET /api/v1/analytics` returns analytics data.
6. `GET /api/v1/resources` returns the project catalog plus scanned supplied materials.
7. `GET /api/v1/roadmap` returns the role roadmap.
8. The Roadmap page displays the supplied `Complete Developer and AI Engineer Roadmap.png` asset.
