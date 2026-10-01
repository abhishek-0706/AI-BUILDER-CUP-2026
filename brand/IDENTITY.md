# Brand identity

## Name candidates

| Name | Rationale |
|---|---|
| Nitya | Sanskrit and Hindi *nitya*, "daily, everyday". Two syllables, same pronunciation in both languages, and it states the positioning without claiming a performance benefit. |
| Urja | Hindi *urja*, "energy". Clear functional read, but the word is heavily used in the Indian power and energy sector and it pulls the portfolio toward sports supplements. |
| Harith | Sanskrit *harit*, "green". Good fit for the chilled salad line, underweights protein, and the English spelling is ambiguous (Harit / Harith / Hareet). |

**Canonical name: Protiva.**

Protiva was chosen and is used throughout the product. Nitya, Urja and Harith above are kept as
the candidate set and the reasoning behind them, not as live options. The identity was designed to be
name-agnostic, so adopting Protiva changed only the wordmark string: at the nav rail it is set to
15px/600 with `letter-spacing: -0.005em` rather than 16px, because Protiva is three syllables against
Nitya's two and that keeps it inside a 232px rail without truncation.

Wordmark setting, either name: `--font-ui`, weight 600, `letter-spacing: -0.01em`, sentence case. Not uppercase, not letterspaced wide. The mark is 32px and the wordmark cap height should optically match the leaf width, which lands at 16px type for a two-syllable name.

## Positioning line

Everyday protein, salads and bars for urban Indian households, priced and merchandised to be bought weekly rather than as a supplement.

## Colour system

Hue placement is deliberate. The brand green is pushed toward teal (hue ~172) so that the semantic success green (hue ~138) stays unambiguous next to it in status chips. The accent is beetroot magenta rather than the obvious turmeric amber, because amber is already spent on `warning` and an accent that collides with a semantic colour is unusable in charts and selected states.

| Role | Token | Hex | Contrast claimed |
|---|---|---|---|
| Brand primary | `--brand-primary` | `#0C6B5F` | 6.39:1 on `#FFFFFF`. Passes AA for body text, links and icons; white text on a primary button fill is the same 6.39:1, so filled buttons also pass AA. |
| Primary dark (nav rail) | `--brand-primary-dark` | `#0A3A33` | 12.61:1 with `#FFFFFF`. Passes AA and AAA for the nav rail label text. |
| Primary light tint | `--brand-primary-tint` | `#EAF4F2` | 1.12:1 on white (a surface, not text). Primary on this tint is 5.70:1, neutral-700 on it is 10.85:1. |
| Nav active surface | `--nav-active` | `#125C51` | 7.85:1 with white text. Only 1.61:1 against the rail, so the active item must also carry a 3px left indicator in `--nav-accent`. |
| Nav accent / indicator | `--nav-accent` | `#2ED3B7` | 6.67:1 against the rail. Light-surface focus rings use `--brand-primary` instead; this colour is 1.89:1 on white and must never be used there. |
| Nav muted label | `--nav-muted` | `#9DB8B2` | 5.96:1 against the rail. For section headers and inactive icons. |
| Accent (beetroot) | `--accent` | `#9B1C5C` | 7.74:1 on white, same with white text on a fill. |
| Success | `--success` | `#157F3C` | 5.08:1 on white. |
| Warning | `--warning` | `#8F5200` | 6.22:1 on white. Chips use this as text on `#FDF3E2`, never as a fill with white text. |
| Danger | `--danger` | `#B3261E` | 6.54:1 on white. |
| Info | `--info` | `#0F56A8` | 7.20:1 on white. |
| Neutral 50 | `--n-50` | `#F8FAF9` | Page background behind cards. |
| Neutral 100 | `--n-100` | `#EDF1F0` | Table header fill, hover rows, disabled fills. |
| Neutral 200 | `--n-200` | `#DCE3E1` | Borders, dividers, card outlines. |
| Neutral 300 | `--n-300` | `#A8B3B0` | Placeholder text, disabled text and icons on light. 2.16:1, non-text use only. |
| Neutral 400 | `--n-400` | `#5E6B68` | Secondary text. 5.56:1 on white, 4.88:1 on `--n-100`, both AA. |
| Neutral 500 | `--n-500` | `#2C3836` | Primary body text. 12.17:1 on white. |
| Neutral 600 | `--n-600` | `#101715` | Page titles and numeric emphasis. 18.18:1 on white. |

Ratios are computed with the WCAG 2.1 relative luminance formula. Card surfaces are `#FFFFFF` on an `--n-50` page, so every "on white" figure above is the real worst case for content text. The one place that is not white is the nav rail, which is a flat `--brand-primary-dark` with no gradient, so its figures hold across the whole rail height.

