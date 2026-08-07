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
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import redis

from app.core.config import settings
from app.services.deid_engine import DeIdentificationEngine
from app.services.llm_adapter import get_llm_adapter
from app.services.asr_service import MultiTierASRService
from app.services.pdf_service import PDFService

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
        return {"status": "EMPTY", "transcript": ""}

    mime_type = request.headers.get("content-type", "audio/webm").split(";")[0].strip()
    transcript = MultiTierASRService.transcribe_audio_bytes(audio_bytes, mime_type=mime_type)
    return {
        "status": "SUCCESS" if transcript else "EMPTY",
        "transcript": transcript
    }

@app.post(f"{settings.API_PREFIX}/encounters/process-transcript")
def process_transcript(payload: dict):
    """
    Screen 3 -> Screen 4: Processes raw speech transcript through De-ID & LLM Adapter,
    returning structured clinical summary (diagnosis, instructions, startMeds, stopMeds, changeMeds, followUpDate).
    """
    raw_transcript = payload.get("raw_transcript", "").strip()
    doctor_info = payload.get("doctor_info", {})

    if not raw_transcript:
        return {
            "status": "EMPTY",
            "diagnosis": "ไม่พบข้อมูลการถอดเสียง",
            "instructions": ["กรุณาบันทึกเสียงบทสนทนาในห้องตรวจอีกครั้ง"],
            "startMeds": [],
            "stopMeds": [],
            "changeMeds": [],
            "followUpDate": "ตามนัดหมายแพทย์"
        }

    # 1. Sanitize raw transcript
    session_meta = {
        "doctor_name": f"{doctor_info.get('first_name', '')} {doctor_info.get('surname', '')}",
        "license_no": doctor_info.get("license_no", "")
    }
    sanitized_text, meta = DeIdentificationEngine.sanitize_transcript(raw_transcript, session_meta)

    # 2. Process through LLM Adapter (Gemini 2.5 Flash Lite ZDR)
    adapter = get_llm_adapter()
    raw_summary = adapter.generate_clinical_summary(sanitized_text)

    # 3. Rehydrate summary
    rehydrated = DeIdentificationEngine.rehydrate_summary(raw_summary, meta)

    patient_view = rehydrated.get("patient_view", {})
    caregiver_matrix = rehydrated.get("caregiver_matrix", {}).get("medication_reconciliation", {})

    raw_diag = (patient_view.get("diagnosis") or "").strip()
    invalid_diags = ["ไม่ระบุ", "ไม่มี", "ไม่พบข้อมูล", "ไม่พบคำวินิจฉัย", "ไม่พบข้อวินิจฉัย", "ไม่ระบุข้อวินิจฉัย", "-", "N/A"]
    diagnosis = "" if raw_diag in invalid_diags else raw_diag
    instructions = patient_view.get("key_instructions") or [
        "รับประทานยาตามที่เภสัชกรแนะนำให้ครบถ้วน",
        "หากมีไข้สูงติดต่อกันเกิน 3 วัน ให้กลับมาพบแพทย์เพื่อตรวจเลือดเพิ่มเติม",
        "พักผ่อนให้เพียงพอและดื่มน้ำสะอาดวันละ 8 แก้ว"
    ]

    start_meds = []
    for m in caregiver_matrix.get("start", []):
        start_meds.append({
            "name": m.get("med_name", "ยาใหม่"),
            "desc": m.get("physical_description", "ลักษณะยา"),
            "usage": f"{m.get('dosage', '')} {m.get('timing', '')} {m.get('instructions', '')}".strip()
        })

    stop_meds = []
    for m in caregiver_matrix.get("stop", []):
        stop_meds.append({
            "name": m.get("med_name", "ยาที่ต้องหยุด"),
            "desc": m.get("physical_description", "ซองเดิม"),
            "warning": f"⚠️ {m.get('discard_instruction', 'หยุดรับประทานทันที')} ({m.get('reason', '')})"
        })

    change_meds = []
    for m in caregiver_matrix.get("change", []):
        change_meds.append({
            "name": m.get("med_name", "ยาที่ปรับขนาด"),
            "desc": m.get("physical_description", "ลักษณะยา"),
            "change": m.get("change_summary") or f"{m.get('new_dosage', '')} {m.get('timing', '')}"
        })

    follow_up = patient_view.get("follow_up", {}).get("follow_up_date_thai") or "ตามนัดหมายแพทย์ (หากมีอาการไข้สูงเกิน 3 วัน ให้กลับมาตรวจเพิ่มเติม)"

    return {
        "status": "SUCCESS",
        "diagnosis": diagnosis,
        "instructions": instructions,
        "startMeds": start_meds,
        "stopMeds": stop_meds,
        "changeMeds": change_meds,
        "followUpDate": follow_up
    }

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

    base_url = getattr(settings, "PUBLIC_BASE_URL", "") or os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if not base_url:
        base_url = f"http://localhost:8080"
    download_url = f"{base_url}{settings.API_PREFIX}/pdf/{pdf_id}/download"

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
    await websocket.accept()
    audio_buffer = bytearray()

    try:
        while True:
            # Receive Opus binary audio chunk into volatile RAM
            data = await websocket.receive_bytes()
            audio_buffer.extend(data)
    except WebSocketDisconnect:
        # Transcribe audio buffer using Typhoon ASR Realtime model
        raw_speech = MultiTierASRService.transcribe_audio_bytes(bytes(audio_buffer))

        session_meta = {
            "patient_name": "ผู้ป่วย",
            "caregiver_name": "ผู้ดูแล",
            "doctor_name": "แพทย์",
            "hn": "HN-DEID",
            "phone_number": "000"
        }

        sanitized_text, meta = DeIdentificationEngine.sanitize_transcript(raw_speech, session_meta)
        is_safe = DeIdentificationEngine.verify_zero_pii(sanitized_text, session_meta)

        if is_safe:
            adapter = get_llm_adapter()
            summary_draft = adapter.generate_clinical_summary(sanitized_text)
            final_draft = DeIdentificationEngine.rehydrate_summary(summary_draft, meta)

            cache_set(f"draft_summary:{encounter_id}", json.dumps(final_draft))
            cache_set(f"encounter:{encounter_id}:status", "REVIEW")
