# Changelog

## [4.0.0] - 2026-11-03

A fresh export of the production camera pool. Every listed source was checked against its
operator's terms. Stream count: 5,997 → 6,903. Every stream is `active` and has a direct URL.

### Changed
- **Regenerated from the production pool** with `scripts/export_from_sqlite.py`. The export takes
  the validated live-video and MJPEG cameras (13,072 rows) and applies the publication policy.
  It opens the database read-only.
- **Allowlist publication policy.** A source is exported only if it has a reviewed entry
  (`SOURCES-REVIEW.md` and `PUBLISHED_FAMILIES` in the script), and only from that
  source's own hosts. Published URLs carry no query string, fragment or path parameters. Any URL with a token, signature, auth, key, expiry, session or `uid`
  parameter, a Wowza per-session chunklist, a bearer path segment, credentials or a bare IP
  host is dropped.
- `sources.json` rebuilt: 26 families, with `license`, `attribution` and `terms_url` fields
  instead of the blanket `fair_use` label. Small producer-specific families are merged:
  `Caltrans_D01..D12` and `OpenTrafficCamMap` into `caltrans`; `ladot`, `ladot_probe` and
  `Louisiana_DOT` into `ladotd_511`; `vdotcameras` into `vdot`. `autobahn_nrw` is renamed
  `hessen_mobil`, because those streams come from Hessen Mobil, not NRW.
- `coordinates_quality`: `exact` unless the importer marked a fallback, or three or more
  cameras share one position (then `city`). Result: 6,453 exact, 449 city, 1 fallback.
- `scripts/validate.py` now probes `mjpeg` and `mp4` URLs. `scripts/stats.py` counts them as
  directly usable.

### Added
- More than 4,000 road-authority cameras: Caltrans (1,676), MnDOT (973), Iowa DOT (543),
  Seattle DOT (341), Louisiana DOTD (330), Hawaii DOT (247), Norway's Statens vegvesen video
  (106), Keelung/Taiwan TDX MJPEG (63) and 13 Indonesian city transport offices (623).
- `attribution` property on every feature: the credit each operator asks for.
- `url_type` values `mjpeg` and `mp4`.
- `SOURCES-REVIEW.md`: the licence/terms finding for every source, included or excluded.

### Removed
- **Retired families are dropped, not marked `status: retired`.** SkylineWebcams (1,684) has
  blocked server access since June 2026, and its URLs need tokens that expire within hours.
  YouTube (475, including `skyline-youtube` and the `youtube-*` discovery families) can no
  longer be extracted server-side. None of these has a validated row in the production
  pool, so nothing could truthfully be marked, and an entry nobody can play is noise for an
  agent filtering this file. `html_page` and `youtube` URL types are gone with them.
- **Sources whose terms forbid listing, or which could not be cleared** (details in
  `SOURCES-REVIEW.md`): opencctv (its terms forbid scraping; this removes the Korean, Turkish,
  Polish and other aggregator rows), 511NY/NYSDOT (needs a developer agreement we have not
  read), iTIC, balticlivecam, worldviewstream, Coastalwatch/maritime-nsw, resortcams,
  camguide, Nova Scotia Webcams, ipcamlive, brownrice, WRAL, Skyrail, wetmet and small
  private sites.
- **ALDOT (552)**: its streams are now FairPlay `SAMPLE-AES` encrypted and cannot be played
  without a licence server.
- webcamera_pl: retired for licence terms.
- Country coverage drops from 98 to 6 (US, ID, TH, NO, TW, DE), and scenic environments are
  gone. This is the cost of listing only cleared sources. Sources can come back as each one
  is cleared directly with its operator.

## [3.0.0] - 2026-06-12

### Changed
- **Full regeneration from the production database.** The dataset is now exported directly from the live RainAlways selector DB, inheriting its continuous validation state. Stream count: 5,172 → 5,997 across 98 countries.
- `status` is now meaningful: 4,226 streams marked `active` with real `last_verified` probe timestamps (previously all 5,172 were `unverified`).
- `quality_tier` now carries the production scoring tiers (`premium`/`high`/`standard`/`low`) instead of `unknown`.
- SkylineWebcams entries publish stable page URLs only — expiring-token HLS URLs removed entirely, including 173 with no known page URL (they were dead within hours of publication).
- `coordinates_quality` recomputed from geocoding confidence: country-centroid fallbacks down from 1,057 to 10.

### Added
- `resolution` field: probed `WxH` for 1,172 streams (717 confirmed 720p+).
- `active_count` per source family in `sources.json`.
- ~200 newly validated cameras in rain-prone, previously under-covered regions: Japan (now 129 streams), New Zealand, Iceland, Norway, Ireland, Scotland, SE Asia (Davao, Bangkok, Hanoi, Da Nang, KL, Singapore), Pacific Northwest, and BC Canada.
- 48 new source families (67 total), including vegvesen, balticlivecam, beachcam_meo, webcamera_pl, worldviewstream, camguide.

### Removed
- ~2,400 stale SkylineWebcams duplicates (expired-token URLs and page-URL duplicates of the same cameras).
- All dead, rejected, and quarantined streams — the dataset now contains only `active` and `unverified` entries.
- `http_image` URL type (static snapshot endpoints dropped; this is a live-video dataset).
- Source families: earthcam (paywalled), panama_canal, quebec511 (dead feeds).

## [2.0.0] - 2026-04-29

### Removed
- 62 Caltrans streams (`wzmedia.dot.ca.gov`) — confirmed returning 403, blacklisted in production
- 8 Indonesian toll road streams (5 source families: margaharjaya, waskitabumiwira, wikaserangpanimbang, serbaraja_toll, tangerangkab) — geo-blocked, unreachable from US/EU servers

### Added
- `url_type` field: `hls`, `youtube`, `html_page`, `http_image` — tells agents what kind of URL they're getting
- `coordinates_quality` field: `exact`, `city`, `country_centroid` — flags 1,057 streams with fake fallback coordinates
- `status` field: `active`, `unverified`, `deprecated` — all streams start as `unverified`
- `last_verified` field: ISO 8601 timestamp, null until validation pipeline runs
- `source_url_requires` field: `browser`, `token_refresh`, or null — flags streams needing special handling
- `sources.json`: per-source-family metadata (full name, license type, notes)
- `scripts/validate.py`: probe stream URLs and update status/last_verified
- `scripts/geocode_swc.py`: fix fallback coordinates using Nominatim geocoding
- `scripts/regenerate_country_files.py`: rebuild data/ from streams.geojson
- `scripts/stats.py`: print dataset statistics
- `.github/workflows/validate.yml`: weekly automated validation via GitHub Actions
- `CHANGELOG.md`: this file

### Changed
- `quality_tier` values reset — 2,106 HTML-page streams previously marked "premium" now marked "unknown"
- `display_name` enriched for DOT and autobahn sources (extracted locality from name field)
- README rewritten with data quality section, known limitations, contributing guide
- `llms.txt` rewritten with agent query patterns and data quality caveats
- Stream count: 5,242 → 5,172

## [1.0.0] - 2026-04-28

### Added
- Initial release with 5,242 streams across 80 countries
- GeoJSON schema with name, url, country_code, environment, source_family, quality_tier, scene_type
- Per-country data files in data/
- llms.txt for LLM/agent consumption
