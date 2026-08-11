# docs/research/export_telemetry_csv.py
"""
MorBok AI — Telemetry & Satisfaction CSV Exporter
=================================================
This script reads telemetry_evaluations.jsonl log data and exports two clean CSV datasets:
1. clinician_satisfaction_evaluations.csv
2. patient_caregiver_satisfaction_evaluations.csv

Usage:
    python docs/research/export_telemetry_csv.py
"""

import os
import json
import csv
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_PATH = os.path.join(BASE_DIR, "backend", "logs", "telemetry_evaluations.jsonl")
OUTPUT_DIR = os.path.join(BASE_DIR, "docs", "research")

def export_telemetry_csv():
    if not os.path.exists(LOG_PATH):
        print(f"⚠️ Telemetry log file not found at: {LOG_PATH}")
        print("Please record evaluations via the web application or API first.")
        return

    doctor_rows = []
    patient_rows = []
    system_rows = []

    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line.strip())
            record_id = entry.get("id")
            timestamp = entry.get("timestamp")
            p = entry.get("payload", {})
            role = entry.get("role") or p.get("role", "UNKNOWN")

            if role == "SYSTEM_BACKGROUND_TELEMETRY":
                system_rows.append({
                    "eval_id": record_id,
                    "timestamp": timestamp,
                    "encounter_id": p.get("encounter_id", ""),
                    "doctor_license": p.get("doctor_license", ""),
                    "time_to_clinical_llm_sec": p.get("time_to_clinical_llm_sec", ""),
                    "time_llm_to_final_doctor_edit_sec": p.get("time_llm_to_final_doctor_edit_sec", ""),
                    "manual_edit_count": p.get("manual_edit_count", ""),
                    "llm_draft_word_count": p.get("llm_draft_word_count", ""),
                    "final_doctor_word_count": p.get("final_doctor_word_count", ""),
                    "word_count_diff": p.get("word_count_diff", "")
                })
            elif role == "DOCTOR":
                doctor_rows.append({
                    "eval_id": record_id,
                    "timestamp": timestamp,
                    "encounter_id": p.get("encounter_id", ""),
                    "doctor_license": p.get("doctor_license", ""),
                    "time_to_sign_off_sec": p.get("time_to_sign_off_sec", ""),
                    "manual_edit_count": p.get("manual_edit_count", ""),
                    "overall_satisfaction_csat": p.get("overall_satisfaction_csat", ""),
                    "workload_reduction_satisfaction": p.get("workload_reduction_satisfaction", ""),
                    "clinical_accuracy_rating_1_10": p.get("clinical_accuracy_rating", ""),
                    "doctor_nps_score_0_10": p.get("doctor_nps_score", ""),
                    "comments": p.get("comments", "")
                })
            elif role in ["PATIENT", "CAREGIVER"]:
                patient_rows.append({
                    "eval_id": record_id,
                    "timestamp": timestamp,
                    "encounter_id": p.get("encounter_id", ""),
                    "channel": p.get("channel", "LINE_OA"),
                    "overall_satisfaction_csat": p.get("overall_satisfaction_csat", ""),
                    "language_clarity_satisfaction": p.get("language_clarity_satisfaction", ""),
                    "med_matrix_clarity_satisfaction": p.get("med_matrix_clarity_satisfaction", ""),
                    "line_audio_convenience_satisfaction": p.get("line_audio_convenience_satisfaction", ""),
                    "reassurance_peace_of_mind": p.get("reassurance_peace_of_mind", ""),
                    "patient_nps_score": p.get("patient_nps_score", ""),
                    "red_flag_recall_score_pct": p.get("red_flag_recall_score", ""),
                    "med_instruction_recall_score_pct": p.get("med_instruction_recall_score", ""),
                    "ambient_mic_comfort_rating": p.get("ambient_mic_comfort_rating", ""),
                    "trust_in_ai_rating": p.get("trust_in_ai_rating", ""),
                    "comments": p.get("comments", "")
                })

    # Write System Telemetry CSV
    sys_csv_path = os.path.join(OUTPUT_DIR, "system_background_telemetry.csv")
    if system_rows:
        with open(sys_csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=system_rows[0].keys())
            writer.writeheader()
            writer.writerows(system_rows)
        print(f"✅ Exported {len(system_rows)} System Telemetry records to: {sys_csv_path}")

    # Write Clinician CSV
    doc_csv_path = os.path.join(OUTPUT_DIR, "clinician_satisfaction_evaluations.csv")
    if doctor_rows:
        with open(doc_csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=doctor_rows[0].keys())
            writer.writeheader()
            writer.writerows(doctor_rows)
        print(f"✅ Exported {len(doctor_rows)} Clinician records to: {doc_csv_path}")

    # Write Patient/Caregiver CSV
    pat_csv_path = os.path.join(OUTPUT_DIR, "patient_caregiver_satisfaction_evaluations.csv")
    if patient_rows:
        with open(pat_csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=patient_rows[0].keys())
            writer.writeheader()
            writer.writerows(patient_rows)
        print(f"✅ Exported {len(patient_rows)} Patient/Caregiver records to: {pat_csv_path}")

    if not doctor_rows and not patient_rows and not system_rows:
        print("ℹ️ No evaluation records found to export.")

if __name__ == "__main__":
    export_telemetry_csv()
