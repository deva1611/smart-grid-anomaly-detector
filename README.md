# Smart Grid Anomaly Detection System

**Live demo:** https://smart-grid-anomaly-detector.onrender.com/docs
*(free-tier instance — spins down when idle, so the first request may take ~50 seconds to wake up)*

A real-time anomaly detection pipeline for smart electricity meter data. A C++ engine flags unusual readings (spikes, flatlines, negative values) as they arrive, a Python API exposes it over HTTP, and everything is persisted to PostgreSQL — the whole stack is containerized, tested on every push via CI, and deployed live.

---

## The problem

Smart meters generate a continuous stream of consumption readings. A single bad reading can mean a faulty sensor, a fraud attempt, or an actual grid fault — and it needs to be caught close to the moment it happens, not discovered days later in a batch report. This project simulates that stream (with an option to replay real UK household consumption data) and detects anomalies in real time using a statistical model implemented in C++ for speed, wrapped in a Python service for accessibility.

## Architecture
Meter readings (simulator / real data replay)
|
v
C++ RollingZScoreDetector --(pybind11)--> FastAPI service
(Welford's algorithm, POST /ingest
sliding window) GET /anomalies
| |
v v
PostgreSQL
(readings + anomalies tables)

Everything above runs in Docker, built and tested by GitHub Actions
on every push, deployed live on Render.
## Tech stack

C++17 (CMake, GoogleTest) - pybind11 - Python 3.12 (FastAPI, psycopg2) - PostgreSQL - Docker - GitHub Actions - Render

## Try it live

```bash
curl -X POST 'https://smart-grid-anomaly-detector.onrender.com/ingest' \
  -H 'Content-Type: application/json' \
  -d '{"meter_id": "meter_001", "timestamp": "2026-08-07T16:00:00", "kwh": 12.5}'

curl 'https://smart-grid-anomaly-detector.onrender.com/anomalies'
```

Or open `/docs` for the interactive Swagger UI.

---

## Key engineering decisions

**Sliding window over lifetime statistics.** The detector was originally built using lifetime running mean/standard deviation. This caused a real bug: a single spike would permanently distort the baseline, masking any anomaly that came after it, since the corrupted mean never recovered. The fix was a bounded sliding window (Welford's algorithm over the last 20 readings) so an old anomaly's influence fades out once it scrolls out of the window. There's a dedicated regression test (`OldSpikeDoesNotPermanentlyMaskLaterAnomalies`) covering exactly this case.

**Two tables instead of one.** `readings` holds the full audit trail of everything ingested; `anomalies` holds only the flagged events, with a foreign key back to `readings`. This keeps the common query path (recent anomalies) fast and small, while still preserving a complete history for later analysis - both indexed on `meter_id` and `timestamp`, the columns actually filtered on.

**A credential near-miss.** Early on, a stray `.env.txt` file (created by Notepad silently defaulting to a `.txt` extension) nearly got committed alongside real database credentials. Since then, credentials are loaded exclusively via environment variables and `.env` is gitignored - but it's a reminder that "gitignored" only protects you if the file actually matches the pattern you think it does.

**A CI-specific dependency gap.** The GitHub Actions build initially failed with `CMake Error: Could not find a package configuration file for "pybind11"` - a dependency present in the local dev environment but never installed on the CI runner. Fixed by explicitly installing `pybind11` via pip in the workflow and pointing CMake at it with `-DCMAKE_PREFIX_PATH="$(python -m pybind11 --cmakedir)"`. A useful reminder that "works on my machine" and "works in a clean container" are different claims, and CI exists precisely to catch the gap between them.

**A silently corrupted `.gitignore`.** A `.gitignore` edit (via Notepad) dropped a newline, merging what should have been `*.csv` and `service/app/*.pyd` into a broken, unanchored `app/` pattern. Because `.gitignore` patterns without a leading slash match at any depth, this silently caused Git to ignore *any* newly created file under a directory named `app` anywhere in the repo - including `service/app/db.py`. The file existed and worked locally, but had never actually been committed, which only became visible when the deployed container crashed with `ModuleNotFoundError: No module named 'db'` despite the exact same code running fine on a developer machine. Diagnosed by comparing `git ls-files` against the real directory contents, and fixed by repairing the ignore rule and force-adding the missing file.

**Making uvicorn's import path deterministic.** The Docker container originally invoked the bare `uvicorn` console script, which does not reliably add the working directory to Python's import path depending on how it's installed. Since `main.py` imports sibling modules with plain `import db`, this needed the working directory guaranteed to be on `sys.path`. Switching the container's start command to `python -m uvicorn main:app` makes that guarantee explicit rather than incidental.

---

## Running locally

```bash
docker-compose up -d
```

This builds the C++ engine from source inside the container, brings up PostgreSQL with the schema in `db/init.sql` already applied, and starts the FastAPI service on port 8000.

## Running tests

```bash
cd engine
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
cd build && ctest --output-on-failure
```

## CI

Every push to `main` builds the C++ engine and runs the full GoogleTest suite via GitHub Actions - see `.github/workflows/ci.yml`.