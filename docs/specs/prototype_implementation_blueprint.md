# Prototype Implementation Blueprint: Layer-by-Layer Technical Setup

---

## 1. Directory Structure Blueprint

To prepare for building a real, delicate prototype, organize your project workspace into a modular mono-repo (or microservices repo):

```text
ai-advice-pvs/
├── docker-compose.yml           # Master container orchestrator
├── .env.example                 # Environment configuration template
├── frontend/                    # Layer 1: Next.js 15 Doctor Approval Portal & Scribe
│   ├── src/
│   │   ├── app/                 # Next.js App Router (pages & API routes)
│   │   ├── components/          # shadcn/ui & medical components
│   │   ├── hooks/               # useAudioRecorder, useWebSocket
│   │   └── store/               # Zustand state management
│   ├── package.json
│   └── tsconfig.json
├── backend/                     # Layer 2 & 3: FastAPI Gateway & Celery Workers
│   ├── app/
│   │   ├── api/                 # REST & WebSocket endpoints
│   │   ├── core/                # Config, Security, Keycloak OIDC
│   │   ├── db/                  # SQLAlchemy models & Alembic migrations
│   │   └── schemas/             # Pydantic v2 & FHIR R4 schemas
│   ├── requirements.txt
│   └── Dockerfile
├── ai_engine/                   # Layer 4: AI & Privacy Enclave
│   ├── asr/                     # faster-whisper & audio buffer manager
│   ├── deid/                    # PyThaiNLP + Presidio + Verification Gate
│   └── llm/                     # LLMAdapter (Typhoon / Gemini / GPT-4o)
└── delivery/                    # Layer 5: LINE OA & PDF Engine
    ├── line/                    # LINE Messaging API & LIFF SDK integration
    ├── pdf/                     # Jinja2 HTML templates & Playwright streamer
    └── templates/               # Thai Sarabun PDF HTML layout
```

---

## 💻 Layer 1: Frontend Scribe & Doctor Portal (`/frontend`)

### 📦 Package Dependencies (`package.json`)
```json
{
  "name": "pvs-doctor-portal",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "15.0.0",
    "react": "19.0.0",
    "react-dom": "19.0.0",
    "typescript": "^5.4.0",
    "tailwindcss": "^3.4.0",
    "@radix-ui/react-dialog": "^1.0.5",
    "@radix-ui/react-slot": "^1.0.2",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0",
    "lucide-react": "^0.350.0",
    "zustand": "^4.5.0",
    "react-hook-form": "^7.51.0",
    "zod": "^3.22.0",
    "@hookform/resolvers": "^3.3.0",
    "recharts": "^2.12.0",
    "qrcode.react": "^3.1.0"
  }
}
```

### 🎙️ Core Audio Recorder Hook (`src/hooks/useAudioRecorder.ts`)
```typescript
import { useState, useRef } from 'react';

export const useAudioRecorder = (encounterId: string) => {
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  const startRecording = async () => {
    // 1. Establish WebSocket Connection to FastAPI Audio Stream
    const wsUrl = `wss://${window.location.host}/ws/audio-stream/${encounterId}`;
    socketRef.current = new WebSocket(wsUrl);

    socketRef.current.onopen = async () => {
      // 2. Request Mic Access (Opus 16kHz)
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });

      // 3. Stream 3-second audio chunks over WebSocket
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0 && socketRef.current?.readyState === WebSocket.OPEN) {
          socketRef.current.send(event.data);
        }
      };

      mediaRecorderRef.current.start(3000); // 3-second slices
      setIsRecording(true);
    };
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    socketRef.current?.close();
    setIsRecording(false);
  };

  return { isRecording, startRecording, stopRecording };
};
```

---

## ⚡ Layer 2: Backend API Gateway (`/backend`)

### 📦 Python Dependencies (`requirements.txt`)
```text
fastapi>=0.110.0
uvicorn[standard]>=0.28.0
pydantic>=2.6.0
pydantic-settings>=2.2.0
sqlalchemy>=2.0.28
alembic>=1.13.1
asyncpg>=0.29.0
redis>=5.0.3
celery>=5.3.6
python-multipart>=0.0.9
requests>=2.31.0
websockets>=12.0
```

### 🎙️ Ephemeral WebSocket Audio Ingestion Endpoint (`app/api/ws_audio.py`)
```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis

