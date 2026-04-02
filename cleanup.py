"""Remove old raw/processed/final data files, keeping the N most recent per source.

Usage:
    python cleanup.py              # dry run — show what would be deleted
    python cleanup.py --delete     # actually delete
    python cleanup.py --keep 5     # keep 5 most recent (default: 3)
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).parent / "data"

# Directories to clean and their filename patterns
# Each file looks like: {source}_{timestamp}.json
DIRS = [
    DATA / "raw",
    DATA / "processed",
    DATA / "final",
]

# Match: name_YYYYMMDDTHHmmss.json
_TS_RE = re.compile(r'^(.+)_(\d{8}T\d{6})\.json$')


def find_stale(directory: Path, keep: int) -> list[Path]:
    """Return files to delete in *directory*, keeping *keep* newest per group."""
    if not directory.exists():
        return []

    groups: dict[str, list[Path]] = defaultdict(list)
    for f in sorted(directory.glob("*.json")):
        if f.name == "parks_latest.json":
            continue  # never delete the latest symlink/copy
        m = _TS_RE.match(f.name)
        if m:
            groups[m.group(1)].append(f)

    stale = []
    for name, files in sorted(groups.items()):
        # Files are sorted alphabetically = chronologically (timestamp format)
        if len(files) > keep:
            stale.extend(files[:-keep])
    return stale


def main():
    parser = argparse.ArgumentParser(description="Clean old pipeline data files")
    parser.add_argument("--keep", "-k", type=int, default=3,
                        help="Number of recent files to keep per source (default: 3)")
    parser.add_argument("--delete", "-d", action="store_true",
                        help="Actually delete files (default: dry run)")
    args = parser.parse_args()

    total = 0
    total_bytes = 0

    for d in DIRS:
        stale = find_stale(d, args.keep)
        if not stale:
            continue

        rel = d.relative_to(Path(__file__).parent)
        print(f"\n{rel}/  ({len(stale)} to remove, keeping {args.keep})")
        for f in stale:
            size = f.stat().st_size
            total_bytes += size
            total += 1
            marker = "DELETE" if args.delete else "would delete"
            print(f"  {marker}: {f.name}  ({size / 1024:.0f} KB)")
            if args.delete:
                f.unlink()

    if total == 0:
        print("Nothing to clean up.")
    else:
        action = "Deleted" if args.delete else "Would delete"
        print(f"\n{action} {total} files ({total_bytes / 1024 / 1024:.1f} MB)")
        if not args.delete:
            print("Run with --delete to actually remove them.")


if __name__ == "__main__":
    main()
