#!/usr/bin/env python3
"""
Export streams.geojson from a RainAlways-style SQLite camera database.

Reads a local SQLite file strictly read-only (``mode=ro``), selects the
``status='validated'`` live-video and MJPEG rows, applies the publication
policy below (no token/signed URLs, no sources whose terms forbid listing,
no retired families) and writes the repository's GeoJSON schema.

Usage:
    python scripts/export_from_sqlite.py --db path/to/streams.db --out streams.geojson
    python scripts/export_from_sqlite.py --db streams.db --out -      # GeoJSON to stdout

Exclusion counts (never URLs) are printed to stderr.
Standard library only.
"""

import argparse
import json
import re
import sqlite3
import sys
import urllib.parse
from collections import Counter
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Publication policy
# ---------------------------------------------------------------------------

# Families that are retired from the dataset (see CHANGELOG 4.0.0).
RETIRED_FAMILIES = {
    "skylinewebcams": "retired: IP-blocked since 2026-06, page URLs need expiring tokens",
    "skyline-youtube": "retired: YouTube server-side extraction blocked",
    "youtube": "retired: YouTube server-side extraction blocked",
    "webcamera_pl": "retired: licence terms forbid redistribution",
}

# Families left out because their terms forbid listing/redistribution or could
# not be cleared. One line per family; details in SOURCES-REVIEW.md.
LICENCE_EXCLUDED_FAMILIES = {
    "opencctv": "aggregator terms forbid scraping/bulk download",
    "manual": "harvested via opencctv; mixed private hosts",
    "paspro": "private toll operator, terms not found",
    "bpjt_stale": "private toll operator hosts, terms not found",
    "wikaserangpanimbang": "private toll operator, terms not found",
    "nysdot_511": "feed access needs the NYSDOT Developers Access Agreement (not reviewed)",
    "itic": "private non-profit, all rights reserved",
    "camguide": "directory of commercial/private streams",
    "brownrice": "commercial host, owners' terms unknown",
    "ipcamlive": "commercial host, owners' terms unknown",
    "osm_webcam_pages": "small private sites, terms not checked",
    "pixels_guyana": "private operator, no terms found",
    "worldviewstream": "re-hosts third-party streams, forbids redistribution",
    "coastalwatch-au": "commercial subscription network",
    "maritime-nsw": "served from Coastalwatch infrastructure",
    "resortcams": "no use without written consent",
    "novascotia_webcams": "commercial, licences sold, non-commercial terms",
    "wral": "broadcaster, redistribution forbidden",
    "skyrail": "personal use only, no data extraction",
    "balticlivecam": "all rights reserved; token URLs",
    "wetmet-poconos": "commercial; per-client uid parameter",
    "aldot": "streams now FairPlay SAMPLE-AES encrypted (checked 2026-11-03)",
}

# Private hosts inside otherwise-cleared public-sector families.
UNCLEARED_HOST_SUFFIXES = (
    "atcsindonesia.info",
    "aldilinux.my.id",
    "jaring.host",
    "iticfoundation.org",
)

# Required or requested credit per published family (see sources.json).
ATTRIBUTION = {
    "caltrans": "Caltrans (California Department of Transportation)",
    "vdot": "VDOT (Virginia Department of Transportation)",
    "mndot": "MnDOT (Minnesota Department of Transportation)",
    "iowa_dot": "Iowa Department of Transportation",
    "mdsha": "State of Maryland (MDOT SHA CHART)",
    "seattle_sdot": "City of Seattle Department of Transportation",
    "ladotd_511": "Louisiana DOTD (511LA)",
    "deldot": "DelDOT (Delaware Department of Transportation)",
    "goakamai_hdot": "Hawaii Department of Transportation (GoAkamai)",
    "vegvesen_video": "Statens vegvesen (NLOD)",
    "tdx_city_cctv": "Keelung City Government via TDX (OGDL-Taiwan-1.0)",
    "trafficvision": "Department of Highways, Thailand",
    "hessen_mobil": "Hessen Mobil",
    "cctv-jogjakota": "Dinas Perhubungan Kota Yogyakarta (Indonesia)",
}
INDONESIAN_CITY_PREFIXES = ("atcs-", "cctv-")

# Hosts whose stream URLs carry expiring or per-session credentials.
TOKEN_HOST_SUFFIXES = (
    "balticlivecam.com",
    "skylinewebcams.com",
    "youtube.com",
    "youtu.be",
    "googlevideo.com",
    "wetmet.net",
)

