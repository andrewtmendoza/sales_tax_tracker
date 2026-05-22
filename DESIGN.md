---
name: Sales Tax Tracker
description: Private self-hosted receipt capture and review for year-to-date sales tax.
colors:
  receipt-green: "#0c885f"
  receipt-green-strong: "#0f766e"
  receipt-green-deep: "#0c5d42"
  receipt-green-soft: "#e6f6ef"
  canvas-gray: "#f3f4f6"
  paper-mist: "#fcfefd"
  mist-panel: "#f8fafc"
  hairline-border: "#dbe2ea"
  ink: "#111827"
  strong-ink: "#0f172a"
  muted-slate: "#64748b"
  success-wash: "#dcfce7"
  success-ink: "#166534"
  warning-wash: "#fef3c7"
  warning-ink: "#92400e"
typography:
  headline:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "1.5rem"
    fontWeight: 800
    lineHeight: 1.2
  title:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "1.125rem"
    fontWeight: 700
    lineHeight: 1.3
  body:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif"
    fontSize: "0.85rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.04em"
rounded:
  md: "0.85rem"
  lg: "1rem"
  xl: "1.25rem"
  panel: "1.5rem"
  shell: "2rem"
  pill: "999px"
spacing:
  xs: "0.25rem"
  sm: "0.75rem"
  md: "1rem"
  lg: "1.25rem"
  xl: "1.5rem"
components:
  button-primary:
    backgroundColor: "{colors.receipt-green-strong}"
    textColor: "{colors.paper-mist}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0.8rem 1.1rem"
  button-secondary:
    backgroundColor: "{colors.paper-mist}"
    textColor: "{colors.strong-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0.35rem 0.75rem"
  nav-pill:
    backgroundColor: "{colors.paper-mist}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0.65rem 0.95rem"
  panel-muted:
    backgroundColor: "{colors.mist-panel}"
    textColor: "{colors.strong-ink}"
    rounded: "{rounded.panel}"
    padding: "1rem"
  badge-status:
    backgroundColor: "{colors.success-wash}"
    textColor: "{colors.success-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0 0.9rem"
---

# Design System: Sales Tax Tracker

## 1. Overview

**Creative North Star: "Pocket Ledger"**

This system is a light, restrained product UI for a self-hosting owner moving between a phone camera and a desktop review screen. It stays calm and brisk: paper-mist and cool gray surfaces, one green-teal accent family, and familiar control shapes that read immediately on first glance. The goal is not to make tax tracking feel premium or dramatic. The goal is to make the chore feel already under control.

The atmosphere is grounded rather than financial. It rejects tax software clutter, heavy accounting dashboards, gamified personal-finance visuals, generic SaaS hero styling, and decorative UI that slows down receipt capture or review. Light theme is the correct fit because this product is most often used in daylight, on a phone over a paper receipt, or at a desk for quick review. Darkness would add mood where the task needs clarity. Core buttons, fields, alerts, badges, cards, and summary panels now live in app-owned classes rather than external component kits, which keeps the system tighter and easier to evolve.

**Key Characteristics:**
- One accent family, used for action and selection only.
- Paper-mist and cool-gray layers that separate capture, review, and status without noise.
- Rounded, touch-friendly controls that feel ready on mobile.
- Familiar product patterns, not invented finance theatrics.
- Feedback first: queue state, sync progress, review state, and save confirmation stay explicit.

## 2. Colors

The palette is restrained and workmanlike: cool paper-mist neutrals, soft slate support tones, and one task-green accent family that signals action, sync, and current selection.

### Primary
- **Receipt Green** (`#0c885f`): The lighter accent note. Use it sparingly for supportive emphasis inside the accent family, not for body text on pale green surfaces.
- **Deep Sync Teal** (`#0f766e`): The primary action anchor. Use it for focus outlines, current states, and the leading color in primary button fills.
- **Ledger Green** (`#0c5d42`): The deepest accent stop. Use it to finish primary gradients so white text stays comfortably above AA contrast.

