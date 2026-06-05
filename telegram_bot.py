"""
Crypto Empire Telegram Bot — Webhook mode for Vercel serverless
"""
import os
import json
import sqlite3
import logging
from html import unescape
import requests

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Token from env (Vercel) or file (local dev)
# ---------------------------------------------------------------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or ""
if not TELEGRAM_TOKEN:
    token_path = os.path.join(os.path.dirname(__file__), ".telegram_token")
    if os.path.exists(token_path):
        TELEGRAM_TOKEN = open(token_path).read().strip()

API_BASE = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ---------------------------------------------------------------------------
# Lazy import from app (avoid circular at module level)
# ---------------------------------------------------------------------------
_app_module = None

def _get_app():
    global _app_module
    if _app_module is None:
        import app as _app_module
    return _app_module

# ---------------------------------------------------------------------------
# Coin symbol → CoinGecko ID lookup for shortcut commands
# ---------------------------------------------------------------------------
SYMBOL_TO_ID = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "xrp": "xrp",
    "ada": "cardano",
    "doge": "dogecoin",
    "dot": "polkadot",
    "matic": "polygon",
    "avax": "avalanche-2",
    "link": "chainlink",
    "bnb": "binancecoin",
    "atom": "cosmos",
    "trx": "tron",
    "ltc": "litecoin",
    "ton": "the-open-network",
    "arb": "arbitrum",
    "op": "optimism",
    "shib": "shiba-inu",
    "uni": "uniswap",
    "pepe": "pepe",
    "apt": "aptos",
    "sui": "sui",
    "near": "near",
    "fil": "filecoin",
    "algo": "algorand",
    "fld": "flow",
    "icp": "internet-computer",
    "egld": "elrond-erd-2",
    "inj": "injective-protocol",
    "sei": "sei-network",
    "tia": "celestia",
    "strk": "starknet",
    "wld": "worldcoin-wld",
    "poly": "polygon-ecosystem-token",
    "ondo": "ondo-finance",
    "pendle": "pendle",
    "ena": "ethena",
    "ethfi": "ether-fi",
    "rezt": "rezzle",
    "om": "mantra-dao",
}

# ---------------------------------------------------------------------------
# Telegram helpers
# ---------------------------------------------------------------------------

def send_message(chat_id, text, parse_mode=None):
    """Send a plain or markdown message to a Telegram chat."""
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        r = requests.post(f"{API_BASE}/sendMessage", json=payload, timeout=8)
        return r.json()
    except Exception as e:
        log.error(f"send_message failed: {e}")
        return None

def send_typing(chat_id):
    """Show 'typing…' indicator."""
    try:
        requests.post(f"{API_BASE}/sendChatAction", json={"chat_id": chat_id, "action": "typing"}, timeout=3)
    except:
        pass

# ---------------------------------------------------------------------------
# Chat type helpers
# ---------------------------------------------------------------------------

def is_group_chat(chat):
    """Check if a chat dict is a group/supergroup."""
    t = chat.get("type", "")
    return t in ("group", "supergroup")

# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_start(chat_id, args=None, chat_type="private"):
    intro = (
        "> CRYPTO_EMPIRE BOT\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
        "Live crypto data at your fingertips.\n\n"
    )
    if chat_type == "group":
        intro += (
            "I reply to commands in this group.\n"
            "Just type /btc, /eth, /sol, /doge, etc. for instant prices.\n\n"
        )

    cmds = (
        "Commands:\n"
        "/price <coin>     — Current price & 24h change\n"
        "/btc /eth /sol    — Shortcuts for top coins\n"
        "/gas              — Gas prices (ETH/Poly/Arb/Base)\n"
        "/fear             — Fear & Greed Index\n"
        "/trending         — Top trending coins\n"
        "/launches         — Upcoming token TGEs & IDOs\n"
        "/news             — Latest crypto headlines\n"
        "/wallet <address> — Multi-chain balance check\n"
        "/dexs             — Top DEXes by volume\n"
        "/tvl              — Ethereum TVL\n"
        "/sparkline <coin> — 7d price chart (ASCII)\\n"
        "/whales           — On-chain whale moves >$100K\\n"
        "/help             — This message\\n\\n"
        "Built autonomously \u2014 github.com/ghassan-gaidi/crypto-empire"
    )

    if chat_type == "group":
        cmds += (
            "\n\nTip: Add me to more groups and use /btc /eth /sol "
            "for quick prices anywhere."
        )

    send_message(chat_id, intro + cmds)

