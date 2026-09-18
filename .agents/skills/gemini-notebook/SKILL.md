---
name: gemini-notebook
description: >-
  Local source-grounded research assistant for querying, analyzing, and synthesizing local documents,
  research papers, technical specifications, and project notes.
  IMPORTANT: Runs ONLY when explicitly requested by the user (e.g. "research in notebook", "synthesize papers", "ground query in docs").
  This is a local Antigravity workflow grounded in your actual files, not Google's hosted NotebookLM service.
  NEVER runs proactively or as a background side effect.
---

# Gemini Notebook (Local Source-Grounded Research)

This skill provides a local, strictly source-grounded research assistant inspired by NotebookLM. It operates over files, documentation, and academic papers you point it to in your repository (such as `Research Papers/`, `docs/`, or architectural specs).

> [!IMPORTANT]
> **Invocation Constraint**: This skill must **only** be executed when the user explicitly asks to research, query, or synthesize specific local documents or folders. Never run proactively.
> **Honest Grounding**: This is a local agent workflow reading local workspace files. It is not connected to the proprietary cloud indexing engine of `notebooklm.google.com`. Every statement must cite real file paths and lines.

---

## Supported Input Sources

- **Academic / Technical Papers**: e.g., PDFs or Markdown extracts in `Research Papers/`.
- **Project Specifications & Docs**: `docs/`, `*.md`, `RFCs`, technical design records.
- **Source Code Files**: Specific modules or algorithms the user requests analysis on.

---

## Core Workflows (On Explicit Request Only)

### 1. Grounded Question Answering (`Query`)
When the user asks a question about their source material:
- Identify and inspect candidate documents using `list_dir`, `grep_search`, or `view_file`.
- Answer the query using **strictly grounded claims**.
- Provide inline file and line references: `[filename.md#L20-L45](path/to/file.md)`.
- If the source material does not contain the answer, explicitly state: *"The provided documents do not contain information on this topic."* Do not speculate.

### 2. Thematic Synthesis / Study Brief (`Brief`)
When requested to create a research brief or source synthesis:
- Extract core hypotheses, methodologies, datasets, benchmarks, and conclusions from the target papers or notes.
- Format as a structured Markdown synthesis:
  - **Executive Summary**: 2-3 sentences summarizing the key finding.
  - **Key Theses / Findings**: Bulleted list with direct citations to sources.
  - **Comparative Analysis**: If multiple papers/sources are provided, compare trade-offs, metrics, and limitations in a Markdown table.
  - **Relevance to Codebase**: How the paper's theory maps to current code in the workspace (e.g., in `ml/` or `server/`).

### 3. Study Guide & Conceptual Deep Dive (`Study Guide`)
When requested to prepare a study guide from documents:
- Generate high-yield key terms and definitions.
- Summarize critical algorithms or mathematical formulations with explanatory notes.
- Detail edge cases, limitations, and future research directions mentioned in the texts.
