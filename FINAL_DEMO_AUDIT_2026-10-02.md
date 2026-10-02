# SKILLSETRA Final Demo Audit — 02 Oct 2026

## Demo configuration

- Demo mode defaults to `true` in backend configuration.
- `NEXT_PUBLIC_DEMO_MODE=true` is bundled for the frontend.
- Supabase authentication is not required for the demo.
- Demo workspace is bundled in `backend/data/skillsetra_demo.db`.
- Frontend API calls use a same-origin `/api/v1` path.
- Next.js rewrites `/api/v1/*` to FastAPI using `BACKEND_INTERNAL_URL`.
- A single Docker service can therefore expose only port 3000.

## Database

- Bundled SQLite demo DB exists and was reseeded to a clean `demo-user` state.
- `workspace_snapshots` contains the initial demo workspace.
- Optional Supabase demo setup SQL is included, but the core demo does not depend on Supabase.

## Core API smoke tests

The FastAPI server was started from source with default demo settings and these endpoints returned HTTP 200:

- `/api/v1/health`
- `/api/v1/career/roles`
- `/api/v1/dashboard`
- `/api/v1/analytics`
- `/api/v1/resources`
- `/api/v1/roadmap`
- `/api/v1/profile/goal` (POST)
- `/api/v1/dashboard` after goal update

The role catalog returned 12 roles.

## Learning materials

The runtime scanner reports:

- 354 resources
- 281 YouTube links
- 64 course/reference links
- 6 PDFs
- 3 slide decks
- 28 populated fields

## Roadmap asset

`frontend/public/skillsetra-roadmap.png` SHA-256 exactly matches the supplied `Complete Developer and AI Engineer Roadmap.png`.

## Source/code checks

- Python compilation: PASS.
- Relative frontend import audit: 0 missing relative imports.
- Changed TypeScript/TSX files transpile successfully for syntax.
- Gemini runtime configuration: removed; current primary provider is Puter, secondary/local provider is Ollama.
- Compiler Lab: not present in the navigation/runtime package.

## Environment limitation

A full Next.js production build was not independently verified in this environment because npm dependency installation timed out and Docker is unavailable in the execution environment. The package includes a single-container Docker deployment path designed to build the complete frontend + backend together.
