# Urban Mobility Data Explorer

**What does slow traffic cost in New York City?** We took 7.6 million yellow taxi trips from January 2019, cleaned them, stored them in MySQL, and built a dashboard that answers that question by **time**, by **place** and by **money**, and shows how far the data can be trusted.

**Team:** Dorcase Lesly Nana Tounda, Tchatchum Chassem Stephane, Olivier Migisha
**Course:** Enterprise Web Development (ALU), Summative

## Links

| Item | Link |
| --- | --- |
| GitHub repository | https://github.com/stephanetchatchum/Urban_Mobility_Data_Explorer/ |
| Video walkthrough (5 min) | https://youtu.be/IRXu7llrP2o |
| Team participation sheet | https://docs.google.com/spreadsheets/d/15akxAc732NmQ7czdXkQ35M9AJZjRKmQZydInbm_4YSk/edit?gid=0#gid=0 |

## 1. Project overview

The system has four stages:

1. **Cleaning pipeline** (Python, pandas, pyarrow, geopandas). It reads the raw trip file in chunks of 500,000 rows, applies 16 exclusion rules and 4 flag rules, and writes every removed record to an exclusion log with its reason. It also derives new features (speed, minutes per mile, fare per minute and more) and precomputes medians.
2. **MySQL database.** A normalised schema with foreign keys, indexes, an exclusion log, and small pre-aggregated statistics tables.
3. **Flask API.** Read-only JSON endpoints. Rankings use a **min-heap we wrote by hand**, not `ORDER BY`.
4. **Dashboard** (HTML, CSS, JavaScript). It only calls the API and never touches the database.

Every number on the dashboard comes with a trust layer: how many trips support it and how many records were removed.

### Data at a glance

| | |
| --- | --- |
| Raw trips (January 2019) | 7,667,792 |
| Removed by cleaning | 88,946 (1.16%) |
| Trips kept | 7,578,846 |
| Taxi zones | 265 |

Trips in unknown zones (264 and 265) are kept and flagged, but never ranked or mapped.

### Our three insights

- **Time:** a mile takes a median 7.6 minutes at 09:00 on weekdays and 3.5 minutes at 04:00. At 09:00 the rider pays more per mile while the driver earns less per minute.
- **Space:** for weekday mornings, the slowest pickup zones are all in Manhattan, led by Penn Station/Madison Sq West. Each ranking shows how many trips stand behind it.
- **Money:** fare, fees and card tip rate change through the day, so slow hours have a price.

Cleaning also changes the answer: the raw average speed is 13.17 mph and the cleaned one is 11.72 mph, so the dashboard has a raw / cleaned switch.

## 2. Project structure

```
pipeline/    load_data, clean_data, feature_engineering, zones_to_geojson, run_pipeline,
             build_aggregates, load_to_db, load_extras, reasons, config
backend/     app.py (Flask), routes/ (story, economics, heatmap), db.py,
             algorithms/custom_algorithm.py (manual min-heap)
frontend/    index.html, css/, js/ (api, charts, map, trips, filters, main)
database/    schema.sql, indexes.sql, init_db.py, schema_design.md
data/        raw/ (not in Git), processed/ and logs/ (generated, not in Git)
docs/        API_SPEC, DATABASE_SCHEMA, architecture_diagram, data_dictionary,
             exclusion_log_notes, heap_notes
tests/       pytest suite (cleaning rules, aggregates, story API, economics, heatmap, heap)
```

The architecture diagram is in [`docs/architecture_diagram.md`](docs/architecture_diagram.md).

## 3. Prerequisites

- Python 3.10 or newer
- MySQL 8, or a MySQL-compatible server (local, or a cloud one). Create an empty server and note its host, port, user and password.
- About 1 GB of free disk space for the data and the database
- A modern browser (we used Chrome)

## 4. Getting the data

The data is too large for Git. Download these files and put them in `data/raw/`:

- `yellow_tripdata_2019-01.csv` (or `.parquet`) from the NYC Taxi and Limousine Commission trip record data
- `taxi_zone_lookup.csv`
- the `taxi_zones` shapefile (`taxi_zones.shp`, `.shx`, `.dbf`, `.prj`)

## 5. Installation and environment setup

