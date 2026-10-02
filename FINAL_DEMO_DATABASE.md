# SKILLSETRA Final Demo Database

The final demo uses two layers:

## 1. Demo workspace database

`backend/data/skillsetra_demo.db`

This SQLite database is bundled with the website and contains the `workspace_snapshots` table plus the initial `demo-user` workspace. It requires no setup and is used when `DEMO_MODE=true`.

The application will update the demo workspace while the backend process is running. On hosts with ephemeral storage, those changes may reset after redeploy/restart; the seeded starting state remains available.

## 2. Optional Supabase database

Supabase files are included for a future authenticated deployment:

- `database/schema.sql`
- `database/seed.sql`
- `SKILLSETRA_SUPABASE_DEMO_SETUP.sql` (when present in the project root)

The final demo does not depend on Supabase being configured.
