# Dominion · Night Edition — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Replace all four design eras in the Dominion Flask app with the approved "Meridian
Press · Night Edition" identity (dark broadsheet + muted cream halftone), across all pages,
both embed widgets, logo, README — with zero functional changes.

**Architecture:** One new module `design.py` holds the entire design system (token core CSS,
halftone overlay builder, newspaper component builders, Telegram print-style scaffolds).
`app.py` pages consume it via `page_shell()`; HTML constants in `app.py` are rewritten
page-by-page, keeping every route, variable, element ID, form field name, and JS hook intact.

**Tech Stack:** Python 3.11, Flask 3 (Jinja `render_template_string`), pytest (dev only),
headless-Chromium screenshot audits (opencode browser tools), git branch
`redesign/night-edition`.

**Spec:** `docs/superpowers/specs/2026-10-22-dominion-night-edition-design.md` (read with
this plan; token values, halftone recipe and hard rules live there verbatim).

## Global Constraints

- Zero functional changes: routes, endpoints, DB, auth, JS element IDs, form field names, URL
  query contracts unchanged. CSS class additions only.
- Design system lives ONLY in `design.py`; no new `:root` tokens inside `app.py`.
- Exact tokens (spec §2.1): `--paper:#17130d --ink:#e9dfc6 --ink-bright:#f2ead4
  --ink-dim:#968b70 --rule:rgba(233,223,198,.22) --rule-strong:rgba(233,223,198,.55)
  --oxblood:#d4635a --print-green:#8fcea5`
- Fonts only Fraunces + IBM Plex Mono (Google Fonts import in `NIGHT_CSS`).
- No `border-radius`, no `box-shadow`, no gradients (except the halftone radial-gradient
  layers + vignette/stains), no card backgrounds on paper pages.
- Halftone = MUTED polarity A only (spec §2.4): two hard-stop radial layers, half-cell
  offset, `background-repeat:round`, ink alpha baked in, `pointer-events:none`, below content.
- Local run needs env `FLASK_SECRET=x ADMIN_SECRET=y DATA_DIR=/tmp`; every page task verifies
  via `curl` status `200` + browser screenshot before its commit.
- One commit per task on `redesign/night-edition`.

## Review Focus

1. **Escaping of user/live values** (wallet addresses, portfolio IDs, blog slugs, news HTML,
   coin names): all `design.py` builders must `html.escape` text; API JSON output unchanged.
   Pinned by unit test in Task 1; per-page audit pinned where those pages render
   (Tasks 3–5, smoke test Task 10).
2. **JS ↔ DOM coupling:** pages ship JS that selects element IDs from the same string
   constants. Pinned by `grep -c "getElementById"` before/after equality step in each page
   task (IDs frozen), plus habitat "page renders and old JS still runs" screenshot check.
