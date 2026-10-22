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
    "NIGHT_CSS", "HALFTONE_DIV", "SECTION_CSS",
    "page_shell", "index_strip", "ledger", "tape_table", "wire",
    "ad_box", "kicker", "headline", "deck", "folio", "nav_links", "TG",
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
    .cols,.cols.folio-grid{grid-template-columns:1fr}
    .cols .col{border-right:none;border-bottom:1px dotted var(--rule-strong)}
    .masthead .name{font-size:26px}
  }
  .toast{position:fixed;left:50%;bottom:28px;transform:translateX(-50%);z-index:60;display:none;background:var(--ink-bright);color:var(--paper);font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.2em;text-transform:uppercase;padding:7px 14px;opacity:0;pointer-events:none;transition:opacity .3s}
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
# Folio-page devices (Task 4: wallet checker, profiler, portfolio)
# ============================================================
FOLIO_CSS = """
.cols.folio-grid{grid-template-columns:2.1fr 1fr}
.form-lbl{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:.18em;text-transform:uppercase;color:var(--ink-dim);margin:14px 0 0}
.tool-form{margin-top:6px}
.tool-input,.pf-form input,.pf-form textarea,.profiler-form input{background:transparent;border:none;border-bottom:1px solid var(--rule-strong);color:var(--ink-bright);font-family:'IBM Plex Mono',monospace;font-size:11px;padding:9px 2px;outline:none;width:100%;min-width:0;letter-spacing:.02em}
.tool-input:focus,.pf-form input:focus,.pf-form textarea:focus,.profiler-form input:focus{border-bottom-color:var(--ink-bright)}
.tool-input::placeholder,.pf-form input::placeholder,.pf-form textarea::placeholder,.profiler-form input::placeholder{color:var(--ink-dim)}
.pf-form textarea,.profiler-form textarea{resize:vertical;min-height:64px;line-height:1.6}
.pf-form{display:flex;flex-direction:column;gap:9px;margin-top:8px}
.pf-form input,.pf-form textarea{border:none}/* width from .tool-input */
.buy{font-family:'IBM Plex Mono',monospace}/* buttons reuse .buy */
.buy:disabled{opacity:.35;cursor:not-allowed}
.summary-row{display:flex;margin:14px 0 0;flex-wrap:wrap}
.summary-box{flex:1;min-width:130px;padding:10px 16px 10px 0;border-right:1px solid var(--rule);margin-right:16px}
.summary-box:last-child{border-right:none;margin-right:0}
.summary-box .label,.summary-box .lbl{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:.18em;text-transform:uppercase;color:var(--ink-dim);margin-bottom:5px}
.summary-box .value,.summary-box .val{font-family:'Fraunces',serif;font-size:21px;font-weight:600;color:var(--ink-bright);font-variant-numeric:tabular-nums;line-height:1.1}
.summary-box .sub{font-family:'IBM Plex Mono',monospace;font-size:8.5px;letter-spacing:.1em;color:var(--ink-dim);margin-top:3px}
.pnl-up{color:var(--print-green)}
.pnl-down{color:var(--oxblood)}
.t-h2{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--ink-bright);border-bottom:2.5px solid var(--ink-bright);padding-bottom:5px;margin:18px 0 8px}
.token-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));margin-top:6px;border-top:1px solid var(--rule)}
.token-card{padding:9px 11px;border-bottom:1px solid var(--rule);border-right:1px solid var(--rule)}
.token-card .sym{font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.16em;color:var(--ink)}
.token-card .bal{font-family:'Fraunces',serif;font-size:14px;color:var(--ink-bright);margin-top:3px}
.token-card .usd{font-family:'IBM Plex Mono',monospace;font-size:8.5px;color:var(--ink-dim);letter-spacing:.06em;margin-top:1px}
.address-display{font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--ink-dim);word-break:break-all;padding:10px 0;letter-spacing:.04em;line-height:1.7}
.address-display .addr{color:var(--ink-bright)}
.share-note{font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--ink-dim);letter-spacing:.08em;margin:12px 0 6px}
.share-note code{color:var(--ink);border-bottom:1px dotted var(--rule-strong)}
.total-val{font-family:'Fraunces',serif;font-size:26px;font-weight:600;color:var(--ink-bright);letter-spacing:-.005em;padding:12px 0 4px}
.chain-row{display:flex;justify-content:space-between;align-items:baseline;gap:12px;padding:7px 0;border-bottom:1px solid var(--rule);font-size:11px}
.chain-row .chain-name{font-family:'Fraunces',serif;font-style:italic;font-size:12px;color:var(--ink-bright)}
.chain-row .chain-bal{font-family:'IBM Plex Mono',monospace;font-size:10.5px;color:#cfc4a6}
.chain-row .chain-usd{font-family:'IBM Plex Mono',monospace;font-size:10.5px;color:var(--ink-dim);margin-left:6px}
.wallet-card{padding:11px 0 12px;border-bottom:1px solid var(--rule)}
.wallet-card .addr{font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--ink-dim);letter-spacing:.04em;word-break:break-all;margin-bottom:7px}
.wallet-card .bal-row{display:flex;justify-content:space-between;font-family:'IBM Plex Mono',monospace;font-size:10px;padding:3px 0;color:#cfc4a6}
.wallet-card .bal-row .sym{color:var(--ink-bright)}
.wallet-card .bal-row .usd{color:var(--ink-dim)}
.w-total{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--ink-dim);text-align:right;margin-top:6px;border-top:1px solid var(--rule);padding-top:5px}
.copy-box{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:9px 11px;border:1px solid var(--rule);margin:12px 0;cursor:pointer;font-family:'IBM Plex Mono',monospace;font-size:9px;color:#cfc4a6;word-break:break-all;transition:.15s}
.copy-box:hover{border-color:var(--rule-strong);color:var(--ink-bright)}
.copy-box .hint{color:var(--print-green);font-size:8px;letter-spacing:.18em;text-transform:uppercase;flex-shrink:0}
.tok-row{display:flex;justify-content:space-between;font-size:10px;padding:3px 0;color:var(--ink-dim);border-bottom:1px solid var(--rule);font-family:'IBM Plex Mono',monospace}
.tok-row .sym{color:var(--ink-bright)}
.back{margin-bottom:4px}
.back a{font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:var(--ink-dim);text-decoration:none}
.back a:hover{color:var(--ink-bright)}
.slot-table{width:100%;border-collapse:collapse;margin:14px 0}
.slot-table th{padding:7px 10px;text-align:left;border-bottom:1px solid var(--rule-strong);color:var(--ink-dim);text-transform:uppercase;letter-spacing:.14em;font-size:8px;font-weight:500;font-family:'IBM Plex Mono',monospace}
.slot-table td{padding:6px 10px;border-bottom:1px solid var(--rule);font-size:10.5px;color:#cfc4a6;font-family:'IBM Plex Mono',monospace}
.slot-table th.r{text-align:right}
.slot-table td.r{text-align:right;color:var(--ink-bright)}
.slot-table td.prem{color:var(--print-green)}
.prem-strip{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;border-top:1px solid var(--print-green);padding:9px 0;margin:14px 0;font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.08em;color:var(--ink-dim)}
.prem-strip b{color:var(--print-green);font-weight:500;letter-spacing:.16em;text-transform:uppercase}
.prem-strip a{color:var(--print-green)}
.hint-line{font-family:'IBM Plex Mono',monospace;font-size:8.5px;color:var(--ink-dim);letter-spacing:.1em;text-transform:uppercase;text-align:center;padding:16px 0}
@media (max-width:900px){
  .cols.folio-grid{grid-template-columns:1fr}
}
"""

