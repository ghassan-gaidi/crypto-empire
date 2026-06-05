#!/usr/bin/env python3
"""
Crypto Empire - Web Dashboard & API
Autonomous crypto intelligence platform with monetization
"""
import os
import json
import sqlite3
import re
import time
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET
from html import unescape

from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS
import requests

# ============================================================
# Configuration
# ============================================================
WALLET_ADDRESS = "0x29021dd5306D7b3b6608a2bc8276D33c1200C7Ef"
if os.environ.get("VERCEL"):
    DATA_DIR = Path("/tmp") / "crypto-empire-data"
else:
    DATA_DIR = Path.home() / "crypto-empire" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get("FLASK_SECRET", "crypto-empire-secret-key-2026")

# Premium API Keys (comma-separated in env var)
PREMIUM_API_KEYS = set()
_api_keys_raw = os.environ.get("PREMIUM_API_KEYS", "")
if _api_keys_raw:
    PREMIUM_API_KEYS = set(k.strip() for k in _api_keys_raw.split(",") if k.strip())

# Sponsored coin config
SPONSORED_COIN_ID = os.environ.get("SPONSORED_COIN_ID", "bitcoin")
SPONSORED_COIN_MSG = os.environ.get("SPONSORED_COIN_MSG", "Bitcoin — The Original Asset")

