import React from "react";
import { Card, CardContent, FormControl, InputLabel, MenuItem, Select, Typography } from "@mui/material";

function LocationSelector({ locations, selectedLocation, onChange }) {
  return (
    <Card
      sx={{
        background: "linear-gradient(145deg, rgba(255,255,255,0.97) 0%, rgba(240,247,255,0.94) 100%)"
      }}
    >
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Corridor Selection
        </Typography>
        <FormControl fullWidth size="small">
          <InputLabel id="location-label">Location</InputLabel>
          <Select
            labelId="location-label"
            value={selectedLocation}
            label="Location"
            onChange={(event) => onChange(event.target.value)}
          >
            {locations.map((loc) => (
              <MenuItem key={loc} value={loc}>
                {loc}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </CardContent>
    </Card>
  );
}

export default LocationSelector;
