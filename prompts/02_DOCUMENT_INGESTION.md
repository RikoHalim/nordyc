# CODEX PROMPT — Phase 02: Whole-Programme Document Ingestion

Read `AGENTS.md`, `docs/01_PRODUCT_SCOPE.md`, `docs/02_BACKEND_ARCHITECTURE.md`, `docs/03_DATA_MODEL.md`, `docs/07_TEST_PLAN.md` and Phase 01 code. Implement Phase 02 **only**.

Build robust upload and extraction of full programme structures plus multiple detailed syllabi. Supported inputs: text-based PDF and DOCX. Use PyMuPDF and python-docx. **Primary unit of ingestion is the entire programme**, not one selected course. Keep each course in the inventory even without a detailed syllabus.

Tasks:
1. Multipart upload with secure validation, storage by generated UUID, file size and type limits, SHA-256 dedup and source document metadata/versioning.
2. Parser adapters yielding structured text blocks with page numbers (PDF, 1-based) or paragraph index (DOCX), text excerpts and stable reference IDs.
3. Programme inventory extractor: course codes/names, compulsory/elective status, year/semester when present; ambiguous items flagged `NEEDS_REVIEW` rather than guessed. Store actual passage anchor IDs.
4. Syllabus extractor: course learning outcomes/topics/assessments **only if found**. Map to course by code or review-confirmed link; ambiguous mapping is flagged, not applied randomly. A regex/heuristic baseline is acceptable; don't pretend it's perfect.
5. `POST /programmes/{id}/ingestions`, `GET /ingestions/{id}`, `GET /programmes/{id}/courses` and relevant document metadata endpoints per API contract.
6. Offline fixture tests with a generated text PDF/DOCX in test code (avoid binary fixtures in repo). Cover multi-course, elective status, missing CLOs, blank/scanned pages, duplicate codes, malicious filename and idempotent re-ingestion.

Return a machine-readable extraction report with extracted courses, unsupported/unknown fields, file locations and review flags. **Do not invent learning outcomes to make the demo look complete.**

Run tests and report remaining extraction limitations. Do not build AI recommendations in this phase.
