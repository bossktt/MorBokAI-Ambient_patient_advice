# backend/app/services/telemetry_service.py
"""
MorBok AI — Clinical Telemetry & User Evaluation Service
=========================================================
This service collects, validates, and persists user feedback, telemetry metrics,
and Satisfaction (CSAT/NPS) scores for Doctors (Clinicians) and Patients/Caregivers.
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
            "overall_satisfaction_csat": 5,      # 1-5 Likert
            "workload_reduction_satisfaction": 5, # 1-5 Likert
            "perceived_patient_impact": 5,       # 1-5 Likert
            "doctor_nps_score": 9,               # 0-10 Score
            "clinical_accuracy_rating": 5,
            "grade5_language_rating": 5,
            "linked_audio_utility_rating": 4,
            "comments": "ช่วยลดเวลาเขียนใบนัดได้ดีมาก"
          }

        - Patient / Caregiver evaluation:
          {
            "role": "PATIENT",
            "encounter_id": "ENC_XXXXX",
            "channel": "LINE_OA",
            "overall_satisfaction_csat": 5,          # 1-5 Likert
            "language_clarity_satisfaction": 5,      # 1-5 Likert (Grade 5 Thai)
            "med_matrix_clarity_satisfaction": 5,    # 1-5 Likert (START/STOP/CHANGE)
            "line_audio_convenience_satisfaction": 5,# 1-5 Likert
            "reassurance_peace_of_mind": 5,          # 1-5 Likert
            "patient_nps_score": 10,                 # 0-10 Score
            "red_flag_recall_score": 100,            # %
            "med_instruction_recall_score": 100,      # %
            "reading_ease_rating": 5,
            "ambient_mic_comfort_rating": 4,
            "trust_in_ai_rating": 5,
            "audio_playback_used": True,
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

    @staticmethod
    def calculate_satisfaction_summary() -> Dict[str, Any]:
        """Calculates CSAT %, NPS, and average Likert scores for Doctors and Patients."""
        records = TelemetryService.get_all_records()
        
        doctor_csat_scores = []
        doctor_nps_scores = []
        patient_csat_scores = []
        patient_nps_scores = []

        for r in records:
            p = r.get("payload", {})
            role = r.get("role") or p.get("role")
            
            if role == "DOCTOR":
                if "overall_satisfaction_csat" in p:
                    doctor_csat_scores.append(float(p["overall_satisfaction_csat"]))
                if "doctor_nps_score" in p:
                    doctor_nps_scores.append(int(p["doctor_nps_score"]))
            elif role in ["PATIENT", "CAREGIVER"]:
                if "overall_satisfaction_csat" in p:
                    patient_csat_scores.append(float(p["overall_satisfaction_csat"]))
                if "patient_nps_score" in p:
                    patient_nps_scores.append(int(p["patient_nps_score"]))

        def calc_csat_pct(scores: List[float]) -> float:
            if not scores:
                return 0.0
            satisfied = sum(1 for s in scores if s >= 4.0)
            return round((satisfied / len(scores)) * 100, 1)

        def calc_nps(scores: List[int]) -> float:
            if not scores:
                return 0.0
            promoters = sum(1 for s in scores if s >= 9)
            detractors = sum(1 for s in scores if s <= 6)
            return round(((promoters - detractors) / len(scores)) * 100, 1)

        return {
            "total_evaluations": len(records),
            "doctor": {
                "count": len(doctor_csat_scores),
                "csat_percentage": calc_csat_pct(doctor_csat_scores),
                "avg_satisfaction_rating": round(sum(doctor_csat_scores) / len(doctor_csat_scores), 2) if doctor_csat_scores else 0.0,
                "nps": calc_nps(doctor_nps_scores)
            },
            "patient_caregiver": {
                "count": len(patient_csat_scores),
                "csat_percentage": calc_csat_pct(patient_csat_scores),
                "avg_satisfaction_rating": round(sum(patient_csat_scores) / len(patient_csat_scores), 2) if patient_csat_scores else 0.0,
                "nps": calc_nps(patient_nps_scores)
            }
        }
