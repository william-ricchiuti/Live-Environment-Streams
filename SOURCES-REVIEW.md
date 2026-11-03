# Source licence review (v4.0.0, 2026-11-03)

Which camera sources this dataset publishes, and why. The question for each
source: may its public stream URL, camera name and coordinates be listed in a
public GeoJSON file? This is a good-faith review of each operator's published
terms. It is not legal advice.

**Rule:** a source is published only if it is cleared. Anything we could not
clear is left out. `scripts/export_from_sqlite.py` enforces this with an
allowlist, so a source nobody has reviewed is never exported.

Verdicts:
- **Cleared:** an explicit open licence or public-domain statement.
- **Cleared (provisional):** a public-sector operator that publishes the feed
  for the public, with no terms found either way. These rest on finding no
  restriction. If an operator objects, we remove it.
- **Excluded:** the terms forbid listing or redistribution, the content is
  commercial or re-hosted, or we could not clear it.

Counts are rows in the production pool on 2026-11-03.

## Published

| Family | Operator | Verdict | Licence / basis | Attribution | Terms read |
|---|---|---|---|---|---|
| `caltrans` (incl. district and OpenTrafficCamMap rows) | Caltrans | Cleared | Caltrans Conditions of Use: site information is public domain | Caltrans | https://dot.ca.gov/conditions-of-use |
| `iowa_dot` | Iowa DOT | Cleared | Open-data camera dataset listed as CC BY 4.0 | Iowa Department of Transportation | https://iowadot.gov/policies-statements/terms-use |
| `mdsha` | MDOT SHA (CHART) | Cleared | MD iMAP: free redistribution, derived data must credit the State | State of Maryland | https://catalog.data.gov/dataset/md-imap-maryland-traffic-cameras-traffic-cameras |
| `vegvesen_video` | Statens vegvesen | Cleared | NLOD (Norwegian Licence for Open Government Data) | Statens vegvesen | https://dataut.vegvesen.no/en/dataset/webkamera |
| `tdx_city_cctv` | Keelung City Government via TDX | Cleared | Open Government Data License v1.0 (Taiwan), as listed for TDX datasets | Keelung City Government via TDX | https://data.gov.tw/en/datasets/161157 |
| `vdot` | Virginia DOT | Cleared (provisional) | No current terms found; a 2001 VDOT policy asks for VDOT credit | VDOT | https://511.vdot.virginia.gov/ |
| `mndot` | MnDOT | Cleared (provisional) | No terms found | MnDOT | https://511mn.org |
| `seattle_sdot` | Seattle DOT | Cleared (provisional) | City open-data camera layer, licence not specified | City of Seattle DOT | Seattle open-data portal |
| `ladotd_511` | Louisiana DOTD | Cleared (provisional) | 511LA disclaimer covers only accuracy | Louisiana DOTD (511LA) | https://511la.org/about/disclaimer |
| `deldot` | DelDOT | Cleared (provisional) | No terms found | DelDOT | https://deldot.gov |
| `goakamai_hdot` | Hawaii DOT | Cleared (provisional) | No terms found | Hawaii DOT (GoAkamai) | https://hidot.hawaii.gov |
| `trafficvision` | Thailand Department of Highways | Cleared (provisional) | No terms found | Department of Highways, Thailand | https://www.highwaytraffic.go.th |
| `hessen_mobil` (was mislabelled `autobahn_nrw`) | Hessen Mobil | Cleared (provisional) | No licence found; site was unreadable (TLS error) | Hessen Mobil | https://www.verkehrsservice.hessen.de |
| `atcs-*`, `cctv-*` (Indonesian cities) | Municipal transport offices (Dinas Perhubungan) | Cleared (provisional) | Published for the public, no terms found | Dinas Perhubungan of the city | none found |

Within these families, rows on private hosts (`atcsindonesia.info`,
`aldilinux.my.id`, `jaring.host`, `iticfoundation.org`) and on bare IP
addresses are left out: 107 rows.