def cmd_price(chat_id, args):
    if not args:
        send_message(chat_id, "Usage: /price <coin_id>  (e.g. /price bitcoin)\nTip: try /btc, /eth, /sol for shortcuts.")
        return
    coin = args[0].lower().strip()
    app = _get_app()
    data = app.fetch_sync(f"{app.COINGECKO_API}/simple/price?ids={coin}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true")
    if data and coin in data:
        d = data[coin]
        usd = d.get("usd", "?")
        chg = d.get("usd_24h_change")
        mc = d.get("usd_market_cap", 0)
        vol = d.get("usd_24h_vol", 0)
        arrow = "\u25b2" if chg and chg >= 0 else "\u25bc"
        chg_str = f"{chg:+.2f}%" if chg is not None else "N/A"
        mc_str = f"${mc:,.0f}" if mc else "N/A"
        vol_str = f"${vol:,.0f}" if vol else "N/A"
        msg = (
            f"> {coin.upper()}\n"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
            f"Price: ${usd:,}\n"
            f"24h:   {arrow} {chg_str}\n"
            f"M.Cap: {mc_str}\n"
            f"Vol:   {vol_str}"
        )
    else:
        msg = f"Coin '{coin}' not found. Try /price bitcoin, or use shortcuts like /btc /eth /sol"
    send_message(chat_id, msg)

def cmd_gas(chat_id, args=None):
    send_typing(chat_id)
    app = _get_app()
    data = app.fetch_sync(f"{app.COINGECKO_API}/simple/price?ids=ethereum&vs_currencies=usd")
    eth_price = ""
    if data and "ethereum" in data:
        eth_price = f"ETH: ${data['ethereum']['usd']:,.0f}\n"

    chains = {
        "ethereum": "https://ethereum-rpc.publicnode.com",
        "polygon":  "https://polygon-rpc.com",
        "arbitrum": "https://arb1.arbitrum.io/rpc",
        "base":     "https://mainnet.base.org",
    }
    lines = ["> GAS TRACKER", "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501"]
    if eth_price:
        lines.append(f"\n{eth_price.strip()}")
    for name, url in chains.items():
        try:
            r = requests.post(url, json={"jsonrpc":"2.0","method":"eth_gasPrice","params":[],"id":1}, timeout=5)
            res = r.json()
            if "result" in res:
                gwei = int(res["result"], 16) / 1e9
                lines.append(f"{name:<10} {gwei:.1f} gwei")
            else:
                lines.append(f"{name:<10} error")
        except:
            lines.append(f"{name:<10} error")
    send_message(chat_id, "\n".join(lines))

def cmd_fear(chat_id, args=None):
    app = _get_app()
    data = app.fetch_sync("https://api.alternative.me/fng/?limit=1")
    if data and "data" in data and data["data"]:
        d = data["data"][0]
        val = d.get("value", "?")
        cls = d.get("value_classification", "N/A")
        arrow = "\U0001f4c8" if int(val) > 50 else "\U0001f4c9" if int(val) < 25 else "\u2795"
        msg = f"> FEAR & GREED\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\nValue: {val}/100\nState: {cls.upper()} {arrow}"
    else:
        msg = "Fear & Greed unavailable"
    send_message(chat_id, msg)

def cmd_trending(chat_id, args=None):
    send_typing(chat_id)
    app = _get_app()
    data = app.fetch_sync(f"{app.COINGECKO_API}/search/trending")
    if data and "coins" in data:
        lines = ["> TRENDING COINS", "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501"]
        for i, coin in enumerate(data["coins"][:10], 1):
            item = coin.get("item", {})
            name = item.get("name", "?")
            sym = (item.get("symbol") or "").upper()
            rank = item.get("market_cap_rank") or "--"
            lines.append(f"{i:2}. {name} ({sym}) \u2014 Rank #{rank}")
        msg = "\n".join(lines)
    else:
        msg = "Trending unavailable"
    send_message(chat_id, msg)

