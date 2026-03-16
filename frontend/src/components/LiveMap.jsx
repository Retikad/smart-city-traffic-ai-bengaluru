import React from "react";
import { Box, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const CORRIDORS = [
  { name: "MG Road", lat: 12.9757, lng: 77.6011 },
  { name: "Silk Board Junction", lat: 12.9176, lng: 77.623 },
  { name: "Whitefield", lat: 12.9698, lng: 77.75 },
  { name: "Electronic City", lat: 12.8452, lng: 77.6602 },
  { name: "Hebbal Flyover", lat: 13.035, lng: 77.597 }
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
  const enrichedCorridors = CORRIDORS.map((corridor) => {
    const live = liveItems.find((item) => item.location_name === corridor.name);
    return {
      ...corridor,
      congestion_index: live?.congestion_index ?? 0,
      current_speed: live?.current_speed ?? null
    };
  });

  const routePath = CORRIDORS.map((corridor) => [corridor.lat, corridor.lng]);

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
          <MapContainer center={[12.9716, 77.5946]} zoom={11} scrollWheelZoom style={{ height: "100%", width: "100%" }}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            <Polyline positions={routePath} pathOptions={{ color: "#0b2447", weight: 3, opacity: 0.5, dashArray: "5 7" }} />

            {enrichedCorridors.map((corridor) => {
              const active = corridor.name === selectedLocation;
              const ci = corridor.congestion_index;
              return (
                <CircleMarker
                  key={corridor.name}
                  center={[corridor.lat, corridor.lng]}
                  radius={markerRadius(ci, active)}
                  pathOptions={{
                    color: active ? "#111827" : "#ffffff",
                    weight: active ? 3 : 1.5,
                    fillColor: markerColor(ci),
                    fillOpacity: 0.86
                  }}
                >
                  <Tooltip direction="top" offset={[0, -6]} opacity={0.95}>
                    <div>
                      <strong>{corridor.name}</strong>
                      <br />
                      Congestion: {(ci * 100).toFixed(1)}%
                      <br />
                      Speed: {corridor.current_speed !== null ? `${corridor.current_speed.toFixed(1)} km/h` : "N/A"}
                    </div>
                  </Tooltip>
                </CircleMarker>
              );
            })}
          </MapContainer>
        </Box>
        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1.5 }}>
          <Chip sx={{ fontWeight: 600 }} color="secondary" label={`Focused: ${selectedLocation}`} />
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
