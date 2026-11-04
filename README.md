# Live Environment Streams

A curated, agent-optimized GeoJSON dataset of public live camera streams from road authorities
in the US, Indonesia, Thailand, Norway, Taiwan and Germany.
Originally created to power [twitch.tv/alwaysrainsomewhere](https://www.twitch.tv/alwaysrainsomewhere).

**6,903 streams · 6 countries · 26 sources · all from public road authorities · every URL directly playable**

Version 4.0.0 (2026-11-03) is a fresh export of the production camera pool. It lists only
sources whose terms allow it (see [`SOURCES-REVIEW.md`](SOURCES-REVIEW.md)), and only URLs
with no tokens or signatures. SkylineWebcams and YouTube are gone. See [`CHANGELOG.md`](CHANGELOG.md).

## Data quality

Not all streams are equal. The schema includes fields that tell you exactly what you're getting:

| Field | What it tells you |
|-------|-------------------|
| `url_type` | `hls` (m3u8 manifest), `mjpeg` (multipart JPEG stream) or `mp4` (short clip the operator refreshes) |
| `coordinates_quality` | Whether coordinates are camera-level (`exact`), city-level (`city`), or a capital fallback (`country_centroid`) |
| `status` | `active` = in the production pipeline's validated pool on the export date |
| `last_verified` | When the production pipeline last recorded a successful validation (may be weeks old; see Known limitations) |
| `resolution` | Probed video resolution where known (e.g. `1280x720`) |
| `source_url_requires` | Special handling needed; always `null` in this release |
| `attribution` | The credit the source operator asks for. Keep it when you republish |

Unlike most webcam lists, `active` here is not a one-time HTTP 200 check. It means the camera is
in the validated pool of a production streaming system that plays these feeds 24/7.

**Recommended query for agent pipelines.** This returns direct video URLs with camera-level positions:

```python
usable = [
    f for f in streams
    if f["properties"]["status"] == "active"
    and f["properties"]["url_type"] == "hls"
    and f["properties"]["coordinates_quality"] == "exact"
]
# 6,389 streams; pass the URL straight to ffmpeg/ffprobe
```

Add `"mjpeg"` and `"mp4"` to the `url_type` filter if your pipeline handles them
(for MJPEG, `ffprobe -f mpjpeg <url>`).

## Quick start (no clone needed)

```python
import json, urllib.request

URL = "https://raw.githubusercontent.com/william-ricchiuti/Live-Environment-Streams/main/streams.geojson"
streams = json.load(urllib.request.urlopen(URL))["features"]

# One country only (smaller download): https://raw.githubusercontent.com/william-ricchiuti/Live-Environment-Streams/main/data/NO.json
```

Pin a version instead of `main` by using a release tag in the URL, e.g.
`https://raw.githubusercontent.com/william-ricchiuti/Live-Environment-Streams/v4.0.0/streams.geojson`.

## Usage

```python
import json
import random

with open("streams.geojson", "r") as f:
    data = json.load(f)

streams = data["features"]
selected = random.choice(streams)
props = selected["properties"]
coords = selected["geometry"]["coordinates"]

print(f"Loading {props['name']} at {coords}")
print(f"URL: {props['url']} (type: {props['url_type']})")
print(f"Resolution: {props['resolution']} | Source: {props['source_family']}")
print(f"Credit: {props['attribution']}")
```

Filter by country or quality:

```python
# All streams for a specific country
no_streams = [f for f in streams if f["properties"]["country_code"] == "NO"]

# HD streams only
hd = [f for f in streams
      if f["properties"]["resolution"]
      and int(f["properties"]["resolution"].split("x")[1]) >= 720]
# 1,028 streams
```

## GeoJSON schema

Each `Feature` in `streams.geojson`:

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [7.939882, 58.141163]
  },
  "properties": {
    "name": "NO - Agder - Fidjane mot Kristiansand (E39)",
    "url": "https://kamera.vegvesen.no/public/1029002_1/manifest.m3u8",
    "display_name": "Agder, Norway",
    "country_code": "NO",
    "environment": "traffic",
    "source_family": "vegvesen_video",
    "quality_tier": "high",
    "scene_type": "traffic",
    "url_type": "hls",
    "resolution": "1024x576",
    "coordinates_quality": "exact",
    "status": "active",
    "last_verified": "2026-10-27T15:15:50+00:00",
    "source_url_requires": null,
    "attribution": "Statens vegvesen (NLOD)"
  }
}
```

### Property reference

| Property | Type | Description |
|----------|------|-------------|
| `name` | string | Descriptive camera name |
| `display_name` | string | Human-readable location label (city/region) |
| `url` | string | Stream URL (HLS manifest, MJPEG stream or MP4 clip) |
| `country_code` | string | ISO 3166-1 alpha-2 country code |
| `environment` | string | Scene category (see table below) |
| `source_family` | string | Data source identifier (see `sources.json`) |
| `quality_tier` | string | `premium`, `high`, `standard`, or `low` (production scoring tier) |
| `scene_type` | string | Granular scene label |
| `url_type` | string | `hls`, `mjpeg`, or `mp4` |
| `resolution` | string/null | Probed video resolution (`WxH`), where known |
| `coordinates_quality` | string | `exact`, `city`, or `country_centroid` |
| `status` | string | `active` |
| `last_verified` | string/null | ISO 8601 UTC timestamp of the last recorded validation |
| `source_url_requires` | null | Kept for compatibility; `null` for every stream in 4.0.0 |
| `attribution` | string | Credit requested by the source operator |

### Environment values

| Environment | Count | Description |
|-------------|------:|-------------|
| `traffic` | 6,893 | Road/highway cameras |
| `landmark` | 8 | Landmarks |
| `lake` | 2 | Lake views |

Scenic, coastal and mountain cameras from commercial networks were dropped in 4.0.0 because
their terms do not allow listing them (see `SOURCES-REVIEW.md`).

### URL types

| Type | Count | How to use |
|------|------:|------------|
| `hls` | 6,832 | Pass directly to ffmpeg/ffprobe |
| `mjpeg` | 63 | `ffmpeg -f mpjpeg -i <url>` |
| `mp4` | 8 | Short clips the operator replaces every few minutes; re-fetch to update |

### Coordinates quality

| Quality | Count | Accuracy |
|---------|------:|----------|
| `exact` | 6,453 | Position from the operator's feed, not shared with two or more other cameras |
| `city` | 449 | Three or more cameras share one position (interchange or city level) |
| `country_centroid` | 1 | Fallback; do not use for geo-queries |

## Sources

| Source | Streams | Operator | Licence / basis |
|--------|--------:|----------|-----------------|
| caltrans | 1,676 | California DOT | Public domain |
| vdot | 1,174 | Virginia DOT | Public sector, no terms found |
| mndot | 973 | Minnesota DOT | Public sector, no terms found |
| iowa_dot | 543 | Iowa DOT | CC BY 4.0 |
| mdsha | 404 | Maryland SHA (CHART) | MD iMAP open data |
| seattle_sdot | 341 | Seattle DOT | Public sector, no terms found |
| ladotd_511 | 330 | Louisiana DOTD | Public sector, no terms found |
| deldot | 260 | Delaware DOT | Public sector, no terms found |
| goakamai_hdot | 247 | Hawaii DOT | Public sector, no terms found |
| trafficvision | 155 | Thailand Department of Highways | Public sector, no terms found |
| vegvesen_video | 106 | Statens vegvesen (Norway) | NLOD |
| tdx_city_cctv | 63 | Keelung City via Taiwan TDX | OGDL-Taiwan 1.0 |
| hessen_mobil | 8 | Hessen Mobil (Germany) | Public sector, no terms found |
| 13 Indonesian city families (`atcs-*`, `cctv-*`) | 623 | City transport offices | Public sector, no terms found |

Full per-source metadata (licence, attribution, terms URL, counts) is in `sources.json`.
Why each source is in or out: `SOURCES-REVIEW.md`.

## Country coverage

| Country | Streams |
|---------|--------:|
| US | 5,948 |
| ID | 623 |
| TH | 155 |
| NO | 106 |
| TW | 63 |
| DE | 8 |

## Licence

- **Data** (`streams.geojson`, `data/`, `sources.json`): [CC BY 4.0](LICENSE). Credit
  "Live Environment Streams (William Ricchiuti)" **and** keep each stream's `attribution`
  field. Some upstream licences (NLOD, CC BY 4.0, MD iMAP) require that operator credit.
- **Scripts** (`scripts/`): [MIT](scripts/LICENSE).
- **Citation:** see [`CITATION.cff`](CITATION.cff), or use GitHub's "Cite this repository" button.

## Attribution

When you republish or display these streams, credit the operator given in each feature's
`attribution` field. Licences that require it:
- **Statens vegvesen:** NLOD. Cite Statens vegvesen as the source.
- **Taiwan TDX / Keelung City Government:** Open Government Data License v1.0. Name the data provider.
- **Iowa DOT:** CC BY 4.0. Credit the Iowa Department of Transportation.
- **Maryland:** MD iMAP. Derived data must credit the State of Maryland.

The video belongs to its operators. This dataset lists where to find each public stream;
it does not grant any right to the footage.

## Directory structure

```
streams.geojson          # Master file (all 6,903 streams)
LICENSE                  # CC BY 4.0 (data); scripts/LICENSE is MIT
CITATION.cff             # How to cite the dataset
sources.json             # Per-source metadata (licence, attribution, terms URL, counts)
SOURCES-REVIEW.md        # Licence/terms finding for every source, included or excluded
data/                    # Per-country GeoJSON subsets (e.g. data/US.json)
scripts/
  export_from_sqlite.py  # Build streams.geojson from a camera SQLite DB, with the publication policy
  validate.py            # Probe stream URLs, update status/last_verified
  geocode_swc.py         # Legacy: SkylineWebcams geocoding (source retired in 4.0.0)
  regenerate_country_files.py  # Rebuild data/ from streams.geojson
  stats.py               # Print dataset statistics
