SKILLSETRA — FULL STACK BUILD

Requirements:
- Node.js 20+
- Python 3.11+

Run:
1. Copy backend/.env.example to backend/.env
2. Set DEMO_MODE=false when you want live backend integrations.
3. Add (no cloud AI key) for Puter AI primary.
4. Start Ollama locally and set OLLAMA_BASE_URL / OLLAMA_MODEL if desired.
5. Add GITHUB_TOKEN only when higher GitHub API limits/private repository access are needed.
6. Configure Supabase variables when production account persistence is enabled.
7. Double-click START_FULLSTACK.bat

Production architecture:
Browser -> Next.js -> FastAPI -> Puter AI primary -> Ollama secondary -> Puter tertiary browser fallback.
