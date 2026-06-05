#!/usr/bin/env python3
"""Whale Tracker — monitors on-chain large token transfers via eth_getLogs.

Polls a public Ethereum RPC for Transfer events on major tokens (USDT, USDC,
WBTC), filters those exceeding a USD-value threshold (~$100K), and maintains a
cached feed for the /whales page. Optionally sends Telegram alerts.
"""
import os
import json
import sys
import requests
from datetime import datetime, timezone
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────
RPC_URL = os.environ.get("WHALE_RPC_URL", "https://ethereum-rpc.publicnode.com")

TOKENS = {
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
}

THRESHOLDS = {"USDT": 100_000, "USDC": 100_000, "WBTC": 2}
DECIMALS = {"USDT": 6, "USDC": 6, "WBTC": 8}

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

DATA_DIR = Path(os.environ.get("DATA_DIR", "/tmp/crypto-empire-data"))
CACHE_FILE = DATA_DIR / "whale_cache.json"

# ── RPC Helpers ─────────────────────────────────────────────────────────

_session = requests.Session()


def rpc_call(method, params):
    resp = _session.post(RPC_URL, json={
        "jsonrpc": "2.0", "method": method, "params": params, "id": 1
    }, timeout=20)
    data = resp.json()
    if "error" in data:
        raise Exception(f"RPC error [{method}]: {data['error']}")
    return data["result"]


def parse_address(hex64):
    """Padded 32-byte hex → address 0x…"""
    return "0x" + hex64[-40:].lower()


def to_int(hex_str):
    return int(hex_str, 16)


# ── Token Transfers ─────────────────────────────────────────────────────

def fetch_transfers(token_name, token_addr, from_block, to_block):
    logs = rpc_call("eth_getLogs", [{
        "address": token_addr,
        "fromBlock": hex(from_block),
        "toBlock": hex(to_block),
        "topics": [TRANSFER_TOPIC]
    }])
    moves = []
    decimals = DECIMALS[token_name]
    threshold = THRESHOLDS[token_name]
    for log in logs:
        topics = log.get("topics", [])
        if len(topics) < 3:
            continue
        raw_val = to_int(log["data"])
        if raw_val == 0:
            continue
        adj = raw_val / (10 ** decimals)
        if adj >= threshold:
            moves.append({
                "txHash": log["transactionHash"],
                "token": token_name,
                "from": parse_address(topics[1]),
                "to": parse_address(topics[2]),
                "value": adj,
                "blockNumber": to_int(log["blockNumber"]),
                "logIndex": to_int(log["logIndex"]),
                "tokenAddress": token_addr,
            })
    return moves


# ── Cache ───────────────────────────────────────────────────────────────

def load_cache():
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            pass
    return {"lastBlock": None, "moves": [], "lastUpdated": None}


def save_cache(cache):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2, default=str))


# ── Price Enrichment ────────────────────────────────────────────────────

def enrich_usd(moves):
    """Fetch current prices and compute USD value for each move."""
    ids = {"USDT": "tether", "USDC": "usd-coin", "WBTC": "wrapped-bitcoin"}
    prices = {}
    # Batch fetch prices
    coin_ids = list(set(ids[t] for t in TOKENS))
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": ",".join(coin_ids), "vs_currencies": "usd"},
            timeout=10,
        )
        if r.status_code == 200:
            prices = r.json()
    except Exception:
        pass
    for m in moves:
        cid = ids.get(m["token"])
        if cid and cid in prices and "usd" in prices[cid]:
            m["usdValue"] = round(m["value"] * prices[cid]["usd"], 2)
        else:
            m["usdValue"] = None
    return moves


# ── Main ────────────────────────────────────────────────────────────────

def fetch_whale_moves():
    cache = load_cache()
    current_block = to_int(rpc_call("eth_blockNumber", []))
    from_block = cache.get("lastBlock")
    if from_block is None:
        from_block = current_block - 100
    else:
        from_block = from_block + 1

    # Don't scan more than 500 blocks at once
    if from_block < current_block - 500:
        from_block = current_block - 500

    if from_block >= current_block:
        print(f"No new blocks (current={current_block})")
        return cache

    print(f"Scanning {from_block} → {current_block} ({current_block - from_block} blocks)")

    all_new = []
    for name, addr in TOKENS.items():
        try:
            mov = fetch_transfers(name, addr, from_block, current_block)
        except Exception as e:
            print(f"  {name}: {e}")
            continue
        if mov:
            print(f"  {name}: {len(mov)} whale moves (>{THRESHOLDS[name]:,})")
            all_new.extend(mov)
        else:
            print(f"  {name}: 0 whale moves")

    if not all_new:
        cache["lastBlock"] = current_block
        cache["lastUpdated"] = datetime.now(timezone.utc).isoformat()
        save_cache(cache)
        return cache

    all_new.sort(key=lambda m: (-m["blockNumber"], -m["logIndex"]))
    all_new = enrich_usd(all_new)

    existing = set(m["txHash"] for m in cache["moves"])
    truly_new = [m for m in all_new if m["txHash"] not in existing]

    if truly_new:
        cache["moves"] = truly_new + cache["moves"]
        cache["moves"] = cache["moves"][:500]  # cap

    cache["lastBlock"] = current_block
    cache["lastUpdated"] = datetime.now(timezone.utc).isoformat()
    save_cache(cache)

    print(f"\nNew whale moves: {len(truly_new)}, Total in cache: {len(cache['moves'])}")

    # Send Telegram alerts for new moves (if configured)
    if truly_new and os.environ.get("TELEGRAM_TOKEN") and os.environ.get("WHALE_ALERT_CHAT_IDS"):
        _send_alerts(truly_new)

    return cache


def _send_alerts(moves):
    """Send whale alerts to configured chat IDs."""
    token = os.environ["TELEGRAM_TOKEN"]
    chat_ids = os.environ["WHALE_ALERT_CHAT_IDS"].split(",")
    max_alerts = min(len(moves), 5)  # max 5 alerts per tick
    for m in moves[:max_alerts]:
        usd = f"${m['usdValue']:,.0f}" if m.get("usdValue") else f"{m['value']:,.2f} {m['token']}"
        msg = (
            f"\U0001F40B Whale Move\n"
            f"{usd} {m['token']}\n"
            f"From: {m['from'][:10]}...{m['from'][-6:]}\n"
            f"To:   {m['to'][:10]}...{m['to'][-6:]}\n"
            f"Tx:   https://etherscan.io/tx/{m['txHash']}"
        )
        for cid in chat_ids:
            cid = cid.strip()
            if not cid:
                continue
            try:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                requests.post(url, json={
                    "chat_id": cid, "text": msg,
                    "parse_mode": "HTML", "disable_web_page_preview": True,
                }, timeout=10)
            except Exception as e:
                print(f"  TG alert to {cid}: {e}")


# ── CLI ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Whale Tracker — {datetime.now(timezone.utc).isoformat()}", flush=True)
    print(f"RPC: {RPC_URL}", flush=True)
    print(flush=True)
    try:
        cache = fetch_whale_moves()
        print(f"\nDone. {len(cache['moves'])} moves in cache.", flush=True)
    except Exception as e:
        print(f"\nFATAL: {e}", flush=True)
        sys.exit(1)
