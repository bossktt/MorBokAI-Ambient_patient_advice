# Doctor Portal Wireframe & UI/UX Specifications (Refined)

---

## 🎯 Overview & Design Philosophy

The **Doctor Approval Dashboard & Ambient Scribe Portal** is designed for extreme simplicity and operational speed during hospital shifts (OPD / ER). 

### 🌟 Core Design Principles
1. **Zero-PIN Pairing**: Patients/caregivers link their LINE account in 1 second by scanning a **Dynamic QR Code** (no manual PIN typing).
2. **WYSIWYG Doctor Review (What You See Is What They Get)**: The doctor's approval screen shows **EXACTLY the unified card view** that the patient and caregiver will see on LINE OA and PDF.
3. **Unified Single-Card View**: Combines diagnosis, patient advice, caregiver medication reconciliation, follow-up, and red flags into **one continuous, seamless advice card** (no split panes or separate tabs).
4. **Direct In-Line Edit (No Audio Playback Buttons)**: Doctors can quickly click and edit any text line directly before sign-off (<15 seconds target).

---

## 🖥️ Screen 1: In-Clinic Visit Setup & Pairing (`/doctor/encounter/new`)

```
+-----------------------------------------------------------------------------------+
|  🏥 โรงพยาบาลตัวอย่าง — ระบบสรุปคำแนะนำแพทย์ (Ambient PVS)     [👨‍⚕️ นพ. สมชาย ใจดี] |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|   ┌──────────────────────────────────┐    ┌───────────────────────────────────┐   |
|   │ 📌 1. สแกน QR Code เพื่อเชื่อมต่อ LINE │    │ 📌 2. ตรวจสอบสถานะความยินยอม      │   |
|   │                                  │    │                                   │   |
|   │     [ 📱 Dynamic QR Code ]       │    │  [✓] ผู้ป่วย/ผู้ดูแลยินยอม        │   |
|   │       https://line.me/...        │    │      บันทึกเสียงบทสนทนา (PDPA)   │   |
|   │                                  │    │                                   │   |
|   │  (สแกนผ่านแอป LINE เพื่อรับสรุป)    │    │  สถานะการเชื่อมต่อ LINE:           │   |
|   │                                  │    │  🟢 เชื่อมต่อแล้ว: คุณ[ผู้ดูแล-ปกปิด]│   |
|   └──────────────────────────────────┘    └───────────────────────────────────┘   |
|                                                                                   |
|   [ 🎙️ เริ่มต้นรับฟังและบันทึกเสียงบทสนทนา (Start Ambient Scribe) ]                  |
+-----------------------------------------------------------------------------------+
```

### UI Component Requirements:
1. **Dynamic QR Code Component**: Renders dynamic URL linked to `ENCOUNTER_ID`. Scanning pairs `LINE_USER_ID` automatically.
2. **Digital Consent Checkbox**: Required validation flag (`is_consent_given: true`). "Start Scribe" button remains disabled until checked.
3. **Real-time Connection Badge**: Listens to Redis pub/sub for LINE pairing events (`status: "PAIRED"`). Displays `🟢 เชื่อมต่อแล้ว` as soon as LINE pairs.

---

## 🎙️ Screen 2: Bedside Ambient Scribe (`/doctor/encounter/[id]/scribe`)

```
+-----------------------------------------------------------------------------------+
|  🏥 ห้องฉุกเฉิน (Emergency Department)                        [ ⏱️ เวลา: 02:45 ]  |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|          🔴 กำลังรับฟังและบันทึกเสียงบทสนทนา (Zero Audio Storage Mode)               |
|                                                                                   |
|                       [ 🔊 CSS / Lucide Pulsing Audio Bars ]                      |
|                                                                                   |
|  ผู้ป่วย: คุณ[ผู้ป่วย-ปกปิด] | ญาติ: คุณ[ผู้ดูแล-ปกปิด] | สิทธิ์การรักษา: สิทธิบัตรทอง |
|                                                                                   |
|          [ ⏹️ หยุดอัดเสียง & สร้างสรุปคำแนะนำ (Stop & Generate Summary) ]           |
+-----------------------------------------------------------------------------------+
```

### UI Component Requirements:
1. **Pulsing Privacy Badge**: Visual indicator reassuring room occupants that audio is processed in RAM only.
2. **Built-in Audio Status Indicator**: Simple CSS / `lucide-react` animated audio bars component (no complex Web Audio API canvas code needed).
3. **Session Timer**: Elapsed time counter (`MM:SS`).
4. **Primary Action Button**: Stops `MediaRecorder` and dispatches async Celery task.

---

