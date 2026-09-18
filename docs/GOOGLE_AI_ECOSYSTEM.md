# Google AI Tools & Experiments: Antigravity Compatibility Guide

This document provides a factual reference for 15 Google AI tools, models, and Labs experiments, detailing their integration status within **Google Antigravity**, their operational lifecycle, and how to use the capabilities added to this workspace.

---

## 1. Quick Feasibility & Integration Summary

| # | Tool | Original Concept | Antigravity Status | Lifecycle / Integration Action |
| :-: | :--- | :--- | :--- | :--- |
| 1 | **AntiGravity** | Agent-first coding IDE | **Native Host** | You are running inside Antigravity right now. |
| 2 | **Stitch** | Prompt-to-UI designs & code | **Native MCP Active** | Fully supported via `StitchMCP` tools and `stitch-design-taste` skill. |
| 3 | **Whisk** | Image blending & remixing | **Native Tool Active** | Built-in via Antigravity's `generate_image` tool with reference image inputs. |
| 4 | **Firebase Studio** | Browser cloud dev environment | **Sunsetting / Deprecated** | New workspace creation disabled June 22, 2026; full shutdown March 22, 2027. Antigravity is the recommended successor. Core Firebase CLI & `cloudrun` MCP server remain active. |
| 5 | **Code Wiki** | Searchable codebase wiki generator | **Added as Skill** | Installed at [`.agents/skills/code-wiki/SKILL.md`](../.agents/skills/code-wiki/SKILL.md). **Explicit user invocation only.** |
| 6 | **Gemini Notebook** | Source-grounded research assistant | **Added as Skill** | Installed at [`.agents/skills/gemini-notebook/SKILL.md`](../.agents/skills/gemini-notebook/SKILL.md). Local grounded research over workspace files/papers. **Explicit user invocation only.** |
| 7 | **Learn Your Way** | Adaptive quizzes & study notes | **Added as Skill** | Installed at [`.agents/skills/learn-your-way/SKILL.md`](../.agents/skills/learn-your-way/SKILL.md). Turns code/docs into active-recall study aids. **Explicit user invocation only.** |
| 8 | **Google AI Studio** | Gemini prompt & SDK playground | **Added as Skill** | Installed at [`.agents/skills/google-ai-studio/SKILL.md`](../.agents/skills/google-ai-studio/SKILL.md). Scaffolds Python/TS SDK code and schemas. **Explicit user invocation only.** |
| 9 | **Google Pomelli** | SMB brand & social creatives | **Covered by Skill** | Antigravity's pre-installed `brandkit` skill handles brand DNA, visual palettes, and marketing creatives. |
| 10 | **Jules** | Autonomous cloud GitHub agent | **External Cloud Service** | Operates on Google cloud VMs via GitHub App and early preview API/CLI (CI/CD, Slack, Jira). Antigravity is your local interactive counterpart. |
| 11 | **Google Illuminate** | Academic paper audio summaries | **On-Demand Prompt** | No persistent skill installed to prevent hallucinated formats. Handled on-demand via direct conversational prompt when needed. |
| 12 | **Google Opal** | Visual drag-and-drop mini-app builder | **Web Application** | Hosted at [opal.google](https://opal.google). No local IDE extension or MCP server exists. |
| 13 | **Mixboard** | Visual concepting & moodboard canvas | **Shutting Down Sept 28, 2026** | Expiring Google Labs experiment; boards and prompts will become inaccessible after shutdown. |
| 14 | **Disco** | Browser tabs into mini-apps (GenTabs) | **Web App (Gated)** | Google Labs experiment with regional availability gates and waitlists. |
| 15 | **Doppl** | Virtual clothing try-on AI | **Discontinued** | Officially shut down on April 30, 2026. |

---

## 2. Newly Installed Workspace Skills

The following 4 skills have been added directly to your workspace inside `.agents/skills/`.

> [!IMPORTANT]
> **Strict Invocation Guardrail**: None of these skills run proactively or trigger as a side effect of code edits, test runs, or git commits. They execute **only when you explicitly ask for them**.

### A. Code Wiki (`code-wiki`)
- **File**: [`.agents/skills/code-wiki/SKILL.md`](../.agents/skills/code-wiki/SKILL.md)
- **Purpose**: Analyzes real workspace files to generate an interactive, searchable Markdown wiki with system architecture diagrams, directory catalogs, and API indexes in `docs/wiki/`.
- **How to invoke**:
  - *"Generate the code wiki for this repository."*
  - *"Create an architecture diagram and module catalog in docs/wiki."*

### B. Gemini Notebook (`gemini-notebook`)
- **File**: [`.agents/skills/gemini-notebook/SKILL.md`](../.agents/skills/gemini-notebook/SKILL.md)
- **Purpose**: Local source-grounded research assistant that inspects specified documents, notes, or files (such as `Research Papers/` or `ATLAS_PROJECT_CONTEXT.md`), extracting strictly grounded insights with file and line citations.
- **Note on Accuracy**: This is a local Antigravity workflow grounded in your actual workspace files, not the proprietary cloud indexing engine of `notebooklm.google.com`.
- **How to invoke**:
  - *"Using the gemini-notebook skill, synthesize the key findings in Research Papers/."*
  - *"Answer [question] strictly grounded in the documents in docs/."*

### C. Learn Your Way (`learn-your-way`)
- **File**: [`.agents/skills/learn-your-way/SKILL.md`](../.agents/skills/learn-your-way/SKILL.md)
- **Purpose**: Produces active-recall quizzes (with difficulty tiers), technical flashcards, and conceptual breakdowns grounded in the actual codebase.
- **How to invoke**:
  - *"Quiz me on server/atlas/ablation_engine.py."*
  - *"Create flashcards for our predictive maintenance data pipeline."*

### D. Google AI Studio (`google-ai-studio`)
- **File**: [`.agents/skills/google-ai-studio/SKILL.md`](../.agents/skills/google-ai-studio/SKILL.md)
- **Purpose**: Scaffolds production-ready Gemini API code, Pydantic structured output schemas, and system prompt architectures using the official `google-genai` Python SDK or `@google/genai` Node.js SDK.
- **How to invoke**:
  - *"Scaffold a Python script using google-genai to classify sensor telemetry."*
  - *"Prototype a Gemini system instruction and schema for anomaly detection."*

---

## 3. Capabilities Already Native in Antigravity

- **Google Stitch**: You already have access to `StitchMCP` in this environment. Tools include `create_project`, `get_project`, `generate_screen_from_text`, `edit_screens`, and `create_design_system`, paired with the `stitch-design-taste` skill.
- **Whisk (Image Remixing)**: Antigravity's native `generate_image` tool accepts up to 3 image references in `ImagePaths` to blend subject, scene, and style with a natural language prompt.
- **Google Pomelli (Brand Creative)**: Antigravity's pre-installed `brandkit` skill generates complete brand systems, visual guidelines, and marketing creative boards.
- **Cloud Run / Deployments**: Antigravity has the `cloudrun` MCP server configured, allowing direct cloud service deployment and log inspection.

---

## 4. Lifecycle Notes on External Services

1. **Firebase Studio Sunsetting**:
   - Google announced the phase-out of Firebase Studio (the web-based IDE).
   - Workspace creation was turned off on June 22, 2026.
   - Complete service termination occurs on March 22, 2027.
   - Google's migration path points developers to **Google Antigravity** as the primary agentic development environment. Use local Firebase CLI commands and Antigravity's Cloud Run MCP tools for hosting and backend services.

2. **Mixboard Sunsetting**:
   - Google Labs experiment Mixboard is scheduled to go offline on **September 28, 2026**. Avoid relying on it for persistent canvas boards.

3. **Jules (Asynchronous Cloud Agent)**:
   - Jules runs on Google cloud infrastructure connected directly to GitHub repositories to triage issue backlogs and submit PRs. It offers an early-preview API and CLI for integration into CI/CD, Slack, Jira, and GitHub Actions.
   - It does not run as an IDE extension; Antigravity serves as your local, interactive, pair-programming counterpart.

4. **Google Illuminate (Ad-hoc Dialogue Requests)**:
   - Rather than keeping an imitation skill that might simulate product outputs, whenever you want paper analysis in conversational dialogue format, ask directly:
     *"Summarize this research paper as a two-host conversational podcast script."*
