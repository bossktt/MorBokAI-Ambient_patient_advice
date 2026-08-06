# MorBok AI (หมอบอก) — Ambient Care Assistant & Patient Advice Generator

> **Clinical AI Platform for Thailand Emergency Department (ED) Discharges & Ambient Consultation Summarization.**
> MorBok AI transcribes ambient physician consultations, extracts structured clinical information, and generates plain-language **After-Visit Summaries (AVS)** and **Medication Reconciliation Tables (START 🟢, STOP 🔴, CHANGE 🟡)** at a Grade 5 (ป.5) reading level.

---

## 🌟 Key Architecture & Highlights

### 1. 🎙️ Multi-Tiered Speech-to-Text (ASR) Pipeline
MorBok AI implements a failover speech recognition pipeline designed for high-accuracy Thai clinical speech:
1. **Live Web Speech API (Client-side)**: Real-time Thai speech-to-text (`th-TH`) directly in the browser with auto-reconnection.
2. **AssemblyAI Speech-to-Text API (Backend ASR)**: Multi-tier audio buffer transcription via `https://api.assemblyai.com/v2` with `language_code="th"`.
3. **Synchronous Persistence Engine**: Guarantees raw transcript data integrity when transitioning between Screen 3 (Scribe) and Screen 4 (Review) via dual `localStorage` fallback keys.

### 2. 🏥 Clinical LLM Adapters & Provider Routing
MorBok AI supports pluggable LLM backends configured via `DEFAULT_LLM_PROVIDER`, `OPENROUTER_MODEL`, and `OPENROUTER_PROVIDER`:
- **OpenRouter (`google/gemini-2.5-flash`) with Google Vertex Routing**: High-speed, multimodal reasoning routed specifically via Google Vertex AI infrastructure (`OPENROUTER_PROVIDER=google-vertex`).
- **Google Gemini 2.5 Flash Lite**: Direct Google AI Studio fallback provider.
- **ED Fallback Summary Engine**: Offline Emergency Department chief complaint pattern matcher covering 9 key clinical conditions (Palpitations, Chest Pain, GI/Abdominal Pain, Vertigo, Asthma Exacerbation, Flu/Fever, Hyperglycemia, Trauma Wounds, Acute Urticaria).

All adapters execute the **Ambient PVS Clinical Summarizer System Prompt**, enforcing Grade 5 Thai reading levels, emergency red flags, and strict zero-hallucination rules.

### 3. 🖥️ 5-Screen Clean Workflow
- **Screen 1 (`/`)**: Physician Profile & Medical License Registration (ว.XXXXX).
- **Screen 2 (`/doctor/pdpa`)**: Patient PDPA Consent & Legal Privacy Compliance.
- **Screen 2b (`/doctor/encounter/new`)**: Case Pairing & LINE OA QR Code PIN Verification.
- **Screen 3 (`/doctor/encounter/[id]/scribe`)**: Real-time Ambient Voice Recording & Live Speech Waveform visualization.
- **Screen 4 (`/doctor/encounter/[id]/review`)**: WYSIWYG Doctor Review & Editable Medication Reconciliation Matrix. Clean, distractor-free UI with streamlined medical processing indicators.
- **Screen 5 (`/doctor/encounter/[id]/pdf`)**: PDF Export Generation (10-minute temporary auto-purge storage) & Patient LINE Flex QR Code.

---

## 📂 Reorganized Project Hierarchy

```
AI-advice/
├── backend/                  # FastAPI Python backend (Uvicorn, PyThaiNLP, ReportLab PDF)
│   ├── app/                  # FastAPI application modules (main, core, services)
│   │   ├── core/             # Application settings & environment configuration
│   │   ├── services/         # Clinical LLM Adapters, De-ID Engine, ASR Pipeline
│   │   └── tests/            # Automated pytest test suites
│   ├── pythainlp_data/       # Offline Thai tokenizers and dictionaries
│   └── test_all_models.py    # Multi-LLM test evaluation suite
├── frontend/                 # Next.js 15 App Router Doctor & Patient Portal (React, TypeScript, TailwindCSS)
│   └── src/app/              # Next.js application routes (5-screen clinical flow)
├── docs/                     # Documentation & Research Knowledge Base
│   ├── specs/                # Technical specifications, PRDs, system architecture & wireframes
│   └── research/             # User research forms, questionnaires, CSV datasets & Excel scripts
├── schemas/                  # Shared JSON, Python & TypeScript schema definitions
│   ├── schema_encounter_draft.json
│   ├── schema_types.py
│   └── schema_types.ts
├── assets/                   # Static design assets & mockups
├── docker-compose.yml        # Multi-container orchestration (FastAPI, Next.js, Redis, Postgres)
├── render.yaml               # Render Cloud Deployment Blueprint
├── .env                      # Application environment variables
├── .env.example              # Environment variables template
├── README.md                 # Markdown Documentation
├── README.txt                # Plain-text Documentation
└── requirements.txt          # Python backend dependencies
```

---

## ⚙️ Environment Configuration

Set up `.env` based on `.env.example`:

```env
# Clinical LLM Adapter Configuration
DEFAULT_LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=google/gemini-2.5-flash
OPENROUTER_PROVIDER=google-vertex

# Gemini Fallback Configuration
GEMINI_MODEL=gemini-1.5-flash
GEMINI_API_KEY=AQ.Ab8RN...

# AssemblyAI ASR
ASSEMBLYAI_API_KEY=ef84aec...
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
python3 -m venv venv
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

### 4. Automated Testing & Verification
```bash
# 1. Test Backend Architecture & Clinical LLM Adapters
cd backend && PYTHONPATH=. ./venv/bin/pytest

# 2. Test Frontend TypeScript & Production Build
cd ../frontend && npx tsc --noEmit && npm run build

# 3. Validate Docker Specification
cd .. && docker compose config
```

---

## 📄 License & Confidentiality
Developed for the **AI in Healthcare Project**. All rights reserved.
