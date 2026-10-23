"""
Dominion Telegram Bot — Webhook mode for Vercel serverless
"""
import os
import json
import sqlite3
import logging
from html import unescape
import requests

from design import TG  # Night print devices (masthead / rule / leader / bullet / foot)

import time


def _when():
    """UTC folio timestamp for wire footers."""
    return time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())

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
    "rndr": "render-token",
    "aave": "aave",
    "mkr": "maker",
    "xlm": "stellar",
    "hbar": "hedera-hashgraph",
    "vet": "vechain",
    "ftm": "fantom",
    "cro": "crypto-com-chain",
    "grt": "the-graph",
    "imx": "immutable-x",
    "sand": "the-sandbox",
    "gala": "gala",
    "axs": "axie-infinity",
    "xtz": "tezos",
    "eos": "eos",
    # v3.7 expansion — meme coins, AI, DeFi
    "wif": "dogwifhat",
    "bonk": "bonk",
    "popcat": "popcat",
    "mew": "cat-in-a-dogs-world",
    "not": "notcoin",
    "jup": "jupiter",
    "pyth": "pyth-network",
    "fetch": "fetch-ai",
    "tao": "bittensor",
    "stx": "stacks",
    "rune": "thorchain",
    "kas": "kaspa",
    "ordi": "ordinals",
    "zro": "layerzero",
    "jto": "jito-governance-token",
    "hmstr": "hamster-kombat",
    "dogs": "dogs",
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
    except Exception:
        pass

def edit_message(chat_id, message_id, text):
    """Edit a previously sent message."""
    try:
        requests.post(f"{API_BASE}/editMessageText", json={
            "chat_id": chat_id, "message_id": message_id, "text": text
        }, timeout=5)
    except Exception:
        pass

def send_loading(chat_id, header):
    """Send a masthead-first loading placeholder, return message_id (or None if failed)."""
    resp = send_message(chat_id, f"{fmt_header(header)}\n\n⟳ setting the type…")
    if resp and resp.get("ok"):
        return resp["result"]["message_id"]
    return None

def edit_or_send(chat_id, message_id, text):
    """Edit existing placeholder, or send fresh if editing fails."""
    if message_id:
        try:
            r = requests.post(f"{API_BASE}/editMessageText", json={
                "chat_id": chat_id, "message_id": message_id, "text": text
            }, timeout=5)
            if r.ok:
                return
        except Exception:
            pass
    send_message(chat_id, text)

# ---------------------------------------------------------------------------
# Night print devices — masthead-first blocks, rule bars, dotted leaders,
# ❧ bullets, ▲/▼ tones, folio footers. Plain text only.
# ---------------------------------------------------------------------------
SEP = TG["rule"]

def fmt_header(title):
    """Masthead-first page head: 'DOMINION — PAGE' + rule bar."""
    return f"{TG['masthead'].format(page=title)}\n{TG['rule']}"

def wire_foot(page, when=""):
    """Folio footer: ❦ page · /help for the index when."""
    when = (when or "").strip()
    return TG["foot"].format(page=page, when=when).rstrip()

def leader_row(label, value):
    """Dotted-leader ledger row."""
    return f"{label} {TG['leader']} {value}"

def bullet(text):
    """Press-bullet line."""
    return f"{TG['bullet']} {text}"

def wire_block(page, rows, when=""):
    """Assemble a wire telegram: masthead → rows → folio footer."""
    lines = [fmt_header(page), ""]
    lines += [r for r in rows if r]
    lines += ["", wire_foot(page, when)]
    return "\n".join(lines)

def fmt_change(chg):
    if chg is None:
        return "N/A"
    arrow = "▲" if chg >= 0 else "▼"
    return f"{arrow} {abs(chg):.2f}%"

def fmt_price(price):
    if price is None or price == 0:
        return "N/A"
    if price >= 1:
        return f"${price:,.2f}"
    return f"${price:.8f}"

