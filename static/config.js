/**
 * PELAGOS Ocean 3D Configuration
 * Production backend deployed on Render: https://pelagos-backend-1eic.onrender.com
 */
window.__PELAGOS_CONFIG__ = {
  API_BASE: (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "http://localhost:8000/api"
    : "https://pelagos-backend-1eic.onrender.com/api"
};
