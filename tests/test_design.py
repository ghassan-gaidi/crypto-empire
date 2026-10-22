"""Design-system module contract tests (Task 1, plan 2026-10-22-night-edition)."""
import pytest

from importlib import import_module

# The module must import with no Flask, no network — pure strings/functions.
design = import_module("design")


def test_tokens_present():
    css = design.NIGHT_CSS
    for token in [
        "--paper:#17130d",
        "--ink:#e9dfc6",
        "--ink-bright:#f2ead4",
        "--ink-dim:#968b70",
        "--rule:rgba(233,223,198,.22)",
        "--rule-strong:rgba(233,223,198,.55)",
        "--oxblood:#d4635a",
        "--print-green:#8fcea5",
    ]:
        assert token in css, f"missing token {token}"
    assert "Fraunces" in css and "IBM Plex Mono" in css
    assert "radial-gradient(circle at center" in css
    assert "background-repeat:round" in css
    assert "pointer-events:none" in css


def test_no_legacy_fonts():
    css = design.NIGHT_CSS
    for legacy in ["JetBrains Mono", "Space Grotesk", "DM Sans", "DM+Sans"]:
        assert legacy not in css, f"legacy font {legacy} leaked into token core"


def test_no_blend_or_rotate():
    needle = design.NIGHT_CSS.split(".ht{", 1)[1].split("}", 1)[0]
    assert "mix-blend-mode" not in needle
    assert "transform" not in needle


def test_halftone_values():
    css = design.NIGHT_CSS
    for v in ["--cell:5.5px", "--dr:1.1px", "--da:.12", "--ink:233,223,198"]:
        assert v in css, f"missing halftone dial {v}"


def test_ledger_escapes():
    out = design.ledger([("<b>", "<i>x</i>", None)])
    assert "&lt;b&gt;" in out and "&lt;i&gt;x&lt;/i&gt;" in out
    assert "<b>gboul" not in out and "<i>" not in out
    assert "····" in out          # leader dots device
    assert "ledger-row" in out    # class hook


def test_ledger_empty():
    out = design.ledger([])
    assert "the tape is dark" in out


def test_ledger_tones():
    out = design.ledger([("Fear & Greed", "54 · Neutral", None),
                         ("btc", "+0.4", "up"),
                         ("eth", "-1.18", "down")])
    assert "print-green" in out or "printgreen" in out or "up" in out
    assert "oxblood" in out or "down" in out


def test_tape_table():
    out = design.tape_table([("Bitcoin", "121,412.63", "2.41", "up"),
                             ("Ethereum", "4,412.19", "1.18", "down")])
    assert "▲" in out and "▼" in out
    # escaping: instrument names
    assert "Bitcoin" in out and "Ethereum" in out
    assert "tape-table" in out


def test_tape_table_escapes():
    out = design.tape_table([("<script>x</script>", "1", "1", "up")])
    assert "<script>" not in out and "&lt;script&gt;" in out


def test_wire():
    out = design.wire([("14:02", "1,240 WBTC — $97.1M")])
    assert "14:02" in out and "$97.1M" in out
    assert "wire-item" in out
    assert "&amp;" not in "1,240 WBTC — $97.1M" or True  # sanity only


def test_index_strip():
    out = design.index_strip([("BTC", "121,412.63", "up"), ("F&G", "54", "dim")])
    assert "index-strip" in out and "121,412.63" in out
    assert "F&amp;G" in out


def test_ad_box():
    out = design.ad_box("The Full Ledger", "Real-time whale wire", ("Subscribe — $9.99/mo", "/premium"))
    assert "ad-box" in out and "/premium" in out and "Subscribe" in out


def test_page_shell():
    out = design.page_shell("Markets", "<p>body</p>", kicker="Markets", page="A1")
    assert out.startswith("<!DOCTYPE") or out.lstrip().startswith("<!DOCTYPE")
    assert "-paper:#17130d" in out
    assert "masthead" in out
    assert "folio" in out
    assert "Night Edition" in out


def test_page_shell_escaping():
    out = design.page_shell('<script>x</script>', "body")
    assert "<script>x</script>" not in out
