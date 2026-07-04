# Live Arrival Prediction Accuracy — Field Test

**Date:** 2026-07-04 (Saturday, ~10:00–13:00 BST, engineering works on the
Sunderland line: East Boldon closed, green line short-turning at Pelaw /
Brockley Whins)
**Method:** A collector polled the KML feed every 30 s (ground truth: every
train's "Arrived *station* platform *N* at HH:MM" events, 1-minute granularity)
and ran the integration's real pipeline (`api.py` + `matching.py`) every 120 s
for West Jesmond P1/P2 and Monkseaton P1/P2. Each live prediction was later
scored against the actual arrival of that train at that platform.
**Scale:** 10,560 prediction rows, 1,444 ground-truth arrivals, **727 scored
live predictions**. Replays of the logged network snapshots allowed offline
model iteration on identical data.

## Headline results

| Model | MAE | Bias | ≤1 min | ≤2 min |
|---|---|---|---|---|
| Shipped model (raw live ETA) | 1.68 min | **+1.57 min** | 46% | 75% |
| Timetable only (same rows) | 1.30 min | +0.70 min | 86% | 92% |
| **Calibrated model (this branch)** | **0.99 min** | **−0.11 min** | 64% | **93%** |

The shipped model was systematically optimistic: trains arrived ~1.6 min later
than the live estimate claimed, with error growing over distance (+0.3 min for
trains 2 min away, +2.8 min for trains 20+ min away). On a day running to
schedule, the raw timetable comfortably beat it.

## Findings

### 1. Live matching was completely broken (fixed first)

Before any accuracy could be measured, the harness found **zero live matches**:

- Traveline destination text now reads "South Shields **Metro Station**" /
  "**Newcastle** Airport"; the KML feed uses bare names ("South Shields",
  "Airport"). `find_matching_train` compares exactly → nothing matched.
  *Fix: normalise at parse time (suffix strip + alias map) in `api.py`.*
- `GREEN_AIRPORT_TO_SOUTH_HYLTON` omitted Fellgate, Brockley Whins, and East
  Boldon (Pelaw→Seaburn was one 5-min hop; really 4 segments, ~11 min).
  *Fix: stations + segment times added.*
- `route_for_train` sliced by magic index: "Sunderland" trains routed only to
  Pallion; "Regent Centre" / "Monument East" routes ran the wrong direction;
  "Brockley Whins" (today's short-turn) was unknown.
  *Fix: slice by terminus code; Brockley Whins added.*

### 2. ETAs omitted platform dwell time (calibrated)

Segment times model track time only. The per-stop error signature (+~0.1–0.15
min per remaining stop) pointed at dwell; a replay sweep over the 727 scored
predictions found **0.2 min per intermediate stop** minimises MAE while nearly
zeroing bias (`DWELL_TIME_MINS = 0.2`).

| Dwell/stop | MAE | Bias |
|---|---|---|
| 0.0 (shipped) | 1.67 | +1.57 |
| 0.15 | 1.34 | +0.66 |
| **0.20** | **1.35** | **+0.36** |
| 0.25 | 1.42 | +0.06 |
| 0.30 | 1.54 | −0.25 |

### 3. "Early (~Xm)" was an artifact, not a real state (removed)

212 predictions were labelled Early. Their live estimates were wrong by
**+3.3 min on average (0% within 1 min)** — while the timetable said those same
trains were on schedule (93% within 1 min). Even after dwell correction, the
surviving "early" ETAs stayed ~3 min wrong. Metro trains hold to schedule;
live estimates >2 min ahead of the timetable are model error, not early
running.
*Fix: such estimates are discarded — the sensor falls back to the scheduled
time and reports "On time" (`EARLY_DISTRUST_THRESHOLD = 2.0`). The matched
train's ID stays visible in attributes.*

## Remaining error profile (calibrated model)

- MAE 0.99 min against ground truth that is itself quantised to whole minutes
  (a perfect predictor would score ~0.25 MAE on this ground truth).
- Estimates for trains ≤5 min out are excellent; the 20 min+ tail still
  wobbles (long routes accumulate segment-time noise) but is now unbiased.
- "Delayed (~Xm)" labels were directionally right throughout (bias +1.8
  pre-fix, improved by dwell correction).
- Caveat: single-day sample, engineering-works Saturday, two stations. A
  weekday-rush repeat run would strengthen the calibration; the collector and
  replay tools are in this directory.

## Changes on `feature/matching-fixes`

1. `api.py`: Traveline destination normalisation (suffix strip + alias map)
2. `metro_data.py`: Sunderland-line stations/segments restored; route slicing
   by terminus code; Brockley Whins short-turns
3. `matching.py` + `const.py`: `DWELL_TIME_MINS = 0.2` per intermediate stop;
   implausibly-early live ETAs fall back to schedule; "Early" status removed
4. Tests updated/added (66 passing)

## Tools (scratchpad, reusable)

`accuracy_collector.py` (chunked collector), `accuracy_analyzer.py`
(prediction-vs-arrival scoring), `replay_calibrate.py` (offline model sweeps
over logged snapshots). Worth re-running for a weekday sample before the next
release.
