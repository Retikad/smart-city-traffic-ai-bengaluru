import { createTheme } from "@mui/material/styles";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#0b2447" },
    secondary: { main: "#e07a5f" },
    success: { main: "#2a9d8f" },
    warning: { main: "#f4a261" },
    error: { main: "#d62828" },
    background: { default: "#fbf9f4", paper: "#ffffff" }
  },
  typography: {
    fontFamily: "'Sora', 'Segoe UI', sans-serif",
    h4: { fontFamily: "'Space Grotesk', 'Sora', sans-serif", fontWeight: 700 },
    h5: { fontFamily: "'Space Grotesk', 'Sora', sans-serif", fontWeight: 700 },
    h6: { fontFamily: "'Space Grotesk', 'Sora', sans-serif", fontWeight: 600 },
    overline: { fontWeight: 600 }
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          border: "1px solid rgba(15, 23, 42, 0.08)",
          boxShadow: "0 16px 40px rgba(11, 36, 71, 0.08)"
        }
      }
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 10
        }
      }
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: "none"
        }
      }
    }
  }
});

export default theme;
