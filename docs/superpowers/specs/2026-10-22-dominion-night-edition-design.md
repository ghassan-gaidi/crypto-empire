# Dominion · Night Edition — Full Redesign Spec

- **Date:** 2026-10-22
- **Repo:** `ghassan-gaidi/crypto-empire` (clone at `/home/leo/Desktop/main projects/crypto-empire`)
- **Branch:** `redesign/night-edition`
- **Status:** approved design (user), this document is the written spec of record

---

## 1 · Goal & audience

**Goal:** a full redesign of the Dominion crypto-intelligence system — web dashboard, embeddable
widgets, logo/favicon, and Telegram bot message style — presented as a **portfolio / job-hunt
showcase piece**. Every visual decision must be distinctive and *defensible*: the design system,
not just the pages, is the artifact being shown.

**Success criteria:**

- One coherent identity across all ~20 pages, both embed widgets, and the Telegram bot
- The old "four design eras" (brutalist crimson, terminal cyan, periwinkle accent, neon widget)
  are fully replaced by a single token core; no leftover palettes or fonts
- Zero functional changes: every route, endpoint, DB write, auth gate, and JS element ID preserved
- The rendered site survives scrutiny at both detail level (type, texture) and system level
  (component reuse, one design-system file)

**Out of scope:** light theme ("morning edition" — a future token flip, deliberately not built:
YAGNI), any backend/data behavior change, new features, template restructuring beyond
`design.py` extraction (Approach 2; full Blueprint refactor rejected).

---

## 2 · Identity: Meridian Press · Night Edition

A **dark broadsheet**: the grammar of a financial newspaper reproduced as a night print —
warm ink-black paper, cream print ink, muted halftone grain. Not a dashboard cliché, not a
crypto-gradient: the interface *is* a newspaper ("Front Page", "The Tape", "The Wire",
"The Ledger", "Page A1 / p. /launches" cross-reference metaphors).

### 2.1 Token core (single source of truth)

```css
:root{
  --paper:#17130d;            /* warm black, brown cast — the "paper" */
  --ink:#e9dfc6;              /* cream print */
  --ink-bright:#f2ead4;       /* display-size type */
  --ink-dim:#968b70;          /* kickers, folio lines, footnotes */
  --rule:rgba(233,223,198,.22);
  --rule-strong:rgba(233,223,198,.55);
  --oxblood:#d4635a;          /* the single accent: falls, alerts, wire emphasis */
  --print-green:#8fcea5;      /* rises */
  --paper-dot:rgba(233,223,198,.12);
}
```

### 2.2 Typography

Two fonts only:

| Role | Font |
|------|------|
| Display, headlines, italic decks, instrument names | **Fraunces** (Google Fonts, 300–900 variable) |
| Figures, labels, kickers, folios, telegram-style text | **IBM Plex Mono** (400/500/600) |

- Headlines: Fraunces 560, tight leading (1.18), sentence case, `'`-quoted terms allowed
- Kickers: Plex Mono 9–10px, letter-spacing .28em, uppercase, `--ink-dim`
- Tables: Plex Mono, tabular figures; instrument names in italic Fraunces 12px

### 2.3 Structural devices (replaces all cards)

| Device | Replaces | Definition |
|--------|----------|------------|
| **Masthead** | logo bar / hero | "DOMINION" in Fraunces 640, uppercase, tracked; kicker between hairline flanks; double rule above edition bar |
| **Index strip** | sticky header | full-width mono tape of live prices separated by rules; acts as the site header |
| **Dotted-leader ledger** | stat cards | `label ······· value` rows with dotted or hairline leaders |
| **Column rules** | panels/gaps | 1px dotted vertical rules between content columns |
| **The Tape** | data tables | hairline row rules, italic serif instruments, right-aligned mono figures, ▲ `--print-green` / ▼ `--oxblood` |
| **The Wire** | activity feeds | timestamped mono entries with hairline separators |
| **Ad box** | premium/CTA slots | double-rule frame, centered composition, CTA = solid cream button with 20% tracked mono caps |
| **Folio** | footer | "Page A1 · ❦ · Dominion · On-Chain Intelligence" |

**Hard rules:** no `border-radius`, no `box-shadow`, no gradients, no card backgrounds.
Decoration lives in rules, leaders, whitespace, and the halftone. Elevation does not exist.

### 2.4 Halftone texture (the layer that makes it "print")

Canonical implementation (css-irl.info / Michelle Barker style): **no blend modes, no
transforms** — two hard-stop radial-gradient dot layers with a half-cell offset simulate the
angled print screen; ink alpha is baked into the gradient color (plain alpha compositing —
verified rendering in headless Chromium after two earlier implementations failed on
HiDPI/GPU rasterization):

```css
.ht{position:absolute;inset:0;z-index:1;pointer-events:none;
  --cell:5.5px; --dr:1.1px; --ink:233,223,198; --da:.12;        /* MUTED locked */
  background-image:
    radial-gradient(circle at center,rgba(var(--ink),var(--da)) var(--dr),transparent 0),
    radial-gradient(circle at center,rgba(var(--ink),calc(var(--da)*.75)) var(--dr),transparent 0);
  background-size:var(--cell) var(--cell);
  background-position:0 0,calc(var(--cell)/2) calc(var(--cell)/2);
  background-repeat:round;}
```

