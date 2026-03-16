# Smart-City Traffic Prediction and Explainable Decision Support System

A full-stack AI system for Bengaluru that:
- Ingests real-time traffic flow from TomTom for 5 monitored corridors.
- Predicts short-term congestion using a location-wise LSTM model.
- Explains predictions via a Fuzzy Cognitive Map (FCM).
- Visualizes live, historical, predictive, and explainable insights in a React dashboard.

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

## Backend Setup
1. Open a terminal and move to backend:

```powershell
cd smart_traffic\backend
```

2. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install Python dependencies:

```powershell
pip install -r requirements.txt
```

4. Create environment file:

```powershell
Copy-Item .env.example .env
```

5. Set your TomTom API key in `.env`.

6. Initialize DB tables:

```powershell
python database.py
```

## Data Pipeline
1. Start ingestion loop (polls every 300 seconds by default):

```powershell
python ingest.py
```

2. Preprocess into 15-minute windows and export training arrays:

```powershell
python preprocess.py
```

3. Train one LSTM model per location:

```powershell
python model/train.py
```

Training prints per-location evaluation:
- MAE
- RMSE
- Comparison table: LSTM vs naive last-value baseline

## Run API
From `smart_traffic/backend`:

```powershell
uvicorn main:app --reload --port 8000
```

- Health check: http://localhost:8000/health
- Swagger docs: http://localhost:8000/docs

## Frontend Setup
1. Open another terminal and move to frontend:

```powershell
cd smart_traffic\frontend
```

2. Create environment file:

```powershell
Copy-Item .env.example .env
```

3. Install and run:

```powershell
npm install
npm start
```

Frontend runs on http://localhost:3000 and calls FastAPI at `REACT_APP_API_BASE`.

## API Summary
- `GET /traffic/live`
  - Latest raw traffic readings for all 5 locations.
- `GET /traffic/history?location=MG+Road&hours=24`
  - Processed records for selected location and time window.
- `POST /predict`
  - Body: `{ "location": "MG Road", "sequence": [[...], ...] }`
  - Returns congestion index, label, confidence.
- `POST /explain`
  - Body: `{ "location": "MG Road", "congestion_index": 0.72, "speed": 18.5, "hour": 17 }`
  - Returns FCM vector, dominant cause, and natural language explanation.
- `GET /health`
  - Returns `{ "status": "ok" }`.

## Notes
- SQLite DB file path is controlled by `DATABASE_URL` (default: `sqlite:///./bengaluru_traffic.db`).
- Saved model directory is controlled by `MODEL_DIR` (default: `model/saved_model`).
- Never hardcode API keys in source; keep them only in `.env`.
