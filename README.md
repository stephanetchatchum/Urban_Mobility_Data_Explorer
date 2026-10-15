# README: replace these parts (the rest can stay)

## Section 1, second paragraph
The system has four stages: a cleaning pipeline (Python, pandas) that logs every excluded record, a MySQL database (normalised schema, indexes, pre-aggregated statistics), a Flask API, and a dashboard (HTML, CSS, JavaScript). Every number on the dashboard comes with a trust layer: how many trips support it and how many records were removed.
Our three insight slices: Time (rush-hour cost), Space (slowest zones, with trust), Economics (fare per minute and per mile at slow and fast hours).

## Section 2 (project structure)
pipeline/    load_data, clean_data, feature_engineering, zones_to_geojson, run_pipeline, build_aggregates, load_to_db, load_extras, reasons, config
backend/     Flask app (app.py), routes/ (trips, zones, insights, story), algorithms/custom_algorithm.py (manual min-heap), db.py, filters.py
frontend/    dashboard (HTML, CSS, JS)
database/    schema.sql, indexes.sql, init_db.py, dump/
data/        raw/ (not in Git), processed/ and logs/ (generated, not in Git)
docs/        API_SPEC, DATABASE_SCHEMA, architecture_diagram, data_dictionary, exclusion_log_notes
tests/       pytest suite (cleaning rules, aggregates, story API, heap)

## Section 3 (prerequisites), add
MySQL 8 or a MySQL-compatible server (local, or a cloud one such as Aiven). Create an empty server and note its host, port, user and password.

## Section 5 (installation), add after pip install
Set the database connection (never write the password in a file or commit it):
    Windows PowerShell:  $env:DB_HOST="..."; $env:DB_PORT="3306"; $env:DB_USER="..."; $env:DB_PASSWORD="..."; $env:DB_NAME="urban_mobility"
    macOS / Linux:       export DB_HOST=... DB_PORT=3306 DB_USER=... DB_PASSWORD=... DB_NAME=urban_mobility
If the server requires SSL, also set DB_SSL_CA to the path of its certificate file.

## Section 6 (pipeline), replace the command with
python -m pipeline.run_pipeline          # about 3 minutes
python -m pipeline.build_aggregates      # about 1 minute

## Section 7 (database), replace everything with
python -m database.init_db schema        # creates the tables and fills zones, payment types and rate codes
python -m pipeline.load_to_db --check    # tests the connection and the table columns
python -m pipeline.load_to_db --sample-every 20   # about 5% of the trips, spread over the whole month
#   or load everything (about 8 minutes on a local server, about 0.8 GB before indexes): python -m pipeline.load_to_db
python -m pipeline.load_extras           # zone geometry and statistics tables
python -m database.init_db indexes       # indexes, after the bulk load
The schema and reference data are in database/schema.sql. The 7.6 million-row trips table is too large for Git, so the dump in database/dump/ holds the sampled data (see below). Create it with:
    mysqldump -u USER -p --no-tablespaces urban_mobility > database/dump/urban_mobility_sample.sql

## Section 8 (backend), replace the last sentence with
Endpoints are listed in docs/API_SPEC.md. The backend reads the same DB_* environment variables as the pipeline.

## Section 9 (frontend), remove the sentence about economics.html unless that file exists in frontend/
