# SKILLSETRA

Competency intelligence platform: **Assess → Analyze → Identify → Improve → Build → Prove → Update**.

This archive is the DEMO package built from the existing SKILLSETRA application. It uses explicit local demo mode and persistent SQLite workspace state. Demo data is labeled and is never presented as a real user's evidence.

## Run demo
Use `START_DEMO.bat`. It sets `DEMO_MODE=true` and `NEXT_PUBLIC_DEMO_MODE=true` for the local processes.

## Production configuration
Use `backend/.env.example` and `frontend/.env.example` as the starting point for the full-stack package. Production requires Supabase Auth/Postgres/RLS and configured external providers.

## Final rebuild verification
See `REBUILD-AUDIT-2026-10-01.md`. The backend test suite passes, frontend TypeScript/TSX syntax and relative imports were statically audited, and the uploaded final SKILLsetra logo is included.

## AI routing
Puter AI is the primary browser AI provider. Ollama is the secondary local provider. No cloud AI key is required for the default demo path.

## Removed surface
Compiler Lab has been removed from navigation, routes and the user-facing product surface.
