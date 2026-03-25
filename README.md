# Smart-City Traffic Prediction and Explainable Decision Support System

A full-stack AI system for Bengaluru that:
- Ingests real-time traffic flow from TomTom for 5 monitored corridors.
- Predicts short-term congestion using a location-wise LSTM model.
- Explains predictions via a Fuzzy Cognitive Map (FCM).
- Visualizes live, historical, predictive, and explainable insights in a React dashboard.
- Shows live corridor status on an OpenStreetMap-based map UI.

## Monitored Corridors
- MG Road (12.9757, 77.6011)
- Silk Board Junction (12.9176, 77.6230)
- Whitefield (12.9698, 77.7500)
- Electronic City (12.8452, 77.6602)
- Hebbal Flyover (13.0350, 77.5970)

## Prerequisites
1. Python 3.11
2. Node.js 18+
3. npm

## Quick Start (Windows)

### 1) Backend Setup
Open a terminal and move to backend:

```powershell
cd smart_traffic\backend
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install Python dependencies:

```powershell
pip install -r requirements.txt
```

Create environment file:

```powershell
Copy-Item .env.example .env
```

Set your TomTom API key in `.env`.

Initialize DB tables:

```powershell
python database.py
```

Start the API server:

```powershell
uvicorn main:app --reload --port 8000
```

Start the ingestion loop in another terminal (same backend folder):

```powershell
python ingest.py
```

Current defaults (from `.env`):
- `POLL_INTERVAL=60` (new pull every 60 seconds)
- `INGEST_BATCH_MULTIPLIER=12` (multiple snapshots per cycle)
- `SNAPSHOT_SPACING_SECONDS=0`

### 2) Frontend Setup
Open another terminal:

```powershell
cd smart_traffic\frontend
Copy-Item .env.example .env
npm install
npm start
```

Frontend runs on http://localhost:3000 and calls FastAPI at `REACT_APP_API_BASE` (default: `http://localhost:8000`).

## Frontend Deployment (GitHub Pages)

This repo is configured to auto-deploy the React frontend using GitHub Actions.

1. Push the latest code to the `main` branch.
2. In GitHub, open your repository settings:
  - `Settings` -> `Pages`
  - Under `Build and deployment`, set `Source` to `GitHub Actions`.
3. The workflow `.github/workflows/deploy-frontend-pages.yml` will:
  - install dependencies from `smart_traffic/frontend`
  - build the app
  - publish `smart_traffic/frontend/build` to GitHub Pages

After the workflow succeeds, your frontend will be available at:

https://retikad.github.io/smart-city-traffic-ai-bengaluru/

### 3) Verify Services
- Health check: http://localhost:8000/health
- API docs (Swagger): http://localhost:8000/docs
- Dashboard: http://localhost:3000

## Model Pipeline

1. Preprocess raw traffic into 5-minute windows and export training arrays:

```powershell
python preprocess.py
```

2. Train one LSTM model per location:

```powershell
python model/train.py
```

Training prints per-location evaluation:
- MAE
- RMSE
- Comparison table: LSTM vs naive last-value baseline

## API Summary
- `GET /traffic/live`
  - Latest raw traffic readings for all 5 locations.
- `GET /traffic/history?location=MG+Road&hours=24`
  - Rolling, gap-filled 5-minute records for selected location and time window.
- `POST /predict`
  - Body: `{ "location": "MG Road", "sequence": [[...], [...], [...]] }`
  - Sequence shape is fixed to 3 timesteps x 4 features.
  - Returns congestion index, label, confidence.
- `POST /explain`
  - Body: `{ "location": "MG Road", "congestion_index": 0.72, "speed": 18.5, "hour": 17 }`
  - Returns FCM vector, dominant cause, and natural language explanation.
- `GET /health`
  - Returns `{ "status": "ok" }`.

## Notes
- SQLite DB file path is controlled by `DATABASE_URL` (default: `sqlite:///./bengaluru_traffic.db`).
- Saved model directory is controlled by `MODEL_DIR` (default: `model/saved_model`).
- Frontend refresh interval is configurable via `REACT_APP_DASHBOARD_REFRESH_MS` (default: 60000 ms).
- Never hardcode API keys in source; keep them only in `.env`.
