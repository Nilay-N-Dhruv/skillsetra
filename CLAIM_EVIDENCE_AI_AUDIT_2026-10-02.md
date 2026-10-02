# SKILLSETRA Claim Evidence AI Audit — 2026-10-02

## New behavior
When a user submits **Claim Evidence**, SKILLSETRA now automatically starts an AI evidence review.

### Provider routing
1. Server-side Ollama is used when it is the selected/available server provider.
2. If server AI is unavailable, the frontend automatically hands the same evidence-review prompt to Puter AI.
3. If all AI providers are unavailable, the claim is finalized as **NO DETECTION** rather than being falsely verified.

### Evidence decision
The AI must return structured evidence support:
- supported: true/false
- confidence: high/medium/low/none
- message
- detected evidence signals

The claim itself is never treated as proof merely because the user typed it.

### Positive evidence path
When AI detects concrete support:
- claim status becomes `ai-supported`
- an AI-reviewed evidence event is added to the evidence ledger
- the competency progression changes according to confidence
- target-role goal progression is recalculated
- dashboard and evidence workspace expose the updated progression

Progression deltas:
- high confidence: +8
- medium confidence: +5
- low confidence: +2

### Negative/no-detection path
When AI finds no support:
- claim status becomes `no-detection`
- UI displays **No detected evidence**
- no fake observed evidence event is created
- competency progression is adjusted downward by 3 points to reflect the unsuccessful claim review

### Existing evidence linking
If the user links an already observed evidence artifact, its activity, competency, evidence text, result, and confidence are included in the AI review context.

## Verification performed
- Backend pytest: **9 passed**
- Python compilation: **PASS**
- Positive AI-review endpoint smoke test: **PASS**
- No-detection AI-review endpoint smoke test: **PASS**
- Claim → AI review → evidence ledger/progression flow: **PASS**
- Dark mode remains the default in AppProvider and persisted user theme migration.
- ZIP integrity verified after packaging.

## Frontend build limitation
A full Next.js production build was not claimed as verified because the environment does not currently have frontend `node_modules`, and npm installation previously timed out. Source-level changes were audited and backend/runtime smoke tests were completed.
