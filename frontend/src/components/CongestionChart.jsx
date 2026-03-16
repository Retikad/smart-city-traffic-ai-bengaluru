import React from "react";
import { Card, CardContent, Typography } from "@mui/material";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

function colorForCI(ci) {
  if (ci < 0.25) return "#2f9e44";
  if (ci < 0.5) return "#f08c00";
  if (ci < 0.75) return "#e67700";
  return "#c92a2a";
}

function CongestionChart({ data }) {
  const chartData = data.map((row) => ({
    ...row,
    time: new Date(row.window_end).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  }));

  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Last 24h Congestion Index
        </Typography>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#d9d9d9" />
            <XAxis dataKey="time" minTickGap={24} />
            <YAxis domain={[0, 1]} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="avg_congestion_index"
              stroke="#0f4c5c"
              strokeWidth={2.5}
              dot={(props) => {
                const { cx, cy, payload } = props;
                return <circle cx={cx} cy={cy} r={3.4} fill={colorForCI(payload.avg_congestion_index)} />;
              }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export default CongestionChart;