# ============================================================
# Monetization devices (Task 5: premium, advertise, api-keys)
# ============================================================
MONET_CSS = """
.sec-title{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--ink-bright);border-bottom:2.5px solid var(--ink-bright);padding-bottom:5px;margin:26px 0 10px}
.ben{display:flex;gap:8px;align-items:baseline;padding:5px 0;border-bottom:1px solid var(--rule);font-size:11px;color:#cfc4a6;line-height:1.5}
.ben .mark{font-family:'IBM Plex Mono',monospace;font-size:10px;width:14px;flex-shrink:0}
.ben.on .mark{color:var(--print-green)}
.ben.off{color:var(--ink-dim)}
.ben.off .mark{color:var(--ink-dim)}
.ben b{font-weight:560;color:var(--ink-bright)}
.ben .why{color:var(--ink-dim);font-size:10px}
.tier-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));margin-top:4px;border-top:1px solid var(--rule);border-left:1px solid var(--rule)}
.tier{padding:15px 16px 17px;border-right:1px solid var(--rule);border-bottom:1px solid var(--rule)}
.tier.featured{background:rgba(212,99,90,.05)}
.tier-name{font-family:'IBM Plex Mono',monospace;font-size:8.5px;letter-spacing:.18em;text-transform:uppercase;color:var(--ink-dim)}
.tier.featured .tier-name{color:var(--oxblood)}
.tier-price{font-family:'Fraunces',serif;font-size:24px;font-weight:600;color:var(--ink-bright);margin:6px 0 2px}
.tier-price .per{font-family:'IBM Plex Mono',monospace;font-size:8.5px;letter-spacing:.12em;color:var(--ink-dim);font-weight:400}
.tier-desc{font-size:9.5px;font-style:italic;color:var(--ink-dim);margin-bottom:8px;font-family:'Fraunces',serif}
.tier ul{list-style:none}
.tier ul li{font-family:'IBM Plex Mono',monospace;font-size:9.5px;color:#cfc4a6;padding:4px 0;border-bottom:1px solid var(--rule)}
.tier ul li:last-child{border-bottom:none}
.tier .cta{display:inline-block;margin-top:11px;padding:6px 14px;border:1px solid var(--rule-strong);font-family:'IBM Plex Mono',monospace;font-size:8.5px;letter-spacing:.18em;text-transform:uppercase;color:var(--ink);text-decoration:none;cursor:pointer;transition:.15s}
.tier .cta:hover{border-color:var(--ink-bright);color:var(--ink-bright)}
.req-list{font-size:10.5px;line-height:1.9;color:#cfc4a6;font-family:'IBM Plex Mono',monospace;margin-top:4px}
.req-list span{color:var(--ink-dim)}
.cta-big{display:inline-block;border:1px solid var(--oxblood);color:var(--oxblood);background:transparent;font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.2em;text-transform:uppercase;padding:11px 20px;text-decoration:none;cursor:pointer;transition:.15s}
.cta-big:hover{background:var(--oxblood);color:var(--paper)}
.code-block{border:1px solid var(--rule);padding:10px 12px;font-family:'IBM Plex Mono',monospace;font-size:10px;color:#cfc4a6;overflow-x:auto;margin-top:8px;line-height:1.7}
.code-block code{background:transparent;color:var(--ink-bright);padding:0}
.divider-accent{display:flex;align-items:center;gap:12px;font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.24em;text-transform:uppercase;color:var(--ink-dim);margin:22px 0 6px}
.divider-accent::before,.divider-accent::after{content:'';height:1px;background:var(--rule-strong);flex:1}
.dv{border-bottom:1px solid var(--rule);margin:26px 0}
"""

