# Session Pairing State Machine & Expiration Logic Specification

---

## 🎯 1. Overview & Objectives

This specification defines the complete state machine, API sequence flow, and Redis data key lifecycle for in-clinic **Patient / Caregiver LINE Pairing**.

### 🌟 Design Goals
1. **Zero-PIN Pairing**: Scanning a dynamic QR code on LINE links `LINE_USER_ID` to `ENCOUNTER_ID` in **<2 seconds**.
2. **Multi-Recipient Support**: Allows both the Patient and Caregiver (up to 2 LINE accounts) to scan the same QR code and receive the summary simultaneously.
3. **Automated Expiration**: Enforces strict TTL (Time-To-Live) expirations on pairing tokens, audio buffers, and temporary draft keys in Redis.

---

## 🔄 2. State Machine Diagram

```mermaid
stateDiagram-v2
    [*] --> STATE_UNPAIRED: Doctor Opens Visit (/doctor/encounter/new)
    
    state STATE_UNPAIRED {
        [*] --> GenerateQR: System Creates Pair Token (TTL: 15 mins)
        GenerateQR --> WaitingScan: Doctor Displays QR Code
    }

    WaitingScan --> STATE_PAIRED: Patient/Caregiver Scans QR Code on LINE
    WaitingScan --> STATE_EXPIRED: 15-Minute TTL Timeout Reached

    STATE_EXPIRED --> GenerateQR: Doctor Taps "Refresh QR Code"

    state STATE_PAIRED {
        [*] --> LineConnected: Store LINE_USER_ID in Redis
        LineConnected --> ReadyToScribe: WebSocket Pushes "🟢 Connected" to Doctor UI
    }

    ReadyToScribe --> STATE_SCRIBE_ACTIVE: Doctor Taps "Start Ambient Scribe"

    state STATE_SCRIBE_ACTIVE {
        [*] --> AudioStreaming: Opus Audio Streams to RAM Buffer
        AudioStreaming --> AudioStopped: Doctor Taps "Stop & Generate"
    }

    AudioStopped --> STATE_PROCESSING: Celery Async Job Dispatched

    state STATE_PROCESSING {
        [*] --> ASR_DeID_LLM: ASR ➔ De-ID ➔ Verification ➔ LLM
        ASR_DeID_LLM --> DraftReady: Save Draft JSON to Redis
    }

    DraftReady --> STATE_REVIEW: Doctor UI Hydrates WYSIWYG Review Screen

    state STATE_REVIEW {
        [*] --> DoctorEditing: In-Line Edits (If Needed)
        DoctorEditing --> Approved: Doctor Taps "Approve & Send to LINE"
    }

    Approved --> STATE_DELIVERED: Webhook Pushes LINE Flex Cards & Enables LIFF Gate
    STATE_DELIVERED --> [*]: Process Completed
```

---

## 📡 3. Sequence Flow: In-Clinic Pairing to Delivery

