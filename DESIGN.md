---
name: AI Digital Twin & Predictive Maintenance
description: Enterprise Industry 4.0 Predictive Edge Analytics Gateway design system
colors:
  primary: "#ededec"
  neutral-bg: "#121213"
  neutral-surface: "#161617"
  accent: "#787774"
  text-primary: "#ededec"
  text-secondary: "#b3b3b1"
  text-muted: "#787774"
  status-normal: "#10b981"
  status-warning: "#f59e0b"
  status-critical: "#ef4444"
typography:
  display:
    fontFamily: "Space Grotesk, sans-serif"
    fontSize: "clamp(2rem, 5vw, 3.5rem)"
    fontWeight: 800
    lineHeight: 1.1
    letterSpacing: "-0.04em"
  body:
    fontFamily: "Plus Jakarta Sans, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Space Grotesk, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    letterSpacing: "0.18em"
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
spacing:
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.text-primary}"
    textColor: "{colors.neutral-bg}"
    rounded: "{rounded.sm}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.text-secondary}"
  card-outer:
    backgroundColor: "{colors.neutral-surface}"
    border: "1px solid {colors.border-color}"
    rounded: "{rounded.lg}"
    padding: "0"
  card-inner:
    backgroundColor: "transparent"
    border: "none"
    rounded: "0"
    padding: "20px"
---

# Design System: AI Digital Twin & Predictive Maintenance

## 1. Overview

**Creative North Star: "The Technical Ledger"**

This system represents a high-density, high-trust industrial analytics dashboard designed on premium editorial minimalism principles. It balances raw engineering utility with typographic restraint. It explicitly rejects SaaS gradient trendiness, heavy drop shadows, and visual clutter in favor of a warm monochrome, document-style workspace layout that is flat, sharp, and highly functional.

### Key Characteristics:
- **Warm Obsidian Canvas:** Dark mode features a warm charcoal backdrop that reduces operator eye strain over long shifts.
- **Utilitarian Minimalism:** Double-bezel loops collapse into crisp single flat-border containers.
- **Spot Pastels for Status:** Preserves load-bearing green, yellow, and red status colors in low-opacity, high-signal pastel/color-mix blends.

## 2. Colors

A highly restrained, warm monochrome palette utilizing color exclusively for operator decision status indicators.

### Primary
- **Restrained Off-White** (#ededec / `oklch(0.94 0.002 60)`): The primary textual and key interface highlight color.

### Neutral
- **Warm Charcoal Base** (#121213 / `oklch(0.14 0.005 60)`): The dark room canvas.
- **Slate Panel Surface** (#161617 / `oklch(0.17 0.006 60)`): Cards and sidebar backgrounds.
- **Warm Slate Border** (#2d2d2f / `oklch(0.24 0.006 60)`): Crisp container divisions.
- **Subtext Gray** (#b3b3b1 / `oklch(0.72 0.004 60)`): Secondary descriptions.

### Semantic (Load-Bearing Statuses)
- **Normal Green** (#10b981 / `oklch(0.72 0.18 145)`): Preserved exactly for healthy metrics.
- **Warning Amber** (#f59e0b / `oklch(0.78 0.19 75)`): Preserved exactly for alert boundaries.
- **Critical Crimson** (#ef4444 / `oklch(0.62 0.22 25)`): Preserved exactly for critical malfunctions.

> [!IMPORTANT]
> **Rationale for Preserving Status Colors:**
> In safety-critical factory-floor environments, operators rely on immediate, pre-attentive sensory processing to distinguish operational states (e.g. diagnosing bearing anomalies vs total machine lock). These status colors are functional indicators, not branding elements. Altering their hues to fit a redesigned color scheme would increase cognitive load, create visual confusion with legacy machinery, and introduce unnecessary operational risk.

**The Functional Color Rule.** Color is a scarce asset. Non-status interface elements must remain strictly monochromatic, reserving colored highlights purely for telemetry indicators.

## 3. Typography

**Display Font:** Space Grotesk (with sans-serif fallback)
**Body Font:** Plus Jakarta Sans (with sans-serif fallback)

### Hierarchy
- **Display** (800, `clamp(2rem, 5vw, 3.5rem)`, 1.1): Used for main dashboard and hero titles. Letter spacing is clamped to `-0.04em`.
- **Headline** (700, 20px, 1.2): Section titles.
- **Body** (400, 14px, 1.6): Diagnostic text and descriptions. Max line-length is constrained to 65-75ch.
- **Label** (600, 11px, tracking 0.18em, uppercase): Eyebrows and metadata kickers.

## 4. Elevation

Surfaces do not use soft ambient drop shadows to suggest depth, as shadows are invisible in dark environments. Instead, depth is conveyed through **tonal nesting** and **inner hairlines**.

### Elevation Rules
**The Flat-By-Default Rule.** Cards and panels sit flush on the background at rest. Concentric outer borders define boundaries. Translating translations (`translateY(-2px)`) are used on hover to suggest proximity response.

## 5. Components

### Buttons
- **Shape:** Rectangular with small corner radius (`var(--radius-sm)`).
- **Primary:** cyber teal background with high contrast white text.
- **Hover/Active:** scale-down transition (`scale(0.97)`) on press.

### Cards / Containers
- **Nested Bezel Structure:** Outer container (`.bezel-outer`) with 6px padding and `var(--radius-lg)` radius. Inner container (`.bezel-inner`) with `calc(var(--radius-lg) - 6px)` radius.
- **Background:** `#08080c` for core surfaces.
- **Border:** 1px hairline border (`rgba(255, 255, 255, 0.05)`).

### Inputs / Fields
- **Style:** Flat 1px outline, resting background `rgba(255, 255, 255, 0.02)`.
- **Focus:** 1px cyan highlight on active select or input.

## 6. Do's and Don'ts

### Do:
- **Do** wrap every major panel or card in the concentric double-bezel wrapper to maintain shape uniformity.
- **Do** use `oklch()` for custom stylesheet values to ensure uniform brightness scaling.
- **Do** respect the prefers-reduced-motion media query by swapping 3D spin coordinates to static states.

### Don't:
- **Don't** use colored accent stripes on only one side of a card (e.g. `border-left: 4px`).
- **Don't** apply diagonal background stripes or raw grid overlay meshes.
- **Don't** use linear gradients for heading text.
