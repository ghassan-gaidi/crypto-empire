"""
Dominion — Meridian Press · Night Edition design system.

Single source of truth for the whole identity (spec:
docs/superpowers/specs/2026-10-22-dominion-night-edition-design.md).

Pure strings + pure functions: no Flask, no network — importable by
app.py (web), the ticker/widget embeds, and both Telegram bots.
"""
from __future__ import annotations

import html
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

__all__ = [
    "NIGHT_CSS", "HALFTONE_DIV",
    "page_shell", "index_strip", "ledger", "tape_table", "wire",
    "ad_box", "kicker", "headline", "deck", "folio", "TG",
]

_E = html.escape


# ============================================================
# Token core — spec §2.1 (edited only in this file)
# ============================================================
NIGHT_CSS = """<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..900;1,9..144,300..900&family=IBM+Plex+Mono:ital,wght@0,400;0,500;0,600;1,400&display=swap');
  *{margin:0;padding:0;box-sizing:border-box}
  :root{
    --paper:#17130d;
    --ink:#e9dfc6;
    --ink-bright:#f2ead4;
    --ink-dim:#968b70;
    --rule:rgba(233,223,198,.22);
    --rule-strong:rgba(233,223,198,.55);
    --oxblood:#d4635a;
    --print-green:#8fcea5;
  }
  body{
    font-family:'Fraunces',Georgia,serif;
    background:var(--paper);
    color:var(--ink);
    font-size:14px;line-height:1.5;
    min-height:100vh;
    -webkit-font-smoothing:antialiased;
  }
  .mono{font-family:'IBM Plex Mono',ui-monospace,monospace}
  .up{color:var(--print-green)}
  .down{color:var(--oxblood)}
  a{color:inherit}
  /* --- masthead --- */
  .masthead{flex-direction:column;align-items:center;display:flex;text-align:center;padding:14px 24px 10px}
  .masthead .name{font-size:40px;font-weight:640;letter-spacing:.16em;text-transform:uppercase;line-height:1;color:var(--ink-bright)}
  .masthead .sub{margin-top:8px;display:flex;justify-content:center;gap:14px;align-items:center;width:100%}
  .masthead .sub i{max-width:130px;flex:0 1 130px;border-top:1px solid var(--rule-strong)}
  .kicker{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.28em;text-transform:uppercase;color:var(--ink-dim)}
  .edition-bar{display:flex;justify-content:space-between;padding:7px 24px;border-top:1px solid var(--rule-strong);border-bottom:2.5px solid var(--ink-bright);font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-dim)}
  /* --- index strip (site header tape) --- */
  .index-strip{display:flex;gap:22px;align-items:center;justify-content:center;padding:7px 24px;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);font-family:'IBM Plex Mono',monospace;font-size:10.5px;white-space:nowrap;overflow-x:auto}
  .index-strip .tk-dim{color:var(--ink-dim)}
  .index-strip b{color:var(--ink-bright)}
  /* --- nav strip (site-wide section index) --- */
  .nav-strip{display:flex;flex-wrap:wrap;justify-content:center;gap:4px 16px;padding:9px 24px;border-bottom:1px solid var(--rule);font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.16em;text-transform:uppercase}
  .nav-strip a{color:var(--ink-dim);text-decoration:none;white-space:nowrap}
  .nav-strip a:hover{color:var(--ink-bright)}
  .nav-strip .nav-here{color:var(--ink-bright);border-bottom:1px solid var(--rule-strong)}
  .skip-link{position:absolute;left:-9999px;top:0}
  .skip-link:focus{left:8px;top:8px;background:var(--ink-bright);color:var(--paper);padding:6px 10px;z-index:60}
  /* --- columns --- */
  .cols{display:grid;grid-template-columns:2.2fr 1.15fr 1.15fr;min-height:0}
  .cols .col{padding:14px 16px 16px;border-right:1px dotted var(--rule-strong);min-width:0}
  .cols .col:last-child{border-right:none}
  @media (max-width:900px){
    .cols{grid-template-columns:1fr}
    .cols .col{border-right:none;border-bottom:1px dotted var(--rule-strong)}
    .masthead .name{font-size:26px}
  }
  /* --- story devices --- */
  .headline{font-size:21px;font-weight:560;letter-spacing:-.005em;line-height:1.18;margin:6px 0 0;color:var(--ink-bright)}
  .deck{font-style:italic;font-weight:380;font-size:13.5px;line-height:1.42;color:#c3b897;margin-top:7px}
  .byle{display:flex;justify-content:space-between;margin:9px 0 0;padding-top:7px;border-top:1px solid var(--rule)}
  .para{font-size:11.3px;line-height:1.55;color:#cfc4a6;margin-top:8px}
  .foot-note{font-size:9.5px;font-style:italic;color:var(--ink-dim);margin-top:9px;border-top:1px solid var(--rule);padding-top:7px;font-family:'Fraunces',serif}
  /* --- dotted-leader ledger --- */
  .ledger{margin-top:12px;border-top:1px solid var(--rule);padding-top:9px}
  .ledger-row{display:flex;align-items:baseline;gap:8px;padding:2.5px 0;font-family:'IBM Plex Mono',monospace;font-size:10.5px}
  .ledger-row .lbl{white-space:nowrap;color:#cfc4a6}
  .ledger-row .dots{flex:1;border-bottom:1px dotted rgba(233,223,198,.45);transform:translateY(-3px)}
  .ledger-row .val{white-space:nowrap;font-weight:600;color:var(--ink-bright)}
  /* --- the tape --- */
  .t-head{display:flex;justify-content:space-between;align-items:baseline;border-bottom:2.5px solid var(--ink-bright);padding-bottom:5px}
  .t-head .kicker{color:var(--ink-bright)}
  .tape-table{width:100%;border-collapse:collapse;font-family:'IBM Plex Mono',monospace;font-size:10.5px}
  .tape-table th{text-align:left;font-weight:500;color:var(--ink-dim);font-size:9px;letter-spacing:.16em;text-transform:uppercase;padding:6px 0 4px;border-bottom:1px solid var(--rule-strong)}
  .tape-table td{padding:5.5px 0;border-bottom:1px solid var(--rule);color:#cfc4a6}
  .tape-table .ser{font-family:'Fraunces',serif;font-style:italic;font-size:12px;white-space:nowrap;color:var(--ink-bright)}
  .tape-table .r{text-align:right}
  /* --- the wire --- */
  .wire-item{padding:8px 0;border-bottom:1px solid var(--rule)}
  .wire-item:last-child{border-bottom:none}
  .wire-t{font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.14em;color:var(--ink-dim)}
  .wire-x{font-size:11.5px;line-height:1.42;margin-top:3px;color:#cfc4a6}
  /* --- ad box & button --- */
  .ad-box{border-top:2.5px solid var(--ink-bright);border-bottom:2.5px solid var(--ink-bright);padding:1px;margin-top:12px}
  .ad-box>div{border-top:1px solid var(--rule-strong);border-bottom:1px solid var(--rule-strong);padding:11px 12px;text-align:center}
  .buy{display:inline-block;background:var(--ink-bright);color:var(--paper);font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.2em;text-transform:uppercase;padding:9px 16px;text-align:center;text-decoration:none;border:none;cursor:pointer}
  .buy:visited{color:var(--paper)}
  /* --- folio --- */
  .folio{display:flex;justify-content:space-between;align-items:center;padding:8px 24px 10px;border-top:1px solid var(--rule-strong);font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.18em;text-transform:uppercase;color:var(--ink-dim)}
  /* --- halftone overlay: canonical two-layer dot screen (spec §2.4) --- */
  .ht{
    position:absolute;inset:0;z-index:1;pointer-events:none;
    --cell:5.5px; --dr:1.1px; --ink:233,223,198; --da:.12;
    background-image:
      radial-gradient(circle at center,rgba(var(--ink),var(--da)) var(--dr),transparent 0),
      radial-gradient(circle at center,rgba(var(--ink),calc(var(--da)*.75)) var(--dr),transparent 0);
    background-size:var(--cell) var(--cell);
    background-position:0 0,calc(var(--cell)/2) calc(var(--cell)/2);
    background-repeat:round;
  }
  .ht .vig{position:absolute;inset:0;background:radial-gradient(115% 90% at 50% 20%,transparent 50%,rgba(0,0,0,.22) 86%,rgba(0,0,0,.38) 100%)}
  .ht .stain{position:absolute;inset:0;background:radial-gradient(30% 22% at 4% 96%,rgba(196,150,90,.06),transparent 70%),radial-gradient(24% 18% at 97% 6%,rgba(196,150,90,.05),transparent 70%)}
  .sheet{position:relative;overflow:hidden;min-height:100vh;display:flex;flex-direction:column}
  .sheet>*{position:relative;z-index:2}
  .sheet .ht{position:absolute;z-index:1}
</style>"""

