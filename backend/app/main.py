# backend/app/main.py
"""
MorBok AI — FastAPI Backend Gateway & WebServices API
=====================================================
This module serves as the primary REST & WebSocket entry point for MorBok AI backend services.

Core Responsibilities:
  1. Encounter Session Management (`/api/v1/encounters/create`, `GET /api/v1/encounters/{id}`):
     - Initializes medical record encounters and stores status in Redis (with in-memory dictionary fallback).
  2. Ambient Audio WebSocket Stream (`/ws/audio-stream/{encounter_id}`):
     - Receives real-time PCM audio chunks via WebSocket from Screen 3 (`scribe/page.tsx`).
     - Passes audio bytes to MultiTierASRService for transcription.
  3. Clinical Transcript Processing (`/api/v1/encounters/process-transcript`):
     - Sanitizes transcript with DeIdentificationEngine (PII removal).
     - Invokes Clinical LLM Adapter (OpenRouter, Typhoon Medical, Gemini, Azure, Local) for Grade 5 Thai summary.
  4. PDF Generation & Purge (`/api/v1/encounters/{id}/export-pdf`, `/api/v1/pdf/{pdf_id}/download`):
     - Generates printable A4 After-Visit Summary sheets.
     - Implements 10-minute auto-purge timer for HIPAA compliance and temporary storage hygiene.

Maintainer Notes:
  - Default Port: 8080 (`uvicorn app.main:app --port 8080`).
  - OpenAPI Swagger Specs: Available at `http://localhost:8080/docs`.
"""

import os
import time
import json
import re
import uuid
import datetime
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import redis

from app.core.config import settings
from app.services.deid_engine import DeIdentificationEngine
from app.services.llm_adapter import get_llm_adapter, ground_summary_to_transcript
from app.services.asr_service import MultiTierASRService
from app.services.pdf_service import PDFService
from app.services.telemetry_service import TelemetryService, TELEMETRY_LOG_PATH

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# Enable CORS for Next.js Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temporary PDF Storage Directory
TEMP_PDF_DIR = os.path.join(os.path.dirname(__file__), "temp_pdfs")
os.makedirs(TEMP_PDF_DIR, exist_ok=True)

# Ensure logs directory exists
LOGS_DIR = settings.LOGS_DIR
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(LOGS_DIR, settings.LOG_FILE_NAME)

from app.services.gdrive_sync import sync_log_to_gdrive_async

def append_encounter_log(log_data: dict):
    """Appends encounter record to backend/logs/encounter_logs.jsonl and auto-syncs to Google Drive."""
    if not settings.ENABLE_ENCOUNTER_LOGGING:
        return
    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"⚠️ Failed to write encounter log: {e}")
    
    # Auto-sync log to Google Drive (non-blocking background thread)
    sync_log_to_gdrive_async(log_data)

# Metadata store for PDF expiry tracking (pdf_id -> {file_path, expires_at})
pdf_metadata_store: Dict[str, Dict[str, Any]] = {}

# In-memory dictionary fallback if Redis is offline during local testing
memory_store = {}

try:
    r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    r.ping()
    use_redis = True
except Exception:
    use_redis = False

def cache_set(key: str, val: str, ttl: int = 86400):
    if use_redis:
        try:
            r.setex(key, ttl, val)
            return
        except Exception:
            pass
    memory_store[key] = val

def cache_get(key: str):
    if use_redis:
        try:
            val = r.get(key)
            if val is not None:
                return val
        except Exception:
            pass
    return memory_store.get(key)

def cleanup_expired_pdfs():
    """
    Scans temporary PDF directory and metadata store to delete files older than 10 minutes (600 seconds).
    """
    now = time.time()
    expired_ids = []
    
    # Check tracked metadata
    for pdf_id, meta in list(pdf_metadata_store.items()):
        if now >= meta.get("expires_at", 0):
            file_path = meta.get("file_path")
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error removing expired PDF {file_path}: {e}")
            expired_ids.append(pdf_id)

    for pid in expired_ids:
        pdf_metadata_store.pop(pid, None)

    # Secondary scan of temp_pdfs directory for any un-tracked file older than 10 minutes
    try:
        for fname in os.listdir(TEMP_PDF_DIR):
            if fname.endswith(".pdf"):
                fpath = os.path.join(TEMP_PDF_DIR, fname)
                mtime = os.path.getmtime(fpath)
                if (now - mtime) > 600: # Older than 10 minutes
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass
    except Exception:
        pass


