---
name: google-ai-studio
description: >-
  Scaffolding, prompt testing, structured output extraction, and SDK integration recipes for Gemini models
  using Google GenAI SDKs (google-genai Python SDK and @google/genai JS/TS SDK).
  IMPORTANT: Runs ONLY when explicitly requested by the user (e.g. "prototype Gemini prompt", "scaffold Gemini API integration").
  Provides SDK code and prompt scaffolding, not a simulated graphical web playground.
---

# Google AI Studio / Gemini SDK Developer Skill

This skill assists developers in prototyping system instructions, structured output schemas (JSON schema / Pydantic), multi-modal prompts, and production-ready integrations using the official Google GenAI SDKs.

> [!IMPORTANT]
> **Invocation Constraint**: Runs **only on explicit user request**. This skill generates code, prompts, and schema structures for use with your `GEMINI_API_KEY`; it does not attempt to simulate or replace the web-based `aistudio.google.com` interface.

---

## Core Capabilities

### 1. Gemini Python SDK Scaffolding (`google-genai`)
Use the official unified Google GenAI SDK:
```bash
pip install google-genai
```
Standard instantiation and typed structured output pattern:
```python
import os
from google import genai
from google.genai import types
from pydantic import BaseModel

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

class StructuredResponse(BaseModel):
    summary: str
    confidence: float
    tags: list[str]

response = client.models.generate_content(
    model="gemini-2.5-flash",  # or gemini-2.5-pro
    contents="Analyze the anomaly log...",
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=StructuredResponse,
        temperature=0.2,
        system_instruction="You are an industrial telemetry expert analyzing bearing failure logs."
    ),
)
```

### 2. Node.js / TypeScript SDK Scaffolding (`@google/genai`)
```bash
npm install @google/genai
```
```typescript
import { GoogleGenAI, Type } from "@google/genai";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

const response = await ai.models.generateContent({
  model: "gemini-2.5-flash",
  contents: "Classify incoming sensor telemetry",
  config: {
    systemInstruction: "You are a predictive maintenance classifier.",
    responseMimeType: "application/json",
    responseSchema: {
      type: Type.OBJECT,
      properties: {
        severity: { type: Type.STRING, enum: ["INFO", "WARNING", "CRITICAL"] },
        actionRequired: { type: Type.BOOLEAN },
      },
      required: ["severity", "actionRequired"],
    },
  },
});
```

### 3. Function Calling & Tool Definition Recipes
When the user asks to integrate tool calling with Gemini:
- Generate standard tool declaration schemas matching the `types.Tool` specifications.
- Provide clean execution loops that handle tool dispatch, response injection, and follow-up generation.

### 4. System Instruction Refinement & Benchmarking
- Craft role-grounded system prompts with few-shot examples, safety settings, and strict negative constraints.
- Provide evaluation test harnesses to benchmark prompt variations across edge-case inputs.
