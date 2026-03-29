import React, { useEffect, useState } from "react";
import { Box, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { MapContainer, Polyline, TileLayer, Tooltip } from "react-leaflet";
import { HeatmapLayer } from "react-leaflet-heatmap-layer-v3";
import { fetchCorridorProbes } from "../api/trafficApi";
import "leaflet/dist/leaflet.css";

const CORRIDORS = [
  { name: "MG Road", lat: 12.9757, lng: 77.6011 },
  { name: "Silk Board Junction", lat: 12.9176, lng: 77.623 },
  { name: "Whitefield", lat: 12.9698, lng: 77.75 },
  { name: "Electronic City", lat: 12.8452, lng: 77.6602 },
  { name: "Hebbal Flyover", lat: 13.035, lng: 77.597 },
  { name: "Koramangala", lat: 12.9352, lng: 77.6245 },
  { name: "Church Street", lat: 12.9755, lng: 77.6058 },
  { name: "JP Nagar", lat: 12.9077, lng: 77.585 },
  { name: "Jayanagar", lat: 12.925, lng: 77.5938 },
  { name: "Commercial Street", lat: 12.9826, lng: 77.6088 },
  { name: "KR Market", lat: 12.9633, lng: 77.576 }
];

function markerColor(ci) {
  if (ci >= 0.75) return "#d62828";
  if (ci >= 0.5) return "#e07a5f";
  if (ci >= 0.25) return "#f4a261";
  return "#2a9d8f";
}

function markerRadius(ci, active) {
  const base = 6 + ci * 10;
  return active ? base + 3 : base;
}

function LiveMap({ selectedLocation, liveItems = [] }) {
  const [probePoints, setProbePoints] = useState([]);
  const [loadingProbes, setLoadingProbes] = useState(false);
  const [probeError, setProbeError] = useState(null);

  useEffect(() => {
    if (!selectedLocation) {
      setProbePoints([]);
      return;
    }
    setLoadingProbes(true);
    setProbeError(null);
    fetchCorridorProbes(selectedLocation)
      .then((data) => {
        // Expecting data as array of { lat, lng, congestion_index }
        setProbePoints(
          Array.isArray(data)
            ? data.map((p) => [p.lat, p.lng, p.congestion_index ?? 0])
            : []
        );
      })
      .catch((err) => setProbeError(err.message))
      .finally(() => setLoadingProbes(false));
  }, [selectedLocation]);
  const enrichedCorridors = CORRIDORS.map((corridor) => {
    const live = liveItems.find((item) => item.location_name === corridor.name);
    return {
      ...corridor,
      congestion_index: live?.congestion_index ?? 0,
      current_speed: live?.current_speed ?? null
    };
  });

  function getRecommendation(ci, etaSeconds) {
    const etaMin = Number.isFinite(etaSeconds) ? Math.round(etaSeconds / 60) : null;
    if (ci >= 0.75) return etaMin ? `Avoid if possible — ≈ ${etaMin} min` : 'Avoid if possible — heavy delay';
    if (ci >= 0.5) return etaMin ? `Consider alternate route — ≈ ${etaMin} min` : 'Consider alternate route';
    if (ci >= 0.25) return etaMin ? `Minor delays — ≈ ${etaMin} min` : 'Minor delays likely';
    return 'Traffic flowing well';
  }

  // Prepare heatmap points: use probe points if available, else fallback to corridor centroids
  const heatmapPoints = probePoints.length > 0 ? probePoints : enrichedCorridors.map((c) => [c.lat, c.lng, c.congestion_index]);

  const routePath = CORRIDORS.map((corridor) => [corridor.lat, corridor.lng]);

  const bangaloreBounds = [
    [12.72, 77.44],
    [13.23, 77.85]
  ];

  return (
    <Card
      sx={{
        mt: 2,
        background: "linear-gradient(155deg, rgba(255,255,255,0.98) 0%, rgba(245,252,251,0.94) 100%)"
      }}
    >
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Bengaluru Corridor Map
        </Typography>
        <Box
          sx={{
            position: "relative",
            height: 320,
            borderRadius: 2,
            overflow: "hidden",
            border: "1px solid rgba(15, 23, 42, 0.12)"
          }}
        >
          <MapContainer
            center={[12.9716, 77.5946]}
            zoom={11}
            minZoom={10}
            maxZoom={15}
            maxBounds={bangaloreBounds}
            maxBoundsViscosity={1}
            preserveViewport={false}
            worldCopyJump={false}
            scrollWheelZoom
            style={{ height: "100%", width: "100%" }}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            <Polyline positions={routePath} pathOptions={{ color: "#0b2447", weight: 3, opacity: 0.5, dashArray: "5 7" }} />

            <HeatmapLayer
              fitBoundsOnLoad={false}
              fitBoundsOnUpdate={false}
              points={heatmapPoints}
              longitudeExtractor={m => m[1]}
              latitudeExtractor={m => m[0]}
              intensityExtractor={m => m[2]}
              max={1}
              radius={20}
              blur={18}
              gradient={{
                0.0: "rgb(0, 255, 0)",
                0.2: "rgb(173, 255, 47)",
                0.4: "rgb(255, 255, 0)",
                0.6: "rgb(255, 165, 0)",
                0.8: "rgb(255, 69, 0)",
                1.0: "rgb(255, 0, 0)"
              }}
            />
            {loadingProbes && (
              <div style={{position: "absolute", top: 10, left: 10, background: "rgba(0,0,0,0.7)", color: "#fff", padding: "4px 10px", borderRadius: 4, zIndex: 1000}}>
                Loading probe points...
              </div>
            )}
            {probeError && (
              <div style={{position: "absolute", top: 10, left: 10, background: "#d62828", color: "#fff", padding: "4px 10px", borderRadius: 4, zIndex: 1000}}>
                {probeError}
              </div>
            )}
          </MapContainer>
        </Box>
        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1.5 }}>
          <Chip sx={{ fontWeight: 600 }} color="secondary" label={`Focused: ${selectedLocation}`} />
          {(() => {
            const sel = liveItems.find((l) => l.location_name === selectedLocation);
            if (!sel) return null;
            const crowdLabel = sel.crowd_density !== undefined ? (sel.crowd_density * 100).toFixed(0) + '%' : 'N/A';
            return (
              <>
                <Chip size="small" label={getRecommendation(sel.congestion_index, sel.eta_seconds)} sx={{ bgcolor: "rgba(0,0,0,0.06)" }} />
                <Chip size="small" label={`Crowd: ${crowdLabel}`} sx={{ bgcolor: '#f97316', color: '#fff', fontWeight: 700, ml: 0.5 }} />
              </>
            );
          })()}
          <Chip size="small" label="Low" sx={{ bgcolor: "#2a9d8f", color: "#fff" }} />
          <Chip size="small" label="Medium" sx={{ bgcolor: "#f4a261", color: "#1f2937" }} />
          <Chip size="small" label="High" sx={{ bgcolor: "#e07a5f", color: "#fff" }} />
          <Chip size="small" label="Severe" sx={{ bgcolor: "#d62828", color: "#fff" }} />
        </Stack>
      </CardContent>
    </Card>
  );
}

export default LiveMap;
