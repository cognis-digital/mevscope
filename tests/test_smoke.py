"""Smoke + behavior tests for MEVSCOPE. No network calls."""
import json
import os
import subprocess
import sys
import tempfile

import pytest

from mevscope import (
    TOOL_NAME,
    TOOL_VERSION,
    load_swaps,
    load_swaps_from_obj,
    detect_sandwiches,
    build_report,
)
from mevscope.core import _amount_out_cpmm, Swap

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(REPO_ROOT, "demos", "01-basic", "swaps.json")


def test_metadata():
    assert TOOL_NAME == "mevscope"
    assert TOOL_VERSION


def test_demo_loads():
    swaps = load_swaps(DEMO)
    assert len(swaps) == 5
    assert all(isinstance(s, Swap) for s in swaps)


def test_detects_exactly_one_sandwich():
    swaps = load_swaps(DEMO)
    found = detect_sandwiches(swaps)
    assert len(found) == 1
    s = found[0]
    assert s.block == 1000
    assert s.victim_tx == "0xvictim01"
    assert s.frontrun_tx == "0xfront01"
    assert s.backrun_tx == "0xback01"
    assert s.attacker == "0xattacker"
    assert s.victim_sender == "0xvictim"
    assert s.method == "exact"


def test_victim_loss_is_positive_and_correct():
    swaps = load_swaps(DEMO)
    s = detect_sandwiches(swaps)[0]
    # Counterfactual output for 10000 USDC on the untouched pool (2,000,000 / 1000).
    ideal_out = _amount_out_cpmm(10000.0, 2000000.0, 1000.0)
    missing = ideal_out - 4.937
    expected_loss = missing * (10000.0 / 4.937)
    assert missing > 0
    assert s.victim_loss_in == pytest.approx(expected_loss, rel=1e-6)
    assert s.victim_loss_in > 0


def test_attacker_profit_positive_usdc():
    swaps = load_swaps(DEMO)
    s = detect_sandwiches(swaps)[0]
    # Spent 5000 USDC on front-run, got 5037.5 USDC back -> +37.5 USDC.
    assert s.profit_token == "USDC"
    assert s.attacker_profit == pytest.approx(37.5, rel=1e-9)


def test_normal_swaps_not_flagged():
    # Two unrelated swaps in their own block, different senders -> no sandwich.
    obj = [
        {"tx": "a", "block": 1, "index": 0, "sender": "0xa", "pool": "p",
         "token_in": "USDC", "token_out": "WETH", "amount_in": 100.0, "amount_out": 0.05},
        {"tx": "b", "block": 1, "index": 1, "sender": "0xb", "pool": "p",
         "token_in": "WETH", "token_out": "USDC", "amount_in": 0.05, "amount_out": 100.0},
    ]
    assert detect_sandwiches(load_swaps_from_obj(obj)) == []


def test_estimated_method_when_no_reserves():
    # Sandwich without reserve data -> estimated loss path.
    obj = [
        {"tx": "f", "block": 5, "index": 0, "sender": "0xatk", "pool": "p",
         "token_in": "USDC", "token_out": "WETH", "amount_in": 5000.0, "amount_out": 2.5},
        {"tx": "v", "block": 5, "index": 1, "sender": "0xvic", "pool": "p",
         "token_in": "USDC", "token_out": "WETH", "amount_in": 10000.0, "amount_out": 4.8},
        {"tx": "b", "block": 5, "index": 2, "sender": "0xatk", "pool": "p",
         "token_in": "WETH", "token_out": "USDC", "amount_in": 2.5, "amount_out": 5100.0},
    ]
    found = detect_sandwiches(load_swaps_from_obj(obj))
    assert len(found) == 1
    assert found[0].method == "estimated"
    assert found[0].victim_loss_in > 0
    assert found[0].attacker_profit == pytest.approx(100.0)


def test_report_totals():
    report = build_report(load_swaps(DEMO))
    assert report.swaps_analyzed == 5
    d = report.to_dict()
    assert d["sandwich_count"] == 1
    assert d["total_victim_loss"] > 0
    assert d["total_attacker_profit"] == pytest.approx(37.5, rel=1e-6)


def test_cli_json_and_exit_codes():
    # JSON output, default exit 0.
    r = subprocess.run(
        [sys.executable, "-m", "mevscope", "scan", DEMO, "--format", "json"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["sandwich_count"] == 1
    assert payload["total_victim_loss"] > 0

    # --fail-on-mev should exit 1 when a sandwich exists.
    r2 = subprocess.run(
        [sys.executable, "-m", "mevscope", "scan", DEMO, "--fail-on-mev"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert r2.returncode == 1


def test_cli_version():
    r = subprocess.run(
        [sys.executable, "-m", "mevscope", "--version"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert r.returncode == 0
    assert TOOL_VERSION in r.stdout


# ---------------------------------------------------------------------------
# Hardening: input validation edge cases
# ---------------------------------------------------------------------------

def test_missing_file_returns_exit_2():
    """CLI must exit 2 with a message on a nonexistent file — no traceback."""
    r = subprocess.run(
        [sys.executable, "-m", "mevscope", "scan", "no_such_file_12345.json"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert r.returncode == 2
    assert "error" in r.stderr.lower()
    assert "no_such_file_12345.json" in r.stderr


def test_malformed_json_returns_exit_2():
    """CLI must exit 2 with a clear message on invalid JSON — no traceback."""
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as fh:
        fh.write("this is not valid json {{{")
        bad_path = fh.name
    try:
        r = subprocess.run(
            [sys.executable, "-m", "mevscope", "scan", bad_path],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert r.returncode == 2
        assert "error" in r.stderr.lower()
    finally:
        os.unlink(bad_path)


def test_empty_swaps_array():
    """Empty swap list produces a report with zero swaps and no sandwiches."""
    report = build_report(load_swaps_from_obj([]))
    assert report.swaps_analyzed == 0
    assert report.sandwiches == []
    assert report.total_victim_loss == 0.0
    assert report.total_attacker_profit == 0.0


def test_load_swaps_from_obj_missing_field():
    """A swap record missing a required field raises a clear ValueError."""
    obj = [{"tx": "0xa", "block": 1, "index": 0}]  # missing sender, pool, tokens, amounts
    with pytest.raises(ValueError, match="missing required field"):
        load_swaps_from_obj(obj)


def test_load_swaps_from_obj_negative_amount():
    """Negative amount_in must raise ValueError with a descriptive message."""
    obj = [
        {
            "tx": "0xa", "block": 1, "index": 0,
            "sender": "0xs", "pool": "0xp",
            "token_in": "USDC", "token_out": "WETH",
            "amount_in": -100.0, "amount_out": 0.05,
        }
    ]
    with pytest.raises(ValueError, match="negative amount_in"):
        load_swaps_from_obj(obj)


def test_load_swaps_from_obj_non_list_raises():
    """Passing a bare dict (not a list and not {'swaps': ...}) raises ValueError."""
    with pytest.raises(ValueError, match="expected a JSON array"):
        load_swaps_from_obj({"foo": "bar"})


def test_cpmm_zero_reserve_in_returns_zero():
    """_amount_out_cpmm must not divide by zero when reserve_in + amount_in == 0."""
    # reserve_in=0 and amount_in=0 → new_reserve_in=0 → should return 0, not raise
    result = _amount_out_cpmm(0.0, 0.0, 1000.0)
    assert result == 0.0


def test_mcp_server_importable():
    """mcp_server module must import without error (no broken symbol imports)."""
    import importlib
    mod = importlib.import_module("mevscope.mcp_server")
    assert callable(mod.serve)