# Query parameters that indicate a token, signature or session credential.
AUTH_PARAM_RE = re.compile(
    r"(token|sig|signature|auth|key|hash|expire|exp$|policy|session|sid$|^uid$|"
    r"jwt|hdnts|hdnea|credential|secret|password|passwd|^st$|^e$)",
    re.IGNORECASE,
)

# Path fragments that indicate session-bound or credential-bearing URLs
# (Wowza per-session chunklists, bearer path segments, JWTs).
AUTH_PATH_RE = re.compile(r"(chunklist_w\d+|/bearer/|/eyJ[A-Za-z0-9_-]{10,})", re.IGNORECASE)

# Producer-specific family names folded into one published family.
FAMILY_ALIASES = {
    "nysdot": "nysdot_511",
    "nysdot_probe": "nysdot_511",
    "ladot": "ladotd_511",
    "ladot_probe": "ladotd_511",
    "Louisiana_DOT": "ladotd_511",
    "vdotcameras": "vdot",
    "iticfoundation": "itic",
    "salatiga": "cctv-salatiga",
    "camguide-ipcamlive": "camguide",
    "brownrice-visitdebeaches": "brownrice",
    "src2-p4-tourism-fiji-samoa": "ipcamlive",
    "src2-p1-osm-choco-amazon": "pixels_guyana",
    "opencctv-eame": "opencctv",
    "OpenTrafficCamMap": "caltrans",
    # Rows labelled autobahn_nrw are Hessen Mobil clips.
    "autobahn_nrw": "hessen_mobil",
}
CALTRANS_DISTRICT_RE = re.compile(r"^Caltrans_D\d+$")

# Production scene/category labels -> published environment.
ENVIRONMENT_MAP = {
    "traffic": "traffic", "highway": "traffic",
    "city": "urban", "urban": "urban", "street": "urban", "webcam": "urban",
    "urban_panorama": "urban",
    "beach": "coastal", "waterfront": "coastal", "pier": "coastal",
    "coastal": "coastal", "boardwalk": "coastal",
    "harbor": "harbor", "marina": "marina",
    "river": "waterway", "water": "waterway", "waterfall": "waterway",
    "lake": "lake",
    "mountain": "mountain", "ski": "mountain",
    "nature": "nature",
    "landmark": "landmark",
    "airport": "transport",
}

QUERY = """
    SELECT url, title, display_name, lat, lng, country_code, source,
           category, scene_type, width, height, last_validated, quality_tier,
           source_kind, geolocation_confidence, quarantine_until
    FROM streams
    WHERE status = 'validated' AND source_kind IN ('video', 'mjpeg')
"""


def canonical_family(source):
    source = (source or "").strip() or "unknown"
    if CALTRANS_DISTRICT_RE.match(source):
        return "caltrans"
    return FAMILY_ALIASES.get(source, source)


def attribution(family):
    if family in ATTRIBUTION:
        return ATTRIBUTION[family]
    if family.startswith(INDONESIAN_CITY_PREFIXES):
        city = family.split("-", 1)[1].replace("kota", "").replace("_", " ").title()
        return f"Dinas Perhubungan {city} (Indonesia)"
    return None