```
git clone https://github.com/stephanetchatchum/Urban_Mobility_Data_Explorer.git
cd Urban_Mobility_Data_Explorer
python -m venv .venv
.venv\Scripts\activate          # macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Set the database connection. Never write the password in a file or commit it.

Windows PowerShell:
```
$env:DB_HOST="127.0.0.1"; $env:DB_PORT="3306"; $env:DB_USER="root"; $env:DB_PASSWORD="your_password"; $env:DB_NAME="urban_mobility"
```

macOS / Linux:
```
export DB_HOST=127.0.0.1 DB_PORT=3306 DB_USER=root DB_PASSWORD=your_password DB_NAME=urban_mobility
```

If the server requires SSL, also set `DB_SSL_CA` to the path of its certificate file.

## 6. Running the data pipeline

```
python -m pipeline.run_pipeline          # cleans the trips, about 3 minutes
python -m pipeline.build_aggregates      # builds the summary tables, about 1 minute
```

This writes `data/processed/` (cleaned trips as Parquet, zone GeoJSON, statistics CSV files) and `data/logs/` (exclusion log and cleaning summary).

## 7. Creating the database

Run these in order:

```
python -m database.init_db schema            # creates the tables and fills zones, payment types and rate codes
python -m pipeline.load_to_db --check        # tests the connection and the table columns
python -m pipeline.load_to_db                # loads the trips, about 8 minutes
python -m pipeline.load_extras               # loads zone geometry facts and the statistics tables
python -m database.init_db indexes           # creates the indexes, after the bulk load
```

Notes:

- Indexes are created last on purpose. Building them during the load would slow down every insert.
- If the database already exists from an earlier attempt, `schema` stops at the first table it finds. Use `python -m database.init_db schema --reset` to rebuild it. **This drops the whole database.**
- `load_to_db --limit-rows N` loads only the first N trips and is for quick tests only. It does not give a fair sample of the month.
- Check the result: `SELECT COUNT(*) FROM trips;` should return about 7.5 million.

Schema design and the reasons behind each choice are in [`database/schema_design.md`](database/schema_design.md).

## 8. Starting the backend

With the environment variables from step 5 set, in the project folder:

```
python -m backend.app
```

The API runs at `http://127.0.0.1:5000`. Check it at `/api/health`, which should return `{"status":"ok"}`. Endpoints are listed in [`docs/API_SPEC.md`](docs/API_SPEC.md). The main ones:

| Path | Purpose |
| --- | --- |
| `/api/story/hour-profile` | Minutes per mile, speed and fares by hour |
| `/api/story/zone-hour` | One value per zone for a chosen hour (map colouring) |
| `/api/story/slowest-zones` | Top slowest zones with the trips behind each |
| `/api/economics/by-hour` | Fare, fees and card tip rate per hour |
| `/api/time/heatmap` | Day of week by hour grid |
| `/api/insights/top-routes` | Busiest pickup and dropoff pairs |
| `/api/trips` | Filter, sort and page through cleaned trips |
| `/api/trust/summary` | Every cleaning rule with its row count |
| `/api/trust/raw-vs-clean` | Average speed before and after cleaning |

## 9. Starting the frontend

In a second terminal:

```
cd frontend
python -m http.server 8080
```

Open `http://localhost:8080/index.html` in the browser. Do not open the file by double-clicking it. Keep both terminals running.

The dashboard has these sections: trip overview, filters (day type, hour, cleaned or raw data), the price of slowness by hour, slowest taxi zones, a time heatmap, a slowness map, busiest routes, economics, a trip explorer with a detail window, and a data trust panel.

Two calls read the full trips table and are slower than the rest: the first heatmap load and the busiest routes. Give the page a moment on first load.

## The min-heap

Rankings use our own `MinHeap` in `backend/algorithms/custom_algorithm.py`, with a helper `k_smallest`. The heap keeps the smallest value at the root. To get the slowest zones we push each zone with its minutes per mile as a negative number and pop K times.

| Operation | Time |
| --- | --- |
| push | O(log n) |
| pop | O(log n) |
| build with n pushes | O(n log n) |
| extract K items | O(K log n) |
| space | O(n) |

With about 260 zones a sort would also be fast. The heap pays off when n is large and K is small. Pseudo-code and the full reasoning are in [`docs/heap_notes.md`](docs/heap_notes.md).

## Tests

```
python -m pytest tests -q
```

The suite covers the cleaning rules, aggregates, the story and economics endpoints, the heatmap and the heap.

## Known limitations

- Only one month of data (January 2019).
- 57.7% of zone, hour and day-type cells have fewer than 30 cleaned trips, so the map shows only reliable cells and uses medians.
- Cash tips are not recorded in the source data, so tip rates cover card payments only.
- Some endpoints read the full trips table and can be slow on a laptop. Statistics and trust endpoints read small precomputed tables and are fast.

## 10. Team and contributions

| Member | Role | Main work |
| --- | --- | --- |
| Dorcase Lesly Nana Tounda | Data Engineer | Loading and cleaning the data, exclusion log, feature engineering, shapefile to GeoJSON, scripts that load the data into the database, Economics insight |
| Tchatchum Chassem Stephane | Database and Backend Engineer | Database schema and dump, Flask app, filter, sort and pagination endpoints, custom min-heap, Space insight (zone ranking, top routes, map data) |
| Olivier Migisha | Frontend Engineer | Dashboard layout, filters, sorting, detail view, responsive design, charts and map, Time insight (heatmap) |

Task status and meeting notes are in the team participation sheet linked at the top.