def cmd_launches(chat_id, args=None):
    send_typing(chat_id)
    app = _get_app()
    data = app.fetch_sync("https://crypto-empire-ten.vercel.app/api/launches")
    if data and "launches" in data:
        launches = data["launches"]
        lines = ["> TOKEN LAUNCH CALENDAR", "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501"]
        upcoming = [l for l in launches if l["status"] == "upcoming"][:5]
        if upcoming:
            for l in upcoming:
                dd = l.get("days_until", "?")
                lines.append(f"\n\U0001f4c5 {l['name']} (${l['symbol']})")
                lines.append(f"   {l['type']} \u2014 {dd} days \u2022 {l['chain']}")
        else:
            lines.append("\nNo upcoming launches right now.")
        msg = "\n".join(lines)
    else:
        msg = "Launch calendar unavailable. See https://crypto-empire-ten.vercel.app/launches"
    send_message(chat_id, msg)

def cmd_news(chat_id, args=None):
    send_typing(chat_id)
    app = _get_app()
    items = app.fetch_rss("https://cointelegraph.com/rss")
    if items:
        lines = ["> CRYPTO NEWS", "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501"]
        for item in items[:5]:
            lines.append(f"\n\u2022 {item['title']}")
            lines.append(f"  {item['date'][:16] if item['date'] else ''}")
        msg = "\n".join(lines)
    else:
        msg = "News unavailable"
    send_message(chat_id, msg)

