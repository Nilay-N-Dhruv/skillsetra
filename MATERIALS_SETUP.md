# SKILLSETRA - Roadmap-Aligned Learning Materials

The `learning-materials/` directory is the source-of-truth content library for the Learning hub and the Roadmap material library.

## Sources imported for this final build

- `yt links.txt` - field-specific YouTube learning links.
- `ppt pdf.txt` - field-specific course/reference/material links.
- `notes and links.pdf` - image-only YouTube-link pages; clean OCR-readable 11-character video IDs only were imported to prevent broken links.
- `Complete Developer and AI Engineer Roadmap.png` - exact visual roadmap supplied by the project team and installed at `frontend/public/skillsetra-roadmap.png`.

See `SOURCE-MATERIALS-INDEX-2026-10-02.md` for the field mapping and import counts.

## Add a YouTube / web / course link

Open the field folder, for example:

`learning-materials/python/links.txt`

Add one line:

`Python Functions Masterclass | https://www.youtube.com/watch?v=VIDEO_ID | youtube | Beginner`

The Learning page and Roadmap field library will show it automatically after the backend reads the catalog.

## Add a PDF / PPT / PPTX

Put the file here:

`learning-materials/python/materials/`

The backend automatically detects `.pdf`, `.ppt`, and `.pptx` files and exposes them in the Learning and Roadmap resource libraries.

## Field organization

The supplied roadmap is reflected in the catalog through fields such as Python, SQL & Databases, Data Analysis & Visualization, Machine Learning, AI Engineering, React & Next.js, Next.js resources, FastAPI & APIs, Docker & Containers, Cloud Engineering, Cybersecurity, System Design, DevOps & CI/CD, Technical Communication, plus supporting fields such as Backend Engineering, Frontend Engineering, Full-Stack Engineering, Kubernetes, Git & GitHub, Data Engineering, RAG & Retrieval, LLM Evaluation, Observability & Reliability, Linux & Networking, Terraform, Distributed Systems, UI Engineering and Flutter & Dart.

Provider-specific cloud links (AWS, Azure and Google Cloud) are grouped under Cloud Engineering, while LLM Evaluation and RAG resources are grouped under AI Engineering. PostgreSQL resources are grouped under SQL & Databases; React/Next.js resources are grouped under React & Next.js; Deep Learning is grouped under Machine Learning.

## Supported link format

`Title | URL | Type | Level`

Supported types include:

- youtube
- pdf
- slides
- course
- reference
- documentation
- learning

## Runtime behavior

The FastAPI backend scans this folder when `/api/v1/materials`, `/api/v1/resources`, `/api/v1/subjects`, and the Roadmap material endpoint are requested. Newly added materials do not require a frontend resource-array edit.

For production, large/private files should be stored in object storage with authenticated download URLs instead of putting sensitive material in the application repository.
