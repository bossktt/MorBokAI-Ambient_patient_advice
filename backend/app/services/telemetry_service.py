# backend/app/services/telemetry_service.py
"""
MorBok AI — Clinical Telemetry & User Evaluation Service
=========================================================
This service collects, validates, and persists user feedback and telemetry metrics
for testing MorBok AI with Doctors (Clinicians) and Patients/Caregivers.
"""

import os
import json
import time
import datetime
from typing import Dict, Any, List, Optional
from app.core.config import settings

TELEMETRY_LOG_PATH = os.path.join(settings.LOGS_DIR, "telemetry_evaluations.jsonl")

class TelemetryService:
    @staticmethod
    def record_evaluation(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Persists a telemetry/survey evaluation entry into telemetry_evaluations.jsonl.
        
        Payload formats:
        - Doctor evaluation:
          {
            "role": "DOCTOR",
            "encounter_id": "ENC_XXXXX",
            "doctor_license": "ว.12345",
            "time_to_sign_off_sec": 24.5,
            "manual_edit_count": 2,
            "sus_scores": [4, 5, 4, 5, 4, 5, 5, 4, 5, 5],
            "sus_total": 92.5,
            "clinical_accuracy_rating": 5,
            "grade5_language_rating": 5,
            "linked_audio_utility_rating": 4,
            "comments": "ช่วยลดเวลาเขียนใบนัดได้ดีมาก"
          }

        - Patient evaluation:
          {
            "role": "PATIENT",
            "encounter_id": "ENC_XXXXX",
            "channel": "LINE_OA",
            "red_flag_recall_score": 100,  # %
            "med_instruction_recall_score": 100,  # %
            "reading_ease_rating": 5,
            "ambient_mic_comfort_rating": 4,
            "trust_in_ai_rating": 5,
            "audio_playback_used": True,
            "nps_score": 10,
            "comments": "สรุปชัดเจน เข้าใจง่าย มีเสียงให้ฟังย้อนหลัง"
          }
        """
        os.makedirs(settings.LOGS_DIR, exist_ok=True)
        
        record = {
            "id": f"EVAL_{int(time.time() * 1000)}",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(),
            "role": data.get("role", "UNKNOWN"),
            "encounter_id": data.get("encounter_id", "N/A"),
            "payload": data
        }

        try:
            with open(TELEMETRY_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"⚠️ Failed to record telemetry evaluation: {e}")

        return record

    @staticmethod
    def get_all_records() -> List[Dict[str, Any]]:
        """Reads all telemetry records from file."""
        if not os.path.exists(TELEMETRY_LOG_PATH):
            return []
        
        records = []
        try:
            with open(TELEMETRY_LOG_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line.strip()))
        except Exception as e:
            print(f"⚠️ Error reading telemetry records: {e}")
        
        return records