router = APIRouter()
r = redis.Redis(host='redis', port=6379, db=0)

@router.websocket("/ws/audio-stream/{encounter_id}")
async def audio_stream_endpoint(websocket: WebSocket, encounter_id: str):
    await websocket.accept()
    buffer_key = f"raw_audio_buffer:{encounter_id}"
    
    try:
        while True:
            # Receive Opus audio bytes into volatile memory (RAM)
            data = await websocket.receive_bytes()
            
            # Append audio bytes to ephemeral Redis stream buffer (TTL: 1 hour)
            r.rpush(buffer_key, data)
            r.expire(buffer_key, 3600)
            
    except WebSocketDisconnect:
        # Trigger Celery processing task upon recording finish
        from app.workers.celery_tasks import process_consultation_task
        process_consultation_task.delay(encounter_id)
```

---

## ⚙️ Layer 3: Async Task Queue & Worker Engine (`/workers`)

### 🔄 Celery Processing Task (`app/workers/celery_tasks.py`)
```python
from celery import Celery
import redis
import json

celery_app = Celery("pvs_tasks", broker="redis://redis:6379/0", backend="redis://redis:6379/0")
r = redis.Redis(host='redis', port=6379, db=0)

@celery_app.task(name="process_consultation_task")
def process_consultation_task(encounter_id: str):
    # 1. Fetch raw Opus audio frames from RAM buffer
    buffer_key = f"raw_audio_buffer:{encounter_id}"
    audio_chunks = r.lrange(buffer_key, 0, -1)
    
    # 2. Transcribe via ASR (faster-whisper)
    from ai_engine.asr.whisper_transcriber import transcribe_audio_chunks
    raw_transcript = transcribe_audio_chunks(audio_chunks)
    
    # 3. INSTANT MEMORY PURGE: Delete raw audio bytes from RAM
    r.delete(buffer_key)
    
    # 4. De-Identify PII locally
    from ai_engine.deid.sanitizer import sanitize_transcript
    sanitized_transcript, metadata = sanitize_transcript(raw_transcript, encounter_id)
    
    # 5. Internal Verification Gate (Assert Zero PII)
    from ai_engine.deid.verification_gate import verify_zero_pii
    assert verify_zero_pii(sanitized_transcript), "🚨 Security Gate Error: PII detected!"
    
    # 6. Clinical LLM Dual Summary Generation
    from ai_engine.llm.llm_adapter import generate_dual_summary
    draft_summary_json = generate_dual_summary(sanitized_transcript)
    
    # 7. Re-hydrate local PII metadata in memory
    from ai_engine.deid.sanitizer import rehydrate_summary
    final_draft = rehydrate_summary(draft_summary_json, metadata)
    
    # 8. Save final draft for Doctor Review
    r.set(f"draft_summary:{encounter_id}", json.dumps(final_draft))
    return {"status": "COMPLETED", "encounter_id": encounter_id}
```

---

## 🧠 Layer 4: AI Engine & Privacy Enclave (`/ai_engine`)

### 🗣️ ASR Ingestor (`ai_engine/asr/whisper_transcriber.py`)
```python
from faster_whisper import WhisperModel
import io

# Load model locally on CUDA GPU
model = WhisperModel("large-v3-turbo", device="cuda", compute_type="float16")

def transcribe_audio_chunks(audio_chunks: list) -> str:
    # Combine chunks in RAM memory stream
    audio_stream = io.BytesIO(b"".join(audio_chunks))
    
    segments, _ = model.transcribe(audio_stream, language="th")
    full_transcript = " ".join([segment.text for segment in segments])
    
    return full_transcript
```

### 🛡️ De-ID Engine & Verification Gate (`ai_engine/deid/sanitizer.py`)
```python
import re
from pythainlp.tag.named_entity import ThaiNameTagger

ner_tagger = ThaiNameTagger()

