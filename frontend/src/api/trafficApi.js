import axios from "axios";

const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE || "http://localhost:8000",
  timeout: 15000
});

export async function fetchLiveTraffic() {
  try {
    const { data } = await api.get("/traffic/live");
    return data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || "Unable to fetch live traffic");
  }
}

export async function fetchHistory(location, hours = 24) {
  try {
    const { data } = await api.get("/traffic/history", { params: { location, hours } });
    return data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || "Unable to fetch traffic history");
  }
}

export async function requestPrediction(payload) {
  try {
    const { data } = await api.post("/predict", payload);
    return data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || "Prediction request failed");
  }
}

export async function requestExplanation(payload) {
  try {
    const { data } = await api.post("/explain", payload);
    return data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || "Explanation request failed");
  }
}
