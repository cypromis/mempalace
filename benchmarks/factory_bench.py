#!/usr/bin/env python3
"""
factory_bench.py — Latency benchmarks for palace_db factory performance.

Measures the specific hotspots identified in the code review:
  1. MempalaceConfig() instantiation cost (disk I/O per get_client() call)
  2. get_client() cold vs warm (cache hit vs miss)
  3. get_collection() overhead (get_or_create_collection per MCP call)
  4. Multiple status-fetch calls vs single shared fetch

Usage:
    python benchmarks/factory_bench.py
    python benchmarks/factory_bench.py --palace /tmp/bench-palace
"""

import argparse
import os
import sys
import tempfile
import timeit
from pathlib import Path

# Allow running from repo root or benchmarks/
sys.path.insert(0, str(Path(__file__).parent.parent))

from mempalace import palace_db
from mempalace.config import MempalaceConfig

ITERATIONS = 200
WARMUP = 5


def fmt(seconds: float, n: int) -> str:
    us = seconds / n * 1_000_000
    ms = us / 1000
    if ms >= 1:
        return f"{ms:.2f} ms"
    return f"{us:.1f} µs"


def bench(label: str, fn, n=ITERATIONS, warmup=WARMUP):
    for _ in range(warmup):
        fn()
    elapsed = timeit.timeit(fn, number=n)
    per_call = fmt(elapsed, n)
    print(f"  {label:<55} {per_call:>10}")
    return elapsed / n


def run(palace_path: str):
    print(f"\n{'=' * 70}")
    print("  palace_db factory latency benchmarks")
    print(f"  palace: {palace_path}")
    print(f"  iterations: {ITERATIONS}  warmup: {WARMUP}")
    print(f"{'=' * 70}\n")

    # ── 1. MempalaceConfig instantiation ─────────────────────────────────
    print("[ 1 ] MempalaceConfig() instantiation cost")
    print("      (this happens on EVERY get_client() call currently)\n")

    config_dir = tempfile.mkdtemp()
    bench("MempalaceConfig() cold (no config.json)", lambda: MempalaceConfig(config_dir=config_dir))

    # Write a config file so it has to parse JSON
    import json

    cfg_file = os.path.join(config_dir, "config.json")
    with open(cfg_file, "w") as f:
        json.dump({"chroma_host": None, "chroma_port": 8000}, f)
    bench(
        "MempalaceConfig() with config.json (JSON parse)",
        lambda: MempalaceConfig(config_dir=config_dir),
    )

    # ── 2. get_client() cold vs warm ──────────────────────────────────────
    print("\n[ 2 ] get_client() cold (cache miss) vs warm (cache hit)\n")

    def cold_get_client():
        palace_db.clear_caches()
        palace_db.get_client(palace_path=palace_path)

    def warm_get_client():
        palace_db.get_client(palace_path=palace_path)

    # Ensure cache is warm for the warm benchmark
    palace_db.get_client(palace_path=palace_path)

    cold = bench("get_client() cold — creates PersistentClient + makedirs", cold_get_client)
    warm = bench("get_client() warm — dict lookup only", warm_get_client)

    if warm > 0:
        ratio = cold / warm
        print(f"\n  Cache speedup: {ratio:.0f}× faster on cache hit\n")

    # ── 3. get_collection() overhead ────────────────────────────────────
    print("[ 3 ] get_collection() overhead per MCP tool call\n")

    # Ensure client is cached
    palace_db.get_client(palace_path=palace_path)

    bench(
        "get_collection() — get_or_create_collection each call",
        lambda: palace_db.get_collection(palace_path=palace_path),
    )

    # ── 4. Simulated MCP status: 4 fetches vs 1 shared fetch ────────────
    print("\n[ 4 ] MCP aggregate tools: 4 independent fetches vs 1 shared fetch\n")

    col = palace_db.get_collection(palace_path=palace_path)

    # Seed some data if empty
    if col.count() == 0:
        col.add(
            ids=[f"bench_{i}" for i in range(100)],
            documents=[f"document {i}" for i in range(100)],
            metadatas=[{"wing": f"wing_{i % 5}", "room": f"room_{i % 10}"} for i in range(100)],
        )

    def four_fetches():
        """Current behaviour: each tool fetches independently."""
        col.get(include=["metadatas"], limit=10000)  # tool_status
        col.get(include=["metadatas"], limit=10000)  # tool_list_wings
        col.get(include=["metadatas"], limit=10000)  # tool_list_rooms
        col.get(include=["metadatas"], limit=10000)  # tool_get_taxonomy

    def one_shared_fetch():
        """Proposed: fetch once, pass to all four tools."""
        all_meta = col.get(include=["metadatas"], limit=10000)
        _ = all_meta  # tool_status
        _ = all_meta  # tool_list_wings
        _ = all_meta  # tool_list_rooms
        _ = all_meta  # tool_get_taxonomy

    t4 = bench("4× independent col.get() — current behaviour", four_fetches)
    t1 = bench("1× shared col.get() — proposed optimisation", one_shared_fetch)

    if t1 > 0:
        ratio = t4 / t1
        print(f"\n  Shared fetch speedup: {ratio:.1f}× faster\n")

    # ── 5. Config-per-call simulation (MCP server hotpath) ───────────────
    print("[ 5 ] MCP server hotpath simulation\n")
    print("      Each MCP tool call invokes get_client() → MempalaceConfig()\n")

    def simulated_mcp_tool_call():
        """What happens today: get_client reads config on every call."""
        palace_db.get_client(palace_path=palace_path)  # config re-read inside

    def simulated_mcp_with_cached_config():
        """What could happen: config cached, only dict lookup."""
        # Simulated by directly doing the dict lookup (what caching would give us)
        _ = palace_db._persistent_clients.get(palace_path)

    bench("current: get_client() with MempalaceConfig() per call", simulated_mcp_tool_call)
    bench("ideal:   cache hit only (dict lookup)", simulated_mcp_with_cached_config)

    print(f"\n{'=' * 70}")
    print("  Done.")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="palace_db factory latency benchmarks")
    parser.add_argument(
        "--palace", default=None, help="Path to palace directory (default: temp dir)"
    )
    args = parser.parse_args()

    if args.palace:
        palace_path = args.palace
    else:
        palace_path = tempfile.mkdtemp(prefix="mempalace_bench_")

    run(palace_path)
