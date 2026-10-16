#!/usr/bin/env python3
"""GitHub Actions monitor script - checks balances and prices"""
import requests
import json
import os
from datetime import datetime

wallet = os.environ.get("WALLET") or os.environ.get("WALLET_ADDRESS") or "0x29021dd5306D7b3b6608a2bc8276D33c1200C7Ef"
etherscan_key = os.environ.get("ETHERSCAN_API_KEY", "")

print(f"Dominion Monitor - {datetime.utcnow().isoformat()}")
print(f"Wallet: {wallet}")
print()

# Check ETH mainnet
try:
    url = f"https://api.etherscan.io/api?module=account&action=balance&address={wallet}&tag=latest&apikey={etherscan_key}"
    r = requests.get(url, timeout=10)
    data = r.json()
    if data.get("status") == "1":
        eth_bal = int(data["result"]) / 1e18
        print(f"ETH: {eth_bal:.8f}")
    else:
        print(f"ETH: API error - {data.get('message', 'unknown')}")
except Exception as e:
    print(f"ETH: {e}")

# Check Polygon
try:
    r = requests.post("https://polygon-rpc.com", json={
        "jsonrpc": "2.0",
        "method": "eth_getBalance",
        "params": [wallet, "latest"],
        "id": 1
    }, timeout=10)
    data = r.json()
    if "result" in data:
        matic_bal = int(data["result"], 16) / 1e18
        print(f"MATIC: {matic_bal:.8f}")
except Exception as e:
    print(f"MATIC: {e}")

# Check Arbitrum
try:
    r = requests.post("https://arb1.arbitrum.io/rpc", json={
        "jsonrpc": "2.0",
        "method": "eth_getBalance",
        "params": [wallet, "latest"],
        "id": 1
    }, timeout=10)
    data = r.json()
    if "result" in data:
        arb_bal = int(data["result"], 16) / 1e18
        print(f"ARB: {arb_bal:.8f}")
except Exception as e:
    print(f"ARB: {e}")

# Check Base
try:
    r = requests.post("https://mainnet.base.org", json={
        "jsonrpc": "2.0",
        "method": "eth_getBalance",
        "params": [wallet, "latest"],
        "id": 1
    }, timeout=10)
    data = r.json()
    if "result" in data:
        base_bal = int(data["result"], 16) / 1e18
        print(f"BASE: {base_bal:.8f}")
except Exception as e:
    print(f"BASE: {e}")

print()

# Check price alerts
print("--- Price Alerts ---")
coins = ["bitcoin", "ethereum", "solana", "cardano", "ripple"]
for coin in coins:
    try:
        r = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd&include_24hr_change=true",
            timeout=10
        )
        data = r.json()
        if coin in data:
            price = data[coin]["usd"]
            change = data[coin].get("usd_24h_change", 0)
            emoji = "🟢" if change >= 0 else "🔴"
            print(f"{emoji} {coin.upper()}: ${price:,.2f} ({change:+.2f}%)")
    except Exception:
        print(f"  {coin}: error")

print()
print("Monitor completed successfully.")
print(f"Time: {datetime.utcnow().isoformat()}")