.github/workflows/
  validate.yml           # Manual-trigger validation
```

## Known limitations

1. **Mostly traffic cameras, mostly the US.** 4.0.0 keeps only sources whose terms allow
   listing them. Scenic networks and the opencctv aggregator were dropped, so Korea, Europe
   (apart from Norway and Hesse) and most scenic views are gone for now.
2. **Regional reachability.** Indonesian and Thai feeds are often slow or time out when
   fetched from North America or Europe, even though they play from the production server.
3. **`last_verified` can be old.** It is the last validation the production pipeline
   recorded. Cameras stay in the pool while they keep playing, and not every pass re-stamps
   the time. 1,308 streams have no recorded timestamp at all.
4. **Provisional clearances.** Most US DOTs and the Indonesian/Thai agencies publish their
   feeds without stated terms. They are listed because nothing we found forbids it. If an
   operator objects, open an issue and the source will be removed.

## Contributing

To add a new source:

1. Check the operator's terms and add a row to `SOURCES-REVIEW.md`. To export it, add the
   family, its attribution and its stream hosts to `PUBLISHED_FAMILIES` in
   `scripts/export_from_sqlite.py`.
2. Add streams to `streams.geojson` following the schema above. All fields are required,
   including `attribution` (`resolution` and `last_verified` may be `null`). Never add URLs with tokens or signatures.
3. Add source metadata to `sources.json`.
4. Run `python scripts/regenerate_country_files.py` to update `data/`.
5. Run `python scripts/stats.py` to verify counts.
6. Update this README with new totals.

<div align="center">
  <code>#dataset</code> <code>#computer-vision</code> <code>#live-weather</code> <code>#machine-learning</code> <code>#webcams</code>
  <code>#hls-streams</code> <code>#geojson</code> <code>#environment-monitoring</code>
  <code>#traffic-cameras</code> <code>#ai-agents</code> <code>#geospatial</code>
</div>