## Excluded

| Family | Rows | Reason | Terms read |
|---|---:|---|---|
| `opencctv` (incl. `opencctv-eame`) | 3,509 | Its terms forbid scraping and bulk download, and say the feeds stay the operators' property. Rows collected through it are not republished. The government feeds behind it (Korean city ITS, Indonesian, Brazilian, Thai) could come back once they are sourced from each agency directly. | https://opencctv.org/terms |
| `nysdot_511` (incl. `nysdot`, `nysdot_probe`) | 1,492 | 511NY releases its feeds only to developers who accept the NYSDOT Developers Access Agreement. We could not read that agreement, so this source is on hold until it is reviewed. | https://511ny.org/developers/resources |
| `aldot` | 552 | The streams are now encrypted with FairPlay `SAMPLE-AES` DRM (checked 2026-11-03 from two networks). They cannot be played without a licence server, and DRM is an access control we should not route around. | n/a |
| `manual` | 247 | Collected through opencctv; mixed private hosts, including livecameras.gr, which forbids retransmitting its streams. | https://opencctv.org/terms |
| `itic` | 98 | A private non-profit that marks its material "all rights reserved" and states no open licence. | https://www.iticfoundation.org/open-data-sharing |
| `balticlivecam` | 56 | All rights reserved, and its URLs carry access tokens. | https://www.balticlivecam.com |
| `worldviewstream` | 25 | Re-hosts other owners' streams and forbids redistribution. | https://worldviewstream.com/terms-and-conditions |
| `novascotia_webcams` | 15 | Commercial operator that sells licences; non-commercial terms with strict credit rules. | https://www-origin.novascotiawebcams.com/copyright |
| `resortcams` | 11 | No use without AppNet's written consent. | https://www.resortcams.com |
| `camguide` | 10 | A private directory of commercial and private streams. | https://www.camguide.net/terms/ |
| `coastalwatch-au`, `maritime-nsw` | 14 | Coastalwatch/Surfline subscription cam network. | https://www.coastalwatch.com/terms |
| `ipcamlive` | 8 | Hosting service; we don't know what each camera owner allows. | https://www.ipcamlive.com/termsofservice |
| `paspro`, `bpjt_stale`, `wikaserangpanimbang` | 10 | Private Indonesian toll operators; no terms found. | none found |
| `osm_webcam_pages` | 6 | Small private sites; terms not checked. Two URLs also carry Wowza tokens. | none read |
| `brownrice` | 3 | Commercial host; owners' terms unknown. | https://www.brownrice.com |
| `wetmet-poconos` | 2 | Commercial; the URL carries a per-client `uid` key. | site unreachable |
| `pixels_guyana` | 2 | Private operator; no terms found. | none found |
| `wral` | 1 | Broadcaster; its notices forbid redistribution. | WRAL copyright notice |
| `skyrail` | 1 | Personal use only; robots and data extraction forbidden. | https://skyrail.com.au/terms-of-use/ |

## Retired families (dropped, not marked)

`skylinewebcams`, `skyline-youtube`, `youtube` (and the many `youtube-*` discovery
families) and `webcamera_pl` are gone from the dataset. SkylineWebcams has blocked
server access since June 2026 and its page URLs need expiring tokens. YouTube Live
can no longer be extracted server-side. webcamera.pl was retired for its licence
terms. None of these sources has a row in the validated production pool, so there is
nothing to mark `retired`. See CHANGELOG 4.0.0.

## URL rules (all families)

Even in a cleared family, a URL is dropped if any of these apply:
- it has a token, signature, auth, key, hash, expiry, session or `uid` query parameter
- its path is a Wowza per-session `chunklist_w…`, a `/bearer/` segment or a JWT
- its host is known to issue expiring tokens (balticlivecam, SkylineWebcams, YouTube/googlevideo, wetmet)
- it has credentials in the URL, or its host is a bare IP address
