import React from "react";
import { Alert, Card, CardContent, Chip, Stack, Typography } from "@mui/material";

const chipColor = {
  low: "success",
  medium: "warning",
  high: "warning",
  severe: "error"
};

function PredictionPanel({ prediction, loading, error }) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          LSTM Next-Interval Prediction
        </Typography>

        {loading && <Alert severity="info">Running LSTM inference...</Alert>}
        {error && <Alert severity="error">{error}</Alert>}

        {!loading && !error && prediction && (
          <Stack spacing={1.2}>
            <Typography variant="h3" sx={{ fontWeight: 700 }}>
              {(prediction.congestion_index * 100).toFixed(1)}%
            </Typography>
            <Chip
              label={prediction.label.toUpperCase()}
              color={chipColor[prediction.label] || "default"}
              sx={{ width: 110, fontWeight: 700 }}
            />
            <Typography variant="body2" color="text.secondary">
              Confidence: {(prediction.confidence * 100).toFixed(1)}%
            </Typography>
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}

export default PredictionPanel;
