import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  AppBar,
  Box,
  Card,
  CardContent,
  Chip,
  Container,
  Divider,
  GlobalStyles,
  Grid,
  LinearProgress,
  Stack,
  Toolbar,
  Typography
} from "@mui/material";
import CongestionChart from "./components/CongestionChart";
import FCMExplainer from "./components/FCMExplainer";
import LiveMap from "./components/LiveMap";
import LocationSelector from "./components/LocationSelector";
import PredictionPanel from "./components/PredictionPanel";
import { fetchHistory, fetchLiveTraffic, requestExplanation, requestPrediction } from "./api/trafficApi";

const DEFAULT_LOCATIONS = [
  "MG Road",
  "Silk Board Junction",
  "Whitefield",
  "Electronic City",
  "Hebbal Flyover",
  "Koramangala",
  "Church Street",
  "JP Nagar",
  "Jayanagar",
  "Commercial Street",
  "KR Market"
];

const DASHBOARD_REFRESH_MS = Number(process.env.REACT_APP_DASHBOARD_REFRESH_MS || 60000);

function labelColor(ci) {
  if (ci < 0.25) return "success";
  if (ci < 0.5) return "warning";
  if (ci < 0.75) return "warning";
  return "error";
}

function severityLabel(ci) {
  if (ci < 0.25) return "Low";
  if (ci < 0.5) return "Medium";
  if (ci < 0.75) return "High";
  return "Severe";
}

function getRecommendation(ci, etaSeconds) {
  const etaMin = Number.isFinite(etaSeconds) ? Math.round(etaSeconds / 60) : null;
  if (ci >= 0.75) return etaMin ? `Severe — avoid if possible (≈ ${etaMin} min)` : 'Severe — expect major delays';
  if (ci >= 0.5) return etaMin ? `High — consider alternate route (≈ ${etaMin} min)` : 'High — expect delays';
  if (ci >= 0.25) return etaMin ? `Moderate — short delays (≈ ${etaMin} min)` : 'Moderate — minor delays';
  return 'Traffic flowing normally';
}

function parseApiDateTime(value) {
  if (!value) return null;
  const raw = String(value).trim();
  // Backend timestamps are UTC without timezone suffix; normalize for browser parsing.
  const hasTimezone = /(?:Z|[+-]\d\d:\d\d)$/i.test(raw);
  const normalized = hasTimezone ? raw : `${raw}Z`;
  const dt = new Date(normalized);
  return Number.isNaN(dt.getTime()) ? null : dt;
}

function freshnessMeta(timestamp) {
  if (!timestamp) return { label: "Unknown", bg: "#9ca3af", fg: "#111827" };
  const dt = parseApiDateTime(timestamp);
  if (!dt) return { label: "Unknown", bg: "#9ca3af", fg: "#111827" };
  const ageSec = Math.max(0, Math.floor((Date.now() - dt.getTime()) / 1000));
  if (ageSec <= 90) return { label: "Fresh", bg: "#2a9d8f", fg: "#ffffff" };
  if (ageSec <= 240) return { label: "Delayed", bg: "#f4a261", fg: "#111827" };
  return { label: "Stale", bg: "#d62828", fg: "#ffffff" };
}

function buildSequence(history) {
  if (!history || history.length < 3) return null;
  const window = history.slice(-3);
  const sequence = window.map((row) => [
    row.norm_speed,
    row.avg_congestion_index,
    row.hour_sin,
    row.hour_cos,
    row.eta_seconds,
    row.weather_temp,
    row.weather_humidity,
    row.weather_rain
  ]);
  const hasInvalid = sequence.some((step) => step.some((value) => !Number.isFinite(value)));
  return hasInvalid ? null : sequence;
}

