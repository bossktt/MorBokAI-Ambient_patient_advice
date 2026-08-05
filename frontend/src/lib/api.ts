// frontend/src/lib/api.ts
// Central API base URL.
// Dev:    NEXT_PUBLIC_API_HOST unset  -> http://localhost:8080
// Prod:   set NEXT_PUBLIC_API_HOST to the deployed backend URL
// Mobile: set NEXT_PUBLIC_API_HOST to your machine's LAN IP (e.g. http://192.168.1.50:8080)
export const API_BASE: string =
  process.env.NEXT_PUBLIC_API_HOST?.replace(/\/$/, '') || 'http://localhost:8080';

// WebSocket URL derived from API_BASE (http->ws, https->wss)
export const WS_BASE: string = API_BASE.replace(/^http/, 'ws');
