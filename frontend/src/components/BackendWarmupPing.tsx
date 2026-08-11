'use client';

import { useEffect } from 'react';
import { API_BASE } from '@/lib/api';

/**
 * BackendWarmupPing Component
 * ============================
 * Triggers an immediate silent background HTTP ping to `${API_BASE}/health`
 * when a user opens the website. This wakes up the Render free tier backend server
 * (preventing 30-60s cold start delays) and sends a recurring ping every 10 minutes
 * to keep the container awake while active.
 */
export default function BackendWarmupPing() {
  useEffect(() => {
    const triggerPing = () => {
      fetch(`${API_BASE}/health`, { mode: 'cors' }).catch(() => {
        // Silently ignore network/warmup errors
      });
    };

    // Immediate initial warmup ping
    triggerPing();

    // Recurring ping every 10 minutes (600,000 ms) to keep Render backend awake
    const interval = setInterval(triggerPing, 600000);
    return () => clearInterval(interval);
  }, []);

  return null;
}
