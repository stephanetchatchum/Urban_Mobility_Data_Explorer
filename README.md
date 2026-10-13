# Urban Mobility Data Explorer

## Links
- GitHub repository: https://github.com/stephanetchatchum/Urban_Mobility_Data_Explorer
- Video walkthrough (5 min): TODO
- Team participation sheet: https://docs.google.com/spreadsheets/d/15akxAc732NmQ7czdXkQ35M9AJZjRKmQZydInbm_4YSk/edit?gid=0#gid=0

## 1. Project overview
We explore the **cost of slow traffic for NYC yellow-taxi riders** using the January 2019 TLC trip file
(7,667,792 trips), the taxi zone lookup table and the taxi zone shapefile.

The system has four stages: a **cleaning pipeline** (Python, pandas) that logs every excluded record,
a **SQLite database** (normalised schema, indexes, pre-aggregated statistics), a **Flask API**, and a
**dashboard** (HTML, CSS, JavaScript). Every number on the dashboard comes with a *trust layer*: how many trips
support it and how many records were removed.

Our three insight slices: **Time** (rush-hour cost), **Space** (slowest zones, with trust), **Economics**
(fares, tips, and the price of slowness).

## 2. Project structure
```
pipeline/    load_data, clean_data, feature_engineering, zones_to_geojson, run_pipeline, load_to_db, reasons, config
backend/     Flask app (app.py), routes/, algorithms/custom_algorithm.py (manual min-heap), db.py
frontend/    dashboard (HTML, CSS, JS); economics.html is a standalone preview of the economics charts
database/    schema.sql, indexes.sql, make_dump.py, dump/urban_mobility_dump.sql
data/        raw/ (not in Git), processed/ (generated), logs/ (exclusion log and cleaning summary)
docs/        API_SPEC, DATABASE_SCHEMA, architecture_diagram, exclusion_log_notes
tests/       pytest suite (cleaning rules, pipeline, API, algorithm)
```

## 3. Prerequisites
- Python 3.10 or newer (tested on 3.12)
- About 3 GB of free disk space and 4 GB of RAM (the CSV is read in chunks)
- Git

## 4. Getting the data
Download these three TLC files and put them in `data/raw/`:
- `yellow_tripdata_2019-01.csv` (or `.parquet`; the pipeline accepts both)
- `taxi_zone_lookup.csv`
- the `taxi_zones` shapefile: **all** its files (`taxi_zones.shp`, `.shx`, `.dbf`, `.prj`, ...)

Source: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page

## 5. Installation and environment setup
```bash
git clone <repository-url>
cd Urban_Mobility_Data_Explorer
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 6. Running the data pipeline
From the repository root:
```bash
python -m pipeline.run_pipeline
```
About 3 minutes. It reads the trips in chunks of 500,000, applies the cleaning rules, adds the derived
features, converts the shapefile to lat/lon GeoJSON, and writes:
- `data/processed/clean_trips.parquet`, `zones.geojson`, `zones_dim.csv`
- `data/logs/exclusion_log.csv` (one row per excluded record and reason), `cleaning_summary.csv`, `cleaning_report.json`

Expected result: **7,578,846 trips kept, 88,946 excluded (1.16%)**. Quick test: `--limit-rows 200000`.

## 7. Creating the database
```bash
python -m pipeline.load_to_db
```
Builds `database/urban_mobility.db` (SQLite) from `schema.sql`, loads all tables, computes the summary tables,
creates the indexes from `indexes.sql` and checks every foreign key. A lightweight SQL dump (schema, indexes,
reference and summary tables) is in `database/dump/urban_mobility_dump.sql`; the full database is rebuilt
with the two commands above because the 7.6 M-row `trips` table is too large for Git.

## 8. Starting the backend
```bash
python -m backend.app
```
API at http://127.0.0.1:5000/api (check http://127.0.0.1:5000/api/health). Endpoints are listed in `docs/API_SPEC.md`.
Optional environment variables: `URBAN_DB_PATH`, `HOST`, `PORT`.

## 9. Starting the frontend
With the backend running, serve the `frontend/` folder as static files:
```bash
cd frontend
python -m http.server 8000
```
Open http://127.0.0.1:8000. The economics charts also have a standalone preview at
http://127.0.0.1:8000/economics.html. To use another API address add `?api=http://host:port/api`.

## 10. Running the tests
```bash
python -m pytest -q
```

## 11. Team and contributions
| Member | Role | Main work |
|---|---|---|
| Dorcase Lesly Nana Tounda | Data engineer | Cleaning pipeline, exclusion log, derived features, shapefile to GeoJSON, database loader, economics slice |
| Tchatchum Chassem Stephane | Database and backend | Schema and indexes, Flask API, custom min-heap, space slice |
| Olivier Migisha | Frontend | Dashboard, filters, charts, map, time slice |

Full details are in the team participation sheet.
