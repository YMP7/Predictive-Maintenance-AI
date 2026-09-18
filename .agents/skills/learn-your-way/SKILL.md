---
name: learn-your-way
description: >-
  Generates adaptive, active-recall study sessions, concept-check quizzes, and flashcards
  grounded in your actual repository code, notes, and technical documentation.
  IMPORTANT: Runs ONLY when explicitly requested by the user (e.g. "quiz me on this module", "generate flashcards for this paper").
  NEVER generates quizzes or study material proactively after edits or background tasks.
---

# Learn Your Way (Adaptive Codebase & Technical Study)

This skill transforms complex technical code, architectural specifications, or research notes into structured active-recall learning materials to accelerate developer onboarding and technical mastery.

> [!IMPORTANT]
> **Invocation Constraint**: Generates quizzes, flashcards, or study sessions **only when explicitly commanded by the user**. Never produce study materials proactively during or after code edits.

---

## Supported Modes (Triggered on Demand)

### 1. Concept-Check Quiz (`Quiz`)
When asked to quiz the user on a codebase area, module, or document:
- Formulate 3-5 high-yield multiple-choice or scenario-based questions based strictly on the selected files.
- Cover real edge cases, architecture decisions, and concurrency or error handling patterns present in the code.
- Include progressive difficulty (Level 1: Fundamentals, Level 2: Architecture & Flow, Level 3: Failure Modes & Edge Cases).
- Provide a hidden or spoiler-tagged explanation key with precise file references so the user can verify their answers.

### 2. Technical Flashcards (`Flashcards`)
When asked to create flashcards:
- Structure cards in question/answer format or front/back format.
- Focus on:
  - **Function & Interface contracts**: "What does `ablation_engine.py` expect as input parameters?"
  - **State transitions & Lifecycles**: "What triggers a model rollback in the training pipeline?"
  - **Key constants & thresholds**: "What is the EMA smoothing factor configured in the baseline test?"

### 3. "Explain Like I'm an Engineer" (`ELIE`)
When asked to explain a difficult algorithm or module:
- Break down the target component using a 3-tier mental model:
  1. **The Core Intuition**: What problem does this solve in plain English?
  2. **The Mechanism**: Line-by-line or function-by-function trace of how it achieves the solution.
  3. **The Gotchas**: Assumptions, performance pitfalls, and race conditions to watch out for.