def cmd_wallet(chat_id, args):
    if not args:
        send_message(chat_id, "Usage: /wallet <0x address>")
        return
    addr = args[0].strip()
    if not addr.startswith("0x"):
        send_message(chat_id, "Invalid address \u2014 must start with 0x")
        return
    send_typing(chat_id)
    app = _get_app()

    # Fetch ETH price
    price_data = app.fetch_sync(f"{app.COINGECKO_API}/simple/price?ids=ethereum,matic-network&vs_currencies=usd")
    eth_p = (price_data or {}).get("ethereum", {}).get("usd", 0)
    matic_p = (price_data or {}).get("matic-network", {}).get("usd", 0)

    chains = {
        "Ethereum": "https://ethereum-rpc.publicnode.com",
        "Arbitrum": "https://arb1.arbitrum.io/rpc",
        "Base":     "https://mainnet.base.org",
        "Polygon":  "https://polygon-rpc.com",
    }
    total = 0
    lines = [f"> WALLET", f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501", f"", f"{addr[:10]}...{addr[-6:]}"]
    for name, url in chains.items():
        try:
            r = requests.post(url, json={"jsonrpc":"2.0","method":"eth_getBalance","params":[addr,"latest"],"id":1}, timeout=6)
            res = r.json()
            if "result" in res:
                bal = int(res["result"], 16) / 1e18
                price = eth_p if name != "Polygon" else matic_p
                usd = bal * price
                total += usd
                bal_s = f"{bal:.4f}" if bal >= 0.001 else f"{bal:.8f}"
                lines.append(f"\n{name:<10} {bal_s}  ${usd:,.2f}")
            else:
                lines.append(f"\n{name:<10} error")
        except:
            lines.append(f"\n{name:<10} error")
    lines.append(f"\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501")
    lines.append(f"TOTAL: ${total:,.2f}")
    send_message(chat_id, "\n".join(lines))

def cmd_tvl(chat_id, args=None):
    app = _get_app()
    data = app.fetch_sync("https://api.llama.fi/v2/historicalChainTvl/Ethereum")
    if data and len(data) > 0:
        latest = data[-1]
        tvl_b = latest.get("tvl", 0) / 1e9
        msg = f"> ETH TVL\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n${tvl_b:.2f}B\nSource: DeFiLlama"
    else:
        msg = "TVL unavailable"
    send_message(chat_id, msg)

def cmd_dexs(chat_id, args=None):
    send_typing(chat_id)
    app = _get_app()
    data = app.fetch_sync("https://api.llama.fi/overview/dexs")
    if data and "protocols" in data:
        top = sorted(data["protocols"], key=lambda x: x.get("total24h", 0) or 0, reverse=True)[:10]
        lines = ["> TOP DEXES (24h Vol)", "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501"]
        for i, d in enumerate(top, 1):
            name = d.get("displayName") or d.get("name", "?")
            vol = d.get("total24h", 0) or 0
            vol_s = f"${vol/1e6:.1f}M" if vol >= 1e6 else f"${vol/1e3:.0f}K"
            chg = d.get("change_1d", 0) or 0
            arrow = "\u25b2" if chg >= 0 else "\u25bc"
            lines.append(f"{i:2}. {name:<20} {vol_s:>10} {arrow}{chg:+.1f}%")
        msg = "\n".join(lines)
    else:
        msg = "DEX data unavailable"
    send_message(chat_id, msg)

def cmd_whales(chat_id, args=None):
    """Show recent on-chain whale moves (>$100K)."""
    send_typing(chat_id)
    app = _get_app()
    data = app.fetch_sync("https://crypto-empire-ten.vercel.app/api/whales?limit=5")
    if data and "moves" in data and data["moves"]:
        lines = ["> WHALE TRACKER", "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501"]
        for m in data["moves"]:
            usd = f"${m['usdValue']:,.0f}" if m.get("usdValue") else f"{m['value']:,.2f}"
            addr_s = f"{m['to'][:6]}...{m['to'][-4:]}"
            lines.append(f"\n\U0001F40B {usd} {m['token']}")
            lines.append(f"   \u2192 {addr_s}  \u2022 {m['txHash'][:8]}...")
        lines.append(f"\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501")
        lines.append(f"Updated: {data['lastUpdated'][:19]} UTC")
        lines.append(f"Tracked: USDT/USDC/WBTC \u2022 crypto-empire-ten.vercel.app/whales")
        msg = "\n".join(lines)
    else:
        msg = "No whale moves found right now. Try again later."
    send_message(chat_id, msg)

def cmd_sparkline(chat_id, args):
    if not args:
        send_message(chat_id, "Usage: /sparkline <coin_id>  (e.g. /sparkline bitcoin)")
        return
    coin = args[0].lower().strip()
    send_typing(chat_id)
    app = _get_app()
    data = app.fetch_sync(f"{app.COINGECKO_API}/coins/{coin}?localization=false&tickers=false&community_data=false&developer_data=false&sparkline=true")
    if data and "market_data" in data:
        prices = data.get("market_data", {}).get("sparkline_7d", {}).get("price", [])
        if prices and len(prices) > 1:
            bars = 30  # ASCII chars
            step = len(prices) / bars
            sample = [prices[min(int(i * step), len(prices) - 1)] for i in range(bars)]
            mn, mx = min(sample), max(sample)
            rng = mx - mn if mx > mn else 1
            h = 8  # rows
            rows = []
            for row in range(h - 1, -1, -1):
                threshold = mn + (row / (h - 1)) * rng
                line = ""
                for p in sample:
                    line += "\u2588" if p >= threshold else " "
                rows.append(line)
            chart = "\n".join(rows)
            arrow = " \u25b2" if sample[-1] >= sample[0] else " \u25bc"
            msg = f"> {coin.upper()} 7d{arrow}\n\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\n{chart}\n\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\u2508\n${sample[-1]:,.2f}"
        else:
            msg = f"No sparkline data for {coin}"
    else:
        msg = f"Coin '{coin}' not found"
    send_message(chat_id, msg)

# ---------------------------------------------------------------------------
# Group event handlers
# ---------------------------------------------------------------------------

def handle_my_chat_member(data):
    """Handle bot being added to or removed from a group."""
    chat = data.get("chat", {})
    chat_id = chat.get("id")
    new_status = data.get("new_chat_member", {}).get("status", "")
    old_status = data.get("old_chat_member", {}).get("status", "")

    if not chat_id:
        return {"ok": False, "reason": "no chat"}

    group_title = chat.get("title", "this group")
    chat_type = chat.get("type", "unknown")

    if new_status == "member" and old_status in ("left", "kicked", "restricted"):
        # Bot was added to group
        welcome = (
            f"\U0001f916 *Crypto Empire Bot added to {group_title}*\n\n"
            f"Type /btc, /eth, /sol or any coin ticker for instant prices.\n"
            f"Use /help to see all commands.\n\n"
            f"More at crypto-empire-ten.vercel.app"
        )
        send_message(chat_id, welcome, parse_mode="Markdown")
        log.info(f"Bot added to group: {group_title} ({chat_id})")

    elif new_status == "left" and old_status == "member":
        # Bot was removed from group
        log.info(f"Bot removed from group: {group_title} ({chat_id})")

    return {"ok": True}

def store_username_mapping(username, chat_id):
    """Store chat_id → username mapping for alert delivery."""
    if not username or not chat_id:
        return
    try:
        app = _get_app()
        conn = sqlite3.connect(str(app.DB_PATH))
        conn.execute("CREATE TABLE IF NOT EXISTS telegram_mapping (username TEXT PRIMARY KEY, chat_id INTEGER)")
        conn.execute(
            "INSERT OR REPLACE INTO telegram_mapping (username, chat_id) VALUES (?, ?)",
            (username, chat_id),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

COMMANDS = {
    "start":     cmd_start,
    "help":      cmd_start,
    "price":     cmd_price,
    "gas":       cmd_gas,
    "fear":      cmd_fear,
    "feargreed": cmd_fear,
    "trending":  cmd_trending,
    "launches":  cmd_launches,
    "launch":    cmd_launches,
    "news":      cmd_news,
    "wallet":    cmd_wallet,
    "tvl":       cmd_tvl,
    "dexs":      cmd_dexs,
    "dex":       cmd_dexs,
    "sparkline": cmd_sparkline,
    "whales":    cmd_whales,
    "whale":     cmd_whales,
}

# Register shortcut commands (e.g., /btc → cmd_price(["bitcoin"]))
for sym, cg_id in SYMBOL_TO_ID.items():
    COMMANDS[sym] = lambda chat_id, args, cg_id=cg_id: cmd_price(chat_id, [cg_id])

def handle_update(data):
    """Parse a Telegram webhook update and execute the command."""
    chat_id = None
    try:
        # Handle group membership events
        my_chat_member = data.get("my_chat_member")
        if my_chat_member:
            return handle_my_chat_member(my_chat_member)

        msg = data.get("message", {})
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        text = (msg.get("text") or "").strip()
        if not chat_id or not text:
            return {"ok": False, "reason": "no message"}

        chat_type = chat.get("type", "private")

        # Store chat_id → username mapping for alert delivery
        user = msg.get("from", {})
        username = (user.get("username") or "").lower().strip()
        store_username_mapping(username, chat_id)

        # Parse command
        parts = text.split()
        cmd = parts[0].lower().lstrip("/").split("@")[0]  # strip / and bot username
        args = parts[1:]

        handler = COMMANDS.get(cmd)
        if handler:
            # Pass chat_type to cmd_start for group-specific messaging
            if cmd in ("start", "help"):
                handler(chat_id, args, chat_type=chat_type)
            else:
                handler(chat_id, args)
        else:
            # In groups, offer helpful suggestions for unknown commands
            suggestions = ""
            if chat_type in ("group", "supergroup"):
                suggestions = "\n\nTry /btc, /eth, /sol for prices, or /help for all commands."
            send_message(chat_id, f"Unknown command: /{cmd}{suggestions}")
        return {"ok": True}
    except Exception as e:
        log.exception("handle_update error")
        if chat_id:
            send_message(chat_id, f"Error: {str(e)[:200]}")
        return {"ok": False, "error": str(e)}
