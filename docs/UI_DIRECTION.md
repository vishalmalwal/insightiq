# UI direction — "Midnight analytics" (for Phase 4)

Locked visual direction. Reads as premium BI SaaS, not a generic AI template.
Deliberately avoids the three overused AI looks (cream + serif + terracotta;
near-black + acid-green; broadsheet with hairline rules).

**Dark-first, but ship both dark and light modes.**

## Palette
- Canvas: deep slate `#0B0F1A`
- Cards: elevated glass — `rgba(255,255,255,0.04)` + a subtle border
- Signature accent: aurora/mesh gradient **violet `#7C3AED` → cyan `#06B6D4` →
  fuchsia `#D946EF`**. Used **only** on the hero, the Ask-bar focus state, and
  KPI accents. Not everywhere — that restraint is the point.

## Type
- Display: a characterful face (Clash Display or General Sans)
- Body/UI: Inter
- Data/SQL: JetBrains Mono
- Clear, deliberate type scale.

## Motion (the modern layer — used sparingly)
- Framer Motion: scroll-triggered reveals + staggered card entrances
- Lenis: smooth scrolling
- Native CSS scroll-driven animation (`animation-timeline: scroll()`) for the
  hero gradient drift
- Hover micro-interactions on cards
- **Respect `prefers-reduced-motion` everywhere.**

## Signature moment (spend boldness here, keep the rest quiet)
The hero **is** the product: an Ask bar that visibly resolves a typed question
into a multi-chart dashboard grid that animates into place (staggered), so the
value lands in ~3 seconds.

## Components
- shadcn/ui on the existing Tailwind + React stack
- ECharts for dashboards (already chosen)
- react-grid-layout for the grid

## The one restraint rule
Let the aurora gradient + the resolving-dashboard hero be the single memorable
thing; keep everything else disciplined. Over-animating is exactly what makes a
UI read as AI-generated.
