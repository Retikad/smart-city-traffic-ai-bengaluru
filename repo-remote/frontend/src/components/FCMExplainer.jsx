import React from "react";
import { Alert, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

function FCMExplainer({ explanation, loading, error }) {
  const chartData = explanation
    ? Object.entries(explanation.fcm_vector).map(([name, value]) => ({
        concept: name,
        activation: value,
        highlight: name === explanation.dominant_cause
      }))
    : [];

  return (
    <Card
      sx={{
        height: "100%",
        background: "linear-gradient(170deg, rgba(255,255,255,0.96) 0%, rgba(250,247,241,0.95) 100%)"
      }}
    >
      <CardContent>
        <Typography variant="h6" gutterBottom>
          FCM Reasoning
        </Typography>

        {loading && <Alert severity="info">Running FCM reasoning...</Alert>}
        {error && <Alert severity="error">{error}</Alert>}

        {!loading && !error && explanation && (
          <>
            <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Dominant cause
              </Typography>
              <Chip size="small" color="secondary" label={explanation.dominant_cause} />
            </Stack>
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 16, left: 34, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ea" />
                <XAxis type="number" domain={[0, 1]} tick={{ fill: "#3c4a56", fontSize: 12 }} />
                <YAxis type="category" dataKey="concept" width={130} tick={{ fill: "#3c4a56", fontSize: 12 }} />
                <Tooltip />
                <Bar
                  dataKey="activation"
                  shape={(props) => {
                    const { x, y, width, height, payload } = props;
                    return (
                      <rect
                        x={x}
                        y={y}
                        width={width}
                        height={height}
                        fill={payload.highlight ? "#e07a5f" : "#0b2447"}
                        rx={3}
                        ry={3}
                      />
                    );
                  }}
                />
              </BarChart>
            </ResponsiveContainer>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {explanation.explanation}
            </Typography>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default FCMExplainer;