def fmt_market_cap(mc):
    if not mc:
        return "N/A"
    if mc >= 1e12:
        return f"${mc/1e12:.2f}T"
    if mc >= 1e9:
        return f"${mc/1e9:.2f}B"
    if mc >= 1e6:
        return f"${mc/1e6:.2f}M"
    return f"${mc:,.0f}"

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
    ref_code = args[0].lower().strip() if args and args[0].startswith("ref_") else None

    if ref_code:
        app = _get_app()
        referrer_code = ref_code[4:]
        if referrer_code and str(chat_id) not in referrer_code:
            app.record_referral(referrer_code, chat_id)

    # Night masthead block
    banner = (
        f"{TG['masthead'].format(page='CRYPTO EMPIRE v3.7')}\n"
        f"{TG['rule']}\n\n"
        f"Live crypto data at your fingertips.\n\n"
    )
    intro = banner
    if chat_type == "group":
        intro += (
            "I reply to commands in this group.\n"
            "Just type /btc, /eth, /sol, etc. for instant prices.\n\n"
        )

    cmds = (
        "Commands:\n"
        "  /price <coin>     — Price & 24h change\n"
        "  /btc /eth /sol    — Shortcuts for 55+ coins\n"
        "  /gas              — Gas prices (ETH/Poly/Arb/Base)\n"
        "  /fear             — Fear & Greed Index\n"
        "  /trending         — Top trending coins\n"
        "  /launches         — Upcoming token TGEs & IDOs\n"
        "  /news             — Latest crypto headlines\n"
        "  /wallet <addr>    — Multi-chain balance check\n"
        "  /dexs             — Top DEXes by volume\n"
        "  /tvl              — Ethereum TVL\n"
        "  /sparkline <coin> — 7d price chart\n"
        "  /whales           — On-chain whale moves >$100K\n"
        "  /movers           — Top 24h gainers & losers\n"
        "  /yields           — Top DeFi yield/APR pools\n"
        "  /profiler <addr>  — Wallet profiler (ETH + tokens)\n"
        "  /top              — Top coins by market cap\n"
        "  /convert <amt> <f> <t> — Crypto converter\n"
        "  /global           — Global market overview\n"
        "  /categories       — Top crypto categories\n"
        "  /alerts           — List / create / delete alerts\n"
        "       e.g. /alerts BTC above 100000\n"
        "  /watchlist        — Your coin watchlist (/add, /rm)\n"
        "  /portfolio <id>   — Shareable portfolio value\n"
        "  /premium          — Unlock premium features\n"
        "  /manage           — Manage subscription\n"
        "  /referral         — Referral link & rewards\n"
        "  /donate           — Support development\n"
        "  /help             — This message\n\n"
        "Built autonomously — github.com/ghassan-gaidi/crypto-empire"
    )

    if chat_type == "private":
        app = _get_app()
        code = app.get_or_create_ref_code(chat_id)
        bot_username = os.environ.get("BOT_USERNAME", "Crypt0Emp1reBot")
        cmds += (
            f"\n\n❧ Referral Program — Earn Free Premium!\n"
            f"Invite friends to add me to their groups.\n"
            f"3 referrals = 1 free month of Premium!\n\n"
            f"Your referral link:\n"
            f"https://t.me/{bot_username}?start=ref_{code}\n\n"
            f"Or add me to a group:\n"
            f"https://t.me/{bot_username}?startgroup=ref_{code}"
        )

    if chat_type == "group":
        cmds += (
            "\n\nTip: Add me to more groups and use /btc /eth /sol "
            "for quick prices anywhere."
        )

    if ref_code:
        cmds += "\n\n❧ Referral recorded! Thanks for spreading the word."

    cmds += "\n\n" + wire_foot("START", _when())

    send_message(chat_id, intro + cmds)

def cmd_price(chat_id, args):
    if not args:
        send_message(chat_id, "Usage: /price <coin_id>  (e.g. /price bitcoin)\nTip: use /btc, /eth, /sol shortcuts.")
        return
    coin = args[0].lower().strip()
    app = _get_app()
    data = app.fetch_sync(f"{app.COINGECKO_API}/simple/price?ids={coin}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true")
    if data and coin in data:
        d = data[coin]
        usd = d.get("usd", 0)
        chg = d.get("usd_24h_change")
        mc = d.get("usd_market_cap", 0)
        vol = d.get("usd_24h_vol", 0)
        msg = wire_block(
            coin.upper(),
            [
                leader_row("price", fmt_price(usd)),
                leader_row("24h", fmt_change(chg)),
                leader_row("m.cap", fmt_market_cap(mc)),
                leader_row("24h vol", fmt_market_cap(vol)),
            ],
            when=_when(),
        )
    else:
        msg = f"Coin '{coin}' not found. Try /price bitcoin."
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
    lines = [fmt_header("GAS TRACKER")]
    if eth_price:
        lines.append(f"\n{eth_price.strip()}")
    rows = []
    for name, url in chains.items():
        try:
            r = requests.post(url, json={"jsonrpc":"2.0","method":"eth_gasPrice","params":[],"id":1}, timeout=5)
            res = r.json()
            if "result" in res:
                gwei = int(res["result"], 16) / 1e9
                rows.append(leader_row(f"{name:<10}", f"{gwei:.1f} gwei"))
            else:
                rows.append(leader_row(f"{name:<10}", "error"))
        except Exception:
            rows.append(leader_row(f"{name:<10}", "error"))
    lines += rows
    lines += ["", wire_foot("GAS TRACKER", _when())]
    send_message(chat_id, "\n".join(lines))

def cmd_fear(chat_id, args=None):
    app = _get_app()
    data = app.fetch_sync("https://api.alternative.me/fng/?limit=1")
    if data and "data" in data and data["data"]:
        d = data["data"][0]
        val = d.get("value", "?")
        cls = d.get("value_classification", "N/A")
        tone = TG["up"] if int(val) > 50 else TG["down"] if int(val) < 25 else "—"
        msg = wire_block(
            "FEAR & GREED",
            [leader_row("value", f"{val}/100"), leader_row("state", f"{cls.upper()} {tone}")],
            when=_when(),
        )
    else:
        msg = "Fear & Greed unavailable"
    send_message(chat_id, msg)

def cmd_trending(chat_id, args=None):
    send_typing(chat_id)
    app = _get_app()
    data = app.fetch_sync(f"{app.COINGECKO_API}/search/trending")
    if data and "coins" in data:
        lines = [fmt_header("TRENDING COINS")]
        for i, coin in enumerate(data["coins"][:10], 1):
            item = coin.get("item", {})
            name = item.get("name", "?")
            sym = (item.get("symbol") or "").upper()
            rank = item.get("market_cap_rank") or "--"
            lines.append(bullet(f"{name} ({sym}) — Rank #{rank}"))
        lines += ["", wire_foot("TRENDING", _when())]
        msg = "\n".join(lines)
    else:
        msg = TG["silent"]
    send_message(chat_id, msg)

