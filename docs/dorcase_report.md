# Report text for Member 1 (edit freely). All numbers are from the January 2019 file and were re-computed independently.

## 1. Problem framing: data challenges and assumptions
The file has 7,667,792 yellow-taxi trips. The cleaning pipeline removes 88,946 (1.16%) and keeps 7,578,846. Every removal is written
to `exclusion_log` with a reason code (98,524 rows, because one trip can break several rules).

| Problem | Trips | Decision |
|---|---|---|
| Distance 0 | 54,770 | Excluded (NON_POSITIVE_DISTANCE): minutes per mile cannot be computed |
| Trip longer than 3 hours | 20,913 | Excluded (EXCESSIVE_DURATION): the meter was left running |
| Negative fare (reversal) | 7,131 | Excluded (REVERSAL_OR_REFUND). Of the 406 rate-code-2 trips that cost exactly -$52, all are refunds |
| Speed above 80 mph, duration above 0 | 6,135 | Excluded (IMPOSSIBLE_SPEED) |
| Duration 0 | 6,290 | Excluded (ZERO_DURATION) |
| Zero fare | 2,426 | Excluded (ZERO_FARE) |
| Rate code 99 (not documented) | 252 | Excluded (INVALID_RATE_CODE) |
| Pickup date outside January 2019 (2001, 2003, 2008, 2009, 2088 ...) | 537 | Excluded (OUT_OF_RANGE_DATE) |
| Fare above $500 / distance above 100 mi | 34 / 32 | Excluded |
| Dropoff before pickup | 4 | Excluded |
| Unknown zone 264 / 265 | 170,637 kept | Kept and flagged (flag_unknown_zone); never ranked or mapped |
| Passenger count 0, missing or above 6 | 115,104 kept | Kept and flagged (flag_passenger_suspect) |
| Speed below 2 mph | 11,585 kept | Kept and flagged (flag_low_speed) |
| total_amount differs from its parts by more than $0.05 | 15,746 kept | Kept and flagged (flag_total_mismatch) |

Assumptions: the thresholds (3 hours, 80 mph, 100 miles, $500) are in `pipeline/config.py` and can be changed in one place.
Congestion surcharge exists in only 37 rows of January 2019, so a missing value is read as $0. Cash tips are not recorded
(311 of 2,137,415 cash trips show a tip, against 5,257,023 of 5,486,027 card trips), so we do not build any feature on tips.
No exact duplicate rows exist in this file; the duplicate check is kept because it costs little and other months may have them.
Why 1.16% and not the 3.38% of the first exploration: that count also removed the unknown-zone trips. We keep them (flagged)
because the trip itself is valid; only the place is unknown.

**Unexpected observation (pick one for the report):** 537 trips are dated 2001 to 2088 inside a January 2019 file, and they
sit in the raw averages. Removing impossible trips lowers the average speed from 13.17 mph (raw) to 11.72 mph (cleaned),
an 11% change, so the cleaning decision changes the headline number. This is why the dashboard has a raw / cleaned toggle.

## 2. Feature engineering (6 derived features, each from several raw columns)
| Feature | Formula | Why it matters |
|---|---|---|
| duration_min | (dropoff - pickup) in minutes | Base of all time features; also used to detect meter errors |
| avg_speed_mph | distance / (duration / 60) | Direct measure of congestion; also detects impossible trips |
| min_per_mile | duration / distance | The "cost of slowness" in time: minutes a rider spends for each mile |
| fare_per_min | fare / duration (flat-fare trips left out) | What a minute of traffic costs the rider and what a minute earns the driver |
| fare_per_mile | fare / distance | The price of distance; compared with min_per_mile it separates time cost from distance cost |
| pickup_hour, pickup_dow, is_weekend | from pickup timestamp | Lets the heatmap group by hour and weekday without recomputing |
| is_flat_fare | rate code = 2 | The $52 JFK fare does not depend on time, so it must not enter fare-per-minute |

## 4. Insights (derive with the endpoints named in brackets)
1. **Slow hours cost riders about 4 extra minutes per mile.** On weekdays the median trip takes 7.6 min/mile at 09:00 and 3.5 min/mile at 04:00.
   At 09:00 the median fare per mile is $6.49, against $4.00 at 04:00, while the fare per minute is lower ($0.82 against $1.19):
   the rider pays more per mile and the taxi earns less per minute. [/api/story/hour-profile?day_type=weekday]
2. **Slowest zones, with the data behind them.** Ranking weekday 08:00-09:59 pickups (30 trips minimum, unknown zones removed) gives
   zone 229, 186, 161, 162 and 100 as the slowest (about 8.7 to 9.4 min/mile). Each is shown with its trip count. [/api/story/slowest-zones?hour_from=8&hour_to=9&day_type=weekday]
3. **Cleaning changes the answer.** Raw mean speed is 13.17 mph and cleaned mean speed is 11.72 mph; the gap is largest at 01:00 on weekdays (4.2 mph),
   where a few impossible speeds weigh most because few trips exist. [/api/trust/raw-vs-clean]
Data limit to state: 57.7% of zone x hour x day-type cells have fewer than 30 cleaned trips (4,403 of 10,402 cells are reliable), so the
map shows only reliable cells and uses medians.
