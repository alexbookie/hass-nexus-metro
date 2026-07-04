# Live Data Investigation — Nexus API Lockdown & travelnortheast.uk

**Date:** 2026-07-03
**Trigger:** Integration sensors reported unavailable; Nexus reportedly "locked down the API"; new travelnortheast.uk site launched.

## Executive summary

1. **Root cause confirmed (post-investigation):** production runs released **v0.1.0**,
   which uses the metro-rti JSON API with Bearer JWTs scraped from the public web app
   (`auth.py`) — precisely what Nexus locked down (now HTTP 401). The Traveline + KML
   rewrite (v0.2.0) exists **only as uncommitted working-tree changes** on `dev`; it was
   never committed, released, or deployed. The new architecture's sources are unaffected
   by the lockdown and serving live data as of today.
2. **The full pipeline still works.** A spike script driving the integration's own
   `api.py` + `matching.py` against the live endpoints produced a correct combined
   departure board for West Jesmond (see `spike_departure_board.py` in this directory).
3. **travelnortheast.uk adds nothing for live Metro.** Its backend covers Metro but
   returns scheduled times only — the real-time layer is enabled for buses, not Metro.
4. **No alternative live source exists.** BODS, Darwin, and Realtime Trains have zero
   Metro coverage. The KML feed is the only open live source.
5. **Recommendation: commit and release the v0.2.0 rewrite, with the hardening below.**
   The rewrite is validated working end-to-end by the spike in this directory.

## What Nexus actually locked down

| Endpoint | Status (2026-07-03) |
|---|---|
| `metro-rti.nexus.org.uk/api/times/{station}/{platform}` | **401** — requires `Authorization: Bearer` (token minted inside the Pop app; no public key programme) |
| `metro-rti.nexus.org.uk/api/stations`, `/api/stations/platforms` | **401** |
| `app-metrortiapi-prod-001.azurewebsites.net/api/geo/trainstatuses.kml` | **200, no auth** — live, updating (verified: content changes between fetches, event times match current UK time) |
| `.../api/geo/traindirections.kml` | 200, no auth — train bearings |
| `.../api/geo/metrostations.kml`, `metrolines.kml` | 200, no auth — static reference |
| `.../api/geo/warning.kml`, `alerts.kml` | 200, no auth — disruption feeds (empty when no alerts) |
| `www.traveline.info/stops/{ATCO}` (with `X-Requested-With: XMLHttpRequest`) | 200 — sr-only fragment parses; 30 departures returned for WJS platform 1 |

The 401 is genuine auth-gating, not user-agent filtering (verified with the Pop app's
okhttp UA plus matching Origin/Referer). The community client for the JSON API
(`DanNixon/cadmium-yellow`) was archived on **2026-07-01** — likely the source of the
"they've locked down the API" news. Apps built on the JSON API broke; ours didn't use it.

**Caveat:** the KML host nominally expects a Bearer token (the official map sends one)
but does not enforce it. It is undocumented and could be gated the same way without
notice — this is the integration's key long-term risk.

## Diagnosis of the "sensors unavailable" report — CONFIRMED

The deployed and working-tree versions had diverged:

- **Production (HACS, tag v0.1.0 — the only release):** `api.py` targets
  `https://metro-rti.nexus.org.uk/api` and `auth.py` scrapes Bearer JWTs from the public
  web app, refreshing every ~30 minutes. Nexus's lockdown killed both the API (401) and
  the token-scraping route → coordinator failures → sensors unavailable.
- **Local working tree (v0.2.0, uncommitted on `dev`):** the full Traveline + KML
  rewrite (new `matching.py`, `metro_data.py`, deleted `auth.py`, rewritten tests).
  Never committed, pushed, released, or deployed — which is why the "current"
  architecture tested healthy from the dev machine while production was down.

The initial confusion arose because the working-tree CLAUDE.md describes the new
architecture, masking the fact that production runs the old one. Verified via
`git show v0.1.0:custom_components/nexus_metro/api.py` and `git status`.

## travelnortheast.uk findings

- Backend: **Trapeze LTS** journey planner on Azure API Management
  (`apim-public.trapezegroupazure.co.uk/tne/lts/lts/v1/public`), fronted by an Angular
  SPA at `jp.travelnortheast.uk`. Auth is a public `Ocp-Apim-Subscription-Key` shipped
  in the SPA's config JSON.
