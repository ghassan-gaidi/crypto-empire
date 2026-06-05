#!/usr/bin/env python3
"""
Crypto Empire — X/Twitter Auto-Poster
Fetches market data and posts formatted tweets via xurl CLI.
Scheduled via GH Actions cron (every 2 hours).
"""
import subprocess
import json
import sys
from datetime import datetime, timezone

BASE = "https://crypto-empire-ten.vercel.app"
USER_AGENT = "CryptoEmpireBot/1.0"


def fetch_json(url):
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[!] fetch failed: {url} — {e}", file=sys.stderr)
        return None


def fmt_price(v):
    if not v:
        return "$0"
    v = float(v)
    if v >= 1000:
        return f"${v:,.2f}"
    elif v >= 1:
        return f"${v:.4f}"
    else:
        return f"${v:.8f}"


def fmt_change(v):
    if v is None:
        return "0.00%"
    v = float(v)
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%"


def get_tweet_rotations():
    """Generate rotating tweet content based on UTC hour (4 formats)"""
    hour = datetime.now(timezone.utc).hour
    rotation = hour % 4

    btc = fetch_json(f"{BASE}/api/price/bitcoin")
    eth = fetch_json(f"{BASE}/api/price/ethereum")
    sol = fetch_json(f"{BASE}/api/price/solana")
    movers = fetch_json(f"{BASE}/api/movers")
    fg = fetch_json(f"{BASE}/api/fear-greed")
    gas = fetch_json(f"{BASE}/api/gas")

    bd = (btc or {}).get("data", {})
    ed = (eth or {}).get("data", {})
    sd = (sol or {}).get("data", {})

    bp = bd.get("usd", 0)
    bc = bd.get("usd_24h_change")
    ep = ed.get("usd", 0)
    ec = ed.get("usd_24h_change")
    sp = sd.get("usd", 0)
    sc = sd.get("usd_24h_change")

    # Fear & Greed is an array from the API
    fg_val = "?"
    fg_label = ""
    if fg and isinstance(fg, list) and len(fg) > 0:
        fg_val = str(fg[0].get("value", "?"))
        fg_label = fg[0].get("value_classification", "")

    # Gas
    gas_val = "?"
    if gas and isinstance(gas, dict):
        gas_val = str(gas.get("ethereum", {}).get("gwei", "?"))

    tweets = [
        # [0] BTC + ETH price update
        f"$BTC {fmt_price(bp)} ({fmt_change(bc)} 24h)\n"
        f"$ETH {fmt_price(ep)} ({fmt_change(ec)} 24h)\n"
        f"\n#Bitcoin #Ethereum #Crypto",

        # [1] Full market snapshot
        f"BTC {fmt_price(bp)} ({fmt_change(bc)})\n"
        f"ETH {fmt_price(ep)} ({fmt_change(ec)})\n"
        f"SOL {fmt_price(sp)} ({fmt_change(sc)})\n"
        f"Gas: {gas_val} Gwei\n"
        f"Fear & Greed: {fg_val}/100 — {fg_label}\n"
        f"\n#Crypto #Markets",

        # [2] Top movers
        f"Market Movers — 24h\n"
        f"{_fmt_movers((movers or {}).get('top_gainers', []), (movers or {}).get('top_losers', []))}"
        f"\n#Altcoins #Crypto",

        # [3] Fear & Greed + market summary
        f"Fear & Greed: {fg_val}/100 — {fg_label}\n"
        f"BTC {fmt_price(bp)} ({fmt_change(bc)})\n"
        f"ETH {fmt_price(ep)} ({fmt_change(ec)})\n"
        f"\nTrack live: crypto-empire-ten.vercel.app\n"
        f"\n#Crypto #Bitcoin #Sentiment",
    ]

    return tweets[rotation]


def _fmt_movers(gainers, losers):
    parts = []
    if gainers:
        g = gainers[0]
        parts.append(f"Top Gainer: ${g['name']} +{g['change']}%")
    if losers:
        l = losers[0]
        parts.append(f"Top Loser: ${l['name']} {l['change']}%")
    if not parts:
        return "Market movers data unavailable\n"
    return "\n".join(parts) + "\n"


def post_tweet(text):
    """Post a tweet using xurl CLI"""
    result = subprocess.run(
        ["xurl", "post", text],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        err = result.stdout or result.stderr
        print(f"[!] xurl failed (exit {result.returncode})", file=sys.stderr)
        if "CreditsDepleted" in err:
            print("[!] X API credits depleted — add credits in developer.x.com (min $5)", file=sys.stderr)
        else:
            print(f"[!] {err[:500]}", file=sys.stderr)
        return False
    try:
        data = json.loads(result.stdout)
        tid = data.get("data", {}).get("id", "?")
        print(f"[+] Tweet posted: https://x.com/LeoFalco2574/status/{tid}")
        return True
    except json.JSONDecodeError:
        print(f"[+] xurl output: {result.stdout.strip()}")
        return True


def main():
    text = get_tweet_rotations()
    print(f"[*] Posting:\n{text}\n")
    success = post_tweet(text)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