def cmd_launches(chat_id, args=None):
    send_typing(chat_id)
    app = _get_app()
    data = app.fetch_sync("https://crypto-empire-ten.vercel.app/api/launches")
    if data and "launches" in data:
        launches = data["launches"]
        lines = [fmt_header("TOKEN LAUNCH CALENDAR")]
        upcoming = [l for l in launches if l["status"] == "upcoming"][:5]
        if upcoming:
            for l in upcoming:
                dd = l.get("days_until", "?")
                lines.append(bullet(f"{l['name']} (${l['symbol']})"))
                lines.append(f"   {l['type']} — {dd} days · {l['chain']}")
        else:
            lines.append("\nNo upcoming launches right now.")
        lines += ["", wire_foot("LAUNCHES", _when())]
        msg = "\n".join(lines)
    else:
        msg = "Launch calendar unavailable. See https://crypto-empire-ten.vercel.app/launches"
    send_message(chat_id, msg)

def cmd_news(chat_id, args=None):
    send_typing(chat_id)
    app = _get_app()
    items = app.fetch_rss("https://cointelegraph.com/rss")
    if items:
        lines = [fmt_header("CRYPTO NEWS")]
        for item in items[:5]:
            lines.append(f"\n{bullet(item['title'])}")
            if item.get('date'):
                lines.append(f"  {item['date'][:16]}")
        lines += ["", wire_foot("NEWS", _when())]
        msg = "\n".join(lines)
    else:
        msg = TG["silent"]
    send_message(chat_id, msg)

def cmd_wallet(chat_id, args):
    if not args:
        send_message(chat_id, "Usage: /wallet <0x address>")
        return
    addr = args[0].strip()
    if not addr.startswith("0x"):
        send_message(chat_id, "Invalid address — must start with 0x")
        return
    send_typing(chat_id)
    app = _get_app()
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
    lines = [fmt_header("WALLET"), "", f"{addr[:10]}...{addr[-6:]}"]
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
                lines.append(leader_row(f"{name:<10}", f"{bal_s}  ${usd:,.2f}"))
            else:
                lines.append(leader_row(f"{name:<10}", "error"))
        except Exception:
            lines.append(leader_row(f"{name:<10}", "error"))
    lines += ["", SEP, leader_row("total", f"${total:,.2f}"), "", wire_foot("WALLET", _when())]
    send_message(chat_id, "\n".join(lines))

def cmd_tvl(chat_id, args=None):
    app = _get_app()
    data = app.fetch_sync("https://api.llama.fi/v2/historicalChainTvl/Ethereum")
    if data and len(data) > 0:
        latest = data[-1]
        tvl_b = latest.get("tvl", 0) / 1e9
        msg = wire_block(
            "ETH TVL",
            [leader_row("tvl", f"${tvl_b:.2f}B"), leader_row("source", "DeFiLlama")],
            when=_when(),
        )
    else:
        msg = "TVL unavailable"
    send_message(chat_id, msg)

def cmd_dexs(chat_id, args=None):
    send_typing(chat_id)
    app = _get_app()
    data = app.fetch_sync("https://api.llama.fi/overview/dexs")
    if data and "protocols" in data:
        top = sorted(data["protocols"], key=lambda x: x.get("total24h", 0) or 0, reverse=True)[:10]
        lines = [fmt_header("TOP DEXES (24h Vol)")]
        for i, d in enumerate(top, 1):
            name = d.get("displayName") or d.get("name", "?")
            vol = d.get("total24h", 0) or 0
            vol_s = f"${vol/1e6:.1f}M" if vol >= 1e6 else f"${vol/1e3:.0f}K"
            chg = d.get("change_1d", 0) or 0
            arrow = "▲" if chg >= 0 else "▼"
            lines.append(bullet(f"{name} — {vol_s} {arrow}{chg:+.1f}%"))
        lines += ["", wire_foot("DEXES", _when())]
        msg = "\n".join(lines)
    else:
        msg = TG["silent"]
    send_message(chat_id, msg)

def cmd_whales(chat_id, args=None):
    send_typing(chat_id)
    msg_id = send_loading(chat_id, "WHALE TRACKER")
    app = _get_app()
    data = app.fetch_sync("https://crypto-empire-ten.vercel.app/api/whales?limit=5")
    if data and "moves" in data and data["moves"]:
        lines = [fmt_header("WHALE TRACKER")]
        for m in data["moves"]:
            usd = f"${m['usdValue']:,.0f}" if m.get("usdValue") else f"{m['value']:,.2f}"
            addr_s = f"{m['to'][:6]}...{m['to'][-4:]}"
            lines.append("\n" + bullet(f"{usd} {m['token']}"))
            lines.append(f"   → {addr_s}  · {m['txHash'][:8]}...")
        lines += [
            "",
            SEP,
            leader_row("updated", f"{data['lastUpdated'][:19]} UTC"),
            leader_row("tracked", "USDT/USDC/WBTC"),
            "",
            wire_foot("WHALES", _when()),
        ]
        msg = "\n".join(lines)
    else:
        msg = TG["silent"]
    edit_or_send(chat_id, msg_id, msg)