@app.get("/")
def read_root():
    cleanup_expired_pdfs()
    return {"status": "ONLINE", "app": settings.APP_NAME, "env": settings.APP_ENV, "use_redis": use_redis}

@app.get("/health")
def health_check():
    return {"status": "HEALTHY", "use_redis": use_redis}


# -----------------------------------------------------------------------------
# Encounter Management API Routes (5-Screen Flow)
# -----------------------------------------------------------------------------

@app.post(f"{settings.API_PREFIX}/encounters/create")
def create_encounter(payload: dict = None):
    """
    Screen 1/2: Creates a new encounter session with doctor metadata.
    """
    encounter_id = f"ENC_{uuid.uuid4().hex[:8].upper()}"
    doctor_info = payload.get("doctor_info", {}) if payload else {}
    
    session_data = json.dumps({
        "encounter_id": encounter_id,
        "doctor_info": doctor_info,
        "status": "CREATED",
        "created_at": time.time()
    })
    
    cache_set(f"encounter:{encounter_id}:data", session_data)
    cache_set(f"encounter:{encounter_id}:status", "CREATED")

    return {
        "encounter_id": encounter_id,
        "status": "CREATED",
        "doctor_info": doctor_info
    }

@app.post(f"{settings.API_PREFIX}/encounters/transcribe-audio")
async def transcribe_audio(request: Request):
    """
    Screen 3: Receives raw audio bytes (WebM/Opus or MP4 from MediaRecorder) and returns
    the transcribed Thai text via the multi-tier ASR pipeline.
    """
    audio_bytes = await request.body()
    if not audio_bytes:
        return MultiTierASRService.transcribe_audio_result(b"").as_dict()

    mime_type = request.headers.get("content-type", "audio/webm").split(";")[0].strip()
    result = MultiTierASRService.transcribe_audio_result(audio_bytes, mime_type=mime_type)
    return result.as_dict()

def count_summary_words(summary_data: dict) -> int:
    """Counts total words/tokens in clinical summary structure for accuracy tracking."""
    text_parts = []
    if isinstance(summary_data, dict):
        text_parts.append(str(summary_data.get("diagnosis", "")))
        insts = summary_data.get("instructions") or []
        if isinstance(insts, list):
            text_parts.extend([str(i) for i in insts])
        elif isinstance(insts, str):
            text_parts.append(insts)

        for m in summary_data.get("startMeds") or []:
            text_parts.extend([str(m.get("name", "")), str(m.get("desc", "")), str(m.get("usage", ""))])
        for m in summary_data.get("stopMeds") or []:
            text_parts.extend([str(m.get("name", "")), str(m.get("desc", "")), str(m.get("warning", ""))])
        for m in summary_data.get("changeMeds") or []:
            text_parts.extend([str(m.get("name", "")), str(m.get("desc", "")), str(m.get("change", ""))])

        text_parts.append(str(summary_data.get("followUpDate", "")))

    combined = " ".join([p for p in text_parts if p]).strip()
    if not combined:
        return 0
    return len(re.findall(r'\S+', combined))


