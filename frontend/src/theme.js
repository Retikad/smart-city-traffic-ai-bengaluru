import { createTheme } from "@mui/material/styles";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#0f4c5c" },
    secondary: { main: "#e36414" },
    success: { main: "#2f9e44" },
    warning: { main: "#f08c00" },
    error: { main: "#c92a2a" },
    background: { default: "#f4f1ea", paper: "#fffaf0" }
  },
  typography: {
    fontFamily: "'Poppins', 'Segoe UI', sans-serif",
    h5: { fontWeight: 700 },
    h6: { fontWeight: 600 }
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 14,
          boxShadow: "0 10px 25px rgba(15, 76, 92, 0.08)"
        }
      }
    }
  }
});

export default theme;
