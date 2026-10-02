SKILLSETRA — FINAL DEMO RUN GUIDE

FASTEST LOCAL OPTION
1. Install Node.js LTS (20+) and Python 3.11+.
2. Double-click START_TEST_NO_SIGNIN.bat.
3. Open http://localhost:3000.
4. Demo mode is enabled automatically. No Supabase sign-in is required.
5. FastAPI docs: http://localhost:8000/docs

DOCKER OPTION
1. Install Docker Desktop.
2. From this folder run: docker compose up --build
3. Open http://localhost:3000
4. Next.js proxies /api/v1 to FastAPI internally, so the browser does not need a public backend URL.

FINAL DEMO DEFAULTS
- DEMO_MODE=true
- NEXT_PUBLIC_DEMO_MODE=true
- bundled SQLite workspace database
- bundled learning materials
- supplied roadmap included
- Puter is the primary AI provider
- Ollama is optional

AUTHENTICATED PRODUCTION MODE
This package includes Supabase integration for a separate future production mode. Do not disable demo mode unless you intentionally configure the authenticated production environment.