def cmd_premium(chat_id, args=None):
    send_typing(chat_id)
    msg = (
        f"{fmt_header('CRYPTO EMPIRE PREMIUM')}\n\n"
        "Unlock premium features:\n\n"
        f"{bullet('Telegram whale alerts — real-time $100K+ push')}\n"
        f"{bullet('Multi-wallet portfolio — track 6+ ETH addresses')}\n"
        f"{bullet('Priority price alerts — instant threshold notifications')}\n"
        f"{bullet('Premium sentiment indicators — buy/sell signals')}\n"
        f"{bullet('Ad-free across all pages')}\n"
        f"{bullet('Support development')}\n\n"
        "Subscribe:\n"
        "https://buy.polar.sh/polar_cl_6tzQXPw5VwincKlZdlyR2aM9XGePVbhfzWCb13P42ox\n\n"
        "Price: $9.99/month — Cancel anytime\n"
        "Powered by Polar.sh\n\n"
        "Already subscribed? Manage at:\n"
        "https://crypto-empire-ten.vercel.app/premium\n\n"
        "Like the bot? Donate ETH:\n"
        "0x29021dd5306D7b3b6608a2bc8276D33c1200C7Ef\n\n"
        + wire_foot("PREMIUM", _when())
    )
    send_message(chat_id, msg)

def cmd_manage(chat_id, args=None):
    send_typing(chat_id)
    url = f"https://crypto-empire-ten.vercel.app/premium?customer_id={chat_id}"
    msg = (
        f"{fmt_header('MANAGE SUBSCRIPTION')}\n\n"
        "Open the web portal to view, upgrade, or cancel:\n\n"
        f"{url}\n\n"
        "Note: Your Telegram ID links your subscription.\n\n"
        + wire_foot("MANAGE", _when())
    )
    send_message(chat_id, msg)

def cmd_referral(chat_id, args=None):
    app = _get_app()
    code = app.get_or_create_ref_code(chat_id)
    stats = app.get_ref_stats(chat_id)
    bot_username = os.environ.get("BOT_USERNAME", "Crypt0Emp1reBot")
    refs = stats["referred_count"]
    rewards = stats["rewards_earned"]
    next_reward = 3 - (refs % 3) if refs % 3 != 0 else 3
    has_premium = app._is_premium(str(chat_id))
    msg = (
        f"{fmt_header('REFERRAL PROGRAM')}\n\n"
        f"Your referrals: {refs}\n"
        f"Premium months earned: {rewards}\n"
        f"Next reward in: {next_reward} more referrals\n\n"
        "3 referrals = 1 free month of Premium\n\n"
        "Your unique referral link:\n"
        f"https://t.me/{bot_username}?start=ref_{code}\n\n"
        "Add me to your group:\n"
        f"https://t.me/{bot_username}?startgroup=ref_{code}\n\n"
    )
    if not has_premium:
        msg += "Already subscribed? Share your link and earn free months!"
    else:
        msg += "You're premium already — each reward extends your subscription by 1 month."
    msg += "\n\n" + wire_foot("REFERRAL", _when())
    send_message(chat_id, msg)

def cmd_donate(chat_id, args=None):
    send_typing(chat_id)
    msg = (
        f"{fmt_header('SUPPORT DEVELOPMENT')}\n\n"
        "All tools are free. If you find this bot useful, consider a donation.\n\n"
        "ETH / BSC / POLYGON / ARBITRUM / BASE:\n"
        "0x29021dd5306D7b3b6608a2bc8276D33c1200C7Ef\n\n"
        "BITCOIN:\n"
        "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh\n\n"
        "Every donation keeps the bot running. Thank you.\n\n"
        + wire_foot("DONATE", _when())
    )
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
            bars = 30
            step = len(prices) / bars
            sample = [prices[min(int(i * step), len(prices) - 1)] for i in range(bars)]
            mn, mx = min(sample), max(sample)
            rng = mx - mn if mx > mn else 1
            h = 8
            rows = []
            for row in range(h - 1, -1, -1):
                threshold = mn + (row / (h - 1)) * rng
                line = ""
                for p in sample:
                    line += "█" if p >= threshold else " "
                rows.append(line)
            chart = "\n".join(rows)
            arrow = " ▲" if sample[-1] >= sample[0] else " ▼"
            price_s = fmt_price(sample[-1])
            msg = f"{fmt_header(f'{coin.upper()} 7d{arrow}')}\n{TG['rule']}\n{chart}\n{TG['rule']}\n{price_s}"
        else:
            msg = f"No sparkline data for {coin}"
    else:
        msg = f"Coin '{coin}' not found"
    send_message(chat_id, msg)

# ---------------------------------------------------------------------------
# New command handlers (v3.5 expansion)
# ---------------------------------------------------------------------------

def cmd_movers(chat_id, args=None):
    send_typing(chat_id)
    msg_id = send_loading(chat_id, "MARKET MOVERS")
    app = _get_app()
    data = app.fetch_sync("https://crypto-empire-ten.vercel.app/api/movers")
    if data and data.get("top_gainers"):
        g = data["top_gainers"][:5]
        l = data["top_losers"][:5]
        lines = [fmt_header("MARKET MOVERS (24h)")]
        lines.append(f"\n▲ TOP GAINERS")
        for c in g:
            sym = (c.get("symbol") or "").upper()
            chg = c.get("change", 0) or 0
            p = c.get("price", "?")
            lines.append(bullet(f"{sym} ▲ {chg:.2f}%  ${p}"))
        lines.append(f"\n▼ TOP LOSERS")
        for c in l:
            sym = (c.get("symbol") or "").upper()
            chg = c.get("change", 0) or 0
            p = c.get("price", "?")
            lines.append(bullet(f"{sym} ▼ {abs(chg):.2f}%  ${p}"))
        lines += ["", wire_foot("MOVERS", _when())]
        msg = "\n".join(lines)
    else:
        msg = TG["silent"]
    edit_or_send(chat_id, msg_id, msg)

