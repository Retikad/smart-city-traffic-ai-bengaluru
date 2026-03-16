import React from "react";
import { Box, Card, CardContent, Chip, Typography } from "@mui/material";

const CORRIDORS = [
  { name: "MG Road", lat: 12.9757, lng: 77.6011 },
  { name: "Silk Board Junction", lat: 12.9176, lng: 77.623 },
  { name: "Whitefield", lat: 12.9698, lng: 77.75 },
  { name: "Electronic City", lat: 12.8452, lng: 77.6602 },
  { name: "Hebbal Flyover", lat: 13.035, lng: 77.597 }
];

function normalize(value, min, max, outMin, outMax) {
  if (max === min) return (outMin + outMax) / 2;
  return outMin + ((value - min) / (max - min)) * (outMax - outMin);
}

function LiveMap({ selectedLocation }) {
  const latVals = CORRIDORS.map((c) => c.lat);
  const lngVals = CORRIDORS.map((c) => c.lng);
  const minLat = Math.min(...latVals);
  const maxLat = Math.max(...latVals);
  const minLng = Math.min(...lngVals);
  const maxLng = Math.max(...lngVals);

  return (
    <Card sx={{ mt: 2 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Bengaluru Corridor Map
        </Typography>
        <Box
          sx={{
            position: "relative",
            height: 220,
            borderRadius: 2,
            overflow: "hidden",
            background:
              "radial-gradient(circle at 20% 20%, rgba(255, 203, 107, 0.7), rgba(15, 76, 92, 0.2)), linear-gradient(135deg, #fefae0 0%, #faedcd 100%)"
          }}
        >
          <svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none">
            <defs>
              <pattern id="grid" width="8" height="8" patternUnits="userSpaceOnUse">
                <path d="M 8 0 L 0 0 0 8" fill="none" stroke="rgba(15,76,92,0.15)" strokeWidth="0.5" />
              </pattern>
            </defs>
            <rect x="0" y="0" width="100" height="100" fill="url(#grid)" />
            {CORRIDORS.map((corridor) => {
              const x = normalize(corridor.lng, minLng, maxLng, 15, 85);
              const y = normalize(corridor.lat, minLat, maxLat, 85, 15);
              const active = corridor.name === selectedLocation;
              return (
                <g key={corridor.name}>
                  <circle cx={x} cy={y} r={active ? 3.4 : 2.4} fill={active ? "#e36414" : "#0f4c5c"} />
                  <text x={x + 1.8} y={y - 1.8} fontSize="2.8" fill="#1f2937">
                    {corridor.name}
                  </text>
                </g>
              );
            })}
          </svg>
        </Box>
        <Chip sx={{ mt: 1.5 }} color="secondary" label={`Focused: ${selectedLocation}`} />
      </CardContent>
    </Card>
  );
}

export default LiveMap;
