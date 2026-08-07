# backend/app/services/gdrive_sync.py
"""
Google Drive Auto-Sync Module for MorBok AI
============================================
Handles real-time asynchronous data sync of encounter logs (transcripts, deid metadata, and LLM summaries)
from Render cloud backend directly to Google Drive.
"""

import os
import json
import threading
import requests
from typing import Dict, Any, Optional

from app.core.config import settings

def sync_log_to_gdrive_async(log_data: Dict[str, Any]) -> None:
    """
    Asynchronously syncs encounter log entry to Google Drive.
    Runs in a non-blocking background thread to preserve low API latency.
    """
    webhook_url = settings.GDRIVE_WEBHOOK_URL or os.environ.get("GDRIVE_WEBHOOK_URL")
    
    def _worker():
        # Method 1: Google Apps Script Webhook (Zero-credentials, instant setup)
        if webhook_url:
            try:
                res = requests.post(
                    webhook_url,
                    json=log_data,
                    headers={"Content-Type": "application/json"},
                    timeout=15
                )
                if res.status_code in [200, 201, 302]:
                    print(f"☁️ [Google Drive Sync] Successfully pushed encounter {log_data.get('encounter_id')} to Google Drive.")
                else:
                    print(f"⚠️ [Google Drive Sync] Webhook returned status {res.status_code}: {res.text[:100]}")
            except Exception as e:
                print(f"⚠️ [Google Drive Sync] Failed to send log to Webhook: {e}")

    # Fire background thread
    threading.Thread(target=_worker, daemon=True).start()
