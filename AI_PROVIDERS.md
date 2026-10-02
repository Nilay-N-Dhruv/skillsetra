# Skillsetra AI providers

## Primary: Puter AI
Puter AI runs in the browser through Puter.js. No server-side API secret is bundled in Skillsetra. The app hands the exact task prompt to the browser provider.

## Secondary: Ollama
Ollama runs locally through the FastAPI backend at `http://localhost:11434` by default. Configure `OLLAMA_MODEL` in `backend/.env`.

## Routing
1. Puter AI is the default provider for AI interactions.
2. If Puter cannot answer, the shared frontend AI helper can send the same prompt to the Ollama fallback endpoint.
3. If both are unavailable, the UI reports the provider failure instead of fabricating an AI answer.

## Security
Do not place provider secrets in browser code. The Ollama endpoint is local by default. Production deployments should configure authentication, CORS and network access appropriately.
