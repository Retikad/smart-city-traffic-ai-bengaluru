import axios from "axios";

const isLocalHost =
  typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

const apiBaseURL = process.env.REACT_APP_API_BASE || (isLocalHost ? "http://localhost:8000" : "");

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
    throw new Error(error.response?.data?.detail || "Unable to fetch live traffic");
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