```mermaid
sequenceDiagram
    autonumber
    actor Doctor
    participant UI as Doctor Portal (Next.js)
    participant API as FastAPI Gateway
    participant Redis as Redis Store (RAM)
    actor Patient as Patient / Caregiver LINE
    participant LINE as LINE Messaging Platform

    rect rgb(240, 248, 255)
        note over Doctor, Redis: 1. Session Setup & QR Generation
        Doctor->>UI: Open New Encounter (/doctor/encounter/new)
        UI->>API: POST /api/v1/encounters/create
        API->>Redis: SET pairing_token:PAIR_9823 -> {encounter_id: "ENC_9823", status: "UNPAIRED"} EX 900
        API-->>UI: Return Pairing QR Code URL (https://line.me/R/ti/p/@bot?start=PAIR_9823)
        UI-->>Doctor: Display Dynamic QR Code
    end

    rect rgb(255, 250, 240)
        note over Patient, Redis: 2. QR Scanning & Automatic Pairing
        Patient->>LINE: Scan QR Code with LINE Camera
        LINE->>API: POST /api/v1/line/webhook (Follow/Postback Event with PAIR_9823 & LINE_USER_ID)
        API->>Redis: GET pairing_token:PAIR_9823
        API->>Redis: SADD encounter:ENC_9823:line_users "U1234567890"
        API->>Redis: SET encounter:ENC_9823:status "PAIRED"
        API->>Redis: PUBLISH encounter_events:ENC_9823 {"event": "PAIRED", "user_name": "คุณ[ผู้ดูแล]"}
        Redis-->>UI: WebSocket Push Event: "🟢 Paired: คุณ[ผู้ดูแล]"
        LINE-->>Patient: Auto-reply: "🟢 เชื่อมต่อกับระบบสรุปคำแนะนำแพทย์เรียบร้อยแล้ว"
    end

    rect rgb(240, 255, 240)
        note over Doctor, Patient: 3. Scribe, Approval & LINE Flex Delivery
        Doctor->>UI: Tap "Start Scribe" ➔ "Stop Scribe" ➔ "Approve & Send"
        UI->>API: POST /api/v1/encounters/ENC_9823/approve
        API->>Redis: SMEMBERS encounter:ENC_9823:line_users
        API->>LINE: Push Flex Message to all paired LINE_USER_IDs
        LINE-->>Patient: Receive Flex Message Summary Card
    end
```

---

## 🔑 4. Redis Data Key Lifecycle & Expiration (TTL) Matrix

To prevent memory bloat and guarantee data privacy, all Redis keys enforce strict **Time-To-Live (TTL)** expiration rules:

| Redis Key Pattern | Data Structure | Contents | TTL (Expiration) | Purpose |
| :--- | :--- | :--- | :---: | :--- |
| `pairing_token:{token}` | String (JSON) | `{"encounter_id": "ENC_9823", "status": "UNPAIRED"}` | **15 Minutes (900s)** | Short-lived QR code pairing window |
| `encounter:{id}:line_users` | Set | `["U1234567890", "U0987654321"]` | **24 Hours (86400s)** | Stores paired LINE user IDs for delivery |
| `encounter:{id}:status` | String | `"UNPAIRED"` ➔ `"PAIRED"` ➔ `"REVIEW"` ➔ `"DELIVERED"` | **24 Hours (86400s)** | Tracks encounter lifecycle state |
| `raw_audio_buffer:{id}` | List (Bytes) | Opus binary audio frames | **1 Hour (3600s)** | **Purged immediately** post-ASR transcription |
| `draft_summary:{id}` | String (JSON) | Unapproved draft JSON payload | **24 Hours (86400s)** | Temporary UI state cache |
| `liff_pdf_token:{token}` | String (JSON) | `{"encounter_id": "ENC_9823", "line_user_id": "U1234..."}` | **1 Hour (3600s)** | Authorizes ephemeral PDF stream view |

---

## 🚨 5. Edge Cases & Exception Recovery

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PAIRING & LIFECYCLE EXCEPTION HANDLING                 │
├──────────────────────┬──────────────────────────────────────────────────────┤
│ Edge Case            │ Technical Recovery Mechanism                         │
├──────────────────────┼──────────────────────────────────────────────────────┤
│ 1. QR Code Expired   │ If patient scans after 15 minutes, LINE bot auto-     │
│    (TTL Exceeded)    │ replies: "⚠️ รหัสสแกนหมดอายุ โปรดแจ้งคุณหมอเพื่อขอรหัสใหม่" │
│                      │ UI shows 1-click "🔄 Refresh QR Code" button.        │
├──────────────────────┼──────────────────────────────────────────────────────┤
│ 2. Multiple Scans    │ Up to 2 relatives scan the same QR code. Both        │
│    (Patient + Relative)│ `LINE_USER_ID`s are added to `encounter:{id}:line_users`│
│                      │ set so both receive summaries simultaneously.        │
├──────────────────────┼──────────────────────────────────────────────────────┤
│ 3. Unpair / Cancel   │ Doctor can tap "❌ Cancel Visit" on UI, which deletes │
│    Visit Session     │ `pairing_token` and `encounter` keys in Redis instantly.│
└──────────────────────┴──────────────────────────────────────────────────────┘
```