Paste form:

```css
:root {
  --brand-primary: #0C6B5F;
  --brand-primary-dark: #0A3A33;
  --brand-primary-tint: #EAF4F2;
  --nav-active: #125C51;
  --nav-accent: #2ED3B7;
  --nav-muted: #9DB8B2;
  --accent: #9B1C5C;
  --success: #157F3C;
  --warning: #8F5200;
  --danger: #B3261E;
  --info: #0F56A8;
  --n-50: #F8FAF9;
  --n-100: #EDF1F0;
  --n-200: #DCE3E1;
  --n-300: #A8B3B0;
  --n-400: #5E6B68;
  --n-500: #2C3836;
  --n-600: #101715;
}
```

## Typography

One family for the whole interface. Inter is a Google Font, has a true tabular figure set, and falls back to Segoe UI Variable Text on Windows at near-identical metrics, so an offline demo does not reflow.

```css
--font-ui: "Inter", "Segoe UI Variable Text", "Segoe UI", system-ui, -apple-system,
           "Noto Sans Devanagari", Arial, sans-serif;
```

`Noto Sans Devanagari` sits in the stack because product names and store names in this portfolio will sometimes carry Devanagari; Inter does not cover that script and without the fallback those strings render as boxes.

| Element | Size / line-height | Weight | Notes |
|---|---|---|---|
| Nav item | 14px / 20px | 500 | `letter-spacing: 0.005em`. Same size active and inactive, state is carried by colour and the left indicator, so labels do not shift. |
| Page title | 24px / 32px | 600 | `letter-spacing: -0.01em`. Single line, truncate rather than wrap. |
| Card title | 16px / 24px | 600 | |
| Body | 14px / 20px | 400 | Dense default for a tool read on a phone in a store aisle. |
| Small label | 12px / 16px | 500 | `letter-spacing: 0.04em`, `text-transform: uppercase` for table column heads and metric captions only. |
| Data / numeric | 14px / 20px | 500 | `font-variant-numeric: tabular-nums`. |
| KPI numeral | 28px / 34px | 600 | `font-variant-numeric: tabular-nums`, `letter-spacing: -0.02em`. |

Tabular numerals are required, not optional, on every data table cell, KPI tile, currency figure and percentage. Proportional figures make right-aligned columns of rupee values visibly ragged and make a number flicker in width when it updates. Apply at the container:

```css
.data-table, .kpi { font-variant-numeric: tabular-nums; }
```

Keep `font-feature-settings` out of it; `font-variant-numeric` is the supported property and does not disable other features.

## Logo rationale

The mark is an open ring around a geometric leaf, with the leaf tip pointing out through the gap in the ring. The ring is the weekly replenishment loop the field rep actually manages, order, shelf, sell-through, reorder, and it is left open because the job is never closed. The leaf is a lens built from two arcs of a single radius, which keeps the silhouette food-adjacent without becoming a literal salad illustration, and the diagonal axis gives the mark direction so it does not read as a static badge.

## Usage notes

**Construction.** 24px square viewBox, drawn on that grid so it is pixel-honest at its smallest intended size. Ring stroke is 2.2 units with round caps, leaf width is 5 units, and the clearance between leaf and ring is 2 units. Both paths use `currentColor`, so the mark inherits text colour and needs no variant files.

**Minimum size.** 20px on screen, 8mm in print. Below 20px the ring-to-leaf clearance closes up; at those sizes hide `#loop` and use the leaf alone.

**In the 32px nav rail square.** Container is 32x32 with an 8px corner radius, filled `--brand-primary`. The mark sits at 20x20, centred, giving 6px padding on all sides. Set `color: #FFFFFF` on the container so both paths pick it up. Do not scale the mark past 22px inside the square; the ring caps start touching the rounded corners. On a light header, invert: white container with a `--n-200` 1px border and the mark in `--brand-primary`.

**Do not.** Do not add a gradient, shadow, outer glow or bevel. Do not place the mark on a photograph or any busy fill. Do not recolour the leaf and ring into two unrelated hues; if a two-tone treatment is needed, set the ring to `--brand-primary` and the leaf to `--accent` and nothing else. Do not rotate, stretch, or change the ring gap angle. Do not add the wordmark inside the SVG, it is HTML type and must stay selectable and translatable. Do not use the mark as a bullet, loading spinner, or success tick.

**Clear space.** One quarter of the mark's width on all four sides, measured from the ring, not from the viewBox edge.
