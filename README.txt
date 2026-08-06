===============================================================================
MorBok AI (หมอบอก) — Ambient Care Assistant & Patient Advice Generator
===============================================================================

Clinical AI Platform for Thailand Emergency Department (ED) Discharges &
Ambient Consultation Summarization.

MorBok AI transcribes ambient physician consultations, extracts structured
clinical information, and generates plain-language After-Visit Summaries (AVS)
and Medication Reconciliation Tables (START 🟢, STOP 🔴, CHANGE 🟡) at a
Grade 5 (ป.5) Thai reading level.

===============================================================================
1. SYSTEM ARCHITECTURE & HIGHLIGHTS
===============================================================================

[Multi-Tier Speech-to-Text (ASR) Pipeline]
- Live Web Speech API (Client-side): Real-time Thai speech-to-text (th-TH) in browser.
- AssemblyAI Speech-to-Text API (Backend ASR): Multi-tier audio buffer transcription.
- Synchronous Persistence Engine: Guarantees raw transcript data transfer between
  Screen 3 (Scribe) and Screen 4 (Review) via dual localStorage keys.

[Clinical LLM Adapters & Provider Routing]
- OpenRouter (google/gemini-2.5-flash) with Google Vertex Routing: High-speed,
  multimodal reasoning routed via Google Vertex AI infrastructure (OPENROUTER_PROVIDER=google-vertex).
- Google Gemini 2.5 Flash Lite: Direct Google AI Studio fallback.
- ED Fallback Summary Engine: Offline Emergency Department chief complaint pattern matcher
  covering 9 key clinical conditions (Palpitations, Chest Pain, GI/Abdominal Pain,
  Vertigo, Asthma Exacerbation, Flu/Fever, Hyperglycemia, Trauma Wounds, Acute Urticaria).

[5-Screen Workflow]
- Screen 1 (/): Physician Profile & Medical License Registration (ว.XXXXX).
- Screen 2 (/doctor/pdpa): Patient PDPA Consent & Privacy Compliance.
- Screen 2b (/doctor/encounter/new): Case Pairing & LINE OA QR Code PIN Verification.
- Screen 3 (/doctor/encounter/[id]/scribe): Real-time Ambient Voice Recording & Live Speech.
- Screen 4 (/doctor/encounter/[id]/review): WYSIWYG Doctor Review & Editable Medication Matrix.
- Screen 5 (/doctor/encounter/[id]/pdf): PDF Export Generation & Patient LINE Flex QR Code.

===============================================================================
2. PROJECT STRUCTURE
===============================================================================

AI-advice/
├── backend/                  FastAPI Python backend (Uvicorn, PyThaiNLP, ReportLab)
│   ├── app/                  Core app, services, and test suites
│   └── pythainlp_data/       Offline Thai tokenizers
├── frontend/                 Next.js 15 Doctor & Patient Portal (React, TS, Tailwind)
│   └── src/app/              5-Screen clinical workflow routes
├── docs/                     Documentation & Research Knowledge Base
│   ├── specs/                Technical specifications & architectural blueprints
│   └── research/             User research forms & datasets
├── schemas/                  Shared JSON, Python & TypeScript schema definitions
├── docker-compose.yml        Multi-container orchestration
├── render.yaml               Render Cloud Blueprint
├── .env                      Application environment configuration
├── README.md                 Markdown Documentation
└── README.txt                Plain-text Documentation

===============================================================================
3. QUICKSTART GUIDE
===============================================================================

[Backend Setup (FastAPI)]
  cd backend
  python3 -m venv venv
  source venv/bin/activate
  pip install -r ../requirements.txt
  PYTHONPATH=. venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

[Frontend Setup (Next.js)]
  cd frontend
  npm install
  npm run dev

  Open http://localhost:3000 in your browser.

[Automated Verification]
  Backend Tests: cd backend && PYTHONPATH=. ./venv/bin/pytest
  Frontend Check: cd frontend && npx tsc --noEmit && npm run build
  Docker Check:   docker compose config

===============================================================================
License & Confidentiality
Developed for the AI in Healthcare Project. All rights reserved.
===============================================================================