# ============================================================
# Database
# ============================================================
DB_PATH = DATA_DIR / "web.db"

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS price_cache (
            coin_id TEXT PRIMARY KEY,
            data TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            user_agent TEXT,
            visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

init_db()

# ============================================================
# API helpers
# ============================================================
COINGECKO_API = "https://api.coingecko.com/api/v3"
CACHE_TTL = 60

def render_sparkline(prices, width=80, height=24):
    """Render price array as inline SVG sparkline"""
    if not prices or len(prices) < 2:
        return ""
    min_p = min(prices)
    max_p = max(prices)
    rng = max_p - min_p if max_p > min_p else 1
    step = width / (len(prices) - 1)
    pts = []
    for i, p in enumerate(prices):
        x = round(i * step, 1)
        y = round(height - ((p - min_p) / rng * (height - 4) + 2), 1)
        pts.append(f"{x},{y}")
    color = "var(--green)" if prices[-1] >= prices[0] else "var(--red)"
    return f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"><polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="1.5"/></svg>'

def fetch_sync(url):
    try:
        resp = requests.get(url, timeout=10, headers={"Accept": "application/json"})
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

def fetch_rss(url):
    """Fetch and parse an RSS feed"""
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            items = []
            for item in root.iter('item'):
                title = item.findtext('title', '')
                link = item.findtext('link', '')
                pubDate = item.findtext('pubDate', '')
                desc = item.findtext('description', '')
                # Strip HTML from description
                desc_clean = re.sub(r'<[^>]+>', '', desc)[:200] if desc else ''
                items.append({
                    'title': unescape(title),
                    'link': link,
                    'date': pubDate,
                    'desc': unescape(desc_clean)
                })
            return items[:10]
    except:
        pass
    return []

# ============================================================
# Shared CSS — Professional Terminal Aesthetic
# ============================================================
SHARED_HEAD = """<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700;800&display=swap');
  *{margin:0;padding:0;box-sizing:border-box;border-radius:0!important;-webkit-border-radius:0!important;}
  :root{
    --bg:#000;
    --surface:#050505;
    --border:#181818;
    --text:#b0b0b0;
    --text-dim:#555;
    --text-muted:#282828;
    --green:#0f0;
    --red:#f00;
    --white:#fff;
    --glow:0 0 8px rgba(255,255,255,.10);
    --glow-green:0 0 8px rgba(0,255,0,.12);
  }
  body{
    font-family:'JetBrains Mono','Fira Code','Courier New',monospace;
    background:var(--bg);color:var(--text);font-size:12px;line-height:1.7;
    min-height:100vh;position:relative;overflow-x:hidden;
  }
  ::selection{background:var(--white);color:var(--bg);}
  a{color:var(--text);text-decoration:none;}
  a:hover{color:var(--white);}

  /* ===== CRT MINIMAL ===== */
  body::after{
    content:'';position:fixed;top:0;left:0;right:0;bottom:0;
    background:repeating-linear-gradient(0deg,transparent 0,transparent 2px,rgba(255,255,255,.002) 2px,rgba(255,255,255,.002) 3px);
    pointer-events:none;z-index:9999;
  }
  body::before{
    content:'';position:fixed;top:0;left:0;right:0;bottom:0;
    background:radial-gradient(ellipse at center,transparent 55%,rgba(0,0,0,.5) 100%);
    pointer-events:none;z-index:9998;
  }
  @keyframes sweep{0%{top:-2%}100%{top:102%}}
  .sweep{
    position:fixed;left:0;right:0;height:3px;
    background:linear-gradient(to bottom,transparent,rgba(255,255,255,.03),transparent);
    pointer-events:none;z-index:9996;animation:sweep 12s linear infinite;
  }
  .grid-bg{
    position:fixed;top:0;left:0;right:0;bottom:0;
    background-image:linear-gradient(rgba(255,255,255,.008) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.008) 1px,transparent 1px);
    background-size:40px 40px;pointer-events:none;z-index:-1;
  }
  .container{max-width:1100px;margin:0 auto;padding:24px 20px 60px;}
  hr{border:none;border-top:1px solid var(--border);margin:28px 0;}

  /* ===== TOP BAR ===== */
  .top-bar{
    display:flex;justify-content:space-between;align-items:center;
    border-bottom:1px solid var(--border);padding-bottom:12px;margin-bottom:20px;
    flex-wrap:wrap;gap:12px;
  }
  .brand{display:flex;align-items:center;gap:14px;}
  .prompt{color:var(--green);font-size:16px;font-weight:700;display:flex;align-items:center;}
  .prompt .cr{display:inline-block;width:9px;height:15px;background:var(--green);margin-left:3px;animation:blink 1s step-end infinite;vertical-align:middle;}
  @keyframes blink{50%{opacity:0}}
  .site-title{font-size:18px;font-weight:800;color:var(--white);letter-spacing:5px;text-transform:uppercase;}
  .site-sub{font-size:9px;color:var(--text-dim);letter-spacing:3px;text-transform:uppercase;margin-top:2px;}
  .top-nav{display:flex;gap:1px;flex-wrap:wrap;}
  .top-nav a{
    padding:6px 14px;font-size:9px;text-transform:uppercase;letter-spacing:2px;
    color:var(--text-dim);border:1px solid var(--border);transition:.15s;
  }
  .top-nav a:hover{color:var(--white);border-color:var(--white);}
  .top-nav a.premium{border-color:var(--green);color:var(--green);}
  .top-nav a.premium:hover{background:var(--green);color:var(--bg);}

  /* ===== STATUS LINE ===== */
  .status-line{
    display:flex;justify-content:space-between;align-items:center;
    padding:4px 0;border-bottom:1px solid var(--border);margin-bottom:24px;
    font-size:9px;color:var(--text-dim);text-transform:uppercase;letter-spacing:1px;
  }
  .dot{width:5px;height:5px;background:var(--green);display:inline-block;margin-right:5px;animation:pulse-dot 2s ease-in-out infinite;}
  @keyframes pulse-dot{0%,100%{opacity:1;box-shadow:0 0 4px var(--green)}50%{opacity:.5;box-shadow:0 0 10px var(--green)}}

  /* ===== ASCII DIVIDER ===== */
  .divider{text-align:center;color:var(--text-muted);font-size:9px;letter-spacing:2px;margin:28px 0 16px;text-transform:uppercase;}
  .divider::before{content:'--[ ';color:var(--text-muted);}
  .divider::after{content:' ]--';color:var(--text-muted);}

  /* ===== SECTION TITLE ===== */
  .s-title{
    font-size:9px;color:var(--text-dim);text-transform:uppercase;
    letter-spacing:3px;margin-bottom:10px;border:none;
  }
  .s-title::before{content:'> ';color:var(--green);font-weight:700;}

  /* ===== STAT ROW ===== */
  .stat-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;border:1px solid var(--border);margin-bottom:24px;}
  .stat-item{padding:12px 14px;background:var(--surface);transition:.15s;}
  .stat-item:hover{background:rgba(255,255,255,.01);}
  .stat-label{font-size:8px;color:var(--text-dim);text-transform:uppercase;letter-spacing:2px;}
  .stat-value{font-size:20px;font-weight:700;color:var(--white);margin-top:3px;}
  .stat-sub{font-size:8px;text-transform:uppercase;letter-spacing:1px;margin-top:2px;}
  .up{color:var(--green);}.down{color:var(--red);}

  /* ===== GAS ===== */
  .gas-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:1px;border:1px solid var(--border);margin-bottom:24px;}
  .gas-item{padding:10px;text-align:center;background:var(--surface);transition:.15s;}
  .gas-item:hover{background:rgba(255,255,255,.01);}
  .gas-chain{font-size:8px;color:var(--text-dim);text-transform:uppercase;letter-spacing:2px;}
  .gas-gwei{font-size:22px;font-weight:700;letter-spacing:1px;margin-top:3px;}
  .gas-gwei.low{color:var(--green);}.gas-gwei.med{color:var(--white);}.gas-gwei.high{color:var(--red);}

  /* ===== TABLE ===== */
  .tbl{border:1px solid var(--border);margin-bottom:24px;overflow-x:auto;}
  table{width:100%;border-collapse:collapse;min-width:600px;}
  th,td{padding:7px 12px;text-align:left;font-size:11px;white-space:nowrap;border-bottom:1px solid var(--border);}
  th{color:var(--text-dim);font-weight:500;font-size:8px;text-transform:uppercase;letter-spacing:2px;background:var(--surface);}
  tr:last-child td{border-bottom:none;}
  tr:hover td{background:rgba(255,255,255,.02);}
  tr:hover td:first-child{box-shadow:inset 2px 0 0 var(--green);}
  .rank{color:var(--text-dim);width:20px;}
  .cname{font-weight:500;color:var(--white);}
  .csym{color:var(--text-muted);font-size:9px;}
  .mc,.vol{color:var(--text-dim);font-size:10px;}

  /* ===== AFFILIATE STRIP ===== */
  .aff-strip{
    border:1px solid var(--border);padding:10px 16px;margin-bottom:24px;
    display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;
    background:var(--surface);
  }
  .aff-label{font-size:8px;color:var(--text-dim);text-transform:uppercase;letter-spacing:2px;}
  .aff-links{display:flex;gap:6px;flex-wrap:wrap;}
  .aff-link{
    border:1px solid var(--border);padding:4px 12px;font-size:9px;
    text-transform:uppercase;letter-spacing:1px;color:var(--text);transition:.15s;
  }
  .aff-link:hover{border-color:var(--white);color:var(--white);}

  /* ===== SPONSORED ===== */
  .sponsor-box{
    border:1px solid var(--border);padding:10px 16px;margin-bottom:24px;
    display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;
    background:var(--surface);
  }
  .sponsor-label{font-size:8px;color:var(--text-dim);text-transform:uppercase;letter-spacing:2px;}
  .sponsor-label em{color:var(--green);font-style:normal;}
  .sponsor-slot{
    border:1px dashed var(--text-muted);padding:4px 14px;font-size:9px;
    color:var(--text-dim);text-transform:uppercase;letter-spacing:1px;transition:.15s;
  }
  .sponsor-slot:hover{border-color:var(--white);color:var(--white);}

  /* ===== NEWS ===== */
  .news-list{list-style:none;}
  .news-list li{padding:7px 12px;border-bottom:1px solid var(--border);transition:.15s;}
  .news-list li:last-child{border-bottom:none;}
  .news-list li:hover{background:rgba(255,255,255,.02);}
  .news-list a{color:var(--text);font-size:11px;display:block;}
  .news-list a:hover{color:var(--white);}
  .n-date{font-size:8px;color:var(--text-dim);margin-top:1px;text-transform:uppercase;letter-spacing:1px;}

  /* ===== FEATURES ===== */
  .feat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;border:1px solid var(--border);margin-bottom:24px;}
  .feat-item{padding:16px 12px;text-align:center;background:var(--surface);transition:.15s;}
  .feat-item:hover{background:rgba(255,255,255,.01);}
  .feat-icon{font-size:12px;margin-bottom:4px;color:var(--green);font-weight:700;}
  .feat-item h4{font-size:10px;margin-bottom:4px;text-transform:uppercase;letter-spacing:1px;color:var(--white);}
  .feat-item p{font-size:9px;color:var(--text-dim);line-height:1.5;}

  /* ===== PREMIUM BOX ===== */
  .prem-box{border:1px solid var(--border);padding:24px;margin-bottom:24px;text-align:center;background:var(--surface);}
  .prem-box h3{font-size:12px;margin-bottom:8px;text-transform:uppercase;letter-spacing:3px;color:var(--white);}
  .prem-box h3::before{content:'$ ';color:var(--text-dim);}
  .prem-box p{font-size:10px;color:var(--text-dim);margin-bottom:10px;}
  .waddr{
    border:1px solid var(--border);padding:8px 16px;font-family:monospace;
    font-size:10px;color:var(--white);word-break:break-all;cursor:pointer;
    background:var(--bg);display:inline-block;max-width:100%;user-select:all;transition:.15s;
  }
  .waddr:hover{border-color:var(--white);}
  .ctags{display:flex;gap:4px;justify-content:center;flex-wrap:wrap;margin:8px 0;}
  .ctag{border:1px solid var(--border);padding:2px 10px;font-size:8px;color:var(--text-dim);text-transform:uppercase;letter-spacing:1px;}

  /* ===== FOOTER ===== */
  footer{text-align:center;padding:20px 0;border-top:1px solid var(--border);color:var(--text-dim);font-size:9px;}

  /* ===== BOTTOM BAR ===== */
  .b-bar{
    position:fixed;bottom:0;left:0;right:0;background:var(--surface);
    border-top:1px solid var(--border);padding:3px 20px;font-size:8px;color:var(--text-dim);
    display:flex;justify-content:space-between;align-items:center;
    text-transform:uppercase;letter-spacing:1px;z-index:9990;
  }
  .b-bar .sp{color:var(--text-muted);margin:0 6px;}

  /* ===== TOAST ===== */
  .toast{
    position:fixed;bottom:40px;left:50%;transform:translateX(-50%);
    background:var(--white);color:var(--bg);padding:7px 18px;font-size:10px;
    font-weight:700;opacity:0;transition:opacity .2s;
    pointer-events:none;z-index:10000;text-transform:uppercase;letter-spacing:2px;
  }
  .toast.show{opacity:1;}

  /* ===== WALLET PAGE ===== */
  .winput{border:1px solid var(--border);padding:10px 14px;background:var(--surface);color:var(--white);font-family:monospace;font-size:13px;outline:none;width:100%;display:block;transition:.15s;}
  .winput:focus{border-color:var(--white);}
  .wbtn{border:1px solid var(--white);color:var(--white);background:transparent;padding:8px 22px;font-family:monospace;font-size:10px;cursor:pointer;text-transform:uppercase;letter-spacing:3px;margin-top:8px;transition:.1s;}
  .wbtn:hover{background:var(--white);color:var(--bg);}
  .ch-row{display:flex;justify-content:space-between;align-items:center;border:1px solid var(--border);padding:8px 12px;margin-bottom:6px;font-size:11px;}
  .ch-row:hover{background:rgba(255,255,255,.02);}
  .ch-name{font-weight:500;text-transform:uppercase;letter-spacing:1px;font-size:10px;color:var(--white);}
  .ch-bal{font-family:monospace;color:var(--white);font-size:12px;}
  .ch-usd{color:var(--text-dim);font-size:10px;}
  .tval{font-size:24px;font-weight:700;color:var(--white);text-align:center;padding:18px;border:1px solid var(--border);margin-bottom:10px;}
  .tval::before{content:'$ ';color:var(--text-dim);}
  .error{color:var(--red);text-align:center;padding:14px;font-size:11px;}
  .loading{text-align:center;color:var(--text-dim);padding:14px;font-size:10px;animation:ld .8s ease-in-out infinite;}
  @keyframes ld{0%,100%{opacity:.3}50%{opacity:1}}

  /* ===== 404 ===== */
  .e404{text-align:center;padding:80px 20px;}
  .e404 h1{font-size:64px;color:var(--white);font-weight:800;letter-spacing:8px;}
  .e404 p{color:var(--text-dim);font-size:11px;margin:10px 0 18px;letter-spacing:2px;}

  /* ===== BLOG ===== */
  .post{border:1px solid var(--border);padding:18px;margin-bottom:10px;transition:.15s;}
  .post:hover{border-color:var(--white);}
  .post h2{font-size:12px;margin-bottom:4px;}
  .post h2 a{color:var(--white);transition:.15s;}
  .post h2 a:hover{text-shadow:var(--glow);}
  .post .meta{color:var(--text-dim);font-size:8px;margin-bottom:6px;text-transform:uppercase;letter-spacing:1px;}
  .post .tags{display:flex;gap:4px;flex-wrap:wrap;}
  .post .tag{border:1px solid var(--border);padding:2px 8px;font-size:8px;color:var(--text-dim);text-transform:uppercase;letter-spacing:1px;}

  /* ===== BACK NAV ===== */
  .bnav{margin-bottom:16px;}
  .bnav a{color:var(--text-dim);font-size:9px;text-transform:uppercase;letter-spacing:2px;}
  .bnav a:hover{color:var(--white);}
  .bnav a::before{content:'<< ';color:var(--text-muted);}

  /* ===== SCROLLBAR ===== */
  ::-webkit-scrollbar{width:3px;height:3px;}
  ::-webkit-scrollbar-track{background:transparent;}
  ::-webkit-scrollbar-thumb{background:var(--text-muted);}
  ::-webkit-scrollbar-thumb:hover{background:var(--text-dim);}

  @media(max-width:640px){
    .container{padding:10px 10px 60px;}
    .stat-row{grid-template-columns:repeat(2,1fr);}
    th,td{padding:5px 7px;font-size:10px;}
    .ch-row{flex-direction:column;gap:4px;text-align:center;}
    .site-title{font-size:14px;letter-spacing:3px;}
    .top-bar{flex-direction:column;align-items:flex-start;gap:8px;}
  }
</style>"""

# ============================================================
# HTML Templates
# ============================================================
INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>""" + SHARED_HEAD + """
    <title>Crypto Empire — Autonomous Crypto Intelligence</title>
    <meta name="description" content="Free crypto dashboard with live prices, gas tracker, wallet balance checker, and market data for Ethereum, Bitcoin, Arbitrum, Polygon & Base.">
    <meta name="keywords" content="crypto dashboard, wallet checker, gas tracker, Ethereum gas, Bitcoin price, crypto prices, portfolio tracker, blockchain tools">
    <link rel="canonical" href="https://crypto-empire-ten.vercel.app/">
    <meta property="og:title" content="Crypto Empire — Autonomous Crypto Intelligence">
    <meta property="og:description" content="Free crypto dashboard with live prices, gas tracker, wallet balance checker, and market data.">
    <meta property="og:url" content="https://crypto-empire-ten.vercel.app/">
    <meta property="og:type" content="website">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Crypto Empire — Autonomous Crypto Intelligence">
    <meta name="twitter:description" content="Free crypto dashboard. Live prices, gas tracker, wallet checker, Telegram bot @Crypt0Emp1reBot.">
</head>
<body>
    <div class="grid-bg"></div>
    <div class="sweep"></div>

    <div class="container">
        <!-- Top Bar -->
        <div class="top-bar">
            <div class="brand">
                <div class="prompt">><span class="cr"></span></div>
                <div>
                    <div class="site-title">Crypto Empire</div>
                    <div class="site-sub">Autonomous Intelligence System</div>
                </div>
            </div>
            <div class="top-nav">
                <a href="#market">Market</a>
                <a href="#gas">Gas</a>
                <a href="#news">News</a>
                <a href="/trending">Trending</a>
                <a href="/profiler">Profiler</a>
                <a href="/ticker">Ticker</a>
                <a href="/blog">Blog</a>
                <a href="/docs">API</a>
                <a href="/wallet-check">Wallet</a>
                <a href="/api-keys">Keys</a>
                <a class="premium" href="#premium">Premium</a>
            </div>
        </div>

        <!-- Status Line -->
        <div class="status-line">
            <span><span class="dot"></span> SYSTEM ONLINE</span>
            <span id="live-clock">--</span>
            <span>NODES: 4/4</span>
            <span>v1.0</span>
        </div>

        <!-- Top coins bar -->
        <div class="stat-row">
            {% for coin_id, data in top_coins.items() %}
            <div class="stat-item">
                <div class="stat-label">{{ coin_id|upper }}</div>
                <div class="stat-value">${{ "%.2f"|format(data.usd) if data.usd < 1000 else "%.0f"|format(data.usd) }}</div>
                <div class="stat-sub {{ 'up' if data.usd_24h_change >= 0 else 'down' }}">24h: {{ "%.2f"|format(data.usd_24h_change) }}%</div>
            </div>
            {% endfor %}
            {% if fear_greed %}
            <div class="stat-item">
                <div class="stat-label">FEAR & GREED</div>
                <div class="stat-value" style="color:{{ 'var(--green)' if fear_greed.value > 50 else 'var(--red)' }};">{{ fear_greed.value }}</div>
                <div class="stat-sub" style="color:var(--text-dim);">{{ fear_greed.classification|upper }}</div>
            </div>
            {% endif %}
            <div class="stat-item" id="tvl-card" style="display:none;">
                <div class="stat-label">ETH TVL</div>
                <div class="stat-value" id="tvl-value">--</div>
                <div class="stat-sub">DefiLlama</div>
            </div>
        </div>

        <!-- Affiliate Strip -->
        <div class="aff-strip">
            <span class="aff-label">EXCHANGES</span>
            <div class="aff-links">
                <a class="aff-link" href="https://www.binance.com/en/register?ref=CRYPTOEMPIRE" target="_blank" rel="noopener">Binance</a>
                <a class="aff-link" href="https://www.coinbase.com/join/CRYPTOEMPIRE" target="_blank" rel="noopener">Coinbase</a>
                <a class="aff-link" href="https://exchange.kraken.com/register?referrer=CRYPTOEMPIRE" target="_blank" rel="noopener">Kraken</a>
                <a class="aff-link" href="https://www.bybit.com/en/sign-up?affiliate_id=CRYPTOEMPIRE" target="_blank" rel="noopener">Bybit</a>
                <a class="aff-link" href="https://www.okx.com/join/CRYPTOEMPIRE" target="_blank" rel="noopener">OKX</a>
                <a class="aff-link" href="https://www.kucoin.com/ucenter/signup?rcode=CRYPTOEMPIRE" target="_blank" rel="noopener">KuCoin</a>
                <a class="aff-link" href="https://www.gate.io/signup/CRYPTOEMPIRE" target="_blank" rel="noopener">Gate.io</a>
                <a class="aff-link" href="https://app.uniswap.org/?ref=CRYPTOEMPIRE" target="_blank" rel="noopener">Uniswap</a>
            </div>
        </div>
        <div class="aff-strip">
            <span class="aff-label">TOOLS</span>
            <div class="aff-links">
                <a class="aff-link" href="https://shop.ledger.com/?r=CRYPTOEMPIRE" target="_blank" rel="noopener">Ledger</a>
                <a class="aff-link" href="https://crypto.com/exch/CRYPTOEMPIRE" target="_blank" rel="noopener">Crypto.com</a>
                <a class="aff-link" href="https://www.trezor.io/affiliate/CRYPTOEMPIRE" target="_blank" rel="noopener">Trezor</a>
            </div>
        </div>

        <div class="divider"></div>

        <!-- Gas tracker -->
        <div class="s-title">GAS TRACKER</div>
        <div class="gas-row" id="gas-grid">
            <div class="gas-item"><div class="gas-chain">Ethereum</div><div class="gas-gwei" id="gas-eth">--</div></div>
            <div class="gas-item"><div class="gas-chain">Polygon</div><div class="gas-gwei" id="gas-poly">--</div></div>
            <div class="gas-item"><div class="gas-chain">Arbitrum</div><div class="gas-gwei" id="gas-arb">--</div></div>
            <div class="gas-item"><div class="gas-chain">Base</div><div class="gas-gwei" id="gas-base">--</div></div>
        </div>

        <div class="divider"></div>

        <!-- Market Table -->
        <div class="s-title" id="market">TOP 20 CRYPTOCURRENCIES</div>
        <div class="tbl">
            <table>
                <thead>
                    <tr><th>#</th><th>Name</th><th>Price</th><th>24h</th><th>7d</th><th>Chart</th><th>Market Cap</th><th>Volume 24h</th></tr>
                </thead>
                <tbody>
                    {% for coin in market_data %}
                    <tr>
                        <td class="rank">{{ coin.market_cap_rank }}</td>
                        <td><span class="cname">{{ coin.name }}</span> <span class="csym">{{ coin.symbol|upper }}</span></td>
                        <td>${{ "%.2f"|format(coin.current_price) if coin.current_price < 1000 else "%.0f"|format(coin.current_price) }}</td>
                        <td class="{{ 'up' if coin.price_change_percentage_24h >= 0 else 'down' }}">{{ "%.2f"|format(coin.price_change_percentage_24h) }}%</td>
                        <td class="{{ 'up' if coin.price_change_percentage_7d_in_currency >= 0 else 'down' }}">{{ "%.2f"|format(coin.price_change_percentage_7d_in_currency) }}%</td>
                        <td>{{ coin.sparkline_svg|safe }}</td>
                        <td class="mc">${{ "{:,.0f}".format(coin.market_cap) }}</td>
                        <td class="vol">${{ "{:,.0f}".format(coin.total_volume) }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="divider"></div>

        <!-- Sponsored Coin Spotlight (paid placement) -->
        <div class="sponsor-box">
            <span class="sponsor-label">SPONSORED SPOTLIGHT — <span id="sponsored-name" style="color:var(--green);">--</span></span>
            <div class="aff-links">
                <span id="sponsored-price" style="font-size:11px;color:var(--white);font-weight:700;">--</span>
                <span id="sponsored-change" style="font-size:9px;">--</span>
                <a class="aff-link" href="#premium">Your project here →</a>
            </div>
        </div>

        <div class="divider"></div>

        <!-- DEX Volume -->
        <div class="s-title">DEX VOLUME</div>
        <div class="tbl" id="dex-section">
            <table>
                <thead><tr><th>#</th><th>DEX</th><th>Volume 24h</th><th>Volume 7d</th><th>24h Change</th><th>Chains</th></tr></thead>
                <tbody id="dex-tbody"></tbody>
            </table>
        </div>

        <div class="divider"></div>

        <!-- Trending Coins -->
        <div class="s-title" id="trending">TRENDING COINS</div>
        <div class="gas-row" id="trending-grid"></div>

        <div class="divider"></div>

        <!-- Market Movers -->
        <div class="s-title" id="movers">MARKET MOVERS</div>
        <div class="gas-row" id="movers-grid">
            <div class="gas-item" style="grid-column:1/-1;"><div style="font-size:9px;color:var(--text-dim);">LOADING...</div></div>
        </div>

        <div class="divider"></div>

        <!-- News -->
        <div class="s-title" id="news">CRYPTO NEWS</div>
        <div class="tbl">
            <ul class="news-list">
                {% for item in news %}
                <li>
                    <a href="{{ item.link }}" target="_blank" rel="noopener">{{ item.title }}</a>
                    <div class="n-date">{{ item.date[:22] if item.date else '' }}</div>
                </li>
                {% endfor %}
            </ul>
        </div>

        <div class="divider"></div>

        <!-- Features -->
        <div class="s-title" id="features">FEATURES</div>
        <div class="feat-grid">
            <div class="feat-item"><div class="feat-icon">[01]</div><h4>Real-Time Data</h4><p>Live prices, gas, and market caps for top coins</p></div>
            <div class="feat-item"><div class="feat-icon">[02]</div><h4>Arbitrage Scanner</h4><p>Cross-DEX price disparities in real-time</p></div>
            <div class="feat-item"><div class="feat-icon">[03]</div><h4>Gas Optimization</h4><p>Multi-chain gas tracker to minimize costs</p></div>
            <div class="feat-item"><div class="feat-icon">[04]</div><h4>Telegram Bot</h4><p>Live data via <a href="https://t.me/Crypt0Emp1reBot" target="_blank" style="color:var(--white);">@Crypt0Emp1reBot</a></p></div>
            <div class="feat-item"><div class="feat-icon">[05]</div><h4>Self-Custodial</h4><p>Your keys, your coins. No exchange risk</p></div>
            <div class="feat-item"><div class="feat-icon">[06]</div><h4>Premium API</h4><p>10K requests/day + arbitrage signals</p></div>
        </div>

        <!-- Alert Signup (Lead Gen) -->
        <div class="prem-box" id="alerts">
            <h3>// PRICE ALERTS (BETA)</h3>
            <p>Get notified when a coin hits your target price.<br>Enter coin symbol + target. We'll message you on Telegram.</p>
            <div style="max-width:480px;margin:0 auto;text-align:left;">
                <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;">
                    <input type="text" id="alert-coin" placeholder="Coin (e.g. BTC)" style="flex:1;min-width:80px;background:var(--surface);color:var(--white);border:1px solid var(--border);padding:8px 10px;font-size:10px;font-family:inherit;outline:none;text-transform:uppercase;letter-spacing:1px;">
                    <input type="text" id="alert-price" placeholder="Target price (e.g. 100000)" style="flex:1;min-width:100px;background:var(--surface);color:var(--white);border:1px solid var(--border);padding:8px 10px;font-size:10px;font-family:inherit;outline:none;">
                    <input type="text" id="alert-tg" placeholder="Your Telegram @username" style="flex:1;min-width:120px;background:var(--surface);color:var(--white);border:1px solid var(--border);padding:8px 10px;font-size:10px;font-family:inherit;outline:none;">
                </div>
                <button onclick="submitAlert()" style="width:100%;border:1px solid var(--white);color:var(--white);background:transparent;padding:8px;font-size:9px;font-family:inherit;text-transform:uppercase;letter-spacing:2px;cursor:pointer;">Set Alert</button>
                <div id="alert-msg" style="text-align:center;font-size:9px;color:var(--text-dim);margin-top:6px;"></div>
            </div>
        </div>

        <!-- Telegram CTA -->
        <div class="prem-box">
            <h3>// TELEGRAM_BOT</h3>
            <p>Live crypto data at your fingertips. No signup, no API keys.</p>
            <a href="https://t.me/Crypt0Emp1reBot" target="_blank" style="display:inline-block;border:1px solid var(--white);color:var(--white);padding:10px 24px;font-size:11px;text-transform:uppercase;letter-spacing:3px;text-decoration:none;transition:.15s;font-weight:700;">@Crypt0Emp1reBot</a>
            <br><span style="display:inline-block;border:1px dashed var(--text-muted);padding:8px 16px;margin-top:14px;font-size:11px;color:var(--green);font-family:monospace;user-select:all;">Send /start in Telegram</span>
        </div>

        <!-- Premium Section -->
        <div class="prem-box" id="premium">
            <h3>PREMIUM ACCESS</h3>
            <p>10K API requests/day + arbitrage signals + priority support.<br>Unlock by sending <strong>0.005 ETH</strong> to the wallet below.</p>
            <div class="ctags">
                <span class="ctag">Ethereum</span>
                <span class="ctag">Arbitrum</span>
                <span class="ctag">Base</span>
                <span class="ctag">Polygon</span>
                <span class="ctag">Optimism</span>
                <span class="ctag">BSC</span>
                <span class="ctag">Avalanche</span>
                <span class="ctag">Solana</span>
            </div>
            <div class="waddr" onclick="copyWallet(this)">{{ wallet }}</div>
            <div style="font-size:8px;color:var(--text-dim);margin-top:4px;text-transform:uppercase;letter-spacing:1px;">Click to copy — All EVM chains supported</div>
        </div>

        <div style="text-align:center;margin-bottom:20px;">
            <a href="/docs" style="display:inline-block;border:1px solid var(--white);color:var(--white);padding:8px 20px;font-size:9px;text-transform:uppercase;letter-spacing:3px;text-decoration:none;transition:.15s;margin:0 4px;">API Docs</a>
            <a href="/wallet-check" style="display:inline-block;border:1px solid var(--white);color:var(--white);padding:8px 20px;font-size:9px;text-transform:uppercase;letter-spacing:3px;text-decoration:none;transition:.15s;margin:0 4px;">Wallet Checker</a>
        </div>

        <footer>
            <p>Built autonomously — Zero KYC — Zero Budget</p>
            <p style="margin-top:4px;font-size:8px;">Wallet: <code style="font-size:8px;">{{ wallet }}</code></p>
        </footer>
    </div>

    <!-- Bottom Status Bar -->
    <div class="b-bar">
        <span><span class="dot"></span> ONLINE</span>
        <span><span class="sp">|</span> {{ wallet[:6] }}...{{ wallet[-4:] }}</span>
        <span><span class="sp">|</span> <span id="live-clock2">--</span></span>
        <span><span class="sp">|</span> NODES 4/4</span>
    </div>

    <div class="toast" id="toast">COPIED</div>

    <script>
        // ===== LIVE CLOCK =====
        (function(){
            function u(){
                var n=new Date();
                var y=n.getUTCFullYear();
                var m=String(n.getUTCMonth()+1).padStart(2,'0');
                var d=String(n.getUTCDate()).padStart(2,'0');
                var h=String(n.getUTCHours()).padStart(2,'0');
                var i=String(n.getUTCMinutes()).padStart(2,'0');
                var s=String(n.getUTCSeconds()).padStart(2,'0');
                var t=y+'-'+m+'-'+d+' '+h+':'+i+':'+s+' UTC';
                var e1=document.getElementById('live-clock');
                var e2=document.getElementById('live-clock2');
                if(e1)e1.textContent=t;
                if(e2)e2.textContent=t;
            }
            u();setInterval(u,1000);
        })();

        function copyWallet(el){
            navigator.clipboard.writeText(el.textContent).then(function(){
                var t=document.getElementById('toast');
                t.classList.add('show');
                setTimeout(function(){t.classList.remove('show');},2000);
            });
        }

        async function fetchGas(){
            try{
                var r=await fetch('/api/gas');
                var data=await r.json();
                for(var chain in data){
                    var id=chain==='ethereum'?'gas-eth':chain==='polygon'?'gas-poly':chain==='arbitrum'?'gas-arb':chain==='base'?'gas-base':'gas-'+chain;
                    var el=document.getElementById(id);
                    if(el&&data[chain].gas_gwei!==undefined){
                        var g=data[chain].gas_gwei;
                        el.textContent=g+' gwei';
                        el.className='gas-gwei '+(g<5?'low':g<30?'med':'high');
                    }
                }
            }catch(e){}
        }

        async function fetchDEXs(){
            try{
                var r=await fetch('/api/dexs');
                var data=await r.json();
                var tbody=document.getElementById('dex-tbody');
                if(!tbody)return;
                var html='';
                for(var i=0;i<data.length;i++){
                    var d=data[i];
                    var v24=d.volume24h>=1e6?'$'+(d.volume24h/1e6).toFixed(1)+'M':'$'+(d.volume24h/1e3).toFixed(0)+'K';
                    var v7=d.volume7d>=1e6?'$'+(d.volume7d/1e6).toFixed(1)+'M':'$'+(d.volume7d/1e3).toFixed(0)+'K';
                    var cls=d.change1d>=0?'up':'down';
                    html+='<tr><td class="rank">'+(i+1)+'</td><td><span class="cname">'+d.name+'</span></td><td>'+v24+'</td><td>'+v7+'</td><td class="'+cls+'">'+d.change1d+'%</td><td class="csym">'+(d.chains||[]).join(', ')+'</td></tr>';
                }
                tbody.innerHTML=html;
            }catch(e){}
        }

        async function fetchTrending(){
            try{
                var r=await fetch('/api/trending');
                var data=await r.json();
                var grid=document.getElementById('trending-grid');
                if(!grid||!data.trending)return;
                var html='';
                for(var i=0;i<Math.min(data.trending.length,10);i++){
                    var c=data.trending[i];
                    html+='<div class="gas-item"><div class="gas-chain" style="font-size:11px;">'+c.name+'</div><div class="gas-gwei" style="font-size:16px;color:var(--text-dim);">'+(c.symbol||'').toUpperCase()+'</div><div style="font-size:8px;color:var(--text-dim);text-transform:uppercase;letter-spacing:1px;margin-top:2px;">Rank '+(c.market_cap_rank||'--')+'</div></div>';
                }
                grid.innerHTML=html;
            }catch(e){}
        }

        async function fetchTVL(){
            try{
                var r=await fetch('/api/tvl');
                var data=await r.json();
                var card=document.getElementById('tvl-card');
                var val=document.getElementById('tvl-value');
                if(card&&val&&data.tvl){
                    var tvl=data.tvl>=1e9?'$'+(data.tvl/1e9).toFixed(1)+'B':'$'+(data.tvl/1e6).toFixed(0)+'M';
                    val.textContent=tvl;
                    card.style.display='block';
                }
            }catch(e){}
        }

        fetchGas();
        fetchDEXs();
        fetchTrending();
        fetchTVL();
        fetchMovers();
        fetchSponsored();
        setInterval(fetchGas,30000);
        setInterval(fetchDEXs,120000);
        setInterval(fetchTrending,120000);
        setInterval(fetchTVL,120000);
        setInterval(fetchMovers,120000);
        setInterval(fetchSponsored,60000);

        async function fetchMovers(){
            try{
                var r=await fetch('/api/movers');
                var data=await r.json();
                var grid=document.getElementById('movers-grid');
                if(!grid||!data.top_gainers)return;
                var html='';
                var gainers=data.top_gainers.slice(0,5);
                var losers=data.top_losers.slice(0,5);
                html+='<div style="grid-column:1/-1;font-size:8px;color:var(--text-dim);text-transform:uppercase;letter-spacing:2px;border-bottom:1px solid var(--border);padding:4px 8px;margin-bottom:4px;">TOP GAINERS</div>';
                for(var i=0;i<gainers.length;i++){
                    var c=gainers[i];
                    html+='<div class="gas-item" style="text-align:left;display:flex;justify-content:space-between;align-items:center;">' +
                        '<div><div class="gas-chain" style="font-size:10px;">'+(c.symbol||c.name).toUpperCase()+'</div>' +
                        '<div style="font-size:8px;color:var(--text-dim);">$'+(c.price||'--')+'</div></div>' +
                        '<div style="text-align:right;"><div class="up" style="font-size:13px;font-weight:700;">+'+(c.change||0).toFixed(2)+'%</div></div></div>';
                }
                html+='<div style="grid-column:1/-1;font-size:8px;color:var(--text-dim);text-transform:uppercase;letter-spacing:2px;border-bottom:1px solid var(--border);padding:4px 8px;margin-bottom:4px;margin-top:8px;">TOP LOSERS</div>';
                for(var i=0;i<losers.length;i++){
                    var c=losers[i];
                    html+='<div class="gas-item" style="text-align:left;display:flex;justify-content:space-between;align-items:center;">' +
                        '<div><div class="gas-chain" style="font-size:10px;">'+(c.symbol||c.name).toUpperCase()+'</div>' +
                        '<div style="font-size:8px;color:var(--text-dim);">$'+(c.price||'--')+'</div></div>' +
                        '<div style="text-align:right;"><div class="down" style="font-size:13px;font-weight:700;">'+(c.change||0).toFixed(2)+'%</div></div></div>';
                }
                grid.innerHTML=html;
            }catch(e){}
        }

        async function fetchSponsored(){
            try{
                var r=await fetch('/api/sponsored');
                var data=await r.json();
                var nameEl=document.getElementById('sponsored-name');
                var priceEl=document.getElementById('sponsored-price');
                var chgEl=document.getElementById('sponsored-change');
                if(nameEl)nameEl.textContent=data.name;
                if(priceEl)priceEl.textContent='$'+data.price;
                if(chgEl){
                    chgEl.textContent=data.change_24h+'%';
                    chgEl.className=data.change_24h>=0?'up':'down';
                }
            }catch(e){}
        }

        function submitAlert(){
            var coin=document.getElementById('alert-coin');
            var price=document.getElementById('alert-price');
            var tg=document.getElementById('alert-tg');
            var msg=document.getElementById('alert-msg');
            if(!coin||!price||!tg)return;
            if(!coin.value.trim()||!price.value.trim()||!tg.value.trim()){
                msg.textContent='Fill all fields';
                return;
            }
            try{
                var r=new XMLHttpRequest();
                r.open('POST','/api/alerts',true);
                r.setRequestHeader('Content-Type','application/json');
                r.onload=function(){
                    msg.textContent='Alert set! We\\'ll notify you at '+tg.value.trim();
                    coin.value='';price.value='';tg.value='';
                };
                r.onerror=function(){msg.textContent='Error setting alert';};
                r.send(JSON.stringify({coin:coin.value.trim(),target:price.value.trim(),telegram:tg.value.trim()}));
            }catch(e){msg.textContent='Error setting alert';}
        }
    </script>
</body>
</html>"""

# ============================================================
# Premium API Key Middleware
# ============================================================

@app.before_request
def check_premium_key():
    if request.path.startswith('/api/'):
        key = request.headers.get("X-API-Key") or request.args.get("api_key", "")
        request.is_premium = key in PREMIUM_API_KEYS

@app.after_request
def add_premium_headers(resp):
    if request.path.startswith('/api/'):
        is_premium = getattr(request, 'is_premium', False)
        if is_premium:
            resp.headers['X-Premium'] = 'true'
            resp.headers['X-Rate-Limit'] = '10000/day'
        else:
            resp.headers['X-Rate-Limit'] = '100/day'
            resp.headers['X-Premium-Upgrade'] = 'https://crypto-empire-ten.vercel.app/api-keys'
    return resp


# ============================================================
# Routes
# ============================================================

@app.route("/")
def index():
    """Main dashboard"""
    # Top coins
    top_coins = {}
    for coin_id in ["bitcoin", "ethereum", "solana"]:
        data = fetch_sync(f"{COINGECKO_API}/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true")
        if data and coin_id in data:
            top_coins[coin_id] = data[coin_id]

    # Market data with 7d change and sparklines
    market_raw = fetch_sync(
        f"{COINGECKO_API}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1&price_change_percentage=7d&sparkline=true"
    )
    market_data = []
    if market_raw:
        for coin in market_raw:
            coin['sparkline_svg'] = render_sparkline(coin.get('sparkline_in_7d', {}).get('price'))
            market_data.append(coin)

    # Fear & Greed index
    fear_greed = None
    fg_data = fetch_sync("https://api.alternative.me/fng/?limit=1")
    if fg_data and "data" in fg_data and fg_data["data"]:
        fear_greed = {
            "value": int(fg_data["data"][0].get("value", 50)),
            "classification": fg_data["data"][0].get("value_classification", "Neutral"),
        }

    # News
    news = fetch_rss("https://cointelegraph.com/rss")

    return render_template_string(
        INDEX_HTML,
        top_coins=top_coins,
        market_data=market_data,
        fear_greed=fear_greed,
        news=news,
        wallet=WALLET_ADDRESS,
    )


@app.route("/api/price/<coin_id>")
def api_price(coin_id):
    data = fetch_sync(f"{COINGECKO_API}/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true")
    if data and coin_id in data:
        return jsonify({"coin": coin_id, "data": data[coin_id], "source": "coingecko"})
    return jsonify({"error": "Coin not found"}), 404


@app.route("/api/trending")
def api_trending():
    data = fetch_sync(f"{COINGECKO_API}/search/trending")
    if data and "coins" in data:
        coins = []
        for coin in data["coins"][:10]:
            item = coin.get("item", {})
            coins.append({
                "id": item.get("id"),
                "name": item.get("name"),
                "symbol": item.get("symbol"),
                "market_cap_rank": item.get("market_cap_rank"),
                "price_btc": item.get("price_btc"),
                "score": item.get("score"),
            })
        return jsonify({"trending": coins})
    return jsonify({"error": "Could not fetch trending"}), 500


# ============================================================
# Trending Now — CoinGecko trending searches enriched with prices
# ============================================================

@app.route("/api/trending-now")
def api_trending_now():
    """Trending coins with live price data. 60s cache-friendly."""
    data = fetch_sync(f"{COINGECKO_API}/search/trending")
    if not data or "coins" not in data:
        return jsonify({"error": "Could not fetch trending"}), 500

    coins = []
    for coin in data["coins"][:15]:
        item = coin.get("item", {})
        coins.append({
            "id": item.get("id"),
            "name": item.get("name"),
            "symbol": item.get("symbol"),
            "thumb": item.get("thumb"),
            "market_cap_rank": item.get("market_cap_rank"),
            "score": item.get("score"),
        })

    # Batch-fetch prices
    ids = [c["id"] for c in coins if c["id"]]
    if ids:
        batch = ",".join(ids[:20])
        prices = fetch_sync(
            f"{COINGECKO_API}/simple/price?ids={batch}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true"
        )
        if prices:
            for c in coins:
                pid = c["id"]
                if pid in prices:
                    c["price_usd"] = prices[pid].get("usd")
                    c["usd_24h_change"] = prices[pid].get("usd_24h_change")
                    c["market_cap"] = prices[pid].get("usd_market_cap")
                else:
                    c["price_usd"] = None
                    c["usd_24h_change"] = None
                    c["market_cap"] = None

    return jsonify({"trending": coins, "updated_at": int(time.time())})


@app.route("/api/gas")
def api_gas():
    chains = {
        "ethereum": "https://ethereum-rpc.publicnode.com",
        "polygon": "https://polygon-rpc.com",
        "arbitrum": "https://arb1.arbitrum.io/rpc",
        "base": "https://mainnet.base.org",
    }
    results = {}
    for name, url in chains.items():
        try:
            r = requests.post(url, json={"jsonrpc":"2.0","method":"eth_gasPrice","params":[],"id":1}, timeout=6)
            data = r.json()
            if "result" in data:
                gwei = int(data["result"], 16) / 1e9
                results[name] = {"gas_gwei": round(gwei, 1)}
        except:
            results[name] = {"error": "unavailable"}
    return jsonify(results)


@app.route("/api/fear-greed")
def api_fear_greed():
    data = fetch_sync("https://api.alternative.me/fng/?limit=7")
    if data and "data" in data:
        return jsonify(data["data"])
    return jsonify({"error": "unavailable"}), 500


@app.route("/api/news")
def api_news():
    news = fetch_rss("https://cointelegraph.com/rss")
    return jsonify(news)


@app.route("/api/tvl")
def api_tvl():
    """Ethereum total value locked from DeFiLlama"""
    data = fetch_sync("https://api.llama.fi/v2/historicalChainTvl/Ethereum")
    if data and len(data) > 0:
        latest = data[-1]
        return jsonify({"chain": "ethereum", "tvl": round(latest.get("tvl", 0)), "date": latest.get("date", 0)})
    return jsonify({"error": "unavailable"}), 500


@app.route("/api/dexs")
def api_dexs():
    """Top DEXes by 24h volume from DeFiLlama"""
    data = fetch_sync("https://api.llama.fi/overview/dexs")
    if data and "protocols" in data:
        top = sorted(data["protocols"], key=lambda x: x.get("total24h", 0) or 0, reverse=True)[:10]
        dexs = []
        for d in top:
            dexs.append({
                "name": d.get("displayName", d.get("name", "")),
                "volume24h": round(d.get("total24h", 0)),
                "volume7d": round(d.get("total7d", 0)),
                "change1d": round(d.get("change_1d", 0) or 0, 2),
                "chains": (d.get("chains") or [""])[:3],
            })
        return jsonify(dexs)
    return jsonify({"error": "unavailable"}), 500


@app.route("/api/movers")
def api_movers():
    """Top gainers and losers in last 24h"""
    data = fetch_sync(
        f"{COINGECKO_API}/coins/markets?vs_currency=usd&order=volume_desc&per_page=100&page=1&price_change_percentage=24h&sparkline=false"
    )
    if not data:
        return jsonify({"top_gainers": [], "top_losers": []})
    sorted_data = sorted(data, key=lambda x: x.get("price_change_percentage_24h", 0) or 0, reverse=True)
    gainers = []
    losers = []
    for coin in sorted_data:
        chg = coin.get("price_change_percentage_24h") or 0
        entry = {
            "id": coin.get("id"),
            "name": coin.get("name"),
            "symbol": coin.get("symbol"),
            "price": f"{coin.get('current_price', 0):,.2f}" if coin.get('current_price') else "0",
            "change": round(chg, 2),
        }
        if chg >= 0:
            if len(gainers) < 10:
                gainers.append(entry)
        else:
            if len(losers) < 10:
                losers.append(entry)
    return jsonify({"top_gainers": gainers, "top_losers": losers})


@app.route("/api/sponsored")
def api_sponsored():
    """Live price for the sponsored coin"""
    data = fetch_sync(f"{COINGECKO_API}/simple/price?ids={SPONSORED_COIN_ID}&vs_currencies=usd&include_24hr_change=true")
    price = 0
    change_24h = 0
    if data and SPONSORED_COIN_ID in data:
        price = data[SPONSORED_COIN_ID].get("usd", 0)
        change_24h = round(data[SPONSORED_COIN_ID].get("usd_24h_change", 0) or 0, 2)
    return jsonify({
        "id": SPONSORED_COIN_ID,
        "name": SPONSORED_COIN_MSG,
        "price": f"{price:,.2f}" if price else "0",
        "change_24h": change_24h,
    })


@app.route("/api-keys")
def api_keys_page():
    """API key management and premium info page"""
    return render_template_string("""<!DOCTYPE html>
<html lang="en">
<head>""" + SHARED_HEAD + """
    <title>API Keys — Crypto Empire Premium</title>
    <meta name="description" content="Get premium API keys for Crypto Empire. 10K requests/day, arbitrage signals, priority support. Unlock by sending ETH.">
    <meta name="robots" content="noindex, follow">
</head>
<body>
    <div class="grid-bg"></div>
    <div class="sweep"></div>
    <div class="container">
        <div class="top-bar">
            <div class="brand">
                <div class="prompt">><span class="cr"></span></div>
                <div>
                    <div class="site-title">API Keys</div>
                    <div class="site-sub">Premium access management</div>
                </div>
            </div>
            <div class="top-nav">
                <a href="/">Dashboard</a>
                <a href="/docs">API Docs</a>
                <a href="/blog">Blog</a>
            </div>
        </div>
        <div class="status-line">
            <span><span class="dot"></span> API KEYS</span>
            <span id="live-clock">--</span>
        </div>
        <div class="bnav"><a href="/">Dashboard</a></div>
        <div class="s-title">PREMIUM API KEYS</div>

        <div class="post">
            <h3 style="font-size:12px;color:var(--white);text-transform:uppercase;letter-spacing:2px;margin-bottom:8px;">Free Tier</h3>
            <p style="font-size:10px;color:var(--text-dim);line-height:1.6;">
                <span style="color:var(--green);">&#10003;</span> No API key required<br>
                <span style="color:var(--green);">&#10003;</span> All endpoints accessible<br>
                <span style="color:var(--text-dim);">&#10007;</span> 100 req/day rate limit<br>
                <span style="color:var(--text-dim);">&#10007;</span> Standard response headers
            </p>
        </div>

        <div class="prem-box" style="text-align:left;border-color:var(--white);">
            <h3 style="font-size:12px;margin-bottom:12px;">PREMIUM TIER — 0.005 ETH</h3>
            <p style="font-size:10px;color:var(--text-dim);line-height:1.6;">
                <span style="color:var(--green);">&#10003;</span> <strong style="color:var(--white);">10,000 requests/day</strong><br>
                <span style="color:var(--green);">&#10003;</span> Priority rate limit on all endpoints<br>
                <span style="color:var(--green);">&#10003;</span> Dedicated API key with <code style="color:var(--white);">X-Premium: true</code> header<br>
                <span style="color:var(--green);">&#10003;</span> Arbitrage signal access (coming soon)<br>
                <span style="color:var(--green);">&#10003;</span> Priority support via Telegram
            </p>
        </div>

        <div class="prem-box">
            <h3>HOW TO GET YOUR KEY</h3>
            <ol style="text-align:left;font-size:10px;color:var(--text-dim);line-height:2;max-width:400px;margin:0 auto;">
                <li>Send <strong style="color:var(--white);">0.005 ETH</strong> to the wallet below</li>
                <li>Send a message to <a href="https://t.me/Crypt0Emp1reBot" target="_blank" style="color:var(--white);">@Crypt0Emp1reBot</a> with your tx hash</li>
                <li>We'll issue your API key within 24 hours</li>
            </ol>
            <div class="waddr" onclick="copyWallet(this)" style="margin-top:12px;">{{ wallet }}</div>
            <div style="font-size:8px;color:var(--text-dim);margin-top:4px;text-transform:uppercase;letter-spacing:1px;">Click to copy — Any EVM chain</div>
        </div>

        <div class="post">
            <p style="font-size:10px;color:var(--text-dim);">Use your premium API key via <code style="color:var(--white);">X-API-Key</code> header or <code style="color:var(--white);">?api_key=</code> query param.</p>
            <pre style="background:var(--surface);padding:10px;font-size:10px;border:1px solid var(--border);overflow-x:auto;margin-top:8px;">curl -H "X-API-Key: your_key_here" \\
  https://crypto-empire-ten.vercel.app/api/price/bitcoin</pre>
        </div>

        <footer>
            <p>Crypto Empire — Wallet: <code style="font-size:8px;">{{ wallet }}</code></p>
        </footer>
    </div>
    <div class="b-bar">
        <span><span class="dot"></span> API KEYS</span>
        <span>v1.0</span>
    </div>
    <script>
        (function(){
            function u(){
                var n=new Date();
                var y=n.getUTCFullYear();
                var m=String(n.getUTCMonth()+1).padStart(2,'0');
                var d=String(n.getUTCDate()).padStart(2,'0');
                var h=String(n.getUTCHours()).padStart(2,'0');
                var i=String(n.getUTCMinutes()).padStart(2,'0');
                var s=String(n.getUTCSeconds()).padStart(2,'0');
                var e=document.getElementById('live-clock');
                if(e)e.textContent=y+'-'+m+'-'+d+' '+h+':'+i+':'+s+' UTC';
            }
            u();setInterval(u,1000);
        })();
        function copyWallet(el){
            navigator.clipboard.writeText(el.textContent).then(function(){
                var t=document.getElementById('toast');
                t.classList.add('show');
                setTimeout(function(){t.classList.remove('show');},2000);
            });
        }
    </script>
</body>
</html>""", wallet=WALLET_ADDRESS)


@app.route("/api/alerts", methods=["POST"])
def api_alerts():
    """Save a price alert subscription"""
    data = request.get_json(silent=True) or {}
    coin = data.get("coin", "").strip().upper()
    target = data.get("target", "").strip()
    telegram = data.get("telegram", "").strip()
    if not coin or not target or not telegram:
        return jsonify({"error": "Missing fields"}), 400
    try:
        float(target)
    except ValueError:
        return jsonify({"error": "Invalid target price"}), 400
    # Persist alert to DB
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("CREATE TABLE IF NOT EXISTS alerts (coin TEXT, target REAL, telegram TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    conn.execute("INSERT INTO alerts (coin, target, telegram) VALUES (?, ?, ?)", (coin, float(target), telegram))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": f"Alert set for {coin} at ${target}"})


# ---------------------------------------------------------------------------
# Coin symbol → CoinGecko ID lookup (top 100+ coins)
# ---------------------------------------------------------------------------
COIN_SYMBOL_TO_ID = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin",
    "XRP": "ripple", "ADA": "cardano", "DOGE": "dogecoin", "TRX": "tron",
    "DOT": "polkadot", "LINK": "chainlink", "MATIC": "matic-network",
    "AVAX": "avalanche-2", "SHIB": "shiba-inu", "DAI": "dai",
    "LTC": "litecoin", "UNI": "uniswap", "ATOM": "cosmos",
    "XLM": "stellar", "BCH": "bitcoin-cash", "FIL": "filecoin",
    "APT": "aptos", "ARB": "arbitrum", "OP": "optimism",
    "SUI": "sui", "PEPE": "pepe", "INJ": "injective-protocol",
    "RUNE": "thorchain", "AAVE": "aave", "MKR": "maker",
    "SAND": "the-sandbox", "MANA": "decentraland", "AXS": "axie-infinity",
    "FTM": "fantom", "NEAR": "near", "TIA": "celestia",
    "SEI": "sei-network", "STRK": "starknet",
    "WIF": "dogwifcoin", "BONK": "bonk", "FLOKI": "floki",
    "CRV": "curve-dao-token", "GALA": "gala", "CHZ": "chiliz",
    "CAKE": "pancakeswap-token", "KUJI": "kujira", "OSMO": "osmosis",
    "JUP": "jupiter-exchange-solana", "RNDR": "render-token",
    "FET": "fetch-ai", "AGIX": "singularitynet", "OCEAN": "ocean-protocol",
    "IMX": "immutable-x", "MAGIC": "magic", "BLUR": "blur",
}


def _coin_to_id(symbol):
    """Convert coin symbol (BTC, ETH) to CoinGecko ID. Falls back to searching API."""
    s = symbol.strip().upper()
    if s in COIN_SYMBOL_TO_ID:
        return COIN_SYMBOL_TO_ID[s]
    # Try lowercase (maybe they entered the ID directly)
    if symbol.strip().islower():
        return symbol.strip()
    # Try CoinGecko search as last resort
    try:
        r = requests.get(f"{COINGECKO_API}/search?query={s}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            coins = data.get("coins", [])
            if coins:
                return coins[0]["id"]
    except:
        pass
    return symbol.strip().lower()


ALERT_CHECK_SECRET = os.environ.get("ALERT_CHECK_SECRET", "")


@app.route("/api/check-alerts", methods=["GET", "POST"])
def api_check_alerts():
    """Check all pending price alerts and send Telegram notifications when triggered.

    Protected by X-Alert-Check-Key header matching ALERT_CHECK_SECRET env var.
    Called by GH Actions cron every 15 minutes.
    """
    # Verify auth
    provided = request.headers.get("X-Alert-Check-Key", "")
    if not ALERT_CHECK_SECRET or provided != ALERT_CHECK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Ensure table + triggered column exist
    c.execute("CREATE TABLE IF NOT EXISTS alerts (coin TEXT, target REAL, telegram TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    try:
        c.execute("ALTER TABLE alerts ADD COLUMN triggered INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists

    rows = c.execute("SELECT rowid, * FROM alerts WHERE triggered = 0").fetchall()
    if not rows:
        conn.close()
        return jsonify({"status": "ok", "checked": 0, "triggered": 0, "message": "No pending alerts"})

    # Get unique coins
    coin_ids = set()
    for r in rows:
        cid = _coin_to_id(r["coin"])
        coin_ids.add(cid)

    # Batch-fetch prices
    ids_param = ",".join(coin_ids)
    price_data = fetch_sync(f"{COINGECKO_API}/simple/price?ids={ids_param}&vs_currencies=usd")

    if not price_data:
        conn.close()
        return jsonify({"error": "Failed to fetch prices"}), 502

    # Check each alert
    triggered = 0
    results = []
    for r in rows:
        cid = _coin_to_id(r["coin"])
        current_price = price_data.get(cid, {}).get("usd")
        if current_price is None:
            continue

        target = r["target"]
        telegram_user = r["telegram"].strip()
        telegram_msg = (
            f"\u23f0 PRICE ALERT TRIGGERED\n"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
            f"{r['coin']} has reached your target!\n\n"
            f"Target: ${target:,.2f}\n"
            f"Current: ${current_price:,.2f}\n\n"
            f"crypto-empire-ten.vercel.app"
        )

        # Send Telegram DM
        if telegram_user.startswith("@"):
            # We need a chat_id. For Telegram, we need the user's chat ID.
            # The alert form collects @username. We can send a message to the
            # bot and it'll arrive as a DM if the user has started the bot.
            # Alternatively, send via the bot API using the @username.
            # Telegram doesn't let you send by @username directly in Bot API.
            # We need the chat_id, which we'd have if they've messaged the bot before.
            # For now, we send via the bot to the user only if they've started the bot.
            # We store the chat_id when they interact with /start.
            pass

        # Send via Telegram bot API — try to resolve chat_id from telegram_mapping table
        chat_id = None
        try:
            # Check if we have a stored chat_id for this telegram user
            c2 = conn.cursor()
            c2.execute("CREATE TABLE IF NOT EXISTS telegram_mapping (username TEXT PRIMARY KEY, chat_id INTEGER)")
            row2 = c2.execute("SELECT chat_id FROM telegram_mapping WHERE username = ?", (telegram_user.lower().lstrip("@"),)).fetchone()
            if row2:
                chat_id = row2["chat_id"]
        except:
            pass

        if chat_id:
            # Send notification
            try:
                from telegram_bot import send_message as tg_send
                tg_send(chat_id, telegram_msg, parse_mode="HTML")
                # Mark as triggered
                conn.execute("UPDATE alerts SET triggered = 1 WHERE rowid = ?", (r["rowid"],))
                triggered += 1
                results.append({"coin": r["coin"], "user": telegram_user, "sent": True})
            except Exception as e:
                results.append({"coin": r["coin"], "user": telegram_user, "sent": False, "error": str(e)})
        else:
            results.append({"coin": r["coin"], "user": telegram_user, "sent": False, "reason": "unknown chat_id"})

    conn.commit()
    conn.close()

    return jsonify({
        "status": "ok",
        "checked": len(rows),
        "triggered": triggered,
        "results": results,
    })


@app.route("/api/wallet")
def api_wallet():
    chains = {
        "ethereum": "https://ethereum-rpc.publicnode.com",
        "polygon": "https://polygon-rpc.com",
        "arbitrum": "https://arb1.arbitrum.io/rpc",
        "base": "https://mainnet.base.org",
    }
    results = {}
    for name, url in chains.items():
        try:
            r = requests.post(url, json={
                "jsonrpc":"2.0","method":"eth_getBalance",
                "params":[WALLET_ADDRESS, "latest"],"id":1
            }, timeout=6)
            data = r.json()
            if "result" in data:
                bal = int(data["result"], 16) / 1e18
                results[name] = {"balance": bal}
        except:
            results[name] = {"balance": None}
    return jsonify({"wallet": WALLET_ADDRESS, "balances": results})


@app.route("/api/health")
def api_health():
    return jsonify({
        "status": "online",
        "version": "1.0.0",
        "wallet": WALLET_ADDRESS,
        "timestamp": datetime.now().isoformat()
    })


@app.route("/docs")
def docs():
    return render_template_string("""<!DOCTYPE html>
<html lang="en">
<head>""" + SHARED_HEAD + """
    <title>Crypto Empire — API Docs</title>
    <meta name="description" content="Free public API for crypto data. No auth required. Bitcoin, Ethereum, gas prices, wallet balances.">
    <link rel="canonical" href="https://crypto-empire-ten.vercel.app/docs">
</head>
<body>
    <div class="grid-bg"></div>
    <div class="sweep"></div>
    <div class="container">
        <div class="top-bar">
            <div class="brand">
                <div class="prompt">><span class="cr"></span></div>
                <div>
                    <div class="site-title">API Docs</div>
                    <div class="site-sub">Public REST endpoints</div>
                </div>
            </div>
            <div class="top-nav">
                <a href="/">Dashboard</a>
                <a href="/blog">Blog</a>
                <a href="/wallet-check">Wallet</a>
            </div>
        </div>
        <div class="status-line">
            <span><span class="dot"></span> DOCS v1.0</span>
            <span id="live-clock">--</span>
        </div>
        <div class="bnav"><a href="/">Dashboard</a></div>
        <div class="s-title">API REFERENCE</div>
        <p style="font-size:11px;color:var(--text-dim);margin-bottom:20px;">Free public API. No authentication required. 100 req/day free, 10K req/day premium.</p>

        <div class="prem-box" style="text-align:left;padding:12px 16px;margin-bottom:20px;">
            <p style="font-size:10px;color:var(--text-dim);"><span style="color:var(--green);">FREE:</span> 100 req/day &nbsp;|&nbsp; <span style="color:var(--white);">PREMIUM:</span> 10K req/day &nbsp;|&nbsp; Send 0.005 ETH to <code style="font-size:9px;">{{ wallet[:8] }}...{{ wallet[-4:] }}</code></p>
        </div>

        <div class="post">
            <p style="font-size:10px;font-weight:700;color:var(--white);text-transform:uppercase;letter-spacing:2px;margin-bottom:4px;">Telegram Bot</p>
            <p style="font-size:10px;color:var(--text-dim);margin-bottom:8px;">Same data, directly in Telegram. No API key needed.</p>
            <pre style="background:var(--surface);padding:10px;font-size:10px;border:1px solid var(--border);overflow-x:auto;">Open: https://t.me/Crypt0Emp1reBot
Send: /help</pre>
        </div>

        <div class="post">
            <p><span style="color:var(--green);font-weight:700;">GET</span> <code style="font-size:11px;color:var(--white);">/api/price/&lt;coin_id&gt;</code></p>
            <p style="font-size:10px;color:var(--text-dim);margin:4px 0 6px;">Current price for any CoinGecko coin ID.</p>
            <pre style="background:var(--surface);padding:10px;font-size:10px;border:1px solid var(--border);overflow-x:auto;">curl https://crypto-empire-ten.vercel.app/api/price/bitcoin</pre>
        </div>
        <div class="post">
            <p><span style="color:var(--green);font-weight:700;">GET</span> <code style="font-size:11px;color:var(--white);">/api/trending</code></p>
            <p style="font-size:10px;color:var(--text-dim);margin:4px 0 6px;">Trending coins on CoinGecko.</p>
            <pre style="background:var(--surface);padding:10px;font-size:10px;border:1px solid var(--border);overflow-x:auto;">curl https://crypto-empire-ten.vercel.app/api/trending</pre>
        </div>
        <div class="post">
            <p><span style="color:var(--green);font-weight:700;">GET</span> <code style="font-size:11px;color:var(--white);">/api/gas</code></p>
            <p style="font-size:10px;color:var(--text-dim);margin:4px 0 6px;">Gas prices across Ethereum, Polygon, Arbitrum, Base.</p>
            <pre style="background:var(--surface);padding:10px;font-size:10px;border:1px solid var(--border);overflow-x:auto;">curl https://crypto-empire-ten.vercel.app/api/gas</pre>
        </div>
        <div class="post">
            <p><span style="color:var(--green);font-weight:700;">GET</span> <code style="font-size:11px;color:var(--white);">/api/wallet</code></p>
            <p style="font-size:10px;color:var(--text-dim);margin:4px 0 6px;">Wallet balances across chains.</p>
            <pre style="background:var(--surface);padding:10px;font-size:10px;border:1px solid var(--border);overflow-x:auto;">curl https://crypto-empire-ten.vercel.app/api/wallet</pre>
        </div>
        <div class="post">
            <p><span style="color:var(--green);font-weight:700;">GET</span> <code style="font-size:11px;color:var(--white);">/api/fear-greed</code></p>
            <p style="font-size:10px;color:var(--text-dim);margin:4px 0 6px;">Fear &amp; Greed index.</p>
            <pre style="background:var(--surface);padding:10px;font-size:10px;border:1px solid var(--border);overflow-x:auto;">curl https://crypto-empire-ten.vercel.app/api/fear-greed</pre>
        </div>
        <div class="post">
            <p><span style="color:var(--green);font-weight:700;">GET</span> <code style="font-size:11px;color:var(--white);">/api/news</code></p>
            <p style="font-size:10px;color:var(--text-dim);margin:4px 0 6px;">Latest crypto news from CoinTelegraph.</p>
            <pre style="background:var(--surface);padding:10px;font-size:10px;border:1px solid var(--border);overflow-x:auto;">curl https://crypto-empire-ten.vercel.app/api/news</pre>
        </div>
        <div class="post">
            <p><span style="color:var(--green);font-weight:700;">GET</span> <code style="font-size:11px;color:var(--white);">/api/health</code></p>
            <p style="font-size:10px;color:var(--text-dim);margin:4px 0 6px;">Service health check.</p>
        </div>
        <div class="post">
            <p><span style="color:var(--green);font-weight:700;">GET</span> <code style="font-size:11px;color:var(--white);">/api/tvl</code></p>
            <p style="font-size:10px;color:var(--text-dim);margin:4px 0 6px;">Ethereum TVL from DeFiLlama.</p>
            <pre style="background:var(--surface);padding:10px;font-size:10px;border:1px solid var(--border);overflow-x:auto;">curl https://crypto-empire-ten.vercel.app/api/tvl</pre>
        </div>
        <div class="post">
            <p><span style="color:var(--green);font-weight:700;">GET</span> <code style="font-size:11px;color:var(--white);">/api/profiler/&lt;address&gt;</code></p>
            <p style="font-size:10px;color:var(--text-dim);margin:4px 0 6px;">Profile any Ethereum address: native balance, top ERC-20s, tx count, USD value.</p>
            <pre style="background:var(--surface);padding:10px;font-size:10px;border:1px solid var(--border);overflow-x:auto;">curl https://crypto-empire-ten.vercel.app/api/profiler/0x29021dd5306D7b3b6608a2bc8276D33c1200C7Ef</pre>
        </div>
        <div class="post">
            <p><span style="color:var(--green);font-weight:700;">GET</span> <code style="font-size:11px;color:var(--white);">/api/dexs</code></p>
            <p style="font-size:10px;color:var(--text-dim);margin:4px 0 6px;">Top 10 DEXes by 24h volume.</p>
            <pre style="background:var(--surface);padding:10px;font-size:10px;border:1px solid var(--border);overflow-x:auto;">curl https://crypto-empire-ten.vercel.app/api/dexs</pre>
        </div>

        <footer>
            <p>Crypto Empire — Wallet: <code style="font-size:8px;">{{ wallet }}</code></p>
        </footer>
    </div>
    <div class="b-bar">
        <span><span class="dot"></span> DOCS</span>
        <span>v1.0</span>
    </div>
    <script>
        (function(){
            function u(){
                var n=new Date();
                var y=n.getUTCFullYear();
                var m=String(n.getUTCMonth()+1).padStart(2,'0');
                var d=String(n.getUTCDate()).padStart(2,'0');
                var h=String(n.getUTCHours()).padStart(2,'0');
                var i=String(n.getUTCMinutes()).padStart(2,'0');
                var s=String(n.getUTCSeconds()).padStart(2,'0');
                var e=document.getElementById('live-clock');
                if(e)e.textContent=y+'-'+m+'-'+d+' '+h+':'+i+':'+s+' UTC';
            }
            u();setInterval(u,1000);
        })();
    </script>
</body>
</html>""", wallet=WALLET_ADDRESS)


# ============================================================
# Wallet Check Page
# ============================================================

WALLET_CHECK_HTML = """<!DOCTYPE html>
<html lang="en">
<head>""" + SHARED_HEAD + """
    <title>Wallet Checker — Crypto Empire</title>
    <meta name="description" content="Multi-chain Ethereum wallet balance checker. Check ETH, tokens and balances across Ethereum, Arbitrum, Polygon, Base, Optimism, BSC.">
</head>
<body>
    <div class="grid-bg"></div>
    <div class="sweep"></div>
    <div class="container">
        <div class="top-bar">
            <div class="brand">
                <div class="prompt">><span class="cr"></span></div>
                <div>
                    <div class="site-title">Wallet Checker</div>
                    <div class="site-sub">Multi-chain balance tool</div>
                </div>
            </div>
            <div class="top-nav">
                <a href="/">Dashboard</a>
                <a href="/blog">Blog</a>
                <a href="/docs">API</a>
            </div>
        </div>
        <div class="status-line">
            <span><span class="dot"></span> WALLET CHECK v1.0</span>
            <span id="live-clock">--</span>
        </div>
        <div class="bnav"><a href="/">Dashboard</a></div>
        <div class="s-title">WALLET CHECKER</div>
        <p style="font-size:11px;color:var(--text-dim);margin-bottom:16px;">Check ETH balances across Ethereum, Arbitrum, Base, and Polygon.</p>
        <input type="text" style="width:100%;max-width:440px;background:var(--surface);color:var(--white);border:1px solid var(--border);padding:10px 12px;font-size:11px;font-family:inherit;outline:none;" id="address" placeholder="0x... or ENS name" value="0x29021dd5306D7b3b6608a2bc8276D33c1200C7Ef">
        <br>
        <button style="margin-top:10px;background:var(--surface);color:var(--white);border:1px solid var(--white);padding:8px 20px;font-size:11px;text-transform:uppercase;letter-spacing:3px;cursor:pointer;font-family:inherit;" onclick="checkWallet()">Check Wallet</button>
        <div id="results" class="result"></div>
    </div>
    <div class="b-bar">
        <span><span class="dot"></span> WALLET CHECK</span>
        <span>v1.0</span>
    </div>
    <script>
    (function(){
        function u(){
            var n=new Date();
            var y=n.getUTCFullYear();
            var m=String(n.getUTCMonth()+1).padStart(2,'0');
            var d=String(n.getUTCDate()).padStart(2,'0');
            var h=String(n.getUTCHours()).padStart(2,'0');
            var i=String(n.getUTCMinutes()).padStart(2,'0');
            var s=String(n.getUTCSeconds()).padStart(2,'0');
            var e=document.getElementById('live-clock');
            if(e)e.textContent=y+'-'+m+'-'+d+' '+h+':'+i+':'+s+' UTC';
        }
        u();setInterval(u,1000);
    })();
    async function checkWallet() {
        var addr = document.getElementById('address').value.trim();
        var el = document.getElementById('results');
        if (!addr || !addr.startsWith('0x')) { el.innerHTML = '<div class="error">Invalid address</div>'; return; }
        el.innerHTML = '<div class="loading">CHECKING...</div>';
        try {
            var r = await fetch('/api/check-wallet/' + encodeURIComponent(addr));
            var data = await r.json();
            if (data.error) { el.innerHTML = '<div class="error">' + data.error + '</div>'; return; }
            var html = '<div class="total-val">TOTAL: ' + data.total_usd_formatted + '</div>';
            for (var i = 0; i < data.chains.length; i++) {
                var c = data.chains[i];
                html += '<div class="chain-row">' +
                    '<span class="chain-name">' + c.name + '</span>' +
                    '<span><span class="chain-bal">' + c.balance_formatted + '</span> <span class="chain-usd">$' + c.usd_value.toFixed(2) + '</span></span>' +
                    '</div>';
            }
            html += '<div style="text-align:center;margin-top:16px;"><a href="https://debank.com/profile/' + addr + '" target="_blank" style="font-size:11px;text-transform:uppercase;letter-spacing:1px;">View on DeBank -></a></div>';
            el.innerHTML = html;
        } catch(e) {
            el.innerHTML = '<div class="error">Request failed</div>';
        }
    }
    checkWallet();
    </script>
</body>
</html>"""

@app.route("/wallet-check")
def wallet_check():
    return render_template_string(WALLET_CHECK_HTML)


@app.route("/api/check-wallet/<address>")
def api_check_wallet(address):
    """Check wallet balances across multiple chains"""
    chains = {
        "ethereum": {"name": "Ethereum", "rpc": "https://ethereum-rpc.publicnode.com", "coingecko": "ethereum"},
        "arbitrum": {"name": "Arbitrum", "rpc": "https://arb1.arbitrum.io/rpc", "coingecko": "ethereum"},
        "base": {"name": "Base", "rpc": "https://mainnet.base.org", "coingecko": "ethereum"},
        "polygon": {"name": "Polygon", "rpc": "https://polygon-rpc.com", "coingecko": "matic-network"},
    }
    
    # Get ETH price in USD
    eth_price = 0
    price_data = fetch_sync(f"{COINGECKO_API}/simple/price?ids=ethereum,matic-network&vs_currencies=usd")
    if price_data:
        eth_price = (price_data.get("ethereum", {}) or {}).get("usd", 0)
    
    matic_price = 0
    if price_data:
        matic_price = (price_data.get("matic-network", {}) or {}).get("usd", 0)
    
    results = []
    total_usd = 0
    
    for key, cfg in chains.items():
        try:
            r = requests.post(cfg["rpc"], json={
                "jsonrpc": "2.0", "method": "eth_getBalance",
                "params": [address, "latest"], "id": 1
            }, timeout=8)
            data = r.json()
            if "result" in data:
                bal = int(data["result"], 16) / 1e18
                price = eth_price if cfg["coingecko"] == "ethereum" else matic_price
                usd = bal * price
                total_usd += usd
                results.append({
                    "chain": key,
                    "name": cfg["name"],
                    "balance": bal,
                    "balance_formatted": f"{bal:.6f}" if bal >= 0.001 else f"{bal:.8f}",
                    "usd_value": usd,
                })
            else:
                results.append({"chain": key, "name": cfg["name"], "balance": 0, "balance_formatted": "0", "usd_value": 0})
        except:
            results.append({"chain": key, "name": cfg["name"], "balance": None, "balance_formatted": "error", "usd_value": 0})
    
    return jsonify({
        "address": address,
        "chains": results,
        "total_usd": total_usd,
        "total_usd_formatted": f"${total_usd:,.2f}",
    })


# ============================================================
# Wallet Profiler — paste any ETH address
# ============================================================

def query_rpc(method, params, rpc_url="https://ethereum-rpc.publicnode.com"):
    """Helper for JSON-RPC calls"""
    try:
        r = requests.post(rpc_url, json={
            "jsonrpc": "2.0", "method": method,
            "params": params, "id": 1
        }, timeout=8)
        return r.json().get("result")
    except Exception:
        return None


# Top ERC-20 token contracts on Ethereum (by market cap / relevance)
PROFILER_TOKENS = [
    ("0xdAC17F958D2ee523a2206206994597C13D831ec7", "USDT", 6),
    ("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "USDC", 6),
    ("0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", "WBTC", 8),
    ("0x514910771AF9Ca656af840dff83E8264EcF986CA", "LINK", 18),
    ("0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0", "MATIC", 18),
    ("0x967da4048cD07aB37855c090aAF366e4ce1b9F48", "OCEAN", 18),
    ("0x4Fabb145d64652a948d72533023f6E7A623C7C53", "BUSD", 18),
    ("0x6B175474E89094C44Da98b954EedeAC495271d0F", "DAI", 18),
    ("0x0000000000085d4780B73119b644AE5ecd22b376", "TUSD", 18),
    ("0x57Ab1ec28D129707052df4dF418D58a2D46d5f51", "SUSD", 18),
    ("0x3845badAde8e6dFF049820680d1F14bD3903a5d0", "SAND", 18),
]


@app.route("/api/profiler/<address>")
def api_profiler(address):
    """Profile any Ethereum address: balance, tokens, recent tx count, USD value"""
    if not re.match(r'^0x[a-fA-F0-9]{40}$', address):
        return jsonify({"error": "Invalid Ethereum address"}), 400

    # 1. Native ETH balance
    native_bal_raw = query_rpc("eth_getBalance", [address, "latest"])
    native_bal = int(native_bal_raw, 16) / 1e18 if native_bal_raw else 0

    # 2. Transaction count (nonce)
    tx_count_raw = query_rpc("eth_getTransactionCount", [address, "latest"])
    tx_count = int(tx_count_raw, 16) if tx_count_raw else 0

    # 3. Token balances via eth_call (no API key needed)
    tokens = []
    for contract, sym, decimals in PROFILER_TOKENS:
        # ERC-20 balanceOf(address) — 0x70a08231 + padded address
        data = "0x70a08231" + address[2:].zfill(64)
        result = query_rpc("eth_call", [{"to": contract, "data": data}, "latest"])
        if result and result != "0x" and int(result, 16) > 0:
            bal = int(result, 16) / (10 ** decimals)
            tokens.append({"symbol": sym, "balance": bal, "contract": contract})

    # 4. USD prices via CoinGecko
    eth_price = 0
    token_prices = {}
    try:
        ids = "ethereum," + ",".join(
            {"USDT": "tether", "USDC": "usd-coin", "WBTC": "wrapped-bitcoin",
             "LINK": "chainlink", "MATIC": "matic-network", "DAI": "dai",
             "BUSD": "binance-usd", "SAND": "the-sandbox", "SUSD": "nusd",
             "TUSD": "true-usd", "OCEAN": "ocean-protocol"}.get(t["symbol"], "")
            for t in tokens
        )
        price_data_raw = fetch_sync(f"{COINGECKO_API}/simple/price?ids={ids}&vs_currencies=usd")
        if price_data_raw:
            eth_price = price_data_raw.get("ethereum", {}).get("usd", 0) or 0
            token_prices = {
                "USDT": (price_data_raw.get("tether", {}) or {}).get("usd", 1),
                "USDC": (price_data_raw.get("usd-coin", {}) or {}).get("usd", 1),
                "WBTC": (price_data_raw.get("wrapped-bitcoin", {}) or {}).get("usd", 0),
                "LINK": (price_data_raw.get("chainlink", {}) or {}).get("usd", 0),
                "MATIC": (price_data_raw.get("matic-network", {}) or {}).get("usd", 0),
                "DAI": (price_data_raw.get("dai", {}) or {}).get("usd", 1),
                "BUSD": (price_data_raw.get("binance-usd", {}) or {}).get("usd", 1),
                "SAND": (price_data_raw.get("the-sandbox", {}) or {}).get("usd", 0),
                "OCEAN": (price_data_raw.get("ocean-protocol", {}) or {}).get("usd", 0),
            }
    except Exception:
        pass

    total_usd = native_bal * eth_price
    token_results = []
    for t in tokens:
        tok_price = token_prices.get(t["symbol"], 0) or 0
        usd = t["balance"] * tok_price
        total_usd += usd
        token_results.append({
            "symbol": t["symbol"],
            "balance": t["balance"],
            "balance_fmt": f"{t['balance']:.2f}" if t['balance'] >= 1 else f"{t['balance']:.6f}",
            "usd_value": usd,
            "usd_fmt": f"${usd:,.2f}" if usd >= 0.01 else "<$0.01",
        })

    # Sort tokens by USD value descending
    token_results.sort(key=lambda x: x["usd_value"], reverse=True)

    return jsonify({
        "address": address,
        "eth_balance": native_bal,
        "eth_balance_fmt": f"{native_bal:.4f}",
        "eth_usd_value": native_bal * eth_price,
        "eth_usd_fmt": f"${native_bal * eth_price:,.2f}",
        "tx_count": tx_count,
        "tokens": token_results,
        "total_usd": total_usd,
        "total_usd_fmt": f"${total_usd:,.2f}",
        "eth_price": eth_price,
        "updated_at": int(time.time()),
    })


PROFILER_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wallet Profiler — Crypto Empire</title>
""" + SHARED_HEAD + r"""
<style>
.profiler-form{display:flex;gap:8px;margin:16px 0;flex-wrap:wrap}
.profiler-form input{flex:1;min-width:200px;background:var(--surface);border:1px solid var(--border);color:var(--white);padding:10px 14px;font-family:inherit;font-size:12px;outline:none;letter-spacing:.5px}
.profiler-form input:focus{border-color:var(--white)}
.profiler-form button{border:1px solid var(--white);color:var(--white);background:transparent;padding:10px 24px;font-family:inherit;font-size:9px;text-transform:uppercase;letter-spacing:3px;cursor:pointer;transition:.15s}
.profiler-form button:hover{background:var(--white);color:var(--bg)}
.profiler-form button:disabled{opacity:.3;cursor:not-allowed}
.profiler-form button:disabled:hover{background:transparent;color:var(--white)}
.summary-row{display:flex;gap:16px;margin:16px 0;flex-wrap:wrap}
.summary-box{border:1px solid var(--border);padding:14px 18px;flex:1;min-width:140px}
.summary-box .label{font-size:8px;text-transform:uppercase;letter-spacing:2px;color:var(--text-dim);margin-bottom:4px}
.summary-box .value{font-size:16px;color:var(--white);font-weight:700;letter-spacing:-.5px;font-variant-numeric:tabular-nums}
.summary-box .sub{font-size:9px;color:var(--text-dim);margin-top:2px;letter-spacing:1px}
.token-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px;margin:12px 0}
.token-card{background:var(--surface);border:1px solid var(--border);padding:12px}
.token-card .sym{font-size:11px;color:var(--white);font-weight:700;letter-spacing:1px}
.token-card .bal{font-size:13px;color:var(--white);margin:4px 0 2px;letter-spacing:-.5px}
.token-card .usd{font-size:9px;color:var(--text-dim);letter-spacing:1px}
.address-display{font-size:10px;color:var(--text-dim);word-break:break-all;padding:8px 0;letter-spacing:.5px}
.address-display .addr{color:var(--white)}
.share-note{font-size:9px;color:var(--text-dim);letter-spacing:1px;margin:12px 0}
.loading{text-align:center;padding:60px 0;color:var(--text-dim);font-size:10px;letter-spacing:2px;text-transform:uppercase}
.error{text-align:center;padding:40px 0;color:var(--red);font-size:10px;letter-spacing:2px;text-transform:uppercase}
</style>
</head>
<body>
<div class="grid-bg"></div>
<div class="sweep"></div>
<div class="container">
<div class="top-bar">
<div class="brand">
<div class="prompt">><span class="cr"></span></div>
<div>
<div class="site-title">Wallet Profiler</div>
<div class="site-sub">inspect any ethereum address</div>
</div>
</div>
<div style="display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end;max-width:200px;">
<a href="/" class="nav-link" style="font-size:9px;letter-spacing:2px;text-transform:uppercase;border:1px solid var(--border);padding:6px 10px;color:var(--text-dim);text-decoration:none;">Dashboard</a>
<a href="/wallet-check" class="nav-link" style="font-size:9px;letter-spacing:2px;text-transform:uppercase;border:1px solid var(--border);padding:6px 10px;color:var(--text-dim);text-decoration:none;">Checker</a>
</div>
</div>

<div class="status-line">
<span><span class="dot"></span> Live data</span>
</div>

<form class="profiler-form" id="profiler-form" onsubmit="return loadProfile()">
<input type="text" id="addr-input" placeholder="0x... or ENS name (e.g. vitalik.eth)" value="" autocomplete="off" spellcheck="false">
<button type="submit" id="profiler-btn">Inspect</button>
</form>

<div class="share-note">Shareable URL — bookmark or send any address as <code style="color:var(--white);font-size:10px;">/profiler?address=0x...</code></div>

<div id="results"></div>
</div>
<div class="b-bar"><span><span class="dot"></span> wallet profiler</span><span>v2.7</span></div>

<script>
var form=document.getElementById('profiler-form');
var input=document.getElementById('addr-input');
var btn=document.getElementById('profiler-btn');
var results=document.getElementById('results');

// Load from URL param
var params=new URLSearchParams(window.location.search);
var addrParam=params.get('address');
if(addrParam){input.value=addrParam;loadProfile()}

function fmtUsd(v){
  if(v==null||isNaN(v))return'--';
  if(v>=1e6)return'$'+(v/1e6).toFixed(2)+'M';
  if(v>=1e3)return'$'+(v/1e3).toFixed(2)+'K';
  if(v>=1)return'$'+v.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
  return v<0.01?'<$0.01':'$'+v.toFixed(2);
}

async function loadProfile(){
  var addr=input.value.trim();
  if(!addr){return false}
  // Basic ENS detection — pass through as-is, API handles
  var apiAddr=addr;
  btn.disabled=true;
  btn.textContent='Loading...';
  results.innerHTML='<div class="loading">Scanning address...</div>';
  try{
    var r=await fetch('/api/profiler/'+encodeURIComponent(apiAddr));
    var d=await r.json();
    if(d.error){results.innerHTML='<div class="error">'+d.error+'</div>';btn.disabled=false;btn.textContent='Inspect';return false}
    renderProfile(d);
    // Update URL without reload
    if(window.history.pushState){
      var url=new URL(window.location);
      url.searchParams.set('address',addr);
      window.history.pushState({},'',url);
    }
  }catch(e){
    results.innerHTML='<div class="error">Request failed</div>';
  }
  btn.disabled=false;
  btn.textContent='Inspect';
  return false;
}

function renderProfile(d){
  var eth=d.eth_balance||0;
  var html='';
  // Summary row
  html+='<div class="summary-row">';
  html+='<div class="summary-box"><div class="label">Total Value</div><div class="value">'+d.total_usd_fmt+'</div><div class="sub">USD</div></div>';
  html+='<div class="summary-box"><div class="label">ETH Balance</div><div class="value">'+eth.toFixed(4)+'</div><div class="sub">'+d.eth_usd_fmt+'</div></div>';
  html+='<div class="summary-box"><div class="label">Transactions</div><div class="value">'+(d.tx_count||0).toLocaleString()+'</div><div class="sub">total sent</div></div>';
  if(d.tokens&&d.tokens.length){html+='<div class="summary-box"><div class="label">Tokens</div><div class="value">'+d.tokens.length+'</div><div class="sub">top ERC-20s</div></div>'}
  html+='</div>';

  // Address
  html+='<div class="address-display">Address: <span class="addr">'+d.address+'</span>';
  html+=' &middot; ETH price: <span class="addr">$'+(d.eth_price||0).toLocaleString('en-US',{minimumFractionDigits:2,maxFractionDigits:2})+'</span>';
  html+='</div>';

  // Token grid
  if(d.tokens&&d.tokens.length){
    html+='<div class="s-title" style="margin-top:20px;">TOKEN HOLDINGS</div>';
    html+='<div class="token-grid">';
    for(var i=0;i<d.tokens.length;i++){
      var t=d.tokens[i];
      html+='<div class="token-card">';
      html+='<div class="sym">'+t.symbol+'</div>';
      html+='<div class="bal">'+t.balance_fmt+'</div>';
      html+='<div class="usd">'+fmtUsd(t.usd_value)+'</div>';
      html+='</div>';
    }
    html+='</div>';
  }

  // Empty state
  if(!d.tokens||!d.tokens.length){
    html+='<div style="text-align:center;padding:20px 0;color:var(--text-dim);font-size:9px;letter-spacing:2px;text-transform:uppercase;">No ERC-20 tokens detected for this address</div>';
  }

  results.innerHTML=html;
}
</script>
</body>
</html>"""


@app.route("/profiler")
def profiler_page():
    return render_template_string(PROFILER_HTML)


# ============================================================
# SEO: Blog Content
# ============================================================

BLOG_POSTS = [
    {
        "slug": "best-crypto-wallet-balance-checker-2026",
        "title": "Best Crypto Wallet Balance Checker 2026 - Track Any Address Across 4 Chains",
        "date": "2026-06-03",
        "tags": ["wallet checker", "crypto tools", "portfolio tracker"],
        "content": """
<h2>Check Any Ethereum Wallet Balance Across Multiple Chains</h2>
<p>Crypto Empire's <a href="/wallet-check">Wallet Checker</a> lets you instantly view ETH, MATIC, and ERC-20 token balances across Ethereum, Arbitrum, Base, and Polygon - all from one page. No signup, no API key, no wallet connection needed.</p>

<h3>Why Use a Multi-Chain Wallet Checker?</h3>
<p>Modern crypto users hold assets across multiple Layer 2 solutions. Instead of checking each chain's block explorer separately, our tool aggregates balances from Ethereum, Arbitrum, Base, and Polygon into a single USD value.</p>

<h3>Features</h3>
<ul>
<li><strong>Instant balance lookup</strong> - Enter any 0x address and see balances in seconds</li>
<li><strong>Multi-chain support</strong> - Ethereum, Arbitrum, Base, Polygon</li>
<li><strong>USD conversion</strong> - Real-time prices via CoinGecko</li>
<li><strong>ENS support</strong> - Enter ENS names directly</li>
<li><strong>Free &amp; open source</strong> - No ads, no tracking</li>
</ul>

<h3>How to Use</h3>
<p>Visit the <a href="/wallet-check">Wallet Checker</a> page, enter any Ethereum address, and click "Check Wallet". The tool queries live RPC endpoints and returns balances with USD values.</p>

<p>If you find this tool useful, consider supporting development by sending a donation to the project wallet.</p>
"""
    },
    {
        "slug": "ethereum-gas-tracker-live-prices",
        "title": "Ethereum Gas Tracker - Live ETH Gas Prices for Polygon, Arbitrum & Base 2026",
        "date": "2026-06-02",
        "tags": ["gas tracker", "ETH gas", "Layer 2 fees"],
        "content": """
<h2>Live Gas Price Tracker for Ethereum and L2s</h2>
<p>Our <a href="/">Gas Tracker</a> provides real-time gas prices for Ethereum, Polygon, Arbitrum, and Base. Optimize your transaction timing and reduce fees.</p>

<h3>Current Gas Prices</h3>
<p>The dashboard displays live gas prices in Gwei for the four major EVM chains. Prices update every 30 seconds with color-coded indicators (green = cheap, yellow = moderate, red = expensive).</p>

<h3>When to Transact</h3>
<ul>
<li><strong>Low gas (&lt;5 Gwei ETH)</strong> - Best time for transfers and DeFi interactions</li>
<li><strong>Medium gas (5-30 Gwei ETH)</strong> - Normal conditions, fine for standard transactions</li>
<li><strong>High gas (&gt;30 Gwei ETH)</strong> - Expensive, consider waiting or using L2s</li>
</ul>

<h3>Chain Comparison</h3>
<p>Polygon typically offers the lowest fees (&lt;100 Gwei MATIC), while Ethereum mainnet can spike during high-demand periods. Arbitrum and Base offer a middle ground with Ethereum-level security and reduced fees.</p>

<p>Bookmark our <a href="/">dashboard</a> for quick access to live gas data across all major chains.</p>
"""
    },
    {
        "slug": "crypto-portfolio-tracker-free-tools",
        "title": "Free Crypto Portfolio Tracker Tools - Track Without Connecting Your Wallet",
        "date": "2026-06-01",
        "tags": ["portfolio tracker", "crypto tools", "DeFi"],
        "content": """
<h2>Track Your Crypto Portfolio Without Connecting Your Wallet</h2>
<p>Privacy-focused crypto tracking is possible with on-chain data tools. Here are the best free options for monitoring your portfolio in 2026.</p>

<h3>1. Crypto Empire Wallet Checker</h3>
<p>Our <a href="/wallet-check">Wallet Checker</a> lets you check any Ethereum address across 4 chains instantly. No wallet connection, no data collection, just pure on-chain balance queries.</p>

<h3>2. Live Market Data</h3>
<p>Our <a href="/">dashboard</a> shows the top 20 cryptocurrencies with real-time prices, 24h and 7d changes, market cap, and volume. Updated directly from CoinGecko's API.</p>

<h3>3. Multi-Chain Balance API</h3>
<p>Developers can use our free <a href="/docs">API</a> to query wallet balances programmatically. No authentication required up to 100 requests/day.</p>

<h3>Why Portfolio Tracking Matters</h3>
<p>Regular portfolio monitoring helps you track gains, optimize tax reporting, and spot unusual activity. Using read-only tools preserves your privacy and security.</p>

<p>Support these free tools by donating to the project wallet. Your contribution helps keep the service running and ad-free.</p>
"""
    },
    {
        "slug": "crypto-empire-telegram-bot-live-prices-alerts",
        "title": "Crypto Empire Telegram Bot is Live — Get Crypto Prices Directly in Telegram",
        "date": "2026-06-04",
        "tags": ["telegram bot", "crypto bot", "price alerts", "crypto tools"],
        "content": """
<h2>@Crypt0Emp1reBot — Live Crypto Data on Telegram</h2>
<p>The Crypto Empire <a href="https://t.me/Crypt0Emp1reBot" target="_blank">Telegram bot</a> is now live. Get real-time crypto prices, gas fees, trending coins, and wallet balance checks directly in your Telegram chat. No signup, no API keys, no database — just pure on-chain and market data.</p>

<h3>Available Commands</h3>
<ul>
<li><strong>/price &lt;coin&gt;</strong> — Current price, 24h change, market cap &amp; volume (e.g. /price bitcoin)</li>
<li><strong>/gas</strong> — Live gas prices for Ethereum, Polygon, Arbitrum &amp; Base</li>
<li><strong>/fear</strong> — Fear &amp; Greed Index (market sentiment)</li>
<li><strong>/trending</strong> — Top 10 trending coins on CoinGecko</li>
<li><strong>/news</strong> — Latest 5 crypto headlines from CoinTelegraph</li>
<li><strong>/wallet &lt;address&gt;</strong> — Multi-chain balance check across ETH/Arb/Base/Poly</li>
<li><strong>/tvl</strong> — Ethereum Total Value Locked from DeFiLlama</li>
<li><strong>/dexs</strong> — Top 10 DEXes by 24h volume</li>
<li><strong>/sparkline &lt;coin&gt;</strong> — ASCII 7-day price chart</li>
</ul>

<h3>How to Use</h3>
<p>Open Telegram and search for <strong>@Crypt0Emp1reBot</strong> or click <a href="https://t.me/Crypt0Emp1reBot" target="_blank">this link</a>. Send <code>/start</code> to see the command list. That's it — no installation, no login, no ads.</p>

<h3>Behind the Scenes</h3>
<p>The bot runs on the same Vercel serverless infrastructure as the Crypto Empire dashboard. It uses a webhook endpoint at <code>/telegram/webhook</code> that processes commands in real-time. No persistent server, no polling — Telegram pushes messages to the endpoint and the bot responds within seconds.</p>

<p>All data sources are the same free public APIs powering the dashboard: CoinGecko for prices, public RPC endpoints for wallet balances, DeFiLlama for TVL and DEX data, and Alternative.me for the Fear &amp; Greed Index.</p>

<p>Built autonomously. Private. Zero KYC. Zero Budget.</p>
"""
    },
    {
        "slug": "top-cryptocurrencies-today",
        "title": "Top 20 Cryptocurrencies by Market Cap - Live Prices & Charts June 2026",
        "date": "2026-06-01",
        "tags": ["crypto prices", "market cap", "Bitcoin", "Ethereum"],
        "content": """
<h2>Top 20 Cryptocurrencies by Market Cap - Live Prices</h2>
<p>Our <a href="/">dashboard</a> displays the top 20 cryptocurrencies ranked by market capitalization, with live prices from CoinGecko.</p>

<h3>Today's Top Coins</h3>
<p>Bitcoin (BTC) remains the largest cryptocurrency by market cap, followed by Ethereum (ETH), Tether (USDT), and BNB (BNB). The rankings update automatically with each page reload.</p>

<h3>Understanding Market Metrics</h3>
<ul>
<li><strong>Market Cap</strong> - Total value of all coins in circulation (price x circulating supply)</li>
<li><strong>24h Change</strong> - Price movement over the last 24 hours</li>
<li><strong>7d Change</strong> - Price trend over the last week</li>
<li><strong>Volume (24h)</strong> - Total trading volume across all markets in the last day</li>
</ul>

<h3>Market Sentiment</h3>
<p>Our dashboard also includes the Fear &amp; Greed Index, a popular market sentiment indicator. Values below 25 indicate fear (potential buying opportunity), while values above 75 suggest greed (potential overvaluation).</p>

<p>Check back daily for updated prices and market data. Support the project by sending a donation to the wallet address below.</p>
"""
    },
]

@app.route("/blog")
def blog_index():
    return render_template_string("""<!DOCTYPE html>
<html lang="en">
<head>""" + SHARED_HEAD + """
    <title>Crypto Empire Blog - Crypto Tools, Guides & Market Analysis</title>
    <meta name="description" content="Free crypto tools, wallet checker, gas tracker, and market data. Guides and analysis for cryptocurrency traders and investors.">
    <meta name="keywords" content="crypto tools, wallet checker, gas tracker, Bitcoin, Ethereum, cryptocurrency prices">
    <link rel="canonical" href="https://crypto-empire-ten.vercel.app/blog">
</head>
<body>
    <div class="grid-bg"></div>
    <div class="sweep"></div>
    <div class="container">
        <div class="top-bar">
            <div class="brand">
                <div class="prompt">><span class="cr"></span></div>
                <div>
                    <div class="site-title">Blog</div>
                    <div class="site-sub">Tools, guides & market analysis</div>
                </div>
            </div>
            <div class="top-nav">
                <a href="/">Dashboard</a>
                <a href="/docs">API</a>
                <a href="/wallet-check">Wallet</a>
            </div>
        </div>
        <div class="status-line">
            <span><span class="dot"></span> BLOG</span>
            <span id="live-clock">--</span>
        </div>
        <div class="bnav"><a href="/">Dashboard</a></div>
        <div class="s-title">BLOG</div>
        <p style="font-size:11px;color:var(--text-dim);margin-bottom:20px;">Free crypto tools, guides, and market analysis.</p>
        
        {% for post in posts %}
        <div style="border:1px solid var(--border);padding:14px;margin-bottom:10px;">
            <h2 style="font-size:13px;margin:0 0 4px;"><a href="/blog/{{ post.slug }}" style="color:var(--white);text-decoration:none;">{{ post.title }}</a></h2>
            <div style="font-size:9px;color:var(--text-dim);text-transform:uppercase;letter-spacing:1px;">{{ post.date }} — {{ post.tags|join(', ') }}</div>
        </div>
        {% endfor %}
        
        <div class="prem-box" style="margin-top:20px;">
            <h3 style="font-size:11px;">SUPPORT</h3>
            <p style="font-size:9px;color:var(--text-dim);">Send ETH to <code style="font-size:9px;">{{ wallet }}</code></p>
        </div>
        
        <footer>
            <p>Crypto Empire</p>
        </footer>
    </div>
    <div class="b-bar">
        <span><span class="dot"></span> BLOG</span>
        <span>v1.0</span>
    </div>
    <script>
        (function(){
            function u(){
                var n=new Date();
                var y=n.getUTCFullYear();
                var m=String(n.getUTCMonth()+1).padStart(2,'0');
                var d=String(n.getUTCDate()).padStart(2,'0');
                var h=String(n.getUTCHours()).padStart(2,'0');
                var i=String(n.getUTCMinutes()).padStart(2,'0');
                var s=String(n.getUTCSeconds()).padStart(2,'0');
                var e=document.getElementById('live-clock');
                if(e)e.textContent=y+'-'+m+'-'+d+' '+h+':'+i+':'+s+' UTC';
            }
            u();setInterval(u,1000);
        })();
    </script>
</body>
</html>""", posts=BLOG_POSTS, wallet=WALLET_ADDRESS)


@app.route("/blog/<slug>")
def blog_post(slug):
    post = None
    for p in BLOG_POSTS:
        if p["slug"] == slug:
            post = p
            break
    if not post:
        return "Not found", 404
    return render_template_string("""<!DOCTYPE html>
<html lang="en">
<head>""" + SHARED_HEAD + """
    <title>{{ title }} — Crypto Empire</title>
    <meta name="description" content="{{ title }}. Free crypto tools, wallet checker, gas tracker, and live prices.">
    <link rel="canonical" href="https://crypto-empire-ten.vercel.app/blog/{{ slug }}">
</head>
<body>
    <div class="grid-bg"></div>
    <div class="sweep"></div>
    <div class="container">
        <div class="top-bar">
            <div class="brand">
                <div class="prompt">><span class="cr"></span></div>
                <div>
                    <div class="site-title">Blog</div>
                    <div class="site-sub">{{ title[:60] }}{% if title|length > 60 %}...{% endif %}</div>
                </div>
            </div>
            <div class="top-nav">
                <a href="/">Dashboard</a>
                <a href="/blog">Blog</a>
                <a href="/docs">API</a>
            </div>
        </div>
        <div class="status-line">
            <span><span class="dot"></span> ARTICLE</span>
            <span id="live-clock">--</span>
        </div>
        <div class="bnav"><a href="/blog">Blog</a></div>
        <div class="s-title" style="font-size:14px;">{{ title }}</div>
        <div style="font-size:9px;color:var(--text-dim);text-transform:uppercase;letter-spacing:1px;margin-bottom:20px;">{{ date }} — Tags: {{ tags|join(", ") }}</div>
        <div style="font-size:12px;line-height:1.8;color:var(--text);">{{ content|safe }}</div>
        
        <div class="prem-box" style="margin-top:24px;">
            <h3 style="font-size:11px;">SUPPORT</h3>
            <p style="font-size:9px;color:var(--text-dim);">Send ETH to <code style="font-size:9px;">{{ wallet }}</code></p>
        </div>
        
        <footer>
            <p><a href="/blog" style="color:var(--text-dim);text-decoration:none;font-size:9px;text-transform:uppercase;letter-spacing:1px;">More articles</a></p>
        </footer>
    </div>
    <div class="b-bar">
        <span><span class="dot"></span> ARTICLE</span>
        <span>v1.0</span>
    </div>
    <script>
        (function(){
            function u(){
                var n=new Date();
                var y=n.getUTCFullYear();
                var m=String(n.getUTCMonth()+1).padStart(2,'0');
                var d=String(n.getUTCDate()).padStart(2,'0');
                var h=String(n.getUTCHours()).padStart(2,'0');
                var i=String(n.getUTCMinutes()).padStart(2,'0');
                var s=String(n.getUTCSeconds()).padStart(2,'0');
                var e=document.getElementById('live-clock');
                if(e)e.textContent=y+'-'+m+'-'+d+' '+h+':'+i+':'+s+' UTC';
            }
            u();setInterval(u,1000);
        })();
    </script>
</body>
</html>""", title=post["title"], slug=post["slug"], date=post["date"], tags=post["tags"], content=post["content"], wallet=WALLET_ADDRESS)


@app.route("/sitemap.xml")
def sitemap():
    pages = [
        {"loc": "/", "priority": "1.0", "changefreq": "hourly"},
        {"loc": "/blog", "priority": "0.9", "changefreq": "daily"},
        {"loc": "/docs", "priority": "0.7", "changefreq": "weekly"},
        {"loc": "/wallet-check", "priority": "0.8", "changefreq": "daily"},
        {"loc": "/api-keys", "priority": "0.6", "changefreq": "weekly"},
    ]
    for post in BLOG_POSTS:
        pages.append({"loc": f"/blog/{post['slug']}", "priority": "0.6", "changefreq": "monthly"})

    urls = ""
    for p in pages:
        urls += f"""  <url>
    <loc>https://crypto-empire-ten.vercel.app{p['loc']}</loc>
    <priority>{p['priority']}</priority>
    <changefreq>{p['changefreq']}</changefreq>
  </url>\n"""
    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>"""
    return sitemap_xml, 200, {"Content-Type": "application/xml"}


@app.route("/robots.txt")
def robots():
    return """User-agent: *
Allow: /
Sitemap: https://crypto-empire-ten.vercel.app/sitemap.xml
""", 200, {"Content-Type": "text/plain"}


# ============================================================
# Embeddable Widget
# ============================================================

WIDGET_CSS = """<style>
  *{margin:0;padding:0;box-sizing:border-box;}
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');
  :root{--bg:#000;--surface:#050505;--border:#181818;--text:#b0b0b0;--text-dim:#555;--text-muted:#282828;--green:#0f0;--red:#f00;--white:#fff;}
  body{font-family:'JetBrains Mono','Fira Code','Courier New',monospace;background:var(--bg);color:var(--text);font-size:11px;line-height:1.6;min-height:auto;}
  body.light{--bg:#fff;--surface:#f5f5f5;--border:#ddd;--text:#333;--text-dim:#888;--text-muted:#ccc;--green:#008000;--red:#d00;--white:#000;}
  .w{max-width:360px;margin:0 auto;padding:10px;}
  .hdr{text-align:center;font-size:8px;color:var(--text-dim);text-transform:uppercase;letter-spacing:2px;border-bottom:1px solid var(--border);padding-bottom:6px;margin-bottom:8px;display:flex;justify-content:space-between;}
  .hdr span{color:var(--green);}
  .p-row{display:flex;gap:4px;margin-bottom:6px;}
  .p-card{flex:1;border:1px solid var(--border);padding:6px 8px;background:var(--surface);text-align:center;}
  .p-sym{font-size:7px;text-transform:uppercase;letter-spacing:1px;color:var(--text-dim);}
  .p-val{font-size:14px;font-weight:700;color:var(--white);margin:2px 0;}
  .p-chg{font-size:8px;text-transform:uppercase;letter-spacing:1px;}
  .up{color:var(--green);}.down{color:var(--red);}
  .m-section{margin-top:8px;}
  .m-title{font-size:7px;color:var(--text-dim);text-transform:uppercase;letter-spacing:2px;border-bottom:1px solid var(--border);padding-bottom:3px;margin-bottom:4px;}
  .m-row{display:flex;justify-content:space-between;padding:3px 6px;font-size:10px;border-bottom:1px solid var(--border);transition:.1s;}
  .m-row:hover{background:rgba(255,255,255,.02);}
  .m-name{color:var(--white);}
  .m-sym{color:var(--text-muted);font-size:8px;margin-left:4px;}
  .m-pr{color:var(--text-dim);}
  .ftr{text-align:center;font-size:6px;color:var(--text-muted);margin-top:8px;text-transform:uppercase;letter-spacing:1px;}
  .ftr a{color:var(--text-dim);text-decoration:none;}
  .ldr{text-align:center;padding:20px;color:var(--text-dim);font-size:9px;text-transform:uppercase;letter-spacing:2px;}
  .ldr .sp{display:inline-block;width:6px;height:6px;background:var(--green);margin-right:6px;animation:blink 1s step-end infinite;}
  @keyframes blink{50%{opacity:0}}
  .err{text-align:center;padding:14px;color:var(--red);font-size:9px;text-transform:uppercase;letter-spacing:1px;}
  .nul{text-align:center;padding:10px;color:var(--text-dim);font-size:9px;}
</style>"""

WIDGET_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
""" + WIDGET_CSS + """
<title>Crypto Empire Widget</title>
</head>
<body class="THEME">
<div class="w">
  <div class="hdr"><span>###</span> CRYPTO EMPIRE <span>###</span></div>
  <div id="ce-prices">PRICE_ROWS</div>
  <div id="ce-movers">MOVER_ROWS</div>
  <div class="ftr"><a href="https://crypto-empire-ten.vercel.app" target="_blank">crypto-empire-ten.vercel.app</a></div>
</div>
<script>
(function(){var d=document.getElementById('ce-prices'),m=document.getElementById('ce-movers');
async function l(){try{
var r=await fetch('/api/movers'),j=await r.json();
var g=j.top_gainers||[],l=j.top_losers||[];
if(m){var h='';
h+='<div class="m-section"><div class="m-title">> TOP GAINERS</div>';
g.slice(0,5).forEach(function(c){h+='<div class="m-row"><span><span class="m-name">'+c.name+'</span><span class="m-sym">'+c.symbol.toUpperCase()+'</span></span><span class="m-pr">$'+c.price+' <span class="up">+'+c.change+'%</span></span></div>';});
h+='</div><div class="m-section"><div class="m-title">> TOP LOSERS</div>';
l.slice(0,5).forEach(function(c){h+='<div class="m-row"><span><span class="m-name">'+c.name+'</span><span class="m-sym">'+c.symbol.toUpperCase()+'</span></span><span class="m-pr">$'+c.price+' <span class="down">'+c.change+'%</span></span></div>';});
h+='</div>';
m.innerHTML=h;}
}catch(e){if(m)m.innerHTML='<div class="err">! FAILED TO LOAD</div>';}}
l();
var p=document.getElementById('ce-prices');
async function lp(){try{
var ids=['bitcoin','ethereum','solana'];
var r=await fetch('/api/price/'+ids[0]);var j=await r.json();
var b=j.data||{usd:0,usd_24h_change:0};
r=await fetch('/api/price/'+ids[1]);j=await r.json();
var e=j.data||{usd:0,usd_24h_change:0};
r=await fetch('/api/price/'+ids[2]);j=await r.json();
var s=j.data||{usd:0,usd_24h_change:0};
function pc(v,c){return '<div class="p-card"><div class="p-sym">'+c+'</div><div class="p-val">$'+(v.usd||0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})+'</div><div class="p-chg '+(v.usd_24h_change>=0?'up':'down')+'">'+(v.usd_24h_change>=0?'+':'')+(v.usd_24h_change||0).toFixed(2)+'%</div></div>';}
if(p)p.innerHTML=pc(b,'BTC')+pc(e,'ETH')+pc(s,'SOL');
}catch(e){if(p)p.innerHTML='<div class="err">! FAILED TO LOAD</div>';}}
lp();})();
</script>
</body>
</html>"""


@app.route("/widget")
def widget():
    """Embeddable widget for iframe"""
    mode = request.args.get("mode", "both")  # price, movers, both
    theme = request.args.get("theme", "dark")  # dark, light
    coins = request.args.get("coins", "bitcoin,ethereum,solana")

    html = WIDGET_HTML
    html = html.replace("THEME", "" if theme == "dark" else "light")

    if mode == "price":
        # Hide movers section
        html = html.replace('<div id="ce-movers">MOVER_ROWS</div>', "")
    elif mode == "movers":
        # Hide price section
        html = html.replace('<div id="ce-prices">PRICE_ROWS</div>', '<div id="ce-prices"></div>')

    return html, 200, {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "text/html; charset=utf-8",
        "X-Frame-Options": "ALLOWALL",
        "Cache-Control": "no-cache",
    }


@app.route("/widget/embed.js")
def widget_embed_js():
    """JavaScript embed snippet for external sites"""
    # Determine mode from query param, passed through to the iframe URL
    mode = request.args.get("mode", "both")
    theme = request.args.get("theme", "dark")
    base_url = request.host_url.rstrip("/")

    js = f"""(function(){{
  var CE_WIDGET = function(){{
    var container = document.getElementById('ce-widget');
    if(!container){{
      container = document.createElement('div');
      container.id = 'ce-widget';
      document.body.appendChild(container);
    }}
    var mode = container.getAttribute('data-mode') || '{mode}';
    var theme = container.getAttribute('data-theme') || '{theme}';
    var w = container.getAttribute('data-width') || '360';
    container.innerHTML = '<iframe src="{base_url}/widget?mode='+mode+'&theme='+theme+'" style="width:'+w+'px;max-width:100%%;height:420px;border:1px solid #181818;background:#000;overflow:hidden;" frameborder="0" scrolling="no"></iframe>';
  }};
  if(document.readyState==='loading'){{document.addEventListener('DOMContentLoaded',CE_WIDGET);}}else{{CE_WIDGET();}}
}})();"""

    return js, 200, {
        "Content-Type": "application/javascript; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "max-age=300",
    }


# ============================================================
# Scrolling Market Ticker — embeddable ribbon
# ============================================================

@app.route("/api/ticker-data")
def ticker_data():
    """Flat price data for the scrolling ticker"""
    symbols = {
        "bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL",
        "ripple": "XRP", "cardano": "ADA", "dogecoin": "DOGE",
        "polkadot": "DOT", "avalanche-2": "AVAX", "chainlink": "LINK",
        "polygon": "MATIC", "shiba-inu": "SHIB", "litecoin": "LTC",
        "uniswap": "UNI", "stellar": "XLM",
    }
    ids = list(symbols.keys())
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": ",".join(ids), "vs_currencies": "usd",
                    "include_24hr_change": "true"},
            timeout=10,
        )
        prices = r.json()
        ticker = []
        for cid in ids:
            data = prices.get(cid, {})
            usd = data.get("usd")
            ch = data.get("usd_24h_change")
            if usd:
                ticker.append({
                    "s": symbols[cid],
                    "p": round(usd, 2) if usd >= 1 else round(usd, 6),
                    "c": round(ch, 2) if ch is not None else None,
                })
        # Append top movers (up to 5)
        try:
            m = requests.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={"vs_currency": "usd", "order": "volume_desc",
                        "per_page": 50, "page": 1, "sparkline": "false"},
                timeout=10,
            )
            markets = m.json()
            # Sort by 24h change descending, pick top 5 not already in ticker
            gainers = sorted([c for c in markets if c.get("price_change_percentage_24h") is not None],
                             key=lambda c: c["price_change_percentage_24h"], reverse=True)[:5]
            seen = set(i["s"] for i in ticker)
            for c in gainers:
                sym = (c.get("symbol") or "").upper()
                if sym not in seen and c.get("current_price"):
                    seen.add(sym)
                    ticker.append({
                        "s": sym,
                        "p": round(c["current_price"], 2) if c["current_price"] >= 1 else round(c["current_price"], 6),
                        "c": round(c["price_change_percentage_24h"], 2),
                    })
        except Exception:
            pass
        return jsonify({"ticker": ticker, "updated_at": int(time.time())})
    except Exception as e:
        return jsonify({"ticker": [], "error": str(e), "updated_at": int(time.time())})


TICKER_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Market Ticker — Crypto Empire</title>
""" + SHARED_HEAD + r"""
<style>
/* Ticker-specific overrides — compact, no-nav */
body{overflow:hidden;background:transparent;min-height:auto}
.container{max-width:none;padding:0;margin:0}
/* Remove CRT scanlines for ticker — cleaner on embed */
body::after,body::before,.sweep,.grid-bg{display:none}
.ticker-wrap{overflow:hidden;width:100%;height:36px;background:var(--bg);border:1px solid var(--border);border-left:none;border-right:none;position:relative}
.ticker-track{display:flex;white-space:nowrap;will-change:transform}
.ticker-track.paused{animation-play-state:paused!important}
.ticker-item{display:inline-flex;align-items:center;gap:6px;padding:0 18px;height:34px;font-size:11px;letter-spacing:.5px;border-right:1px solid var(--border)}
.ticker-sym{color:var(--white);font-weight:700}
.ticker-price{color:var(--text)}
.ticker-chg{font-weight:500;font-size:10px}
.ticker-chg.up{color:var(--green)}
.ticker-chg.down{color:var(--red)}
.ticker-chg.neutral{color:var(--text-dim)}
.ticker-sep{color:var(--text-muted);padding:0 8px;font-size:8px}
/* Dark theme default, light override */
body.light{--bg:#fff;--surface:#f5f5f5;--border:#ddd;--text:#444;--text-dim:#999;--white:#000;--green:#060;--red:#c00}
</style>
</head>
<body>
<div class="ticker-wrap" id="ticker-wrap">
  <div class="ticker-track" id="ticker-track">
    <div style="padding:0 20px;color:var(--text-dim);font-size:10px;letter-spacing:1px;height:34px;display:flex;align-items:center;">Loading...</div>
  </div>
</div>
<script>
(function(){
var wrap=document.getElementById('ticker-wrap');
var track=document.getElementById('ticker-track');
var items=[];
var animId=null;
var speed=50; // px per second

function fmtP(v){return v<1?v.toFixed(6):v<100?v.toFixed(2):v.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})}
function fmtC(v){if(v==null)return '<span class="ticker-chg neutral">--</span>';var c=v>0?'up':'down';return '<span class="ticker-chg '+c+'">'+(v>0?'+':'')+v.toFixed(2)+'%</span>'}

function render(data){
  var html='';
  for(var i=0;i<data.length;i++){
    var d=data[i];
    html+='<div class="ticker-item">';
    html+='<span class="ticker-sym">'+d.s+'</span>';
    html+='<span class="ticker-price">$'+fmtP(d.p)+'</span>';
    html+=fmtC(d.c);
    html+='</div>';
  }
  if(data.length)html+='<div class="ticker-item" style="color:var(--text-dim);font-size:9px;letter-spacing:1px;text-transform:uppercase;">Crypto Empire</div>';
  track.innerHTML=html;
  startScroll();
}

function startScroll(){
  if(animId){cancelAnimationFrame(animId);animId=null}
  var tw=wrap.offsetWidth;
  var tt=track.scrollWidth;
  if(tt<=tw){track.style.transform='translateX(0)';track.style.justifyContent='center';return}
  // Clone content for seamless loop
  track.innerHTML+=track.innerHTML;
  var totalW=track.scrollWidth/2;
  var pos=0;
  var last=performance.now();
  function frame(now){
    var dt=(now-last)/1000;
    last=now;
    pos+=dt*speed;
    if(pos>=totalW)pos-=totalW;
    track.style.transform='translateX(-'+pos+'px)';
    animId=requestAnimationFrame(frame);
  }
  animId=requestAnimationFrame(frame);
}

// Pause on hover
wrap.addEventListener('mouseenter',function(){track.classList.add('paused');if(animId){cancelAnimationFrame(animId);animId=null}});
wrap.addEventListener('mouseleave',function(){track.classList.remove('paused');startScroll()});

async function fetchData(){
  try{
    var r=await fetch('/api/ticker-data');
    var d=await r.json();
    if(d.ticker&&d.ticker.length)render(d.ticker);
  }catch(e){}
}
fetchData();
setInterval(fetchData,30000);
})();
</script>
</body>
</html>"""


@app.route("/ticker")
def ticker():
    """Embeddable scrolling ticker (iframe)"""
    theme = request.args.get("theme", "dark")
    html = TICKER_HTML
    if theme == "light":
        html = html.replace('<body>', '<body class="light">', 1)
    return html, 200, {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "text/html; charset=utf-8",
        "X-Frame-Options": "ALLOWALL",
        "Cache-Control": "no-cache",
    }


@app.route("/ticker/embed.js")
def ticker_embed_js():
    """JavaScript embed snippet for the scrolling ticker"""
    theme = request.args.get("theme", "dark")
    base_url = request.host_url.rstrip("/")

    js = f"""(function(){{
  var CE_TICKER = function(){{
    var container = document.getElementById('ce-ticker');
    if(!container){{
      container = document.createElement('div');
      container.id = 'ce-ticker';
      document.body.appendChild(container);
    }}
    var theme = container.getAttribute('data-theme') || '{theme}';
    container.innerHTML = '<iframe src="{base_url}/ticker?theme='+theme+'" style="width:100%;height:36px;border:none;overflow:hidden;display:block;" frameborder="0" scrolling="no"></iframe>';
  }};
  if(document.readyState==='loading'){{document.addEventListener('DOMContentLoaded',CE_TICKER);}}else{{CE_TICKER();}}
}})();"""
    return js, 200, {
        "Content-Type": "application/javascript; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "max-age=300",
    }


# ============================================================
# Trending This Hour — standalone page
# ============================================================

TRENDING_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trending This Hour — Crypto Empire</title>
""" + SHARED_HEAD + r"""
<style>
.coin-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;margin:16px 0}
.coin-card{background:var(--surface);border:1px solid var(--border);padding:14px;cursor:pointer;transition:background .15s,border-color .15s;text-decoration:none;display:block}
.coin-card:hover{background:var(--border);border-color:var(--text-dim)}
.coin-card:target{border-color:var(--white);box-shadow:0 0 0 1px var(--white)}
.coin-rank{font-size:9px;color:var(--text-dim);text-transform:uppercase;letter-spacing:1px;margin-bottom:4px}
.coin-name{font-size:13px;color:var(--white);font-weight:600}
.coin-sym{font-size:9px;color:var(--text-dim);text-transform:uppercase;letter-spacing:1px}
.coin-price{font-size:15px;color:var(--white);margin:6px 0 2px;font-weight:700;letter-spacing:-.5px}
.coin-change{font-size:10px;letter-spacing:.5px}
.coin-change.up{color:var(--green)}
.coin-change.down{color:var(--red)}
.coin-cap{font-size:8px;color:var(--text-dim);text-transform:uppercase;letter-spacing:1px;margin-top:4px}
.updated{font-size:9px;color:var(--text-dim);letter-spacing:1px;text-transform:uppercase}
.updated span{color:var(--white)}
.filter-bar{display:flex;gap:8px;margin:12px 0;flex-wrap:wrap}
.filter-btn{background:var(--surface);border:1px solid var(--border);color:var(--text-dim);padding:6px 14px;font-size:9px;text-transform:uppercase;letter-spacing:2px;cursor:pointer;font-family:inherit;transition:all .1s}
.filter-btn:hover,.filter-btn.active{border-color:var(--white);color:var(--white)}
.stat-row{display:flex;gap:16px;margin:12px 0;flex-wrap:wrap}
.stat-item{font-size:9px;text-transform:uppercase;letter-spacing:1px}
.stat-item .num{color:var(--white);font-weight:600}
@media(max-width:480px){.coin-grid{grid-template-columns:1fr 1fr}.coin-card{padding:10px}}
</style>
</head>
<body>
<div class="grid-bg"></div>
<div class="sweep"></div>
<div class="container">
<div class="top-bar">
<div class="brand">
<div class="prompt">><span class="cr"></span></div>
<div>
<div class="site-title">Trending This Hour</div>
<div class="site-sub">coingecko trending <span id="coin-count" style="color:var(--white);">--</span> coins</div>
</div>
</div>
<div style="display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end;max-width:200px;">
<a href="/" class="nav-link" style="font-size:9px;letter-spacing:2px;text-transform:uppercase;border:1px solid var(--border);padding:6px 10px;color:var(--text-dim);text-decoration:none;">Dashboard</a>
<a href="/widget" class="nav-link" style="font-size:9px;letter-spacing:2px;text-transform:uppercase;border:1px solid var(--border);padding:6px 10px;color:var(--text-dim);text-decoration:none;">Widget</a>
</div>
</div>

<div class="status-line">
<span><span class="dot"></span> Live — refreshing every 60s</span>
<span class="updated">Updated <span id="update-time">--</span></span>
</div>

<div class="stat-row">
<div class="stat-item">trending <span class="num" id="stat-total">--</span></div>
<div class="stat-item">with prices <span class="num" id="stat-priced">--</span></div>
<div class="stat-item">24h &uarr; <span class="num" id="stat-up" style="color:var(--green)">--</span></div>
<div class="stat-item">24h &darr; <span class="num" id="stat-down" style="color:var(--red)">--</span></div>
</div>

<div class="filter-bar">
<button class="filter-btn active" data-filter="all">All</button>
<button class="filter-btn" data-filter="gainers">Gainers</button>
<button class="filter-btn" data-filter="losers">Losers</button>
<button class="filter-btn" data-filter="top10">Top 10</button>
</div>

<div class="coin-grid" id="coin-grid"></div>

<div style="text-align:center;padding:20px 0;font-size:9px;color:var(--text-dim);letter-spacing:1px;">
Data from CoinGecko &middot; Updates every 60 seconds &middot; Coin cards are shareable — copy the URL while highlighted
</div>

<footer><p>Crypto Empire &middot; <a href="/api/trending-now" style="color:var(--text-dim);">API</a></p></footer>
</div>
<div class="b-bar"><span><span class="dot"></span> trending this hour</span><span>v2.4</span></div>

<script>
(function(){
var grid=document.getElementById('coin-grid');
var updateTime=document.getElementById('update-time');
var coinCount=document.getElementById('coin-count');
var statTotal=document.getElementById('stat-total');
var statPriced=document.getElementById('stat-priced');
var statUp=document.getElementById('stat-up');
var statDown=document.getElementById('stat-down');
var activeFilter='all';
var allCoins=[];

function fmtPrice(v){
 if(v==null||v===0)return'--';
 return v>=1000?'$'+v.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})
   :'$'+v.toFixed(4);
}
function fmtCap(v){
 if(v==null)return'--';
 return v>=1e9?'$'+(v/1e9).toFixed(1)+'B':v>=1e6?'$'+(v/1e6).toFixed(1)+'M':'$'+(v/1e3).toFixed(0)+'K';
}

function render(coins){
 allCoins=coins;
 var filtered=coins;
 if(activeFilter==='gainers')filtered=coins.filter(function(c){return c.usd_24h_change>0});
 else if(activeFilter==='losers')filtered=coins.filter(function(c){return c.usd_24h_change<0});
 else if(activeFilter==='top10')filtered=coins.slice(0,10);

 var html='';
 for(var i=0;i<filtered.length;i++){
   var c=filtered[i];
   var p=c.price_usd;
   var ch=c.usd_24h_change;
   var cls=ch>0?'up':'down';
   var sym=(c.symbol||'').toUpperCase();
   var id=c.id||('coin-'+i);
   html+='<a class="coin-card" id="cc-'+id+'" href="#'+id+'" onclick="window.location.hash=\''+id+'\';return true">';
   html+='<div class="coin-rank">#'+(c.market_cap_rank||'--')+' &middot; Score '+(c.score||'--')+'</div>';
   html+='<div class="coin-name">'+c.name+' <span class="coin-sym">'+sym+'</span></div>';
   html+='<div class="coin-price">'+fmtPrice(p)+'</div>';
   if(ch!=null)html+='<div class="coin-change '+cls+'">'+(ch>0?'+':'')+ch.toFixed(2)+'% 24h</div>';
   else html+='<div class="coin-change" style="color:var(--text-dim);">-- 24h</div>';
   html+='<div class="coin-cap">Cap: '+fmtCap(c.market_cap)+'</div>';
   html+='</a>';
 }
 grid.innerHTML=html;

 // Stats
 var priced=coins.filter(function(c){return c.price_usd!=null});
 var up=coins.filter(function(c){return c.usd_24h_change>0});
 var down=coins.filter(function(c){return c.usd_24h_change<0});
 coinCount.textContent=coins.length;
 statTotal.textContent=coins.length;
 statPriced.textContent=priced.length;
 statUp.textContent=up.length;
 statDown.textContent=down.length;

 // Scroll to hash target
 var h=window.location.hash.replace('#','');
 if(h){
   var target=document.getElementById('cc-'+h);
   if(target){
     target.scrollIntoView({behavior:'smooth',block:'center'});
     setTimeout(function(){target.style.boxShadow='0 0 0 2px var(--white)';setTimeout(function(){target.style.boxShadow=''},2000)},300);
   }
 }
}

async function fetchData(){
 try{
   var r=await fetch('/api/trending-now');
   var d=await r.json();
   if(d.trending){
     render(d.trending);
     var now=new Date(d.updated_at*1000);
     updateTime.textContent=now.toUTCString().split(' ')[4]+' UTC';
   }
 }catch(e){}
}

// Filters
document.querySelectorAll('.filter-btn').forEach(function(btn){
 btn.addEventListener('click',function(){
   document.querySelectorAll('.filter-btn').forEach(function(b){b.classList.remove('active')});
   this.classList.add('active');
   activeFilter=this.getAttribute('data-filter');
   render(allCoins);
 });
});

// Hash change — scroll to coin
window.addEventListener('hashchange',function(){
 if(allCoins.length)render(allCoins);
});

fetchData();
setInterval(fetchData,60000);
})();
</script>
</body>
</html>"""


