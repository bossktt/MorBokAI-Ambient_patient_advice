# MorBok AI (หมอบอก) — Ambient Care Assistant & Patient Advice Generator

> **Clinical AI Platform for Thailand Emergency Department (ED) Discharges & Ambient Consultation Summarization.**
> MorBok AI transcribes ambient physician consultations, extracts structured clinical information, and generates plain-language **After-Visit Summaries (AVS)** and **Medication Reconciliation Tables (START 🟢, STOP 🔴, CHANGE 🟡)** at a Grade 5 (ป.5) reading level.

---

## 🌟 Key Architecture & Highlights

### 1. 🎙️ Multi-Tiered Speech-to-Text (ASR) Pipeline
MorBok AI implements a 4-step failover speech recognition pipeline designed for high-accuracy Thai clinical speech:
1. **Step 1 (Primary)**: **OpenRouter ASR** (`openai/whisper-large-v3-turbo` → `fish-audio/transcribe-1` → `nvidia/parakeet-tdt-0.6b-v3`)
2. **Step 2 (Secondary)**: **AssemblyAI Speech-to-Text API** (`https://api.assemblyai.com/v2` with `language_code="th"`)
3. **Step 3 (Tertiary)**: **Google Speech-to-Text** (`th-TH` via `gcp-key.json`)
4. **Step 4 (Offline)**: Offline Thai audio transcript fallback for local offline testing.

### 2. 🏥 Clinical LLM Adapters & Prompt Standard
MorBok AI supports pluggable LLM backends configured via `DEFAULT_LLM_PROVIDER`:
- **OpenRouter (`google/gemini-2.5-flash`)**: High-speed, multimodal reasoning with Google provider routing.
- **Typhoon 1.5 Medical**: Thai Native Medical LLM (by SCB 10X / Opn).
- **Google Gemini 2.5 Flash Lite**: Direct Google AI Studio API key.
- **Azure OpenAI (GPT-4o)**: Enterprise Zero Data Retention (ZDR) HIPAA-compliant adapter.
- **Local Ollama (`llama3` / `typhoon-7b`)**: 100% private, on-premise hospital network deployment.

All adapters execute the **Ambient PVS Clinical Summarizer System Prompt**, enforcing Grade 5 reading levels, emergency red flags, and strict zero-hallucination rules.

### 3. 🖥️ 5-Screen Workflow
- **Screen 1 (`/`)**: Doctor License Login & QR Pairing.
- **Screen 2 (`/doctor/pdpa`)**: Patient PDPA Consent & Privacy Agreement.
- **Screen 2b (`/doctor/encounter/new`)**: New Case Selection & Medical Record Initialization.
- **Screen 3 (`/doctor/encounter/[id]/scribe`)**: Real-time Ambient Voice Recording & Live Speech Waveform visualization via WebSocket.
- **Screen 4 (`/doctor/encounter/[id]/review`)**: WYSIWYG Doctor Review & Editable Medication Reconciliation Matrix.
- **Screen 5 (`/doctor/encounter/[id]/pdf`)**: PDF Export Generation (10-minute temporary auto-purge storage) & Patient LINE Flex QR Code.

---

## 📂 Reorganized Project Hierarchy

```
AI-advice/
├── backend/                  # FastAPI Python backend (Uvicorn, PyThainLP, ReportLab PDF)
│   ├── app/                  # FastAPI application modules (main, core, services)
│   ├── pythainlp_data/       # Offline Thai tokenizers and dictionaries
│   └── test_all_models.py    # Multi-LLM test evaluation suite
├── frontend/                 # Next.js 15 App Router Doctor & Patient Portal (React, TypeScript, TailwindCSS)
│   └── src/app/              # Next.js application routes
├── docs/                     # Documentation & Research Knowledge Base
│   ├── specs/                # Technical specifications, PRDs, system architecture & wireframes
│   └── research/             # User research forms, questionnaires, CSV datasets & Excel scripts
├── schemas/                  # Shared JSON, Python & TypeScript schema definitions
│   ├── schema_encounter_draft.json
│   ├── schema_types.py
│   └── schema_types.ts
├── assets/                   # Static design assets & mockups
│   └── design/               # Wireframe archives & design bundles
├── scripts/                  # Helper scripts (model downloads)
├── .github/workflows/        # GitHub Actions CI/CD Pipeline (ci-cd.yml)
├── docker-compose.yml        # Multi-container orchestration (FastAPI, Next.js, Redis, Postgres, Whisper)
├── .env                      # Application environment variables
├── .env.example              # Environment variables template
├── requirements.txt          # Python backend dependencies
└── package.json              # Node.js workspace configuration
```

---

## 🚀 Quickstart Guide

### Prerequisites
- Node.js >= 20.x
- Python >= 3.11
- Docker & Docker Compose (optional for full stack containerization)

### 1. Local Backend Setup (FastAPI)
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt

# Run backend development server
PYTHONPATH=. venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### 2. Local Frontend Setup (Next.js)
```bash
cd frontend
npm install

# Run frontend development server
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### 3. Docker Compose Orchestration
```bash
docker compose up --build -d
```

### 4. Running CI/CD Pipeline Verification Locally
```bash
# 1. Test Backend Architecture & LLM Adapters
cd backend && PYTHONPATH=. venv/bin/python test_all_models.py

# 2. Test Frontend TypeScript & Production Build
cd ../frontend && npx tsc --noEmit && npm run build

# 3. Validate Docker Specification
cd .. && docker compose config
```

---

## 📄 License & Confidentiality
Developed for the **AI in Healthcare Project**. All rights reserved.
