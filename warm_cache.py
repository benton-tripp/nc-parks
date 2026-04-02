"""Geocode cache warming — incrementally fill the geocode cache.

Runs the pipeline with --skip-fetch and a small --geocode-batch in a loop,
pausing between rounds to respect Nominatim rate limits.

Usage:
    python warm_cache.py                    # default: 200 per round, 60s pause
    python warm_cache.py --batch 100        # 100 per round
    python warm_cache.py --rounds 5         # run 5 rounds then stop
    python warm_cache.py --pause 120        # 120s between rounds
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent
_CACHE_PATH = _ROOT / "data" / "reference" / "geocode_cache.json"
_LATEST = _ROOT / "data" / "final" / "parks_latest.json"


def _count_uncached() -> tuple[int, int]:
    """Count parks still needing forward and reverse geocoding."""
    if not _LATEST.exists():
        return -1, -1

    with open(_LATEST) as f:
        parks = json.load(f)

    cache = {"forward": {}, "reverse": {}}
    if _CACHE_PATH.exists():
        with open(_CACHE_PATH) as f:
            cache = json.load(f)
        if "reverse" not in cache:
            cache = {"reverse": cache, "forward": {}}

    need_fwd = sum(
        1 for p in parks
        if p.get("latitude") is None and p.get("address")
        and p["address"].strip().lower() not in cache.get("forward", {})
    )
    need_rev = sum(
        1 for p in parks
        if not p.get("address") and p.get("latitude") is not None
        and f"{p['latitude']:.5f},{p['longitude']:.5f}" not in cache.get("reverse", {})
    )
    return need_fwd, need_rev


def main():
    parser = argparse.ArgumentParser(description="Incrementally warm the geocode cache")
    parser.add_argument("--batch", type=int, default=200,
                        help="Geocode API calls per round (default: 200)")
    parser.add_argument("--rounds", type=int, default=0,
                        help="Max rounds (0 = until done)")
    parser.add_argument("--pause", type=int, default=60,
                        help="Seconds to pause between rounds (default: 60)")
    args = parser.parse_args()

    round_num = 0
    while True:
        round_num += 1
        if args.rounds and round_num > args.rounds:
            logger.info("Reached max rounds (%d). Done.", args.rounds)
            break

        need_fwd, need_rev = _count_uncached()
        logger.info("Round %d — uncached: ~%d forward, ~%d reverse",
                    round_num, max(need_fwd, 0), max(need_rev, 0))

        if need_fwd == 0 and need_rev == 0:
            logger.info("All parks geocoded! Cache is warm.")
            break

        logger.info("Running pipeline --skip-fetch --geocode-batch %d ...", args.batch)
        cmd = [
            sys.executable, "-m", "data-pipeline.pipeline",
            "--skip-fetch",
            "--geocode-batch", str(args.batch),
        ]
        result = subprocess.run(cmd, cwd=str(_ROOT))

        if result.returncode != 0:
            logger.error("Pipeline exited with code %d", result.returncode)
            break

        if round_num < (args.rounds or float("inf")):
            remaining_fwd, remaining_rev = _count_uncached()
            if remaining_fwd == 0 and remaining_rev == 0:
                logger.info("All parks geocoded after round %d!", round_num)
                break

            logger.info("Pausing %ds before next round...", args.pause)
            time.sleep(args.pause)

    logger.info("Cache warming complete after %d round(s).", round_num)


if __name__ == "__main__":
    main()