def cmd_yields(chat_id, args=None):
    send_typing(chat_id)
    msg_id = send_loading(chat_id, "YIELD AGGREGATOR")
    app = _get_app()
    data = app.fetch_sync("https://crypto-empire-ten.vercel.app/api/yields")
    if data:
        lines = [fmt_header("YIELD AGGREGATOR")]
        for cat in ["lending", "stablecoin"]:
            pools = data.get(cat, [])[:3]
            if pools:
                lines.append(f"\n{cat.upper()}")
                for p in pools:
                    apy = p.get("apy", 0) or 0
                    sym = p.get("symbol", "?")
                    chain = p.get("chain", "?")
                    tvl = p.get("tvlUsd", 0) or 0
                    tvl_s = f"${tvl/1e6:.1f}M" if tvl >= 1e6 else f"${tvl/1e3:.0f}K"
                    lines.append(bullet(f"{sym} {apy:.2f}% — {chain} · {tvl_s}"))
        lines += ["", SEP, "crypto-empire-ten.vercel.app/yields", "", wire_foot("YIELDS", _when())]
        msg = "\n".join(lines)
    else:
        msg = TG["silent"]
    edit_or_send(chat_id, msg_id, msg)

def cmd_profiler(chat_id, args):
    if not args:
        send_message(chat_id, "Usage: /profiler <0x address>")
        return
    addr = args[0].strip()
    if not addr.startswith("0x"):
        send_message(chat_id, "Invalid address — must start with 0x")
        return
    send_typing(chat_id)
    msg_id = send_loading(chat_id, "WALLET PROFILER")
    app = _get_app()
    data = app.fetch_sync(f"https://crypto-empire-ten.vercel.app/api/profiler/{addr}")
    if data:
        eth_bal = data.get("ethBalance", "0")
        usd_val = data.get("totalUsdValue", 0) or 0
        tokens = data.get("tokens", [])
        tx_count = data.get("txCount", "?")
        lines = [
            fmt_header("WALLET PROFILER"),
            "",
            f"{addr[:10]}...{addr[-6:]}",
            "",
            leader_row("eth", f"{eth_bal}  ${usd_val:,.2f}"),
            leader_row("txs", f"{tx_count}"),
        ]
        if tokens:
            lines.append(f"\nTOKENS:")
            for t in tokens[:8]:
                sym = t.get("symbol", "?")
                bal = t.get("balance", "0")
                val = t.get("usdValue", 0) or 0
                lines.append(bullet(f"{sym} {bal}  ${val:,.2f}"))
        lines += ["", wire_foot("PROFILER", _when())]
        msg = "\n".join(lines)
    else:
        msg = f"Profiler unavailable for {addr[:10]}..."
    edit_or_send(chat_id, msg_id, msg)

def cmd_top(chat_id, args=None):
    send_typing(chat_id)
    msg_id = send_loading(chat_id, "TOP COINS")
    app = _get_app()
    data = app.fetch_sync(
        f"{app.COINGECKO_API}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&sparkline=false"
    )
    if data:
        lines = [fmt_header("TOP COINS (by Market Cap)")]
        for i, c in enumerate(data, 1):
            sym = (c.get("symbol") or "").upper()
            p = c.get("current_price", 0) or 0
            chg = c.get("price_change_percentage_24h", 0) or 0
            mc = c.get("market_cap", 0) or 0
            arrow = "▲" if chg >= 0 else "▼"
            p_s = f"${p:,.2f}" if p >= 1 else f"${p:.8f}" if p else "N/A"
            lines.append(leader_row(f"{i:2}. {sym:<6}", f"{p_s}  {arrow}{abs(chg):.2f}%"))
        lines += ["", wire_foot("TOP", _when())]
        msg = "\n".join(lines)
    else:
        msg = TG["silent"]
    edit_or_send(chat_id, msg_id, msg)

def cmd_convert(chat_id, args):
    if len(args) < 3:
        send_message(chat_id, "Usage: /convert <amount> <from> <to>\n  e.g., /convert 1 btc usd")
        return
    try:
        amount = float(args[0])
    except ValueError:
        send_message(chat_id, "Invalid amount.")
        return
    from_coin = args[1].lower()
    to_currency = args[2].lower()
    send_typing(chat_id)
    app = _get_app()
    alias = {"usd": "usd", "usdt": "tether", "usdc": "usd-coin",
             "btc": "bitcoin", "eth": "ethereum", "sol": "solana",
             "bnb": "binancecoin", "xrp": "xrp", "ada": "cardano"}
    from_id = alias.get(from_coin, from_coin)
    to_id = alias.get(to_currency, to_currency)
    ids = [from_id]
    if to_id not in ("usd", from_id):
        ids.append(to_id)
    price_data = app.fetch_sync(
        f"{app.COINGECKO_API}/simple/price?ids={','.join(ids)}&vs_currencies=usd"
    )
    if not price_data:
        send_message(chat_id, f"Could not fetch price for {from_coin}.")
        return
    from_usd = (price_data.get(from_id) or {}).get("usd", 0)
    if from_usd == 0:
        send_message(chat_id, f"Could not find '{from_coin}'.")
        return
    from_total = amount * from_usd
    if to_currency in ("usd",):
        msg = f"{fmt_header('CONVERT')}\n\n{amount} {from_coin.upper()} = ${from_total:,.2f}"
    else:
        to_usd = (price_data.get(to_id) or {}).get("usd", 0)
        if to_usd == 0:
            send_message(chat_id, f"Could not find '{to_currency}'.")
            return
        result = from_total / to_usd
        msg = f"{fmt_header('CONVERT')}\n\n{amount} {from_coin.upper()} = {result:,.6f} {to_currency.upper()}"
    send_message(chat_id, msg)

