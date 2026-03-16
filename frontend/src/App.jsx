import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  AppBar,
  Box,
  Card,
  CardContent,
  Chip,
  Container,
  Grid,
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
  "Hebbal Flyover"
];

function labelColor(ci) {
  if (ci < 0.25) return "success";
  if (ci < 0.5) return "warning";
  if (ci < 0.75) return "warning";
  return "error";
}

function buildSequence(history) {
  if (!history || history.length < 12) return null;
  const window = history.slice(-12);
  return window.map((row) => [row.norm_speed, row.norm_congestion, row.hour_sin, row.hour_cos]);
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

  const selectedLive = useMemo(
    () => liveItems.find((item) => item.location_name === selectedLocation),
    [liveItems, selectedLocation]
  );

  const refreshData = async () => {
    try {
      const [liveData, historyData] = await Promise.all([
        fetchLiveTraffic(),
        fetchHistory(selectedLocation, 24)
      ]);

      setLiveItems(liveData.items || []);
      if (liveData.items && liveData.items.length > 0) {
        setLocations(Array.from(new Set([...DEFAULT_LOCATIONS, ...liveData.items.map((x) => x.location_name)])));
      }

      const records = historyData.records || [];
      setHistory(records);
      setError("");

      const sequence = buildSequence(records);
      if (!sequence) {
        setPrediction(null);
        setExplanation(null);
        setPredictionError("Need at least 12 processed windows for prediction.");
        setExplainError("");
        return;
      }

      setPredictionError("");
      setLoadingPredict(true);
      const pred = await requestPrediction({ location: selectedLocation, sequence });
      setPrediction(pred);
      setLoadingPredict(false);

      const liveForLocation = (liveData.items || []).find((x) => x.location_name === selectedLocation);
      const speed = liveForLocation?.current_speed ?? records[records.length - 1]?.avg_speed ?? 0;
      const hour = new Date().getHours();

      setLoadingExplain(true);
      const fcm = await requestExplanation({
        location: selectedLocation,
        congestion_index: pred.congestion_index,
        speed,
        hour
      });
      setExplanation(fcm);
      setExplainError("");
      setLoadingExplain(false);
    } catch (err) {
      setError(err.message || "Unexpected error while loading traffic data");
      setLoadingPredict(false);
      setLoadingExplain(false);
    }
  };

  useEffect(() => {
    refreshData().catch(() => {});
    const id = setInterval(() => {
      refreshData().catch(() => {});
    }, 60000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedLocation]);

  return (
    <Box sx={{ minHeight: "100vh", background: "linear-gradient(180deg, #f4f1ea 0%, #fefae0 100%)" }}>
      <AppBar position="static" color="primary">
        <Toolbar>
          <Typography variant="h6">Bengaluru Smart Traffic AI</Typography>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ py: 3 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Stack spacing={2}>
              <LocationSelector
                locations={locations}
                selectedLocation={selectedLocation}
                onChange={setSelectedLocation}
              />

              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Live Stats
                  </Typography>
                  {selectedLive ? (
                    <Stack spacing={1}>
                      <Typography variant="body2">
                        Current Speed: <strong>{selectedLive.current_speed.toFixed(1)} km/h</strong>
                      </Typography>
                      <Typography variant="body2">
                        Confidence: <strong>{(selectedLive.confidence * 100).toFixed(1)}%</strong>
                      </Typography>
                      <Chip
                        label={`Congestion ${(selectedLive.congestion_index * 100).toFixed(1)}%`}
                        color={labelColor(selectedLive.congestion_index)}
                        sx={{ width: 190, fontWeight: 700 }}
                      />
                    </Stack>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      Waiting for live telemetry from ingest.py...
                    </Typography>
                  )}
                </CardContent>
              </Card>

              <LiveMap selectedLocation={selectedLocation} />
            </Stack>
          </Grid>

          <Grid item xs={12} md={8}>
            <CongestionChart data={history} />
          </Grid>

          <Grid item xs={12} md={6}>
            <PredictionPanel prediction={prediction} loading={loadingPredict} error={predictionError} />
          </Grid>

          <Grid item xs={12} md={6}>
            <FCMExplainer
              explanation={explanation}
              loading={loadingExplain}
              error={explainError}
            />
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
}

export default App;