@app.post(f"{settings.API_PREFIX}/encounters/process-transcript")
def process_transcript(payload: dict):
    """
    Screen 3 -> Screen 4: Processes raw speech transcript through De-ID & LLM Adapter,
    returning structured clinical summary (diagnosis, instructions, startMeds, stopMeds, changeMeds, followUpDate).
    """
    raw_transcript = payload.get("raw_transcript", "").strip()
    doctor_info = payload.get("doctor_info", {})
    encounter_id = payload.get("encounter_id", f"ENC_{uuid.uuid4().hex[:8].upper()}")

    if not raw_transcript:
        return {
            "status": "CANNOT_EXTRACT_SAFELY",
            "clinical_extraction_status": "CANNOT_EXTRACT_SAFELY",
            "message": "ไม่มีต้นฉบับถอดเสียงที่ตรวจสอบได้ จึงไม่สร้างคำแนะนำทางคลินิก",
            "diagnosis": "",
            "instructions": [],
            "startMeds": [],
            "stopMeds": [],
            "changeMeds": [],
            "followUpDate": "",
            "llm_calculation_time_sec": 0.0,
            "llm_draft_word_count": 0
        }

    # 1. Sanitize raw transcript
    session_meta = {
        "doctor_name": f"{doctor_info.get('first_name', '')} {doctor_info.get('surname', '')}",
        "license_no": doctor_info.get("license_no", "")
    }
    sanitized_text, meta = DeIdentificationEngine.sanitize_transcript(raw_transcript, session_meta)
    if not DeIdentificationEngine.verify_zero_pii(sanitized_text, session_meta):
        return {
            "status": "CANNOT_EXTRACT_SAFELY",
            "clinical_extraction_status": "CANNOT_EXTRACT_SAFELY",
            "message": "พบข้อมูลส่วนบุคคลที่ยังไม่ถูกปกปิด จึงไม่ส่งข้อความไปยัง clinical LLM",
            "error": "พบข้อมูลส่วนบุคคลที่ยังไม่ถูกปกปิด จึงไม่ส่งข้อความไปยัง clinical LLM",
            "diagnosis": "",
            "instructions": [],
            "startMeds": [],
            "stopMeds": [],
            "changeMeds": [],
            "followUpDate": "",
            "llm_calculation_time_sec": 0.0,
            "llm_draft_word_count": 0,
        }

    # 2. Process through LLM Adapter (Gemini 2.5 Flash Lite ZDR) with time measurement
    adapter = get_llm_adapter()
    t_start = time.time()
    raw_summary = adapter.generate_clinical_summary(sanitized_text)
    llm_calc_time_sec = round(time.time() - t_start, 2)

    # 3. Enforce source evidence before rehydrating any local metadata.
    grounded_summary = ground_summary_to_transcript(raw_summary, sanitized_text)
    rehydrated = DeIdentificationEngine.rehydrate_summary(grounded_summary, meta)

    patient_view = rehydrated.get("patient_view", {})
    medication_box = rehydrated.get("medication_box", {})

    raw_diag = (patient_view.get("diagnosis") or "").strip()
    invalid_keywords = ["ไม่ระบุ", "ไม่มี", "ไม่พบข้อมูล", "ไม่พบคำวินิจฉัย", "ไม่พบข้อวินิจฉัย", "ไม่ระบุข้อวินิจฉัย", "ไม่พบการวินิจฉัย", "no diagnosis", "not specified"]
    is_invalid_diag = not raw_diag or raw_diag.lower() in ["-", "n/a"] or any(kw in raw_diag.lower() for kw in invalid_keywords)
    diagnosis = "" if is_invalid_diag else raw_diag
    # Never fill missing clinical facts with generic advice. Missing means the
    # transcript did not support that fact and the doctor must review it.
    instructions = patient_view.get("key_instructions") or []

    start_meds = []
    for m in medication_box.get("start", []):
        if not isinstance(m, dict) or not (m.get("name") or "").strip():
            continue
        start_meds.append({
            "name": m.get("name", ""),
            "desc": m.get("appearance", ""),
            "usage": m.get("how_to_take", "")
        })

    stop_meds = []
    for m in medication_box.get("stop", []):
        if not isinstance(m, dict) or not (m.get("name") or "").strip():
            continue
        stop_meds.append({
            "name": m.get("name", ""),
            "desc": m.get("appearance", ""),
            "warning": f"⚠️ {m.get('action', '')} ({m.get('reason', '')})"
        })

    change_meds = []
    for m in medication_box.get("change", []):
        if not isinstance(m, dict) or not (m.get("name") or "").strip():
            continue
        change_meds.append({
            "name": m.get("name", ""),
            "desc": m.get("appearance", ""),
            "change": m.get("new_instruction", "")
        })

    follow_up = patient_view.get("follow_up", {}).get("date") or patient_view.get("follow_up", {}).get("follow_up_date_thai") or ""

    draft_summary_dict = {
        "diagnosis": diagnosis,
        "instructions": instructions,
        "startMeds": start_meds,
        "stopMeds": stop_meds,
        "changeMeds": change_meds,
        "followUpDate": follow_up
    }
    llm_draft_words = count_summary_words(draft_summary_dict)

    has_grounded_facts = any([diagnosis, instructions, start_meds, stop_meds, change_meds, follow_up])
    response_payload = {
        "status": "SUCCESS" if has_grounded_facts else "CANNOT_EXTRACT_SAFELY",
        "clinical_extraction_status": "GROUNDED" if has_grounded_facts else "CANNOT_EXTRACT_SAFELY",
        "message": "" if has_grounded_facts else "ไม่พบข้อเท็จจริงทางคลินิกที่มีหลักฐานตรงกับต้นฉบับ จึงเว้นช่องว่างทั้งหมดเพื่อให้แพทย์ตรวจสอบ",
        "canonical_transcript": raw_transcript,
        "diagnosis": diagnosis,
        "instructions": instructions,
        "startMeds": start_meds,
        "stopMeds": stop_meds,
        "changeMeds": change_meds,
        "followUpDate": follow_up,
        "llm_calculation_time_sec": llm_calc_time_sec,
        "llm_draft_word_count": llm_draft_words
    }

    # Append log entry (Syncs to Google Drive)
    log_entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(),
        "encounter_id": encounter_id,
        "doctor_info": doctor_info,
        "llm_config": {
            "provider": settings.DEFAULT_LLM_PROVIDER,
            "model": settings.OPENROUTER_MODEL if settings.DEFAULT_LLM_PROVIDER == "openrouter" else settings.GEMINI_MODEL
        },
        "raw_transcript": raw_transcript,
        "sanitized_transcript": sanitized_text,
        "deid_metadata": meta,
        "clinical_summary": response_payload
    }
    append_encounter_log(log_entry)

    return response_payload

