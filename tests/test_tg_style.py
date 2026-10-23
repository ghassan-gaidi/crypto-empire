"""Night print style contract for the Telegram wire (Task 10).

The bot is the paper's courier: masthead-first blocks, rule bars,
dotted-leader ledger rows, ❧ bullets, ▲/▼ tones, and folio footers.
Plain text only — Telegram renders it as sent; no markdown/HTML markup
may leak into a wire.
"""
import subprocess
import sys
from pathlib import Path

import pytest

from design import TG
import telegram_bot as tb

REPO = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# design.py scaffolds (Task 10 Step 1: importable + shaped)
# ---------------------------------------------------------------------------

def test_tg_scaffolds_shaped():
    assert TG["masthead"] == "DOMINION — {page}"
    assert TG["rule"] == "─" * 24
    assert TG["leader"] == "····"
    assert TG["bullet"] == "❧"
    assert TG["up"] == "▲" and TG["down"] == "▼"
    assert "❦" in TG["foot"] and "/help for the index" in TG["foot"]
    assert TG["silent"] == "the wire is silent."


def test_tg_scaffolds_format():
    assert TG["masthead"].format(page="GAS TRACKER") == "DOMINION — GAS TRACKER"


# ---------------------------------------------------------------------------
# Builders: masthead-first, rules, leaders, footers
# ---------------------------------------------------------------------------

def test_fmt_header_is_masthead_first_with_rule():
    h = tb.fmt_header("GAS TRACKER")
    first = h.splitlines()[0]
    assert first == "DOMINION — GAS TRACKER"
    assert TG["rule"] in h
    assert not first.startswith(">")  # terminal prompt glyph retired


def test_wire_foot_is_folio_line():
    f = tb.wire_foot("PRICE", "2026-10-23 05:12 UTC")
    assert f.startswith("❦ PRICE")
    assert "/help for the index" in f
    assert "2026-10-23 05:12 UTC" in f


def test_wire_foot_without_when_still_reads():
    f = tb.wire_foot("PRICE")
    assert f.startswith("❦ PRICE")
    assert f.rstrip() == f


def test_leader_row_uses_dotted_leader():
    row = tb.leader_row("24h", "▲ 1.20%")
    assert TG["leader"] in row
    assert "24h" in row and "▲ 1.20%" in row


def test_bullet_line_uses_press_bullet():
    assert tb.bullet("Ethereum (ETH)").startswith("❧ ")


def test_wire_block_assembles_masthead_rows_foot():
    msg = tb.wire_block(
        "PRICE",
        [tb.leader_row("price", "$1.00"), "❧ line two"],
        when="now",
    )
    assert msg.splitlines()[0] == "DOMINION — PRICE"
    assert TG["rule"] in msg
    assert "❦" in msg and "now" in msg


# ---------------------------------------------------------------------------
# Tones
# ---------------------------------------------------------------------------

def test_fmt_change_arrows():
    assert tb.fmt_change(3.2).startswith("▲")
    assert tb.fmt_change(-3.2).startswith("▼")
    assert tb.fmt_change(None) == "N/A"


def test_silent_wire():
    assert TG["silent"] == "the wire is silent."


# ---------------------------------------------------------------------------
# Plain text hygiene (parse_mode respected — nothing to escape)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("poison", ["```", "**", "<b>", "__", "</", "~~"])
def test_wire_block_carries_no_markdown_or_html(poison):
    msg = tb.wire_block("PRICE", [tb.leader_row("label", poison and "value")], when="")
    assert poison not in msg


# ---------------------------------------------------------------------------
# Module importable without token (webhook + cron cold start)
# ---------------------------------------------------------------------------

def test_telegram_bot_imports_clean(capsys):
    r = subprocess.run(
        [sys.executable, "-c", "import telegram_bot; print('WIRED')"],
        cwd=str(REPO), capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert "WIRED" in r.stdout
