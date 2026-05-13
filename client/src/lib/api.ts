// In dev, VITE_API_BASE_URL is unset so apiUrl returns relative paths and the
// Vite proxy handles forwarding to Flask. In prod (cross-origin deploy), set
// VITE_API_BASE_URL to the backend's absolute URL.
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}