- `POST /departures` covers Metro stations (`stopType: "TRAM_STOP_AREA"`, platform ATCO
  codes as `stopIds`) and returns clean JSON — but `realTimeDeparture` is **null on
  every Metro row** while bus rows at the same instant carry real predictions and
  vehicle-tracking references. Tenant config confirms: `enableLiveTracking: false`.
- The prediction engine self-identifies as **ETNA** — the same upstream that feeds our
  KML — so if Nexus ever wires Metro real-time into this board, it would become a single
  structured live+scheduled source. Worth an occasional manual re-check, but today it is
  timetable-only for Metro, undocumented, key-rotatable, and terms-wise not intended for
  third-party use. **Do not build on it.**

## Alternative sources considered

| Source | Live Metro data? | Notes |
|---|---|---|
| Nexus KML feeds | **Yes** (current source) | Only open live source; unofficial, could be gated |
| Nexus JSON times API | Was best; now dead | 401, no key programme, no developer portal |
| travelnortheast.uk (Trapeze) | No — scheduled only for Metro | Live layer is bus-only today |
| BODS (DfT) SIRI-VM / GTFS-RT | No | Legally scoped to buses; light rail excluded |
| National Rail Darwin / Realtime Trains | No | Metro units absent from the national timetable, even on the shared Sunderland line |
| TransportAPI / Ito World / Google | No | Metro presence is static-GTFS derived |
| TNDS (Traveline National Dataset) | Timetable only | **Best official timetable source**: TransXChange covering light rail, weekly updates; free registration (~2 working days, FTP) |

## Recommendation

**Keep the Traveline + KML architecture. Harden it:**

1. **Fail-soft on Traveline errors.** Today a Traveline connection error raises
   `UpdateFailed` and (after retries) marks sensors unavailable, even though the KML
   side may be fine. Serve live-only (or last-known-schedule) data instead, and expose a
   `binary_sensor` or attribute for degraded mode.
2. **Add the disruption feeds.** `warning.kml` + `alerts.kml` are free to poll (same
   host, no auth) → disruption `binary_sensor` + attributes. Verified working in the
   spike.
3. **Defensive KML parsing.** The payload is free-text English inside HTML tables.
   Parser already returns `None` per placemark on mismatch — add a counter/log when the
   *overall* match rate collapses (signals a format change rather than quiet data loss).
4. **Poll the Azure host directly** (already the case) — the Cloudflare-fronted
   `metro-rti.nexus.org.uk` host issues bot challenges; the Azure origin does not.
5. **Polling etiquette.** Keep intervals ≥30–60s (current default 60s is fine). The feed
   is unofficial; low traffic is what keeps community access alive. Do **not** attempt
   to obtain/replay Pop-app Bearer tokens for the locked JSON API.
6. **Consider TNDS** as a longer-term replacement for Traveline HTML scraping (official,
   structured TransXChange vs. regexing sr-only text). Registration isn't instant, so
   it would ship as bundled/refreshed static data, not a config-flow credential.
7. **Watchdog idea (optional):** a periodic check that Metro rows on the Trapeze
   `/departures` endpoint still have `realTimeDeparture: null` — if that ever changes,
   revisit it as a cleaner primary source.

## Spike

`docs/research/spike_departure_board.py` — runs the integration's real `api.py`,
`matching.py`, and `metro_data.py` outside HA (stubs `homeassistant.const`, skips
`__init__.py`) and prints a combined live/scheduled board plus alert-feed status.

```
python docs/research/spike_departure_board.py WJS
```

Verified output (2026-07-03 18:05): 26 live trains; West Jesmond platforms 1–2 showing
correct destinations with `On time` / `Early (~Xm)` / `Delayed (~Xm)` / `Scheduled`
statuses and live ETAs matched to train running numbers.

## Next steps

1. Commit the v0.2.0 rewrite on `dev` (it is currently uncommitted working-tree state),
   finish the test rewrite in the devcontainer, and apply hardening items 1–3.
2. Note the branch divergence: `dev` carries the v0.1.0 release commits while `main`
   carries unmerged dependabot merges — reconcile before the next release.
3. Deploy to staging, verify, then release v0.2.0 → production via HACS.
4. Optionally register for TNDS now (lead time ~2 working days) so the timetable
   migration path is available later.