- Polarity A (site pages & embeds): cream dots on ink-black paper (above). The dark embed
  strips match the site exactly.
- Polarity B (reverse, deferred): ink dots on cream — only a future "morning edition" needs
  it; the builder supports the polarity flip today, the theme is not shipped (see §1).
- Vignette + faint corner stains ride on the same overlay (separate radial-gradients,
  plain alpha): edges press to true black, corners gain aged warmth. Independent dials.

### 2.5 Navigation & motion

- Header = index strip + kickers; no hamburger; all section pages reachable from kickers
- Motion budget: none essential. Hover states are rule-weight changes and oxblood
  application; no keyframes in v1 unless an interaction obviously needs it
- Responsive: 3-column grids collapse to single column < 900px; masthead scales down;
  index strip scrolls horizontally on mobile

---

## 3 · Architecture change

**One new module: `design.py`** (Approach 2 — design-system module; full template extraction
rejected). It becomes the showable "design system file":

```python
# design.py (sketch)
NIGHT_CSS: str            # token core + halftone + device CSS above
def halftone_sheet(): ... # overlay div builder (polarity, dials as kwargs)
def page_shell(title, body, *, kicker=...) -> str   # <!DOCTYPE>…masthead…folio
def index_strip(items): ...
def ledger(rows): ...     # rows = [(label, value, tone)]
def tape_table(rows): ...
def wire(entries): ...
def ad_box(title, sub, cta, *, href): ...
def kicker(text) / headline(text) / deck(text) ...
TG = {...}                # plain-text print-style scaffolds for Telegram bots
                          # (masthead bars, rules, leaders, ❦, ▲▼)
```

- `app.py`: `SHARED_HEAD` and its three rival `:root` palettes are deleted; routes import
  from `design.py`; each page keeps only its unique markup/CSS. HTML stays in `app.py`
  (no Flask structural change; Vercel entry `api/index.py` untouched).
- `telegram_bot.py` (webhook bot, primary) + key commands in `bot.py` (polling daemon) adopt
  `TG` print-style message formatting: mono-styled bars via Unicode rules/leaders/bullets.
- `logo.svg` + favicon: DOMINION masthead wordmark (Fraunces subset embedded or hand-tuned
  outlines; decided at implementation — whichever keeps the file self-contained).
- Public symbols stay stable: CSS class names are the only allowed addition; existing JS
  event hooks, element IDs, and form field names must not change.

---

## 4 · Rollout order (flagship first)

| # | Page(s) | “Section” metaphor | Notes |
|---|---------|--------------------|-------|
| 1 | `/` dashboard | Front Page | proves every device; real live data |
| 2 | `/whales` `/trending` `/yields` `/launches` | Sections | ledger/tape/wire reuse |
| 3 | `/portfolio` (+`/portfolio/<pid>`) `/profiler` `/wallet-check` | Folio | forms → ledger entries |
| 4 | `/premium` `/advertise` `/api-keys` | Compositions | ad-box patterns |
| 5 | `/docs` `/blog` (+ post) | Index + Feuilleton | long-form typography |
| 6 | `/admin` (+`/admin/stats`) | Back office | same core, denser |
| 7 | `/ticker` `/widget` (+`embed.js`) | Strips | reverse polarity |
| 8 | `logo.svg`, favicon | Masthead mark | self-contained SVG |
| 9 | `telegram_bot.py`, `bot.py` | Telegram | print-style messages |
| 10 | README, badges, screenshots | Press kit | final |

**Commit hygiene:** one commit per page/step on `redesign/night-edition`; each page's diff
stays reviewable; old/new comparison tickets possible at any point.

---

## 5 · Verification plan

1. **Per page:** render locally (Flask dev run, later gunicorn), screenshot in my own
   headless browser at desktop and ~820px widths; fix visual regressions before the next page.
2. **Escape audit:** all f-string/template content audited for attribute escaping and
   `Markup` safety (known risk: mechanical rewrites around user-injected values such as
   addresses, portfolio IDs, blog slugs).
3. **Smoke tests after rollout:** `curl` every route (status 200/expected), verify JSON API
   payloads unchanged, run existing GH Actions secret-scan.
4. **Bot check:** send rendered commands to a scratch Telegram chat (manual) to confirm
   monospace block rendering; polling bot parity on `/price` `/gas` `/whales`.
5. **Acceptance:** the four-era leftovers are gone (`grep` for old palettes/fonts returns
   nothing except intentional history); README updated; screenshots attached.

## 6 · Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| Escaping/quote breaks in 20 inline templates | per-page small diffs + browser screenshot audit per page |
| JS ↔ CSS coupling breaks interactivity | element IDs and semantic names frozen; CSS-only additions |
| Live-data edge states (empty tables, API failure) | style empty/error states explicitly (“the wire is silent”, “the tape is dark” treatments) |
| Halftone over text harming readability (perceived) | overlay is below content (z-ink < content) & 12% alpha; verified legibility in screenshots |
| Scope creep into backend refactor | spec §1 excludes it; new tasks re-classified before starting |

## 7 · Deliberately rejected alternatives

- **In-place CSS patching again** (4th era) — repeats the exact failure this redesign fixes
- **Full template/Blueprint extraction** — high regression risk on a live Vercel app,
  cost not justified by the visual goal
- **Light "morning edition" theme** — future token flip, not now (YAGNI)
- **Additional fonts (3rd face)** — two-font system is the defensible decision
