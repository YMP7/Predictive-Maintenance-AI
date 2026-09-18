---
name: code-wiki
description: >-
  Generates an interactive, searchable, and structured Markdown wiki with architecture diagrams,
  module catalogs, and API indexes for the codebase.
  IMPORTANT: Runs ONLY when explicitly requested by the user (e.g. "generate code wiki", "create codebase wiki").
  NEVER runs proactively or as a background side effect.
---

# Code Wiki Generator

This skill turns a codebase into a structured, interactive, living Markdown wiki grounded entirely in the actual files present in the repository.

> [!IMPORTANT]
> **Invocation Constraint**: This skill must **only** be executed when the user explicitly prompts to generate or update the codebase wiki. Never trigger this skill proactively, after code edits, or during unrelated tasks.

---

## Output Location

By default, write generated wiki files to:
`docs/wiki/`

Index file: `docs/wiki/README.md`

---

## Wiki Structure

When invoked, inspect the workspace and produce or update the following core documents:

1. **`docs/wiki/README.md` (Wiki Home & Navigation)**:
   - System Overview: 1-paragraph summary of what the project does.
   - High-level architecture summary.
   - Table of contents with relative markdown links to all wiki pages.

2. **`docs/wiki/ARCHITECTURE.md` (Architecture & Data Flow)**:
   - High-level system architecture diagram using Mermaid syntax (`mermaid`).
   - Core subsystem boundaries (e.g., frontend, backend services, database, streaming/queues, ML pipelines).
   - Data flow walkthrough from ingestion/input to processing, storage, and UI presentation.

3. **`docs/wiki/MODULE_CATALOG.md` (Subsystems & Modules)**:
   - Directory-by-directory breakdown of the repository.
   - For each directory: Primary responsibility, key entrypoints, core interfaces, and internal dependencies.
   - Links to key files using standard markdown links (e.g., `[server/api.py](../../server/api.py)`).

4. **`docs/wiki/API_AND_INTERFACES.md` (APIs & Schemas)**:
   - REST/WebSocket endpoints, message queues (MQTT/Kafka), or CLI interfaces discovered in the code.
   - Request/response contracts, Pydantic models, or JSON schemas.
   - Authentication, headers, and error code conventions.

5. **`docs/wiki/DEVELOPER_RUNBOOK.md` (Setup & Workflows)**:
   - Environment variables (referenced from `.env.example` if present).
   - Local startup commands (backend, frontend, services, docker-compose).
   - Testing guidelines (test runners, coverage commands, CI pipelines).

---

## Generation Rules

1. **Grounding in Active Code**:
   - Inspect actual files using `list_dir`, `grep_search`, and `view_file`.
   - Never invent imaginary dependencies, frameworks, or endpoints. If something is missing or stubbed, document it as such.

2. **Mermaid Diagram Best Practices**:
   - Keep diagrams clear and readable.
   - Enclose node labels in double quotes (e.g., `api["FastAPI Server"] --> db[("PostgreSQL")]`).
   - Avoid special characters without quotes.

3. **Incremental Updates**:
   - If `docs/wiki/` already exists, check existing files and selectively update outdated sections rather than wiping out manual notes.