HALFTONE_DIV = '<div class="ht"><div class="vig"><div class="stain"></div></div></div>'


# ============================================================
# Components (all text escaped — Review Focus §1)
# ============================================================
def kicker(text: str) -> str:
    return f'<div class="kicker">{_E(text)}</div>'


def headline(text: str) -> str:
    return f'<h3 class="headline">{_E(text)}</h3>'


def deck(text: str) -> str:
    return f'<p class="deck">{_E(text)}</p>'


_TONE_CLASS = {"up": "up", "down": "down", "dim": "tk-dim"}


def _tone_span(text: str, tone: Optional[str]) -> str:
    if tone in _TONE_CLASS:
        return f'<span class="{_TONE_CLASS[tone]}">{_E(text)}</span>'
    return _E(text)


def index_strip(items: Optional[Sequence[Tuple[str, str, str]]]) -> str:
    if not items:
        return '<div class="index-strip"><span class="tk-dim">the tape is dark</span></div>'
    spans = []
    for label, value, tone in items:
        spans.append(f'<span><b>{_E(label)}</b> {_tone_span(value, tone)}</span>')
    return '<div class="index-strip">' + "".join(spans) + "</div>"


def ledger(rows: Iterable[Tuple[str, str, Optional[str]]]) -> str:
    rows = list(rows)
    if not rows:
        return ('<div class="ledger north"><p class="foot-note">the wire is silent — '
                'the tape is dark.</p><div class="leg-dummy" style="display:none">····</div></div>')
    out = ['<div class="ledger">']
    for label, value, tone in rows:
        out.append(
            '<div class="ledger-row">'
            f'<span class="lbl">{_E(label)}</span>'
            '<span class="dots">············································</span>'
            f'<span class="val">{_tone_span(value, tone)}</span>'
            "</div>"
        )
    out.append("</div>")
    return "".join(out)