### Neutral
- **Canvas Gray** (`#f3f4f6`): The application backdrop behind the main surfaces. It keeps the interface light without falling flat.
- **Paper Mist** (`#fcfefd`): The primary reading surface for cards, menus, tables, and forms. It stays nearly white while avoiding the dead flatness of literal white.
- **Mist Panel** (`#f8fafc`): Secondary surface for muted containers, upload panels, preview frames, and hover states.
- **Hairline Border** (`#dbe2ea`): Default boundary color for panels, previews, and menus.
- **Ink** (`#111827`): Standard interface text color for navigation and general UI copy.
- **Strong Ink** (`#0f172a`): Heavier text color for metrics, merchant names, and action labels that need more authority.
- **Muted Slate** (`#64748b`): Secondary copy for helper text, dates, and low-emphasis metadata.
- **Success Wash** (`#dcfce7`) with **Success Ink** (`#166534`): Positive online or saved state.
- **Warning Wash** (`#fef3c7`) with **Warning Ink** (`#92400e`): Review-needed and offline caution state.

### Named Rules
**The One Accent Rule.** Receipt Green is scarce on purpose. If a screen starts reading as green overall, the accent has stopped doing its job.

**The Soft Contrast Rule.** Paper Mist surfaces never sit alone. Pair them with Canvas Gray, Mist Panel, and Hairline Border so the interface stays legible without harsh contrast jumps.

## 3. Typography

**Display Font:** Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
**Body Font:** Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
**Label/Mono Font:** No distinct mono or label family. Labels stay in the primary sans stack.

**Character:** One family carries the whole product. Weight, not font swapping, creates hierarchy. The result feels native, fast, and credible on both phone and desktop.

### Hierarchy
- **Headline** (800, `1.5rem`, `1.2`): Reserved for top-level page titles such as capture, login, and major review headings.
- **Title** (700-800, `1.125rem`, `1.3`): Used for merchant names, card titles, and section-level emphasis inside task surfaces.
- **Body** (400, `1rem`, `1.5`): Default copy and form text. Keep continuous prose within `65-75ch`.
- **Label** (700, `0.78rem-0.85rem`, `1.2`, optional `0.04em` tracking when uppercase): Used for buttons, badges, data labels, and compact table metadata.

### Named Rules
**The One Family Rule.** Do not solve hierarchy with a second font. Use weight, size, and spacing inside the existing sans stack.

**The No Billboard Rule.** Product screens do not need heroic type. If a heading starts behaving like marketing copy, it is already too large.

## 4. Elevation

This system is flat by default. Depth comes from borders, tinted surfaces, spacing, and type hierarchy rather than ambient shadows. The interface should feel printed and orderly, closer to a ledger sheet than a floating app shell.

### Shadow Vocabulary
- **No Ambient Shadow** (`none`): Default for cards, headers, menus, and primary action surfaces.
- **Focus Ring** (`0 0 0 3px rgba(15, 118, 110, 0.18)`): The only persistent shadow-like effect in the system, reserved for keyboard focus clarity.

### Named Rules
**The Flat-By-Default Rule.** If a surface needs a shadow to make sense, its border, spacing, or tonal separation is not doing enough work.

## 5. Components

The component vocabulary is rounded and ready. Controls are easy to hit on a phone, familiar on desktop, and direct about state changes.

### Buttons
- **Shape:** Fully rounded pills for actions (`999px` radius), with smaller rounded rectangles (`0.85rem`) for menu items.
- **Primary:** Solid Deep Sync Teal fill (`#0f766e`), Paper Mist text, strong label weight, and compact horizontal padding (`0.8rem 1.1rem` on capture actions, `0.65rem 0.95rem` in nav pills).
- **Hover / Focus:** Hover shifts to soft green backgrounds or border emphasis. Focus is explicit and uses Deep Sync Teal (`2px` outline using `#0f766e`).
- **Secondary / Ghost:** Secondary review actions stay on Paper Mist with a neutral border. Ghost actions remain transparent with slate text and no decorative color fill.

