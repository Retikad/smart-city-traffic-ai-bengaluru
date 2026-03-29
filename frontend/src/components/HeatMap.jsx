import React, { useEffect, useState } from "react";
import { Card, CardContent, Typography, Box, CircularProgress, Stack, Chip } from "@mui/material";
import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { fetchHeatMap } from "../api/trafficApi";

function colorForCI(ci) {
  if (ci >= 0.75) return "#d62828";
  if (ci >= 0.5) return "#e07a5f";
  if (ci >= 0.25) return "#f4a261";
  return "#2a9d8f";
}

function severityLabel(ci) {
  if (ci < 0.25) return "Low";
  if (ci < 0.5) return "Medium";
  if (ci < 0.75) return "High";
  return "Severe";
}

function densityToRadius(density) {
  // Density is confidence (0-1), scale for marker size
  return 8 + (density || 0) * 16;
}

const defaultCenter = [12.9716, 77.5946];
const bangaloreBounds = [
  [12.72, 77.44], // SW lat/lng
  [13.23, 77.85]  // NE lat/lng
];

const HeatMap = () => {
  const [heatData, setHeatData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchHeatMap()
      .then(setHeatData)
      .catch((err) => setError(err.message || "Failed to load heat map"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Card sx={{ mt: 2, background: "linear-gradient(155deg, rgba(255,255,255,0.98) 0%, rgba(245,252,251,0.94) 100%)" }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Bengaluru Congestion & Density Heat Map
        </Typography>
        <Box sx={{ position: "relative", height: 340, borderRadius: 2, overflow: "hidden", border: "1px solid rgba(15, 23, 42, 0.12)" }}>
          {loading ? (
            <Stack alignItems="center" justifyContent="center" sx={{ height: 340 }}>
              <CircularProgress />
            </Stack>
          ) : error ? (
            <Typography color="error">{error}</Typography>
          ) : (
            <MapContainer
              center={defaultCenter}
              zoom={11}
              minZoom={10}
              maxZoom={15}
              scrollWheelZoom
              style={{ height: "100%", width: "100%" }}
              maxBounds={bangaloreBounds}
              maxBoundsViscosity={1}
              maxBoundsOptions={{ padding: [20, 20] }}
              worldCopyJump={false}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {heatData.map((item) => (
                <CircleMarker
                  key={item.location_name}
                  center={[item.lat, item.lng]}
                  radius={densityToRadius(item.density)}
                  pathOptions={{
                    color: colorForCI(item.congestion_index),
                    fillColor: colorForCI(item.congestion_index),
                    fillOpacity: 0.7,
                    weight: 2
                  }}
                >
                  <Tooltip direction="top" offset={[0, -6]} opacity={0.95}>
                    <div>
                      <strong>{item.location_name}</strong>
                      <br />
                      Traffic: {severityLabel(item.congestion_index)} — {(item.congestion_index * 100).toFixed(0)}%
                      <br />
                      Expected delay: {item.eta_seconds ? Math.round(item.eta_seconds / 60) + " min" : "No significant delay"}
                      <br />
                      Crowdedness: <strong>{item.crowd_density !== undefined ? (item.crowd_density * 100).toFixed(0) + "%" : "N/A"}</strong>
                    </div>
                  </Tooltip>
                </CircleMarker>
              ))}
            </MapContainer>
          )}
        </Box>
        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1.5 }}>
          <Chip size="small" label="Low" sx={{ bgcolor: "#2a9d8f", color: "#fff" }} />
          <Chip size="small" label="Medium" sx={{ bgcolor: "#f4a261", color: "#1f2937" }} />
          <Chip size="small" label="High" sx={{ bgcolor: "#e07a5f", color: "#fff" }} />
          <Chip size="small" label="Severe" sx={{ bgcolor: "#d62828", color: "#fff" }} />
        </Stack>
      </CardContent>
    </Card>
  );
};

export default HeatMap;