function App() {
  const [locations, setLocations] = useState(DEFAULT_LOCATIONS);
  const [selectedLocation, setSelectedLocation] = useState(DEFAULT_LOCATIONS[0]);
  const [liveItems, setLiveItems] = useState([]);
  const [history, setHistory] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [error, setError] = useState("");
  const [predictionError, setPredictionError] = useState("");
  const [explainError, setExplainError] = useState("");
  const [loadingPredict, setLoadingPredict] = useState(false);
  const [loadingExplain, setLoadingExplain] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(true);

  const avgNetworkCongestion = useMemo(() => {
    if (!liveItems.length) return 0;
    return liveItems.reduce((sum, item) => sum + item.congestion_index, 0) / liveItems.length;
  }, [liveItems]);

  const avgNetworkEta = useMemo(() => {
    if (!liveItems.length) return NaN;
    const etas = liveItems.map((i) => Number.isFinite(i.eta_seconds) ? i.eta_seconds / 60 : NaN).filter(Number.isFinite);
    if (!etas.length) return NaN;
    return etas.reduce((s, v) => s + v, 0) / etas.length;
  }, [liveItems]);

  const highRiskCount = useMemo(
    () => liveItems.filter((item) => item.congestion_index >= 0.5).length,
    [liveItems]
  );

  const sortedLive = useMemo(
    () => [...liveItems].sort((a, b) => b.congestion_index - a.congestion_index),
    [liveItems]
  );

  const selectedLive = useMemo(
    () => liveItems.find((item) => item.location_name === selectedLocation),
    [liveItems, selectedLocation]
  );
  const liveFreshness = useMemo(() => freshnessMeta(selectedLive?.timestamp), [selectedLive]);

  const refreshData = async () => {
    let liveData;
    let historyData;
    try {
      [liveData, historyData] = await Promise.all([
        fetchLiveTraffic(),
        fetchHistory(selectedLocation, 24)
      ]);
    } catch (err) {
      setError(err.message || "Unexpected error while loading traffic data");
      setLoadingPredict(false);
      setLoadingExplain(false);
      return;
    }

    setLiveItems(liveData.items || []);
    // Debug: Log liveItems and their eta_seconds values
    if (liveData.items) {
      console.log('[DEBUG] liveItems:', liveData.items.map(item => ({ location: item.location_name, eta_seconds: item.eta_seconds })));
    }
    if (liveData.items && liveData.items.length > 0) {
      setLocations(Array.from(new Set([...DEFAULT_LOCATIONS, ...liveData.items.map((x) => x.location_name)])));
    }

    const records = historyData.records || [];
    console.log("[DEBUG] Records received from fetchHistory:", records);
    if (records && records.length) {
      console.log("[DEBUG] Timestamps of records:", records.map(r => r.window_end || r.timestamp));
    }
    setHistory(records);
    setError("");

    const sequence = buildSequence(records);
    if (!sequence) {
      console.log("[DEBUG] Sequence construction failed. Records:", records);
      records.slice(-3).forEach((row, idx) => {
        console.log(`[DEBUG] Step ${idx}:`, {
          norm_speed: row.norm_speed,
          avg_congestion_index: row.avg_congestion_index,
          hour_sin: row.hour_sin,
          hour_cos: row.hour_cos,
          eta_seconds: row.eta_seconds,
          weather_temp: row.weather_temp,
          weather_humidity: row.weather_humidity,
          weather_rain: row.weather_rain
        });
      });
      setPrediction(null);
      setExplanation(null);
      setPredictionError("Need at least 3 valid processed windows for prediction.");
      setExplainError("");
      return;
    }

    try {
      setPredictionError("");
      setLoadingPredict(true);
      const pred = await requestPrediction({ location: selectedLocation, sequence });
      setPrediction(pred);
      setLoadingPredict(false);

      const liveForLocation = (liveData.items || []).find((x) => x.location_name === selectedLocation);
      const speed = liveForLocation?.current_speed ?? records[records.length - 1]?.avg_speed ?? 0;
      const hour = new Date().getHours();

      try {
        setLoadingExplain(true);
        const fcm = await requestExplanation({
          location: selectedLocation,
          congestion_index: pred.congestion_index,
          speed,
          hour
        });
        setExplanation(fcm);
        setExplainError("");
      } catch (err) {
        setExplanation(null);
        setExplainError(err.message || "Explanation request failed");
      } finally {
        setLoadingExplain(false);
      }
    } catch (err) {
      setPrediction(null);
      setExplanation(null);
      setPredictionError(err.message || "Prediction request failed");
      setLoadingPredict(false);
      setLoadingExplain(false);
    }
  };

  useEffect(() => {
    refreshData().catch(() => {});
    const id = setInterval(() => {
      refreshData().catch(() => {});
    }, DASHBOARD_REFRESH_MS);
    return () => clearInterval(id);
  }, [selectedLocation]);

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const res = await fetch(`${process.env.REACT_APP_API_BASE || 'http://127.0.0.1:8000'}/health`);
        if (!res.ok) throw new Error('Backend health check failed');
      } catch (err) {
        setError('Backend unreachable or unhealthy; please restart backend and ingest service.');
      }
    };
    checkBackend();
  }, []);

  return (
    <Box
      sx={{
        minHeight: "100vh",
        background:
          "radial-gradient(circle at 15% 20%, rgba(246, 189, 96, 0.25), transparent 34%), radial-gradient(circle at 82% 8%, rgba(30, 96, 145, 0.2), transparent 30%), linear-gradient(155deg, #fbf9f4 0%, #f1f7fb 48%, #f8f3e8 100%)"
      }}
    >
      <GlobalStyles
        styles={{
          "@keyframes fadeUp": {
            from: { opacity: 0, transform: "translateY(10px)" },
            to: { opacity: 1, transform: "translateY(0)" }
          }
        }}
      />

      <AppBar
        position="sticky"
        elevation={0}
        sx={{
          backdropFilter: "blur(10px)",
          background: "rgba(11, 36, 71, 0.82)",
          borderBottom: "1px solid rgba(255,255,255,0.08)"
        }}
      >
        <Toolbar>
          <Typography variant="h6" sx={{ letterSpacing: 0.4 }}>
            Bengaluru Mobility Nerve Center
          </Typography>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Card
          sx={{
            mb: 2.5,
            background:
              "linear-gradient(120deg, rgba(11,36,71,0.94) 0%, rgba(20,58,96,0.92) 60%, rgba(224,122,95,0.85) 100%)",
            color: "#f8fafc",
            animation: "fadeUp 420ms ease"
          }}
        >
          <CardContent>
            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} md={8}>
                <Typography variant="overline" sx={{ letterSpacing: 1.8, opacity: 0.9 }}>
                  Live Urban Intelligence
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 700, lineHeight: 1.15 }}>
                  Real-time congestion forecasting for Bengaluru corridors
                </Typography>
                <Typography sx={{ mt: 0.8, opacity: 0.9 }}>
                  Combined stream of live telemetry, LSTM risk prediction, and FCM explanation.
                </Typography>
              </Grid>
              <Grid item xs={12} md={4}>
                <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" justifyContent={{ xs: "flex-start", md: "flex-end" }}>
                  <Chip
                    label={`Network Congestion ${(avgNetworkCongestion * 100).toFixed(1)}%`}
                    sx={{ bgcolor: "rgba(248,250,252,0.18)", color: "#f8fafc", fontWeight: 700 }}
                  />
                  <Chip
                    label={`High Risk Corridors ${highRiskCount}`}
                    sx={{ bgcolor: "rgba(248,250,252,0.18)", color: "#f8fafc", fontWeight: 700 }}
                  />
                </Stack>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {showOnboarding && (
          <Alert
            severity="info"
            onClose={() => setShowOnboarding(false)}
            sx={{ mb: 2 }}
          >
            This dashboard shows live congestion for major Bangalore corridors — colors indicate severity and the map shows expected delay. Click a corridor for details.
          </Alert>
        )}

        <Card sx={{ mb: 2, animation: "fadeUp 420ms ease" }}>
          <CardContent>
            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} md={8}>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  City Snapshot
                </Typography>
                <Typography sx={{ mt: 0.3 }}>
                  Overall traffic is <strong>{severityLabel(avgNetworkCongestion)}</strong> across monitored corridors.
                </Typography>
                <Typography sx={{ mt: 0.3 }} color="text.secondary">
                  Average expected delay: <strong>{Number.isFinite(avgNetworkEta) ? Math.round(avgNetworkEta) + ' min' : 'N/A'}</strong>
                </Typography>
              </Grid>
              <Grid item xs={12} md={4}>
                <Stack direction="row" spacing={1} justifyContent={{ xs: 'flex-start', md: 'flex-end' }}>
                  <Chip label={`${highRiskCount} corridors at elevated risk`} sx={{ fontWeight: 700 }} />
                </Stack>
              </Grid>
            </Grid>
          </CardContent>
        </Card>

        <Grid container spacing={1.5} sx={{ mb: 2.2 }}>
          {sortedLive.map((item) => (
            <Grid item xs={12} sm={6} md={4} lg={2.4} key={item.location_name}>
              <Card sx={{ minHeight: 200, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', animation: "fadeUp 520ms ease" }}>
                <CardContent sx={{ pb: "12px !important", flexGrow: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary">
                    {item.location_name}
                  </Typography>
                  <Typography variant="h6" sx={{ mt: 0.4, mb: 0.6 }}>
                    {(item.congestion_index * 100).toFixed(1)}%
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={item.congestion_index * 100}
                    color={labelColor(item.congestion_index)}
                    sx={{ height: 8, borderRadius: 99, mb: 0.9 }}
                  />
                  <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.5 }}>
                    <Chip size="small" label={severityLabel(item.congestion_index)} color={labelColor(item.congestion_index)} />
                    <Typography variant="caption" color="text.secondary">
                      {item.current_speed.toFixed(0)} km/h
                    </Typography>
                  </Stack>
                  <Stack direction="row" spacing={0.7} alignItems="center" sx={{ mb: 0.5, flexWrap: 'wrap' }}>
                    <Chip size="small" label={`Delay: ${item.eta_seconds ? Math.round(item.eta_seconds / 60) + ' min' : 'N/A'}`} color="info" />
                    <Chip size="small" label={`Confidence: ${item.confidence !== undefined ? (item.confidence * 100).toFixed(0) + '%' : 'N/A'}`} color="secondary" />
                    <Chip size="small" label={`Crowd`} sx={{ bgcolor: '#f97316', color: '#fff', fontWeight: 700 }} />
                  </Stack>
                  <Box sx={{ mt: 0.4, display: 'flex', alignItems: 'baseline', gap: 1, flexWrap: 'wrap' }}>
                    <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>
                      Crowdedness:
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 700, wordBreak: 'break-word' }}>
                      {item.crowd_density !== undefined ? (item.crowd_density * 100).toFixed(0) + '%' : 'N/A'}
                    </Typography>
                  </Box>
                  {item.weather_main && (
                    <Stack direction="row" spacing={0.7} alignItems="center">
                      <Chip size="small" label={`Weather: ${item.weather_main}`} color="primary" />
                      {item.weather_temp !== undefined && (
                        <Chip size="small" label={`Temp: ${item.weather_temp.toFixed(1)}°C`} color="default" />
                      )}
                      {item.weather_rain !== undefined && (
                        <Chip size="small" label={`Rain: ${item.weather_rain} mm`} color="info" />
                      )}
                    </Stack>
                  )}
                  <Divider sx={{ my: 0.8 }} />
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {getRecommendation(item.congestion_index, item.eta_seconds)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        <Grid container spacing={2.2}>
          <Grid item xs={12} md={4}>
            <Stack spacing={2}>
              <LocationSelector
                locations={locations}
                selectedLocation={selectedLocation}
                onChange={setSelectedLocation}
              />

              <Card sx={{ animation: "fadeUp 450ms ease" }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Live Stats
                  </Typography>
                  {selectedLive ? (
                    <Stack spacing={1.2}>
                      <Typography variant="body2" color="text.secondary">
                        Selected Corridor
                      </Typography>
                      <Typography variant="h5" sx={{ fontWeight: 700, lineHeight: 1.1 }}>
                        {selectedLocation}
                      </Typography>
                      <Typography variant="body2">
                        Current Speed: <strong>{selectedLive.current_speed.toFixed(1)} km/h</strong>
                      </Typography>
                      <Typography variant="body2">
                        Confidence: <strong>{(selectedLive.confidence * 100).toFixed(1)}%</strong>
                      </Typography>
                      <Typography variant="body2">
                        ETA: <strong>{selectedLive.eta_seconds ? Math.round(selectedLive.eta_seconds / 60) + ' min' : 'N/A'}</strong>
                      </Typography>
                      {selectedLive.weather_main && (
                        <Typography variant="body2">
                          Weather: <strong>{selectedLive.weather_main}</strong>
                          {selectedLive.weather_temp !== undefined && (
                            <> | Temp: <strong>{selectedLive.weather_temp.toFixed(1)}°C</strong></>
                          )}
                          {selectedLive.weather_rain !== undefined && (
                            <> | Rain: <strong>{selectedLive.weather_rain} mm</strong></>
                          )}
                        </Typography>
                      )}
                      <Typography variant="body2" color="text.secondary">
                        Last updated: <strong>{(parseApiDateTime(selectedLive.timestamp) || new Date(selectedLive.timestamp)).toLocaleTimeString([], { hour12: false })}</strong>
                      </Typography>
                      <Chip
                        size="small"
                        label={`Data ${liveFreshness.label}`}
                        sx={{
                          width: 120,
                          fontWeight: 700,
                          bgcolor: liveFreshness.bg,
                          color: liveFreshness.fg
                        }}
                      />
                      <Divider sx={{ my: 0.4 }} />
                      <Typography variant="body2" color="text.secondary">
                        Real-time severity: <strong>{severityLabel(selectedLive.congestion_index)}</strong>
                      </Typography>
                      <Chip
                        label={`Congestion ${(selectedLive.congestion_index * 100).toFixed(1)}%`}
                        color={labelColor(selectedLive.congestion_index)}
                        sx={{ width: 210, fontWeight: 700 }}
                      />
                    </Stack>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      Waiting for live telemetry from ingest.py...
                    </Typography>
                  )}
                </CardContent>
              </Card>

              <LiveMap selectedLocation={selectedLocation} liveItems={liveItems} />
            </Stack>
          </Grid>

          <Grid item xs={12} md={8}>
            <Box sx={{ animation: "fadeUp 550ms ease" }}>
              <CongestionChart data={history} />
            </Box>
          </Grid>

          <Grid item xs={12} md={6}>
            <Box sx={{ animation: "fadeUp 650ms ease" }}>
              <PredictionPanel prediction={prediction} loading={loadingPredict} error={predictionError} />
            </Box>
          </Grid>

          <Grid item xs={12} md={6}>
            <Box sx={{ animation: "fadeUp 750ms ease" }}>
              <FCMExplainer
                explanation={explanation}
                loading={loadingExplain}
                error={explainError}
              />
            </Box>
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
}

export default App;
