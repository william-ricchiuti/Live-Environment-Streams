#!/usr/bin/env python3
"""
Probe stream URLs and update status/last_verified fields.
Requires: requests (pip install requests)

Usage:
    python scripts/validate.py                    # Validate all streams
    python scripts/validate.py --source vdot      # Validate one source family
    python scripts/validate.py --type hls         # Validate only HLS streams
    python scripts/validate.py --limit 100        # Validate first N streams
    python scripts/validate.py --dry-run          # Show what would be checked
"""

import json
import sys
import argparse
import subprocess
from datetime import datetime, timezone
from pathlib import Path

GEOJSON_PATH = Path(__file__).parent.parent / "streams.geojson"


def probe_hls(url: str, timeout: int = 10) -> bool:
    """Check if an HLS manifest is reachable and returns valid content."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "-L", "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 5
        )
        status = result.stdout.strip()
        return status.startswith("2")
    except (subprocess.TimeoutExpired, Exception):
        return False


def probe_youtube(url: str) -> bool:
    """Check if a YouTube Live URL is currently live."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "10", url],
            capture_output=True, text=True, timeout=15
        )
        return "isLiveBroadcast" in result.stdout or '"isLive":true' in result.stdout
    except (subprocess.TimeoutExpired, Exception):
        return False


def probe_http(url: str, timeout: int = 10) -> bool:
    """Check if an HTTP endpoint is reachable."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "-L", "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 5
        )
        status = result.stdout.strip()
        return status.startswith("2") or status.startswith("3")
    except (subprocess.TimeoutExpired, Exception):
        return False


def validate_stream(feature: dict) -> str:
    """Probe a single stream and return its status."""
    props = feature["properties"]
    url_type = props.get("url_type", "")
    url = props.get("url", "")

    if url_type == "html_page":
        return "unverified"  # Can't probe HTML pages without browser

    if url_type == "hls":
        return "active" if probe_hls(url) else "deprecated"
    elif url_type == "youtube":
        return "active" if probe_youtube(url) else "unverified"  # YT may be offline temporarily
    elif url_type in ("mjpeg", "mp4"):
        return "active" if probe_http(url) else "deprecated"
    elif url_type == "http_image":
        return "active" if probe_http(url) else "deprecated"

    return "unverified"


def main():
    parser = argparse.ArgumentParser(description="Validate stream URLs")
    parser.add_argument("--source", help="Only validate this source_family")
    parser.add_argument("--type", help="Only validate this url_type")
    parser.add_argument("--limit", type=int, help="Max streams to validate")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without probing")
    args = parser.parse_args()

    with open(GEOJSON_PATH) as f:
        data = json.load(f)

    features = data["features"]
    targets = []

    for feat in features:
        props = feat["properties"]
        if args.source and props.get("source_family") != args.source:
            continue
        if args.type and props.get("url_type") != args.type:
            continue
        if props.get("url_type") == "html_page":
            continue  # Skip HTML pages
        targets.append(feat)

    if args.limit:
        targets = targets[:args.limit]

    print(f"Validating {len(targets)} streams...")

    if args.dry_run:
        for t in targets[:20]:
            p = t["properties"]
            print(f"  [{p['url_type']}] {p['source_family']}: {p['name']}")
        if len(targets) > 20:
            print(f"  ... and {len(targets) - 20} more")
        return

    now = datetime.now(timezone.utc).isoformat()
    active = 0
    deprecated = 0
    unchanged = 0

    for i, feat in enumerate(targets):
        props = feat["properties"]
        status = validate_stream(feat)
        props["status"] = status
        props["last_verified"] = now

        if status == "active":
            active += 1
        elif status == "deprecated":
            deprecated += 1
        else:
            unchanged += 1

        if (i + 1) % 50 == 0:
            print(f"  Progress: {i + 1}/{len(targets)} "
                  f"(active={active}, deprecated={deprecated})")

    with open(GEOJSON_PATH, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Results: {active} active, {deprecated} deprecated, "
          f"{unchanged} unchanged")
    print(f"Updated {GEOJSON_PATH}")


if __name__ == "__main__":
    main()
