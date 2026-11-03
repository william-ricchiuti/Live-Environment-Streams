#!/usr/bin/env python3
"""
Print dataset statistics from streams.geojson.

Usage:
    python scripts/stats.py
"""

import json
from collections import Counter
from pathlib import Path

GEOJSON_PATH = Path(__file__).parent.parent / "streams.geojson"


def main():
    with open(GEOJSON_PATH) as f:
        data = json.load(f)

    features = data["features"]
    total = len(features)

    url_types = Counter(f["properties"]["url_type"] for f in features)
    coord_quality = Counter(f["properties"]["coordinates_quality"] for f in features)
    quality_tiers = Counter(f["properties"]["quality_tier"] for f in features)
    statuses = Counter(f["properties"]["status"] for f in features)
    sources = Counter(f["properties"]["source_family"] for f in features)
    countries = Counter(f["properties"]["country_code"] for f in features)
    environments = Counter(f["properties"]["environment"] for f in features)
    requires = Counter(str(f["properties"].get("source_url_requires")) for f in features)

    verified = sum(1 for f in features if f["properties"].get("last_verified"))

    print(f"=== Live Environment Streams ===")
    print(f"Total: {total} streams")
    print(f"Countries: {len(countries)}")
    print(f"Source families: {len(sources)}")
    print(f"Verified: {verified}/{total} ({verified/total*100:.1f}%)")

    print(f"\n--- URL Types ---")
    for k, v in url_types.most_common():
        print(f"  {k}: {v}")

    print(f"\n--- Coordinate Quality ---")
    for k, v in coord_quality.most_common():
        print(f"  {k}: {v}")

    print(f"\n--- Quality Tiers ---")
    for k, v in quality_tiers.most_common():
        print(f"  {k}: {v}")

    print(f"\n--- Status ---")
    for k, v in statuses.most_common():
        print(f"  {k}: {v}")

    print(f"\n--- Source Families ---")
    for k, v in sources.most_common():
        print(f"  {k}: {v}")

    print(f"\n--- Environments ---")
    for k, v in environments.most_common():
        print(f"  {k}: {v}")

    print(f"\n--- Top 20 Countries ---")
    for k, v in countries.most_common(20):
        print(f"  {k}: {v}")

    # Agent-usability summary
    directly_usable = sum(1 for f in features
                          if f["properties"]["url_type"] in ("hls", "mjpeg", "mp4")
                          and f["properties"]["coordinates_quality"] != "country_centroid")
    print(f"\n--- Agent Usability ---")
    print(f"  Directly usable (HLS/MJPEG/MP4 + real coords): {directly_usable}")
    print(f"  Needs browser extraction: {url_types.get('html_page', 0)}")
    print(f"  Has fallback coordinates: {coord_quality.get('country_centroid', 0)}")


if __name__ == "__main__":
    main()