def sanitize_transcript(raw_text: str, encounter_id: str) -> tuple[str, dict]:
    sanitized = raw_text
    
    # 1. Regex PII Stripping (Citizen ID & Phone)
    sanitized = re.sub(r'\b\d{13}\b|\b\d{1}-\d{4}-\d{5}-\d{2}-\d{1}\b', '[CITIZEN_ID]', sanitized)
    sanitized = re.sub(r'\b0\d{1,2}[- ]?\d{3,4}[- ]?\d{4}\b', '[PHONE_NUMBER]', sanitized)
    sanitized = re.sub(r'(?i)\b(HN|hn)\s*:?\s*[\d-]+\b', '[HOSPITAL_NUMBER]', sanitized)
    
    # 2. PyThaiNLP Name Tagging
    tagged = ner_tagger.get_ner(sanitized)
    metadata = {"extracted_names": []}
    
    for word, tag in tagged:
        if tag == "PERSON":
            metadata["extracted_names"].append(word)
            sanitized = sanitized.replace(word, "[PERSON_NAME]")
            
    return sanitized, metadata

def verify_zero_pii(text: str) -> bool:
    # Verification Gate: Return False if any unmasked 13-digit ID or 10-digit Phone remains
    if re.search(r'\b\d{13}\b|\b0\d{9}\b', text):
        return False
    return True
```

### 🧠 LLM Adapter Pattern (`ai_engine/llm/llm_adapter.py`)
```python
from abc import ABC, abstractmethod
import requests

class BaseLLMAdapter(ABC):
    @abstractmethod
    def generate_summary(self, sanitized_prompt: str) -> dict:
        pass

class TyphoonMedicalAdapter(BaseLLMAdapter):
    def generate_summary(self, sanitized_prompt: str) -> dict:
        # Call Typhoon Medical LLM API with strict JSON format
        response = requests.post(
            "https://api.opn.ai/v1/chat/completions",
            json={
                "model": "typhoon-1.5-medical",
                "messages": [
                    {"role": "system", "content": "You are a clinical summarizer. Output strictly JSON."},
                    {"role": "user", "content": sanitized_prompt}
                ],
                "response_format": {"type": "json_object"}
            }
        )
        return response.json()["choices"][0]["message"]["content"]
```

---

## 📄 Layer 5: Delivery & Playwright PDF Engine (`/delivery`)

### 📄 HTML-to-PDF Streamer (`delivery/pdf/pdf_generator.py`)
```python
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright

async def generate_pdf_stream(summary_data: dict) -> bytes:
    # 1. Render Jinja2 Template with Thai Sarabun Google Font
    env = Environment(loader=FileSystemLoader("delivery/templates"))
    template = env.get_template("pvs_pdf_template.html")
    html_content = template.render(data=summary_data)
    
    # 2. Compile PDF via Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html_content, wait_until="networkidle")
        pdf_bytes = await page.pdf(format="A4", print_background=True)
        await browser.close()
        
    return pdf_bytes
```

---

## 🐳 Layer 6: Orchestration & Docker Setup (`docker-compose.yml`)

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: pvs_db
      POSTGRES_USER: pvs_admin
      POSTGRES_PASSWORD: SecretPassword123
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  faster-whisper-asr:
    image: fedirz/faster-whisper-server:latest-cuda
    environment:
      - WHISPER_MODEL=large-v3-turbo
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    ports:
      - "8000:8000"

  fastapi-backend:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql+asyncpg://pvs_admin:SecretPassword123@postgres:5432/pvs_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  celery-worker:
    build: ./backend
    command: celery -A app.workers.celery_tasks worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://pvs_admin:SecretPassword123@postgres:5432/pvs_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
      - faster-whisper-asr

  nextjs-frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_HOST=localhost:8080

volumes:
  pgdata:
```

---

## 🚀 Execution Checklist to Launch Prototype

1. **Clone repository structure** as specified in directory blueprint.
2. **Run `docker-compose up -d`** to launch Postgres, Redis, `faster-whisper`, FastAPI, Celery, and Next.js.
3. **Access Scribe Web Portal** at `http://localhost:3000`.
4. **Test audio stream & 15-second doctor sign-off flow**.