def url_exclusion(url):
    """Return a reason string if the URL must not be published, else None."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return "non_http_url"
    if parts.username or parts.password:
        return "credentials_in_url"
    host = (parts.hostname or "").lower()
    if any(host == s or host.endswith("." + s) for s in TOKEN_HOST_SUFFIXES):
        return "token_host"
    if any(host == s or host.endswith("." + s) for s in UNCLEARED_HOST_SUFFIXES):
        return "uncleared_host"
    if re.fullmatch(r"[\d.]+|\[[0-9a-f:]+\]", host):
        return "bare_ip_host"
    for key, _ in urllib.parse.parse_qsl(parts.query, keep_blank_values=True):
        if AUTH_PARAM_RE.search(key):
            return "auth_query_param"
    if AUTH_PATH_RE.search(parts.path):
        return "session_or_bearer_path"
    return None


def url_type(url, source_kind):
    if source_kind == "mjpeg":
        return "mjpeg"
    parts = urllib.parse.urlsplit(url)
    path = parts.path.lower()
    query = parts.query.lower()
    if ".m3u8" in path:
        return "hls"
    if path.endswith(".mp4") or "format=mp4" in query:
        return "mp4"
    return "hls"


def iso_utc(value):
    if value in (None, "", 0):
        return None
    try:
        epoch = float(value)
        return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        pass
    text = str(value).strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            dt = datetime.strptime(text[:26], fmt)
            return dt.replace(tzinfo=timezone.utc).isoformat(timespec="seconds")
        except ValueError:
            continue
    return None


def coordinates_quality(confidence, shared_count):
    """Camera-level unless the position is shared by several cameras or the
    importer marked it as a fallback."""
    confidence = 0.5 if confidence is None else float(confidence)
    if confidence < 0.45:
        return "country_centroid"
    if confidence >= 0.8:
        return "exact"
    return "exact" if shared_count < 3 else "city"


def build(db_path, now_epoch):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = conn.execute(QUERY).fetchall()
    finally:
        conn.close()

    excluded = Counter()
    candidates = []
    seen_urls = set()
    for (url, title, display_name, lat, lng, cc, source, category, scene_type,
         width, height, last_validated, tier, source_kind, geo_conf, quarantine_until) in rows:
        url = (url or "").strip()
        family = canonical_family(source)
        if family in RETIRED_FAMILIES:
            excluded["retired_family"] += 1
            continue
        if family in LICENCE_EXCLUDED_FAMILIES:
            excluded[f"licence:{family}"] += 1
            continue
        if attribution(family) is None:
            # Allowlist: a family nobody has reviewed is never published.
            excluded[f"not_reviewed:{family}"] += 1
            continue
        reason = url_exclusion(url)
        if reason:
            excluded[reason] += 1
            continue
        if quarantine_until and float(quarantine_until) > now_epoch:
            excluded["currently_quarantined"] += 1
            continue
        try:
            lat, lng = float(lat), float(lng)
        except (TypeError, ValueError):
            excluded["no_coordinates"] += 1
            continue
        if not (-90 <= lat <= 90 and -180 <= lng <= 180) or (lat == 0 and lng == 0):
            excluded["bad_coordinates"] += 1
            continue
        if url in seen_urls:
            excluded["duplicate_url"] += 1
            continue
        seen_urls.add(url)
        candidates.append((url, title, display_name, lat, lng, cc, family, category,
                           scene_type, width, height, last_validated, tier,
                           source_kind, geo_conf))

    shared = Counter((round(c[3], 4), round(c[4], 4)) for c in candidates)
    features = []
    for (url, title, display_name, lat, lng, cc, family, category, scene_type,
         width, height, last_validated, tier, source_kind, geo_conf) in candidates:
        scene = (scene_type or category or "").strip().lower() or "traffic"
        environment = ENVIRONMENT_MAP.get(scene) or ENVIRONMENT_MAP.get(
            (category or "").strip().lower(), "urban")
        name = (title or "").strip() or (display_name or "").strip() or family
        if family == "hessen_mobil":
            name = name.replace("Germany - NRW - ", "Germany - Hessen - ")
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lng, 6), round(lat, 6)]},
            "properties": {
                "name": name,
                "url": url,
                "display_name": (display_name or "").strip() or name,
                "country_code": (cc or "").strip().upper() or "XX",
                "environment": environment,
                "source_family": family,
                "quality_tier": (tier or "standard").strip().lower(),
                "scene_type": scene,
                "url_type": url_type(url, source_kind),
                "resolution": f"{int(width)}x{int(height)}" if width and height else None,
                "coordinates_quality": coordinates_quality(
                    geo_conf, shared[(round(lat, 4), round(lng, 4))]),
                "status": "active",
                "last_verified": iso_utc(last_validated),
                "source_url_requires": None,
                "attribution": attribution(family),
            },
        })

    features.sort(key=lambda f: (f["properties"]["country_code"],
                                 f["properties"]["source_family"],
                                 f["properties"]["name"], f["properties"]["url"]))
    return {"type": "FeatureCollection", "features": features}, len(rows), excluded


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--db", required=True, help="Path to a local SQLite file (opened read-only)")
    parser.add_argument("--out", required=True, help="Output GeoJSON path, or - for stdout")
    args = parser.parse_args()

    now = datetime.now(timezone.utc).timestamp()
    data, total, excluded = build(args.db, now)

    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if args.out == "-":
        sys.stdout.write(text)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)

    print(f"rows selected: {total}", file=sys.stderr)
    print(f"features written: {len(data['features'])}", file=sys.stderr)
    for reason, count in sorted(excluded.items(), key=lambda kv: -kv[1]):
        print(f"excluded {reason}: {count}", file=sys.stderr)


if __name__ == "__main__":
    main()
