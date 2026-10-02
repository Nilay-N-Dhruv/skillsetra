# SKILLSETRA Final AI Evidence + Materials Audit — 2026-10-02

## AI claim evidence
- Claim review now compares the user's claim against the supplied evidence title, description, URL and linked observed artifact context.
- AI is required to return a structured evidence score (0–100), claim match, ownership score, verification score, confidence, detected signals and a user-facing message.
- Positive evidence creates an AI-supported evidence ledger event.
- No-detection evidence does not create a verified evidence event.
- Competency progression is calculated from the evidence score rather than a fixed unconditional increase.
- Strong evidence raises progression; weak/no evidence can lower progression.
- Progression is clamped to 0–100.
- AI-supported claim evidence counts toward target-role coverage; no-detection claims do not.
- If the provider returns malformed output, the parser uses a conservative fallback and never converts a plain claim into verified evidence.

## Materials library
- Added `learning-materials/` as the source-of-truth content folder.
- Every seeded subject has `README.md`, `links.txt`, and `materials/`.
- `links.txt` accepts `Title | URL | Type | Level`.
- `.pdf`, `.ppt`, and `.pptx` files in a subject's `materials/` folder are discovered automatically.
- FastAPI exposes the files through an authenticated material endpoint.
- Learning page loads the folder catalog and displays links, PDFs and presentation files.
- Existing field-guide PDFs and study-deck PPTX files were copied into relevant subject folders as starter material.
- New resources can be added without editing the frontend resource array.

## Tests
- Python compilation: PASS.
- Backend pytest: 9 passed.
- Materials scan smoke test: 19 material resources / 13 material subject folders detected.
- Positive AI-review smoke: supported=true, evidence_score=92, progress_delta=+8, goal progression updated.
- No-detection AI-review smoke: supported=false, evidence_score=8, progress_delta=-8, no evidence event created.

## Build limitation
A full Next.js production build was not performed because frontend dependencies are not installed in the audit environment. Do not describe the frontend as production-build-verified until `npm install` and the production build succeed in the target environment.
