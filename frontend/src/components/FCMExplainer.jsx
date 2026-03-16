import React from "react";
import { Alert, Card, CardContent, Typography } from "@mui/material";
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
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          FCM Reasoning
        </Typography>

        {loading && <Alert severity="info">Running FCM reasoning...</Alert>}
        {error && <Alert severity="error">{error}</Alert>}

        {!loading && !error && explanation && (
          <>
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 16, left: 34, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 1]} />
                <YAxis type="category" dataKey="concept" width={130} />
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
                        fill={payload.highlight ? "#f08c00" : "#0f4c5c"}
                        rx={3}
                        ry={3}
                      />
                    );
                  }}
                />
              </BarChart>
            </ResponsiveContainer>
            <Typography variant="body2" sx={{ mt: 1 }}>
              {explanation.explanation}
            </Typography>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default FCMExplainer;
