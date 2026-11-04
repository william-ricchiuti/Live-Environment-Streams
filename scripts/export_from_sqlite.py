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
import ipaddress
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

# The allowlist: every published family, the credit it asks for, and the
# host suffixes its streams may use. A family not listed here is never
# exported, and a row whose host is not one of its family's hosts is dropped.
PUBLISHED_FAMILIES = {
    "caltrans": ("Caltrans (California Department of Transportation)", ("wzmedia.dot.ca.gov",)),
    "vdot": ("VDOT (Virginia Department of Transportation)", ("vdotcameras.com",)),
    "mndot": ("MnDOT (Minnesota Department of Transportation)", ("video.dot.state.mn.us",)),
    "iowa_dot": ("Iowa Department of Transportation", ("iowadot.gov",)),
    "mdsha": ("State of Maryland (MDOT SHA CHART)", ("sha.maryland.gov",)),
    "seattle_sdot": ("City of Seattle Department of Transportation", ("61e0c5d388c2e.streamlock.net",)),
    "ladotd_511": ("Louisiana DOTD (511LA)", ("dotd.la.gov",)),
    "deldot": ("DelDOT (Delaware Department of Transportation)", ("deldot.gov",)),
    "goakamai_hdot": ("Hawaii Department of Transportation (GoAkamai)", ("cdn3.wowza.com",)),
    "vegvesen_video": ("Statens vegvesen (NLOD)", ("kamera.vegvesen.no",)),
    "tdx_city_cctv": ("Keelung City Government via TDX (OGDL-Taiwan-1.0)", ("cctv.klcg.gov.tw",)),
    "trafficvision": ("Department of Highways, Thailand", ("highwaytraffic.go.th",)),
    "hessen_mobil": ("Hessen Mobil", ("verkehrsservice.hessen.de",)),
    "atcs-bandung": ("Dinas Perhubungan Bandung (Indonesia)", ("bandung.go.id",)),
    "atcs-cianjur": ("Dinas Perhubungan Cianjur (Indonesia)", ("cianjurkab.go.id",)),
    "atcs-denpasar": ("Dinas Perhubungan Denpasar (Indonesia)", ("denpasarkota.go.id",)),
    "atcs-palembang": ("Dinas Perhubungan Palembang (Indonesia)", ("palembang.go.id",)),
    "atcs-pekanbaru": ("Dinas Perhubungan Pekanbaru (Indonesia)", ("pekanbaru.go.id",)),
    "atcs-tasikmalaya": ("Dinas Perhubungan Tasikmalaya (Indonesia)", ("tasikmalayakota.go.id",)),
    "cctv-cirebon": ("Dinas Perhubungan Cirebon (Indonesia)", ("cirebonkota.go.id",)),
    "cctv-jogjakota": ("Dinas Perhubungan Kota Yogyakarta (Indonesia)", ("jogjakota.go.id",)),
    "cctv-kebumen": ("Dinas Perhubungan Kebumen (Indonesia)", ("kebumenkab.go.id",)),
    "cctv-magelang": ("Dinas Perhubungan Magelang (Indonesia)", ("magelangkota.go.id",)),
    "cctv-padang": ("Dinas Perhubungan Padang (Indonesia)", ("padang.go.id",)),
    "cctv-salatiga": ("Dinas Perhubungan Salatiga (Indonesia)", ("salatiga.go.id",)),
    "cctv-wonosobo": ("Dinas Perhubungan Wonosobo (Indonesia)", ("wonosobokab.go.id",)),
}

# Hosts whose stream URLs carry expiring or per-session credentials.
TOKEN_HOST_SUFFIXES = (
    "balticlivecam.com",
    "skylinewebcams.com",
    "youtube.com",
    "youtu.be",
    "googlevideo.com",
    "wetmet.net",
)

# Query parameters allowed in a published URL. Everything else (tokens,
# signatures, session ids, unknown keys) drops the URL.
SAFE_QUERY_KEYS = frozenset()

PRIVATE_HOST_SUFFIXES = (".local", ".internal", ".lan", ".home", ".localdomain", ".localhost")

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
    ORDER BY url, source
