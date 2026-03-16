import React from "react";
import { Box, Card, CardContent, Typography } from "@mui/material";
import { CartesianGrid, Line, LineChart, ReferenceArea, Tooltip, XAxis, YAxis } from "recharts";

function colorForCI(ci) {
  if (ci < 0.25) return "#2f9e44";
  if (ci < 0.5) return "#f08c00";
  if (ci < 0.75) return "#e67700";
  return "#c92a2a";
}

function parseApiDateTime(value) {
  if (!value) return null;
  const raw = String(value).trim();
  // Backend returns naive UTC timestamps (no timezone suffix). Treat them as UTC.
  const hasTimezone = /(?:Z|[+-]\d\d:\d\d)$/i.test(raw);
  const normalized = hasTimezone ? raw : `${raw}Z`;
  const dt = new Date(normalized);
  return Number.isNaN(dt.getTime()) ? null : dt;
}

function CongestionChart({ data }) {
  const chartData = data.map((row) => ({
    ...row,
    time: (parseApiDateTime(row.window_end) || new Date(row.window_end)).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false
    })
  }));
  const chartWidth = Math.max(760, chartData.length * 36);
  const maxCI = chartData.reduce((m, r) => Math.max(m, r.avg_congestion_index || 0), 0);
  const yMax = maxCI < 0.3 ? 0.3 : 1.0;

  return (
    <Card
      sx={{
        height: "100%",
        background: "linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(247,250,252,0.95) 100%)"
      }}
    >
      <CardContent>
        <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
          Last 24h Congestion Index
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
          Scroll horizontally to view the full 24-hour timeline.
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1.2 }}>
          Corridor peak in this window: {(maxCI * 100).toFixed(1)}%
        </Typography>
        <Box sx={{ width: "100%", overflowX: "auto", overflowY: "hidden", pb: 0.5 }}>
          <LineChart width={chartWidth} height={320} data={chartData}>
            <ReferenceArea y1={0} y2={0.25} fill="#2a9d8f" fillOpacity={0.08} />
            <ReferenceArea y1={0.25} y2={0.5} fill="#f4a261" fillOpacity={0.08} />
            <ReferenceArea y1={0.5} y2={0.75} fill="#e07a5f" fillOpacity={0.08} />
            <ReferenceArea y1={0.75} y2={1} fill="#d62828" fillOpacity={0.08} />
            <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ea" />
            <XAxis dataKey="time" minTickGap={24} tick={{ fill: "#3c4a56", fontSize: 12 }} />
            <YAxis domain={[0, yMax]} tick={{ fill: "#3c4a56", fontSize: 12 }} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="avg_congestion_index"
              stroke="#0b2447"
              strokeWidth={3}
              dot={(props) => {
                const { cx, cy, payload } = props;
                return <circle cx={cx} cy={cy} r={3.4} fill={colorForCI(payload.avg_congestion_index)} />;
              }}
            />
          </LineChart>
        </Box>
      </CardContent>
    </Card>
  );
}

export default CongestionChart;
