# How the Departure Prediction Works (Plain English)

**1. Get the timetable.** For your platform, we ask Traveline for the departure
board — "South Shields in 7 mins, Airport in 12 mins…". This is just the
schedule; it knows nothing about where trains actually are.

**2. Get the live trains.** Separately, the Nexus feed tells us where every
train on the network is right now, one short sentence per train: *"Train 123 —
Approaching Wallsend platform 2 at 16:04 — destination St James."*

**3. Pair them up.** For each scheduled departure, we look for a live train
that could be it: same destination, heading the right way for your platform,
and due at your station within 15 minutes of what the timetable expects.
Closest fit wins, and no train can be claimed by two departures.

**4. Estimate when the live train reaches you.** Every route is a known chain
of stations, and we have a run-time table for each hop (West Jesmond →
Jesmond: 2 min, etc.). Add up the hops between where the train was last seen
and your station, then three corrections:

- If it was "departing" or "approaching" its last station, it's already
  partway into the next hop — knock off half or 90% of that hop.
- Add **12 seconds per station it must stop at** on the way (the dwell time
  calibrated in the 2026-07-04 field test — without it, every stop drifted the
  estimate ~12 s further from reality).
- Subtract the minutes that have passed since the train was last spotted.

**5. Sanity-check against the timetable.**

- Live and schedule roughly agree (within ~3 min) → show the live ETA,
  **"On time"**.
- Live says notably *later* → believe it, **"Delayed (~X min)"** — trains
  genuinely run late, and testing showed these calls are right.
- Live says more than 2 min *earlier* → **don't believe it**. Metro trains
  wait at stations rather than run early; testing showed these "early" ETAs
  were almost always our own arithmetic being wrong. Show the scheduled time
  instead.
- No live train matched → just show the timetable, **"Scheduled"**.

## Worked example

Timetable says South Shields in 7 minutes. Train 131 was last seen departing
Ilford Road, two stops away — 3 min of track, minus 1 min for the hop it's
already in, plus 12 s dwell at West Jesmond ≈ 6½ min. That agrees with the
schedule, so you see *"South Shields — 6.5 min — On time [train 131]"*. Had
the sum come out at 11, you'd see *"Delayed (~11m)"*; at 3, we'd assume we
were wrong and show the scheduled 7.

The 2026-07-04 field test is the report card on steps 4–5: the displayed
number lands within about 1¼ minutes of the actual arrival on average, with no
systematic lean toward optimistic or pessimistic.
