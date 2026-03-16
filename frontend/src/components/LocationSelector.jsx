import React from "react";
import { Card, CardContent, FormControl, InputLabel, MenuItem, Select, Typography } from "@mui/material";

function LocationSelector({ locations, selectedLocation, onChange }) {
  return (
    <Card>
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