# ============================================================
# Long-form devices (Task 6: docs endpoint tape, blog feuilleton)
# ============================================================
LONGFORM_CSS = """
.ep{border-top:1px solid var(--rule);padding:9px 0 12px}
.ep .kind{display:flex;gap:9px;align-items:baseline}
.ep .meth{font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.18em;color:var(--print-green)}
.ep .path{font-family:'IBM Plex Mono',monospace;font-size:11.5px;color:var(--ink-bright)}
.ep .desc{font-size:10.5px;color:#cfc4a6;line-height:1.5;margin:3px 0 0}
.rate-line{font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-dim);border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);padding:8px 0;margin-top:14px}
.rate-line b{color:var(--print-green);font-weight:400}
.rate-line i{color:var(--ink-bright);font-style:normal}
.dcopy{font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.18em;color:var(--print-green);cursor:pointer;flex-shrink:0}
.dcopy.copied{color:var(--oxblood)}
.post-row{border-top:1px solid var(--rule);padding:12px 0}
.post-row:last-child{border-bottom:1px solid var(--rule)}
.post-meta{font-family:'IBM Plex Mono',monospace;font-size:8.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--ink-dim)}
.post-title{font-family:'Fraunces',serif;font-size:16.5px;font-weight:560;color:var(--ink-bright);text-decoration:none;line-height:1.3;display:inline-block}
.post-title:hover{text-decoration:underline}
.article-body h2{font-family:'Fraunces',serif;font-size:17px;font-weight:600;color:var(--ink-bright);margin:20px 0 6px;letter-spacing:-.005em;line-height:1.25}
.article-body h3{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.18em;text-transform:uppercase;color:var(--oxblood);margin:16px 0 5px;font-weight:400}
.article-body p{font-size:11.5px;line-height:1.7;color:#cfc4a6;margin:0 0 9px}
.article-body a{color:var(--print-green);text-decoration:none;border-bottom:1px dotted var(--print-green)}
.article-body ul,.article-body ol{margin:0 0 10px;padding-left:16px}
.article-body li{font-size:11.5px;line-height:1.65;color:#cfc4a6;margin-bottom:4px}
.article-body code{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--ink-bright);border:1px solid var(--rule);padding:1px 4px}
.article-body pre{border:1px solid var(--rule);padding:10px 12px;font-family:'IBM Plex Mono',monospace;font-size:10px;color:#cfc4a6;overflow-x:auto;margin:6px 0 10px;line-height:1.7}
.article-body pre code{border:none;padding:0;color:var(--ink-bright)}
.article-body blockquote{border-left:2px solid var(--oxblood);margin:10px 0;padding:2px 0 2px 12px;font-style:italic;color:var(--ink-dim)}
"""

