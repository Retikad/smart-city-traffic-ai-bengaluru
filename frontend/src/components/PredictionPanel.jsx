import React from "react";
import { Alert, Card, CardContent, Chip, LinearProgress, Stack, Typography } from "@mui/material";

const chipColor = {
  low: "success",
  medium: "warning",
  high: "warning",
  severe: "error"
};

function PredictionPanel({ prediction, loading, error }) {
  return (
    <Card
      sx={{
        height: "100%",
        background: "linear-gradient(150deg, rgba(255,255,255,0.96) 0%, rgba(245,248,255,0.95) 100%)"
      }}
    >
      <CardContent>
        <Typography variant="h6" gutterBottom>
          LSTM Next-Interval Prediction
        </Typography>

        {loading && <Alert severity="info">Running LSTM inference...</Alert>}
        {error && <Alert severity="error">{error}</Alert>}

        {!loading && !error && prediction && (
          <Stack spacing={1.2}>
            <Typography variant="h3" sx={{ fontWeight: 700, color: "#0b2447" }}>
              {(prediction.congestion_index * 100).toFixed(1)}%
            </Typography>
            <Chip
              label={prediction.label.toUpperCase()}
              color={chipColor[prediction.label] || "default"}
              sx={{ width: 120, fontWeight: 700 }}
            />
            <Typography variant="body2" color="text.secondary">
              Predicted next 5-minute congestion level
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Confidence: {(prediction.confidence * 100).toFixed(1)}%
            </Typography>
            <LinearProgress
              variant="determinate"
              value={Math.max(0, Math.min(100, prediction.confidence * 100))}
              sx={{ height: 8, borderRadius: 99 }}
            />
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}

export default PredictionPanel;