3. **Halftone stacking/legibility:** overlay must sit below content (`z-index`), not
   intercept events. Pinned by CSS content assertion (Task 1) + visual audit (every page
   task's screenshot step).
4. **Empty / failed live data** (Coingecko rate-limit, empty whale wire): pages must render
   styled empty states ("the tape is dark") rather than blank/HTML soup. Pinned by
   component tests (Task 1) and by Task 10's smoke run with a blocked network flag.
5. **Mobile collapse <900px:** grids collapse to single column, index strip scrolls.
   Pinned by ~820px screenshot in the Bluetooth-flagship page task (Task 2) and final sweep.

---

### Task 1: `design.py` — the design system module

**Files:**
- Create: `design.py`
- Create: `tests/test_design.py`
- Create: `requirements-dev.txt` (content: `pytest`)
- Modify: `.gitignore` (if it lacks `.superpowers/`)

**Interfaces (produced for all later tasks):**
```python
NIGHT_CSS: str                    # full token core + fonts import + halftone + device CSS
def page_shell(title, body, *, kicker="", page="A1", edition="Night Edition", extra_css="", strip_items=None) -> str
def index_strip(items) -> str     # items = [(label, value, tone)] tone in {"up","down","dim"}
def ledger(rows) -> str           # rows = [(label, value, tone|None)]
def tape_table(rows) -> str       # rows = [(name, last, chg, tone)]
def wire(entries) -> str          # entries = [(time, text)]
def ad_box(title, sub, cta: tuple[str, str], note="ADVERTISEMENT") -> str   # cta=(label,href)
def kicker(text) / headline(text) / deck(text) / folio(page) -> str
HALFTONE_DIV: str                 # <div class="ht"> overlay markup
TG: dict[str, str]                # print-style plaintext scaffolds for Telegram
```

- [x] **Step 1: Write failing tests** `tests/test_design.py`:
  `test_tokens_present` (NIGHT_CSS contains exact token strings above + both Google font
  names + `radial-gradient(circle at center` + `background-repeat:round` +
  `pointer-events:none`), `test_no_legacy_fonts` (not in NIGHT_CSS: `JetBrains Mono`,
  `Space Grotesk`, `DM Sans`), `test_no_blend_or_rotate` (no `mix-blend-mode` and no
  `transform:` near halftone layer class .ht), `test_halftone_values` (contains
  `--cell:5.5px`, `--dr:1.1px`, `--da:.12`), `test_ledger_escapes` (`ledger([("<b>", "x",
  None)])` output contains `&lt;b&gt;` and `····`, no raw `<b>`), `test_ledger_empty`
  (`ledger([])` contains "the tape is dark"), `test_tape_table` (`▲` green span and `▼`
  oxblood span for tone up/down), `test_page_shell` (contains `<!DOCTYPE`, `-paper:#17130d`,
  masthead class, folio class). **Run:** `pytest tests/ -q` → expected FAIL (module missing).
- [x] **Step 2: Implement `design.py`** with the CSS from the spec §2.1–2.4 verbatim
  (halftone values: cell 5.5px, dot 1.1px, `--ink:233,223,198`, `--da:.12`; vignette +
  corner stains on the overlay; body uses `--paper`) and the component functions above;
  escaping via `html.escape` on label/value/name/text args; page template =
  masthead + index_strip placeholder slot (script fills via data attr or server-side items
  arg) — decide: `page_shell` takes optional `strip_items` parameter (default None).
- [x] **Step 3: Run tests** `pytest tests/ -q` → PASS.
- [x] **Step 4: Commit**

### Task 2: Flagship — Dashboard `/` becomes the Front Page

**Files:**
- Modify: `app.py` — `INDEX_HTML` constant and `index()` (lines ~1624–1700 + HTML constant)
- Test: browser screenshot + curl (no unit test; interface JSON untouched)

**Interfaces:** consumes `page_shell, index_strip, ledger, tape_table, wire, kicker/
headline/deck, ad_box, folio, NIGHT_CSS, HALFTONE_DIV`; `index()` context vars
(`top_coins`, `market_data`, `fear_greed`, `news`, `wallet`) unchanged; JS element IDs in
INDEX_HTML: freeze list discovered in Step 1 via `grep -o 'id="[^"]+"' app.py`.

- [x] **Step 1: Record frozen IDs** — `grep -o "getElementById([^)]*)" app.py` before edit → saved to `/tmp/frozen_ids.txt`; unchanged after edit (Step 5 re-grep and diff).
- [x] **Step 2: Rewrite `INDEX_HTML`** as `page_shell` wrapper + composition: index strip
  (live majors from row 1 `top_coins`), lead story block with `headline`/`deck`
  (fear_greed + gas strings server-computed as before), dotted `ledger` (F&G, dominance
  computed, gas from `/api/gas` data already fetched — reuse existing fetches), `tape_table`
  from `market_data` (first 10), `wire` from whale cache (existing `/api/whales` fetch path
  in template context as today), footer ad_box + wallet donation folio text. Layout: three
  columns (`grid-template-columns:2.2fr 1.15fr 1.15fr`), collapse <900px.
- [x] **Step 3: Run app + curl + screenshots** — `FLASK_SECRET=x ADMIN_SECRET=y DATA_DIR=/tmp
  python -m flask run` (or gunicorn); `curl -s -o /dev/null -w "%{http_code}" localhost:5000/`
  → 200 and body contains `--paper:#17130d`; browser screenshots at 1400px and ~820px →
  visually audit (halftone visible, no overlaps, strip scrolls on mobile).
- [x] **Step 4: Frozen-ID diff** — re-grep IDs, diff with `/tmp/frozen_ids.txt` → identical.
- [x] **Step 5: Commit**

### Task 3: Sections

- [`/whales` `WHALE_HTML` → "The Wire" full page,
  `/trending` `TRENDING_HTML`, `/yields` `YIELDS_HTML`, `/launches` `LAUNCHES_HTML` →
  calendar as "Diary of Issuances", countdown keeps its JS IDs]. 4 pages, 1 commit.

### Task 4: Folio

[`PORTFOLIO_HTML` (create flow + `/portfolio/<pid>` share view),
`PROFILER_HTML`, `WALLET_CHECK_HTML`]; forms keep seriffed inputs styled as ledger rows;
addresses render mono.

### Task 5: Monetization

[`/premium` (inline HTML in `app.py` premium route), 
`ADVERTISE_HTML`, `/api-keys`]; premium composition centered ad_box + benefits ledger.

### Task 6: Long-form

[`/docs` ("The Index": endpoint list as tape table), `/blog` +
post pages as feuilleton (Fraunces 17px/1.65 prose column, `.ser` figures)].

### Task 7: Admin dashboard

**Files:** Modify `ADMIN_DASHBOARD_HTML` (+ its style block ~2125): denser variant — same
tokens, smaller type scale (11px base), table-heavy; admin auth headers unchanged.

### Task 8: Embed strips

**Files:** Modify `WIDGET_CSS` (~4967), `/widget`, `/ticker`, `/widget/embed.js`,
`/ticker/embed.js` templates: ink strip = NIGHT polarity A + live mono tape; light-host
sites still receive the dark strip (ink chrome). Widths/idempotent script untouched;
restyle only via replaced CSS constants + minimal markup.

### Task 9: Logo + favicon

**Files:** Modify `logo.svg`; add `static/favicon.svg` + `<link rel="icon">` in
`page_shell` head. Wordmark = "DOMINION" Fraunces-look, tracked uppercase, double-rule
flourish; file self-contained (embedded font subset or vector outlines), current `logo.svg`
palette (dark/crimson) replaced with paper/ink.

### Task 10: Telegram print style + bot parity

**Files:** Modify `telegram_bot.py` (message builders use `TG` scaffolds: rule bars, dotted
leaders, ❦, ▲/▼, masthead-first blocks, folio footers), `bot.py` (`/price`, `/gas`,
`/whales`, `/start`, `/help` same scaffolds for parity).
- [ ] **Step 1:** unit tests: `tests/test_tg_style.py` — `TG` scaffolds importable, formatted
  messages contain rule lines and no markdown-HTML (Telegram `parse_mode` respected).
- [ ] **Step 2:** implement; run `python -c "import telegram_bot"` (no token needed w/ guard) +
  pytest PASS.
- [ ] **Step 3: Commit.**

### Task 11: Final sweep, README, press kit

**Files:** Modify `README.md` (screenshots + updated stack/design section), scripts.
- [ ] **Step 1: Legacy-palette grep = zero**:
  `grep -rn "07090d\|070b12\|090b10\|5ee7ff\|93a5ff\|JetBrains\|Space Grotesk\|DM Sans\|DC2626"` → no
  matches outside docs/specs/README-history.
- [ ] **Step 2:** cut real screenshots (desktop + mobile) of `/`, `/premium`, `/whales`,
  `/docs`, ticker strip; embed into README; refresh badges (Python/Flask/Vercel kept;
  design line updated to Night Edition).
- [ ] **Step 3:** smoke script run: `curl` every route (/admin authed header, JSON endpoints)
  → expected status codes list all pass.
- [ ] **Step 4: Commit. Whole-branch review.**

---

## Execution notes

- Tasks 3–6 look identical mechanically; if a page's HTML constant is >1 page of markup,
  convert iteratively (masthead/folio first, then columns) but keep one commit per page.
- All page tasks run the app the same way (`FLASK_SECRET=x ADMIN_SECRET=y DATA_DIR=/tmp`);
  external APIs may be rate-limited — code paths already handle None gracefully; the halftone
  and shell must render regardless (Review Focus §4).
