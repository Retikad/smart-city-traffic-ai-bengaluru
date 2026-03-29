// Fetch all probe points for a corridor (for local heatmap)
export async function fetchCorridorProbes(location) {
  ensureApiBaseConfigured();
  try {
    const { data } = await api.get("/traffic/probes", { params: { location } });
    return data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || "Unable to fetch probe points");
  }
}
import axios from "axios";

const isDev = process.env.NODE_ENV !== "production";
const apiBaseURL = process.env.REACT_APP_API_BASE || (isDev ? "http://127.0.0.1:8000" : "");

const api = axios.create({
  baseURL: apiBaseURL,
  timeout: 15000
});

function ensureApiBaseConfigured() {
  if (api.defaults.baseURL) return;
  throw new Error(
    "API base URL is not configured for production. Set REACT_APP_API_BASE to your deployed backend URL."
  );
}

export async function fetchLiveTraffic() {
  ensureApiBaseConfigured();
  try {
    const { data } = await api.get("/traffic/live");
    return data;
  } catch (error) {
    const backendDetail = error.response?.data?.detail;
    const networkDetail = error.request ? "Backend unreachable at API base URL" : null;
    throw new Error(backendDetail || networkDetail || error.message || "Unable to fetch live traffic");
  }
}

export async function fetchHistory(location, hours = 24) {
  ensureApiBaseConfigured();
  try {
    const { data } = await api.get("/traffic/history", { params: { location, hours } });
    return data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || "Unable to fetch traffic history");
  }
}

export async function requestPrediction(payload) {
  ensureApiBaseConfigured();
  try {
    const { data } = await api.post("/predict", payload);
    return data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || "Prediction request failed");
  }
}

export async function requestExplanation(payload) {
  ensureApiBaseConfigured();
  try {
    const { data } = await api.post("/explain", payload);
    return data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || "Explanation request failed");
  }
}


// Fetch heatmap data (congestion and density for all corridors)
export async function fetchHeatMap() {
  ensureApiBaseConfigured();
  try {
    const { data } = await api.get("/traffic/heatmap");
    return data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || "Unable to fetch heat map data");
  }
}

// Helper: fetchLiveTraffic already returns ETA, weather, and density fields in each item.
// Example usage in frontend:
//   item.eta_seconds, item.weather_main, item.weather_description, item.weather_temp, item.weather_humidity, item.weather_rain, item.confidence