## 💻 Screen 3: Unified WYSIWYG Review & 15-Second Sign-Off (`/doctor/encounter/[id]/review`)

This screen displays **EXACTLY the continuous card layout** that the patient and caregiver will receive on LINE OA and PDF:

```
+-----------------------------------------------------------------------------------+
|  👤 ผู้ป่วย: คุณ[ผู้ป่วย-ปกปิด]  HN: 65-XXXXXX | แผนก: ห้องฉุกเฉิน    [ ⏱️ Target: <15s ]   |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  🏥 สรุปคำแนะนำจากคุณหมอ (Patient & Caregiver Advice Card)    [ ✏️ คลิกเพื่อแก้ไข ]|
|  ===============================================================================  |
|  🩺 ข้อวินิจฉัยโรค (Diagnosis):                                                    |
|  • ภาวะความดันโลหิตสูงและระดับน้ำตาลในเลือดสูงชั่วคราว                                |
|                                                                                   |
|  📌 คำแนะนำการดูแลตนเองสำหรับผู้ป่วย:                                               |
|  • ทานยาปรับระดับน้ำตาลตัวใหม่ (เม็ดใหญ่สีขาว) เช้า-เย็น หลังอาหารทันที                   |
|  • จิบน้ำสะอาดเรื่อยๆ อย่างน้อยวันละ 8 แก้ว                                        |
|  • งดอาหารรสจัดและของหวานมัน                                                       |
|                                                                                   |
|  💊 ตารางการบริหารยาสำหรับผู้ดูแล (Caregiver Medication Reconciliation Matrix):     |
|  🟢 ยาเริ่มใหม่ (START):                                                          |
|     Metformin 1000mg (ยาเม็ดใหญ่สีขาว รูปไข่) — ทาน 1 เม็ด เช้า-เย็น หลังอาหารทันที    |
|  🔴 ยาให้หยุดทันที (STOP):                                                        |
|     Metformin 500mg (ยาเม็ดเล็กสีขาวซองเดิม) — ⚠️ หยิบทิ้งถังขยะทันที ห้ามทานซ้ำ!   |
|  🟡 ยาปรับขนาด (CHANGE):                                                         |
|     Amlodipine 5mg (ยาลดความดัน เม็ดสีเหลือง) — ปรับลดเหลือ 1 เม็ด ก่อนนอน          |
|                                                                                   |
|  📅 วันนัดครั้งถัดไป (Follow-Up):                                                  |
|  • วันอาทิตย์ที่ 16 สิงหาคม 2026 เวลา 09:00 น.                                       |
|  • คลินิกอายุรกรรมหัวใจและหลอดเลือด (งดน้ำและอาหารหลังเที่ยงคืนก่อนวันตรวจ)               |
|                                                                                   |
|  🚨 อาการเตือนฉุกเฉิน (Red Flags):                                                 |
|  • เจ็บแน่นหน้าผาก / หน้ามืดเป็นลม / แขนขาอ่อนแรงครึ่งซีก ➔ โทร 1669 ทันที            |
|  ===============================================================================  |
|                                                                                   |
|  [ ✏️ แก้ไขข้อมูล (In-Line Edit) ]   [ ✅ อนุมัติ & ส่งเข้า LINE OA ทันที (Approve) ] |
+-----------------------------------------------------------------------------------+
```

### UI Component Requirements:
1. **1:1 WYSIWYG Unified Card Preview**: Displays a single, continuous vertical card that matches the LINE OA Flex Message layout.
2. **No Separate Panes or Tabs**: Patient advice, diagnosis, caregiver medication reconciliation, follow-up, and red flags are presented sequentially in one unified view.
3. **Direct In-Line Edit**: Doctors can click on any text block (e.g. diagnosis or medication dosage) to edit it directly on screen before approval.
4. **No Audio Playback Buttons**: Audio timestamps are omitted for speed and simplicity.
5. **Primary Action Button**: High-visibility Green Button: **"✅ อนุมัติ & ส่งเข้า LINE OA ทันที"** (Triggers LINE Webhook + LIFF PDF Streamer).

---

## 📊 Summary of Refined Doctor Portal Screens

| Screen Route | Primary Function | Target User Action | Target Duration |
| :--- | :--- | :--- | :---: |
| **1. `/doctor/encounter/new`** | QR Pairing (No PIN) & Consent | Patient scans QR on LINE | <10 seconds |
| **2. `/doctor/encounter/[id]/scribe`** | Ambient Audio Scribe | Tap "Stop & Generate" | Consultation duration |
| **3. `/doctor/encounter/[id]/review`** | Unified WYSIWYG Audit & Edit | Tap "Approve & Send" | **<15 seconds** |