def tape_table(rows: Sequence[Tuple[str, str, str, str]],
               header: Tuple[str, str, str] = ("Instrument", "Last", "Chg")) -> str:
    out = ['<div class="t-head-wrap"><table class="tape-table">', "<tr><th></th></tr>"]
    out = [
        f'<table class="tape-table">'
        f"<tr><th>{_E(header[0])}</th><th class=\"r\">{_E(header[1])}</th>"
        f"<th class=\"r\">{_E(header[2])}</th></tr>"
    ]
    for name, last, chg, tone in rows:
        glyph = "▲" if tone == "up" else ("▼" if tone == "down" else "·")
        sign = "" if chg.startswith("-") else ("+" if tone in ("up", "down") else "")
        out.append(
            f'<tr><td class="ser">{_E(name)}</td>'
            f'<td class="r">{_E(last)}</td>'
            f"<td class=\"r {_TONE_CLASS.get(tone, 'tk-dim')}\">{glyph} {_E(sign)}{_E(chg)}</td></tr>"
        )
    out.append("</table>")
    return "".join(out)


def wire(entries: Sequence[Tuple[str, str]]) -> str:
    if not entries:
        return '<p class="foot-note">the wire is silent.</p>'
    out = []
    for time_text, text in entries:
        out.append(
            '<div class="wire-item">'
            f'<span class="wire-t">{_E(time_text)}</span>'
            f'<div class="wire-x">{_E(text)}</div>'
            "</div>"
        )
    return "".join(out)


def ad_box(title: str, sub: str, cta: Tuple[str, str], note: str = "ADVERTISEMENT") -> str:
    label, href = cta
    return (
        '<div class="ad-box"><div>'
        f'<div class="kicker">{_E(note)}</div>'
        f'<div style="font-size:14.5px;font-weight:560;margin-top:4px;color:var(--ink-bright)">{_E(title)}</div>'
        f'<div class="kicker" style="margin-top:3px">{_E(sub)}</div>'
        f'<a class="buy" href="{_E(href, quote=True)}">{_E(label)}</a>'
        "</div></div>"
    )


def folio(page: str = "A1") -> str:
    return (
        '<div class="folio">'
        f"<span>Page {_E(page)}</span><span>❦</span>"
        "<span>Dominion · On-Chain Intelligence</span>"
        "</div>"
    )


def nav_links(items, here: Optional[str] = None) -> str:
    """Site-wide mono nav strip. items = [(label, href)]; `here` marks the
    active label with an underscored rule."""
    links = []
    for label, href in items:
        cls = ' class="nav-here"' if here is not None and label == here else ""
        links.append(
            f'<a{cls} href="{_E(href, quote=True)}">{_E(label)}</a>'
        )
    return '<nav class="nav-strip">' + "".join(links) + "</nav>"


def page_shell(title: str, body: str, *, kicker: str = "", page: str = "A1",
               edition: str = "Night Edition", extra_css: str = "",
               strip_items: Optional[Sequence[Tuple[str, str, str]]] = None,
               head_extra: str = "") -> str:
    lot = _E(kicker) if kicker else "On-Chain Intelligence"
    return (
        "<!DOCTYPE html>\n"
        f'<html lang="en"><head><title>{_E(title)} · Dominion</title>'
        + head_extra
        + NIGHT_CSS
        + (f"<style>{extra_css}</style>" if extra_css else "")
        + "</head><body><div class=\"sheet\">"
        + '<div class="masthead"><div class="name">Dominion</div>'
        f'<div class="sub"><i></i><span class="kicker">{lot}</span><i></i></div></div>'
        + '<div class="edition-bar"><span>Crypto Intelligence Bureau · Berlin</span>'
        + f"<span>{_E(edition)}</span><span>Dominion</span></div>"
        + index_strip(strip_items)
        + body
        + folio(page)
        + HALFTONE_DIV
        + "</div></body></html>"
    )


# ============================================================
# Telegram print-style scaffolds (plaintext, spec §3)
# ============================================================
TG: Dict[str, str] = {
    "masthead": "DOMINION — {page}",
    "rule": "─" * 24,
    "leader": "····",
    "bullet": "❧",
    "up": "▲",
    "down": "▼",
    "strip": "{label}: {value} {tone}",
    "foot": "❦ {page} · /help for the index {when}",
    "silent": "the wire is silent.",
}