# ---------------------------------------------------------------------------
# Watchlist — server-side per-chat storage via shared SQLite alerts DB
# ---------------------------------------------------------------------------

def _watchlist_conn():
    app = _get_app()
    conn = sqlite3.connect(str(app.DB_PATH))
    conn.execute("CREATE TABLE IF NOT EXISTS watchlists (chat_id TEXT PRIMARY KEY, coins TEXT DEFAULT '[]', updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    return conn


def _watchlist_get(chat_id):
    conn = _watchlist_conn()
    try:
        row = conn.execute("SELECT coins FROM watchlists WHERE chat_id = ?",
                           (str(chat_id),)).fetchone()
        return json.loads(row[0]) if row and row[0] else []
    except Exception:
        return []
    finally:
        conn.close()


def _watchlist_set(chat_id, coins):
    conn = _watchlist_conn()
    try:
        conn.execute("INSERT OR REPLACE INTO watchlists (chat_id, coins) VALUES (?, ?)",
                     (str(chat_id), json.dumps(coins[:25])))
        conn.commit()
    finally:
        conn.close()


def cmd_watchlist(chat_id, args=None):
    """Show your watchlist with live prices. Managed with /add and /rm."""
    coins = _watchlist_get(chat_id)
    if not coins:
        send_message(chat_id, (
            f"{fmt_header('WATCHLIST')}\n\n"
            "Empty — the wire is dark until something is pinned.\n"
            "Add coins: /add btc, /add eth,sol\n\n"
            "Tip: /btc /eth /sol work too."
        ))
        return
    send_typing(chat_id)
    msg_id = send_loading(chat_id, "WATCHLIST")
    app = _get_app()
    ids = ",".join(coins)
    data = app.fetch_sync(
        f"{app.COINGECKO_API}/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
    ) or {}
    lines = [fmt_header(f"WATCHLIST ({len(coins)})")]
    for cid in coins:
        d = data.get(cid, {})
        p, chg = d.get("usd"), d.get("usd_24h_change")
        if p is None:
            lines.append(f"\n{cid.upper():<12} unavailable")
            continue
        arrow = "▲" if (chg or 0) >= 0 else "▼"
        lines.append(f"\n{cid.upper():<12} {fmt_price(p)}  {arrow}{abs(chg or 0):.2f}%")
    lines.append("\n/add <coin> add · /rm <coin> remove")
    edit_or_send(chat_id, msg_id, "\n".join(lines))


def cmd_add(chat_id, args):
    """Add coin(s) to your watchlist: /add btc  or  /add eth,sol,link"""
    if not args:
        send_message(chat_id, "Usage: /add <coin>  or  /add eth,sol,link")
        return
    app = _get_app()
    requested = [c.strip().lower() for a in args for c in a.split(",") if c.strip()]
    resolved = []
    for sym in requested:
        cg_id = SYMBOL_TO_ID.get(sym, sym)
        # Verify it exists on CoinGecko before storing
        data = app.fetch_sync(f"{app.COINGECKO_API}/simple/price?ids={cg_id}&vs_currencies=usd")
        if data and cg_id in data:
            resolved.append(cg_id)
    coins = _watchlist_get(chat_id)
    added = [c for c in resolved if c not in coins]
    coins.extend(added)
    _watchlist_set(chat_id, coins)
    unknown = [s for s in requested if SYMBOL_TO_ID.get(s, s) not in resolved]
    parts = [fmt_header("WATCHLIST")]
    if added:
        parts.append(f"\n❧ Added: {', '.join(c.upper() for c in added)}")
    else:
        parts.append("\nNothing new (already tracked or unknown).")
    if unknown:
        parts.append(f"\n— Unknown: {', '.join(unknown)}")
    parts.append(f"\nTotal: {len(coins)} coins. See /watchlist")
    parts += ["", wire_foot("WATCHLIST", _when())]
    send_message(chat_id, "\n".join(parts))


def cmd_rm(chat_id, args):
    """Remove coin(s) from your watchlist: /rm btc  or  /rm all"""
    if not args:
        send_message(chat_id, "Usage: /rm <coin>  or  /rm all")
        return
    coins = _watchlist_get(chat_id)
    if args[0].lower() in ("all", "clear"):
        _watchlist_set(chat_id, [])
        send_message(chat_id, f"{fmt_header('WATCHLIST')}\n\nCleared. Add with /add\n\n" + wire_foot("WATCHLIST", _when()))
        return
    wanted = {SYMBOL_TO_ID.get(c.strip().lower(), c.strip().lower())
              for a in args for c in a.split(",")}
    kept = [c for c in coins if c not in wanted]
    _watchlist_set(chat_id, kept)
    send_message(chat_id, f"{fmt_header('WATCHLIST')}\n\nRemoved {len(coins) - len(kept)}. {len(kept)} left. See /watchlist\n\n" + wire_foot("WATCHLIST", _when()))


def cmd_portfolio(chat_id, args):
    """Link to your shareable portfolio page + top-line value.

    Usage: /portfolio <id>  — e.g. /portfolio a1b2c3d4
    Create one on the dashboard: /portfolio page → "create".
    """
    if not args:
        send_message(chat_id, (
            f"{fmt_header('PORTFOLIO')}\n\n"
            "Usage: /portfolio <id>\n"
            "Create a shareable portfolio on the dashboard:\n"
            "https://crypto-empire-ten.vercel.app/portfolio\n\n"
            "Up to 5 wallets free, unlimited with Premium.\n\n"
            + wire_foot("PORTFOLIO", _when())
        ))
        return
    pid = args[0].strip().lower()
    base = os.environ.get("BASE_URL", "https://crypto-empire-ten.vercel.app")
    try:
        r = requests.get(f"{base}/api/portfolio/{pid}", timeout=12)
        data = r.json() if r.ok else {}
    except Exception:
        data = {}
    if not data or data.get("error"):
        send_message(chat_id, f"{fmt_header('PORTFOLIO')}\n\n— Portfolio {pid} not found.\n\n" + wire_foot("PORTFOLIO", _when()))
        return
    total = data.get("total_usd", 0) or 0
    wallets = data.get("wallets", [])
    lines = [fmt_header(f"PORTFOLIO — {data.get('name', pid)}"),
             leader_row("total", f"${total:,.2f}"),
             leader_row("wallets", f"{len(wallets)}")]
    for w in wallets[:5]:
        lines.append(bullet(f"{w.get('address','')[:10]}…  ${w.get('total_usd', 0):,.2f}"))
    lines += ["", f"Full view: {base}/portfolio/{pid}", "", wire_foot("PORTFOLIO", _when())]
    send_message(chat_id, "\n".join(lines))


def cmd_alerts(chat_id, args=None):
    """List active alerts, create new ones, or delete by ID.

    Usage: /alerts                     — list active
           /alerts BTC above 100000    — create
           /alerts BTC below 50000     — create
           /alerts del <id>            — delete
    """
    app = _get_app()
    base = os.environ.get("BASE_URL", "https://crypto-empire-ten.vercel.app")

    # Delete path
    if args and args[0].lower() in ("del", "delete", "rm", "remove") and len(args) >= 2:
        try:
            rid = int(args[1])
        except ValueError:
            send_message(chat_id, f"{fmt_header('PRICE ALERTS')}\n\nUsage: /alerts del <id>\nSee IDs with /alerts\n\n" + wire_foot("ALERTS", _when()))
            return
        try:
            r = requests.delete(f"{base}/api/alerts",
                                params={"chat_id": str(chat_id), "rowid": rid}, timeout=10)
            ok = r.ok and r.json().get("deleted")
            send_message(chat_id, f"{fmt_header('PRICE ALERTS')}\n\n{'❧ Alert deleted.' if ok else '— No alert with that ID.'}\n\n" + wire_foot("ALERTS", _when()))
        except Exception as e:
            send_message(chat_id, f"{fmt_header('PRICE ALERTS')}\n\nError deleting alert: {e}")
        return

    # Create path: /alerts BTC above 100000
    if args and len(args) >= 3 and args[1].lower() in ("above", "below", ">", "<", "over", "under"):
        coin = args[0].upper()
        direction = "above" if args[1].lower() in ("above", ">", "over") else "below"
        try:
            target = float(args[2].replace(",", "").replace("$", ""))
            if target <= 0:
                raise ValueError
        except ValueError:
            send_message(chat_id, f"{fmt_header('PRICE ALERTS')}\n\nUsage: /alerts BTC above 100000\n\n" + wire_foot("ALERTS", _when()))
            return
        try:
            r = requests.post(f"{base}/api/alerts",
                              json={"coin": coin, "target": target,
                                    "chat_id": str(chat_id), "direction": direction},
                              timeout=10)
            data = r.json() if r.ok else {}
            if r.ok and data.get("status") == "ok":
                send_message(chat_id, f"{fmt_header('PRICE ALERTS')}\n\n❧ {data.get('message')}\nI'll DM you when it triggers.\n\n" + wire_foot("ALERTS", _when()))
            else:
                send_message(chat_id, f"{fmt_header('PRICE ALERTS')}\n\n— {data.get('error', 'Could not save alert.')}\n\n" + wire_foot("ALERTS", _when()))
        except Exception as e:
            send_message(chat_id, f"{fmt_header('PRICE ALERTS')}\n\nError saving alert: {e}")
        return

    # List path
    try:
        r = requests.get(f"{base}/api/alerts", params={"chat_id": str(chat_id)}, timeout=10)
        rows = r.json().get("alerts", []) if r.ok else []
    except Exception:
        rows = []
    if not rows:
        msg = (
            f"{fmt_header('PRICE ALERTS')}\n\n"
            "No active alerts — the wire is quiet.\n\n"
            "Create one:\n"
            "/alerts BTC above 100000\n"
            "/alerts ETH below 2000\n\n"
            "Or set alerts on the dashboard:\n"
            "https://crypto-empire-ten.vercel.app/#alerts\n\n"
            "Premium users get priority alert delivery.\n\n"
            + wire_foot("ALERTS", _when())
        )
    else:
        lines = [fmt_header(f"YOUR ALERTS ({len(rows)})")]
        for row in rows[:10]:
            arrow = "▲" if (row.get("direction") or "above") == "above" else "▼"
            lines.append(leader_row(f"#{row.get('rowid')} {row.get('coin')} {arrow}", f"${row.get('target'):,.2f}"))
        lines += ["", "Delete: /alerts del <id>", "", wire_foot("ALERTS", _when())]
        msg = "\n".join(lines)
    send_message(chat_id, msg)

# ---------------------------------------------------------------------------
# v3.7 expansion — global market + categories
# ---------------------------------------------------------------------------

def cmd_global(chat_id, args=None):
    """Global crypto market overview: total cap, volume, BTC dominance."""
    send_typing(chat_id)
    msg_id = send_loading(chat_id, "GLOBAL MARKET")
    app = _get_app()
    data = app.fetch_sync(f"{app.COINGECKO_API}/global")
    if data and "data" in data:
        d = data["data"]
        active = d.get("active_cryptocurrencies", "?")
        total_mc = d.get("total_market_cap", {}).get("usd", 0)
        total_vol = d.get("total_volume", {}).get("usd", 0)
        btc_dom = d.get("market_cap_percentage", {}).get("btc", 0)
        eth_dom = d.get("market_cap_percentage", {}).get("eth", 0)
        mc_chg = d.get("market_cap_change_percentage_24h_usd", 0) or 0
        exchanges = d.get("markets", "?")
        def fmt_b(n):
            if n >= 1e12: return f"${n/1e12:.2f}T"
            if n >= 1e9:  return f"${n/1e9:.2f}B"
            return f"${n:,.0f}"
        arrow = "▲" if mc_chg >= 0 else "▼"
        lines = [
            fmt_header("GLOBAL MARKET"),
            "",
            leader_row("active coins", f"{active}"),
            leader_row("exchanges", f"{exchanges}"),
            "",
            leader_row("market cap", fmt_b(total_mc)),
            leader_row("24h volume", fmt_b(total_vol)),
            leader_row("24h change", f"{arrow}{abs(mc_chg):.2f}%"),
            "",
            leader_row("btc dom.", f"{btc_dom:.1f}%"),
            leader_row("eth dom.", f"{eth_dom:.1f}%"),
            "",
            wire_foot("GLOBAL", _when()),
        ]
        msg = "\n".join(lines)
    else:
        msg = TG["silent"]
    edit_or_send(chat_id, msg_id, msg)

def cmd_categories(chat_id, args=None):
    """Top crypto categories by market cap from CoinGecko."""
    send_typing(chat_id)
    msg_id = send_loading(chat_id, "CATEGORIES")
    app = _get_app()
    data = app.fetch_sync(f"{app.COINGECKO_API}/coins/categories")
    if data and isinstance(data, list):
        sorted_cats = sorted(data, key=lambda x: x.get("market_cap", 0) or 0, reverse=True)[:12]
        lines = [fmt_header("TOP CATEGORIES (by Market Cap)")]
        for i, c in enumerate(sorted_cats, 1):
            name = c.get("name", "?")
            mc = c.get("market_cap", 0) or 0
            chg = c.get("market_cap_change_24h", 0) or 0
            if mc >= 1e9:
                mc_s = f"${mc/1e9:.1f}B"
            elif mc >= 1e6:
                mc_s = f"${mc/1e6:.1f}M"
            else:
                mc_s = f"${mc:,.0f}"
            arrow = "▲" if chg >= 0 else "▼"
            lines.append(bullet(f"{i:2}. {name} — {mc_s} {arrow}{abs(chg):.1f}%"))
        lines += ["", wire_foot("CATEGORIES", _when())]
        msg = "\n".join(lines)
    else:
        msg = TG["silent"]
    edit_or_send(chat_id, msg_id, msg)

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
        bot_username = os.environ.get("BOT_USERNAME", "Crypt0Emp1reBot")
        welcome = (
            f"{fmt_header('BOT ADDED TO ' + group_title.upper())}\n\n"
            f"Type /btc, /eth, /sol or any coin ticker for instant prices.\n"
            f"Use /help to see all commands.\n\n"
            f"More at crypto-empire-ten.vercel.app\n\n"
            f"Earn Free Premium\n"
            f"Share this link with friends to earn rewards:\n"
            f"https://t.me/{bot_username}?start=ref_your_code\n"
            f"3 referrals = 1 free month!"
        )
        send_message(chat_id, welcome)
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
    "premium":   cmd_premium,
    "subscribe": cmd_premium,
    "manage":    cmd_manage,
    "referral":  cmd_referral,
    "ref":       cmd_referral,
    "affiliate": cmd_referral,
    "donate":    cmd_donate,
    "donation":  cmd_donate,
    "support":   cmd_donate,
    "movers":    cmd_movers,
    "gainers":   cmd_movers,
    "losers":    cmd_movers,
    "yields":    cmd_yields,
    "yield":     cmd_yields,
    "apy":       cmd_yields,
    "profiler":  cmd_profiler,
    "top":       cmd_top,
    "convert":   cmd_convert,
    "conv":      cmd_convert,
    "alerts":    cmd_alerts,
    "alert":     cmd_alerts,
    "myalerts":  cmd_alerts,
    "watchlist": cmd_watchlist,
    "watch":     cmd_watchlist,
    "wl":        cmd_watchlist,
    "add":       cmd_add,
    "rm":        cmd_rm,
    "remove":    cmd_rm,
    "portfolio": cmd_portfolio,
    "pf":        cmd_portfolio,
    # v3.7 expansion
    "global":    cmd_global,
    "market":    cmd_global,
    "categories": cmd_categories,
    "cats":      cmd_categories,
    "sectors":   cmd_categories,
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