@app.get(f"{settings.API_PREFIX}/encounters/export-logs")
def export_encounter_logs():
    """Download collected raw transcript & clinical LLM summary log dataset."""
    if not os.path.exists(LOG_FILE_PATH):
        raise HTTPException(status_code=404, detail="No encounter logs found.")
    return FileResponse(
        path=LOG_FILE_PATH,
        media_type="application/x-ndjson",
        filename=f"encounter_logs_{int(time.time())}.jsonl"
    )

# -----------------------------------------------------------------------------
# Telemetry & User Satisfaction (CSAT/NPS/SUS) Evaluation Endpoints
# -----------------------------------------------------------------------------

@app.post(f"{settings.API_PREFIX}/telemetry/record")
def record_telemetry_evaluation(payload: dict):
    """
    Records a Doctor or Patient/Caregiver evaluation survey response,
    including CSAT %, NPS, SUS scores, and qualitative feedback.
    """
    record = TelemetryService.record_evaluation(payload)
    return {"status": "SUCCESS", "record_id": record["id"], "timestamp": record["timestamp"]}

@app.get(f"{settings.API_PREFIX}/telemetry/summary")
def get_telemetry_satisfaction_summary():
    """
    Returns aggregated Doctor & Patient satisfaction metrics (CSAT %, NPS, avg ratings).
    """
    return TelemetryService.calculate_satisfaction_summary()

@app.get(f"{settings.API_PREFIX}/telemetry/export")
def export_telemetry_evaluations():
    """Download raw JSONL telemetry dataset containing Doctor & Patient satisfaction metrics."""
    if not os.path.exists(TELEMETRY_LOG_PATH):
        raise HTTPException(status_code=404, detail="No telemetry evaluation logs found yet.")
    return FileResponse(
        path=TELEMETRY_LOG_PATH,
        media_type="application/x-ndjson",
        filename=f"telemetry_evaluations_{int(time.time())}.jsonl"
    )

@app.get(f"{settings.API_PREFIX}/encounters/{{encounter_id}}")
def get_encounter(encounter_id: str):
    """
    Fetches current encounter status & draft summary.
    """
    cleanup_expired_pdfs()
    draft = cache_get(f"draft_summary:{encounter_id}")
    status_str = cache_get(f"encounter:{encounter_id}:status") or "CREATED"
    session_str = cache_get(f"encounter:{encounter_id}:data")

    return {
        "encounter_id": encounter_id,
        "status": status_str,
        "session_data": json.loads(session_str) if session_str else None,
        "draft_summary": json.loads(draft) if draft else None
    }


# -----------------------------------------------------------------------------
# Screen 4 -> Screen 5: PDF Generation & 10-Minute Temporary Storage Endpoints
# -----------------------------------------------------------------------------