"""


def canonical_family(source):
    source = (source or "").strip() or "unknown"
    if CALTRANS_DISTRICT_RE.match(source):
        return "caltrans"
    return FAMILY_ALIASES.get(source, source)


def host_matches(host, suffixes):
    return any(host == s or host.endswith("." + s) for s in suffixes)


def url_exclusion(url, family):
    """Return a reason string if the URL must not be published, else None."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return "non_http_url"
    if parts.username or parts.password:
        return "credentials_in_url"
    if parts.fragment or ";" in parts.path:
        return "fragment_or_path_params"
    host = (parts.hostname or "").lower()
    try:
        ipaddress.ip_address(host)
        return "bare_ip_host"
    except ValueError:
        pass
    if "." not in host or host.endswith(PRIVATE_HOST_SUFFIXES) or re.fullmatch(r"[0-9a-fx.]+", host):
        return "private_host"
    if host_matches(host, TOKEN_HOST_SUFFIXES):
        return "token_host"
    if not host_matches(host, PUBLISHED_FAMILIES[family][1]):
        return "host_not_in_family"
    for key, _ in urllib.parse.parse_qsl(parts.query, keep_blank_values=True):
        if key.lower() not in SAFE_QUERY_KEYS:
            return "query_param"
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
    """ISO 8601 UTC string, None for an empty value, ValueError if unparseable."""
    if value in (None, "", 0):
        return None
    try:
        epoch = float(value)
    except (TypeError, ValueError):
        epoch = None
    if epoch is not None:
        if epoch > 1e12:  # milliseconds
            epoch /= 1000.0
        return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat(timespec="seconds")
    dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def normalised_url_key(url):
    """Duplicate-detection key: lower-case host, default ports dropped."""
    parts = urllib.parse.urlsplit(url)
    host = (parts.hostname or "").lower()
    port = parts.port
    if port and not ((parts.scheme == "https" and port == 443) or (parts.scheme == "http" and port == 80)):
        host = f"{host}:{port}"
    return (host, parts.path, parts.query)


def coordinates_quality(confidence, shared_count):
    """Camera-level unless the position is shared by several cameras or the
    importer marked it as a fallback."""
    confidence = 0.5 if confidence is None else float(confidence)
    if confidence < 0.45:
        return "country_centroid"
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
        if family not in PUBLISHED_FAMILIES:
            # Allowlist: a family nobody has reviewed is never published.
            excluded[f"not_reviewed:{family}"] += 1
            continue
        reason = url_exclusion(url, family)
        if reason:
            excluded[reason] += 1
            continue
        try:
            quarantined = bool(quarantine_until) and float(quarantine_until) > now_epoch
        except (TypeError, ValueError):
            quarantined = True  # unreadable state fails closed
        if quarantined:
            excluded["currently_quarantined"] += 1
            continue
        try:
            last_verified = iso_utc(last_validated)
        except (TypeError, ValueError):
            excluded["unparseable_last_validated"] += 1
            continue
        try:
            lat, lng = float(lat), float(lng)
        except (TypeError, ValueError):
            excluded["no_coordinates"] += 1
            continue
        if not (-90 <= lat <= 90 and -180 <= lng <= 180) or (lat == 0 and lng == 0):
            excluded["bad_coordinates"] += 1
            continue
        key = normalised_url_key(url)
        if key in seen_urls:
            excluded["duplicate_url"] += 1
            continue
        seen_urls.add(key)
        candidates.append((url, title, display_name, lat, lng, cc, family, category,
                           scene_type, width, height, last_verified, tier,
                           source_kind, geo_conf))

    shared = Counter((round(c[3], 4), round(c[4], 4)) for c in candidates)
    features = []
    for (url, title, display_name, lat, lng, cc, family, category, scene_type,
         width, height, last_verified, tier, source_kind, geo_conf) in candidates:
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
                "last_verified": last_verified,
                "source_url_requires": None,
                "attribution": PUBLISHED_FAMILIES[family][0],
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