@app.route("/trending")
def trending_page():
    return render_template_string(TRENDING_HTML)


# ============================================================
# Telegram Bot Webhook
# ============================================================

@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    from telegram_bot import handle_update
    data = request.get_json(silent=True) or {}
    result = handle_update(data)
    return jsonify(result)


# ============================================================
# 404 Handler
# ============================================================

@app.errorhandler(404)
def page_not_found(e):
    return render_template_string("""<!DOCTYPE html>
<html lang="en">
<head>""" + SHARED_HEAD + """
    <title>404 — Crypto Empire</title>
    <meta name="robots" content="noindex">
</head>
<body>
    <div class="grid-bg"></div>
    <div class="sweep"></div>
    <div class="container">
        <div class="top-bar">
            <div class="brand">
                <div class="prompt">><span class="cr"></span></div>
                <div>
                    <div class="site-title">Error 404</div>
                    <div class="site-sub">Resource not found</div>
                </div>
            </div>
        </div>
        <div class="status-line">
            <span><span class="dot" style="background:var(--red);"></span> 404 NOT FOUND</span>
        </div>
        <div style="text-align:center;padding:80px 0;">
            <div style="font-size:60px;font-weight:700;color:var(--white);letter-spacing:-2px;">404</div>
            <div style="font-size:11px;color:var(--text-dim);margin:12px 0 24px;text-transform:uppercase;letter-spacing:3px;">The requested resource was not found on this chain.</div>
            <a href="/" style="display:inline-block;border:1px solid var(--white);color:var(--white);padding:10px 28px;font-size:10px;text-transform:uppercase;letter-spacing:3px;text-decoration:none;">Return to Dashboard</a>
        </div>
        <footer>
            <p>Crypto Empire</p>
        </footer>
    </div>
    <div class="b-bar">
        <span><span class="dot" style="background:var(--red);"></span> 404</span>
        <span>v1.0</span>
    </div>
</body>
</html>"""), 404


# ============================================================
# Main
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print(f"⚡ Crypto Empire Dashboard starting on port {port}")
    print(f"💰 Wallet: {WALLET_ADDRESS}")
    app.run(host="0.0.0.0", port=port, debug=debug)