# ============================================================
# Section-page devices (Tasks 3+: whales, trending, yields, launches…)
# ============================================================
SECTION_CSS = """
.featured-star{color:var(--ink-bright);font-size:14px;margin-right:4px}
.src-note{font-size:9.5px;font-style:italic;color:var(--ink-dim);text-align:center;padding:14px 0 6px;border-top:1px solid var(--rule);margin-top:12px}
.loading,.error{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.18em;text-transform:uppercase;color:var(--ink-dim);padding:22px 0;text-align:center}
.error{color:var(--oxblood)}
.filter-row{display:flex;gap:7px;flex-wrap:wrap;padding:9px 0 11px}
.filter-btn,.y-filt,.chain-filt{background:transparent;border:1px solid var(--rule);color:var(--ink-dim);padding:5px 12px;font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.16em;text-transform:uppercase;cursor:pointer}
.filter-btn:hover,.filter-btn.active,.y-filt:hover,.y-filt.active,.chain-filt:hover,.chain-filt.active{border-color:var(--rule-strong);color:var(--ink-bright)}
.updated{font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--ink-dim);letter-spacing:.14em;text-transform:uppercase}
.updated span{color:var(--ink-bright)}
.empty-state{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--ink-dim);text-align:center;padding:40px 0}
/* — whale wire rows — */
.stat-row{display:flex;margin:10px 0 0}
.stat-row .stat-item{font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-dim);padding:7px 16px 7px 0;border-right:1px solid var(--rule);margin-right:16px}
.stat-row .stat-item:last-child{border-right:none;margin-right:0}
.stat-row .stat-item .num{color:var(--ink-bright);font-weight:600}
.whale-feed{margin-top:8px}
.whale-item{display:grid;grid-template-columns:auto 1fr auto;gap:16px;align-items:start;padding:11px 0;border-bottom:1px solid var(--rule);transition:background .15s}
.whale-item:hover{background:rgba(233,223,198,.03)}
.whale-amt{font-family:'IBM Plex Mono',monospace;font-size:12.5px;font-weight:600;color:var(--ink-bright);white-space:nowrap}
.whale-usd{font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--ink-dim);letter-spacing:.06em;margin-top:2px}
.whale-tag{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:.14em;text-transform:uppercase;border:1px solid currentColor;padding:1px 6px;display:inline-block;margin-bottom:5px}
.whale-tag.usdt{color:var(--print-green)}
.whale-tag.usdc{color:var(--ink)}
.whale-tag.wbtc{color:var(--ink-bright)}
.whale-addrs{font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--ink-dim);line-height:1.7;letter-spacing:.04em}
.whale-addrs .label{font-size:8px;letter-spacing:.18em;text-transform:uppercase}
.whale-addrs .addr{color:#cfc4a6}
.whale-tx{font-family:'IBM Plex Mono',monospace;font-size:9px;text-align:right;white-space:nowrap;color:var(--ink-dim)}
.whale-tx a{color:var(--ink-dim);text-decoration:none;border-bottom:1px dotted var(--rule-strong)}
.whale-tx a:hover{color:var(--ink-bright)}
.whale-time{font-size:8px;letter-spacing:.08em;margin-top:3px}
/* — trending coin cells (no cards: ruled cells) — */
.coin-grid:empty::after{content:'the tape is dark — upstream feed late.';display:block;padding:22px 0;text-align:center;font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-dim);border-bottom:1px solid var(--rule)}
.daddr{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:150px;display:inline-block;vertical-align:bottom}
.coin-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(228px,1fr));margin:10px 0 0;border-top:1px solid var(--rule)}
.coin-card{display:block;padding:11px 13px;border-bottom:1px solid var(--rule);border-right:1px solid var(--rule);text-decoration:none;color:inherit;outline:0 solid transparent;transition:background .15s}
.coin-card:hover{background:rgba(233,223,198,.03)}
.coin-card:target{outline:2px solid var(--rule-strong);outline-offset:-2px}
.coin-rank{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-dim);margin-bottom:3px}
.coin-name{font-family:'Fraunces',serif;font-style:italic;font-size:13px;font-weight:600;color:var(--ink-bright)}
.coin-sym{font-family:'IBM Plex Mono',monospace;font-size:8.5px;color:var(--ink-dim);letter-spacing:.12em;font-style:normal}
.coin-price{font-family:'IBM Plex Mono',monospace;font-size:13px;color:var(--ink-bright);margin-top:4px}
.coin-change{font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:.06em;margin-top:2px}
.coin-change.up{color:var(--print-green)}
.coin-change.down{color:var(--oxblood)}
.coin-cap{font-family:'IBM Plex Mono',monospace;font-size:8px;color:var(--ink-dim);letter-spacing:.1em;text-transform:uppercase;margin-top:3px}
/* — yields ledger — */
.y-filters{display:flex;gap:7px;flex-wrap:wrap;border-bottom:1px solid var(--rule);padding:8px 0}
.chain-filters{display:flex;gap:5px;flex-wrap:wrap;padding:8px 0}
.y-status{font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--ink-dim);letter-spacing:.1em;margin:10px 0;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}
.y-table{width:100%;border-collapse:collapse;font-family:'IBM Plex Mono',monospace;font-size:10px}
.y-table th{text-align:left;padding:6px 8px 4px;border-bottom:1px solid var(--rule-strong);color:var(--ink-dim);text-transform:uppercase;letter-spacing:.14em;font-weight:500;font-size:8px}
.y-table td{padding:5.5px 8px;border-bottom:1px solid var(--rule);color:#cfc4a6}
.y-table tr:hover td{background:rgba(233,223,198,.03)}
.y-table .apy-val{font-weight:600;color:var(--ink-bright)}
.y-table .apy-green{color:var(--print-green)}
.y-table .apy-yellow{color:var(--ink)}
.y-table .apy-dim{color:var(--ink-dim)}
.y-table .proj{font-family:'Fraunces',serif;font-style:italic;font-size:11.5px;text-transform:lowercase;color:var(--ink-bright)}
.y-table .chain{color:var(--ink-dim)}
.y-table .tvl{color:var(--ink-dim)}
.y-table .il{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:.16em;text-transform:uppercase}
.y-table .il-no{color:var(--print-green)}
.y-table .il-yes{color:var(--oxblood)}
.y-table .meta{color:var(--ink-dim);font-size:8px;max-width:110px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.y-loading{font-family:'IBM Plex Mono',monospace;font-size:9.5px;letter-spacing:.18em;text-transform:uppercase;color:var(--ink-dim);padding:26px 0;text-align:center}
.y-loading .spinner{display:inline-block;width:7px;height:7px;background:var(--print-green);margin-right:8px;animation:blink 1s step-end infinite}
@keyframes blink{50%{opacity:0}}
.tbl-wrap{overflow-x:auto}
/* — launch diary — */
.launch-card{padding:13px 0 15px;border-bottom:1px solid var(--rule)}
.launch-header{display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px}
.launch-name{font-family:'Fraunces',serif;font-size:15px;font-weight:600;color:var(--ink-bright);letter-spacing:-.005em}
.launch-symbol{font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--ink-dim);letter-spacing:.16em;text-transform:uppercase}
.launch-type{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-dim);border:1px solid var(--rule);padding:1px 7px;display:inline-block;margin-left:6px;vertical-align:2px}
.countdown{font-family:'IBM Plex Mono',monospace;font-size:16px;font-weight:600;color:var(--ink-bright);font-variant-numeric:tabular-nums;min-width:130px;text-align:right}
.countdown-unit{font-size:7px;color:var(--ink-dim);letter-spacing:.1em;text-transform:uppercase;margin-left:2px;font-weight:400}
.countdown-label{font-family:'IBM Plex Mono',monospace;font-size:8.5px;color:var(--ink-dim);letter-spacing:.08em;text-align:right;margin-top:2px}
.launch-desc{font-size:11.3px;line-height:1.55;color:#cfc4a6;margin:8px 0 2px;max-width:52em}
.launch-meta{font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--ink-dim);letter-spacing:.08em;display:flex;gap:14px;flex-wrap:wrap}
.launch-meta span{display:inline-flex;align-items:center;gap:4px}
.launch-links{display:flex;gap:7px;margin-top:9px;flex-wrap:wrap}
.exchange-link{border:1px solid var(--rule);padding:4px 11px;font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:.16em;text-transform:uppercase;color:var(--ink);text-decoration:none;transition:.15s}
.exchange-link:hover{border-color:var(--rule-strong);color:var(--ink-bright)}
.status-badge{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:.16em;text-transform:uppercase;display:inline-block}
.status-upcoming{color:var(--print-green)}
.status-ongoing{color:var(--ink-bright);border-bottom:1px solid var(--rule-strong)}
.status-ended{color:var(--ink-dim)}
@media (max-width:700px){.whale-item{grid-template-columns:1fr;gap:8px}.whale-tx{text-align:left}.countdown{text-align:left}}
"""


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