@app.post(f"{settings.API_PREFIX}/encounters/{{encounter_id}}/export-pdf")
def export_encounter_pdf(encounter_id: str, payload: dict):
    """
    Screen 4: Doctor confirms clinical note. Generates a patient summary PDF sheet.
    The PDF file is saved temporarily for 10 minutes and automatically purged afterwards.
    """
    cleanup_expired_pdfs()
    
    doctor_info = payload.get("doctor_info", {
        "first_name": "หมอ",
        "surname": "ผู้ตรวจ",
        "license_no": "-"
    })
    summary_data = payload.get("summary_data", payload)
    telemetry_data = payload.get("telemetry", {})

    # Record background telemetry automatically
    if telemetry_data:
        TelemetryService.record_evaluation({
            "role": "SYSTEM_BACKGROUND_TELEMETRY",
            "encounter_id": encounter_id,
            "doctor_license": doctor_info.get("license_no", "N/A"),
            "time_to_clinical_llm_sec": telemetry_data.get("time_to_clinical_llm_sec", 0.0),
            "time_llm_to_final_doctor_edit_sec": telemetry_data.get("time_llm_to_final_doctor_edit_sec", 0.0),
            "manual_edit_count": telemetry_data.get("manual_edit_count", 0),
            "llm_draft_word_count": telemetry_data.get("llm_draft_word_count", 0),
            "final_doctor_word_count": telemetry_data.get("final_doctor_word_count", 0),
            "word_count_diff": telemetry_data.get("word_count_diff", 0)
        })

    pdf_result = PDFService.generate_patient_summary_pdf(
        encounter_id=encounter_id,
        doctor_info=doctor_info,
        summary_data=summary_data,
        output_dir=TEMP_PDF_DIR
    )

    pdf_id = pdf_result["pdf_id"]
    file_path = pdf_result["file_path"]
    expires_at = pdf_result["expires_at"]

    # Save to active PDF tracking store
    pdf_metadata_store[pdf_id] = {
        "encounter_id": encounter_id,
        "file_path": file_path,
        "created_at": pdf_result["created_at"],
        "expires_at": expires_at
    }

    cache_set(f"encounter:{encounter_id}:status", "PDF_GENERATED")
    cache_set(f"encounter:{encounter_id}:pdf_id", pdf_id)
    cache_set(f"draft_summary:{encounter_id}", json.dumps(summary_data))

    base_url = getattr(settings, "PUBLIC_BASE_URL", "") or os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if not base_url:
        base_url = f"http://localhost:8080"
    download_url = f"{base_url}{settings.API_PREFIX}/pdf/{pdf_id}/download"

    # Append log entry for final doctor-edited summary & PDF creation (Auto-syncs to Google Drive)
    pdf_log_entry = {
        "event": "PDF_CREATED",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(),
        "encounter_id": encounter_id,
        "doctor_info": doctor_info,
        "clinical_summary": summary_data,
        "pdf_id": pdf_id,
        "telemetry": telemetry_data
    }
    append_encounter_log(pdf_log_entry)

    return {
        "status": "PDF_CREATED",
        "encounter_id": encounter_id,
        "pdf_id": pdf_id,
        "download_url": download_url,
        "created_at": pdf_result["created_at"],
        "expires_at": expires_at,
        "ttl_seconds": 600
    }

@app.get(f"{settings.API_PREFIX}/pdf/{{pdf_id}}/download")
def download_pdf(pdf_id: str):
    """
    Screen 5 / Patient QR Scanner: Downloads generated PDF.
    Enforces 10-minute maximum lifespan (returns 410 Gone if expired).
    """
    cleanup_expired_pdfs()

    meta = pdf_metadata_store.get(pdf_id)
    file_path = os.path.join(TEMP_PDF_DIR, f"{pdf_id}.pdf")

    if not meta and not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="เอกสาร PDF นี้ไม่มีอยู่ในระบบหรือถูกลบออกไปแล้วตามนโยบาย PDPA (PDF not found)"
        )

    # Check 10-minute expiry time
    if meta:
        if time.time() >= meta["expires_at"]:
            cleanup_expired_pdfs()
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="เอกสาร PDF นี้หมดอายุและถูกลบจากเซิร์ฟเวอร์เรียบร้อยแล้ว (expired after 10 mins)"
            )
    else:
        # Check mtime fallback
        if os.path.exists(file_path):
            if (time.time() - os.path.getmtime(file_path)) > 600:
                os.remove(file_path)
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="เอกสาร PDF นี้หมดอายุและถูกลบจากเซิร์ฟเวอร์เรียบร้อยแล้ว (expired after 10 mins)"
                )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=f"MorBok_Advice_{pdf_id}.pdf"
    )


# -----------------------------------------------------------------------------
# Ephemeral Audio Streaming WebSocket Endpoint
# -----------------------------------------------------------------------------

@app.websocket("/ws/audio-stream/{encounter_id}")
async def audio_stream_endpoint(websocket: WebSocket, encounter_id: str):
    """Consume live chunks for connection health only.

    Final ASR is performed exactly once by ``POST /transcribe-audio`` after the
    recorder stops. Processing on WebSocket disconnect used to create a second,
    different transcript and LLM draft.
    """
    await websocket.accept()

    try:
        while True:
            await websocket.receive_bytes()
    except WebSocketDisconnect:
        # The browser uploads the complete recording through the REST endpoint.
        # Do not infer a clinical result from a socket lifecycle event.
        return