### Chips
- **Style:** Small lowercase pills with centered text, strong weight, and no outline-first styling.
- **State:** Success and warning chips use tinted backgrounds with dark semantic text. Count chips use a neutral slate fill (`#e2e8f0`) rather than accent color.

### Cards / Containers
- **Corner Style:** Task containers use generous curves from `1.25rem` through `2rem`. Large shells get the widest radius.
- **Background:** Primary work surfaces stay on Paper Mist (`#fcfefd`). Secondary work areas use Mist Panel (`#f8fafc`) for quiet separation.
- **Shadow Strategy:** No ambient lift. Main shells, menus, and summary areas stay flat, relying on borders and surface shifts instead.
- **Border:** Default border is Hairline Border (`#dbe2ea`). Selected states may use soft green tinting and full-surface background change, not colored side stripes.
- **Internal Padding:** Most containers sit on a `1rem`, `1.25rem`, `1.5rem` rhythm.

### Inputs / Fields
- **Style:** Neutral bordered inputs on Paper Mist surfaces with familiar product-UI proportions. Inputs should remain visually quiet beside stronger receipt imagery and action buttons.
- **Focus:** Focus treatment should use accent emphasis, not glow theatrics. Prefer border or outline clarity over shadow effects.
- **Error / Disabled:** Error should use warning-family feedback without changing the field shape. Disabled states should reduce contrast, never hide boundaries.

### Navigation
- **Style:** Sticky Paper Mist header, strong product wordmark, pill navigation links, and a mobile menu that becomes a bordered paper-mist panel.
- **States:** Current page gets a pale green fill with Receipt Green text. Hover stays neutral first, active second.
- **Mobile Treatment:** The mobile menu is a compact lifted panel, not a full-screen takeover.

### Signature Component
- **Capture Camera Tile:** The capture tile is the system's clearest product-specific affordance. It combines a solid green circular icon well, a bordered Mist Panel frame, and an invisible full-area file input. It should always read as the obvious first tap on mobile.

## 6. Do's and Don'ts

### Do:
- **Do** keep the interface light, with Canvas Gray (`#f3f4f6`) behind Paper Mist (`#fcfefd`) and misted working surfaces.
- **Do** use Deep Sync Teal (`#0f766e`) and Ledger Green (`#0c5d42`) for primary action fills and focus emphasis, while reserving Receipt Green (`#0c885f`) for lighter accent support.
- **Do** keep the core product vocabulary in app-owned classes, not external component kits.
- **Do** preserve the rounded, touch-friendly control language: `999px` pills for actions, `1.25rem` to `2rem` radii for primary containers.
- **Do** separate work zones with borders, Paper Mist surfaces, Mist Panel surfaces, and spacing before considering any depth effect.
- **Do** keep copy calm and brief. This is a tool for capture and review, not a finance brand performance.

### Don't:
- **Don't** introduce tax software clutter. Dense finance chrome, over-labeled dashboards, and audit-software theatrics are prohibited.
- **Don't** drift into heavy accounting dashboards. Large data walls, dark analyst palettes, and hard-grid enterprise styling fight the product purpose.
- **Don't** use gamified personal-finance visuals. No reward language, celebratory charts, mascot energy, or streak mechanics.
- **Don't** add generic SaaS hero styling. No marketing gradients, hero-metric templates, or decorative empty-state illustrations that feel imported from a landing page kit.
- **Don't** add decorative UI that slows down receipt capture or review. Motion, glass effects, and ornamental color are forbidden unless they clarify state.
- **Don't** use ambient shadows or hover lift to fake hierarchy. This system stays flat on purpose.
- **Don't** use colored side stripes, gradient text, or default glassmorphism. Those patterns fail this product immediately.
