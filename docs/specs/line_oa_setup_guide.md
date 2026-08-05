# 🚀 คู่มือการตั้งค่า LINE Official Account (LINE OA Setup Guide)
## สำหรับระบบ "หมอบอก" (MedBridge AI)

---

## 📌 ขั้นตอนที่ 1: สร้างบัญชี LINE Official Account

1. ไปที่เว็บไซต์ [LINE Official Account Manager](https://manager.line.biz/) หรือดาวน์โหลดแอป **LINE Official Account** บนสมาร์ตโฟน
2. เข้าสู่ระบบด้วย **LINE Account** หรือ **Business Account**
3. กดปุ่ม **"สร้างบัญชีทางการ" (Create Official Account)**
4. กรอกข้อมูลบัญชี:
   * **ชื่อบัญชี (Account Name):** `หมอบอก - สรุปคำแนะนำแพทย์` (หรือ `หมอบอก`)
   * **หมวดหมู่หลัก (Main Category):** `การแพทย์และสุขภาพ (Medical & Health)`
   * **หมวดหมู่ย่อย (Sub-Category):** `โรงพยาบาล / คลินิก (Hospital / Clinic)`
   * **ชื่อบริษัท/ธุรกิจ (Company Name):** `MedBridge AI`

---

## 🖼️ ขั้นตอนที่ 2: ตั้งค่ารูปโปรไฟล์และภาพปก (Profile & Cover Setup)

ไปที่ **ตั้งค่า (Settings)** ➔ **ตั้งค่าพื้นฐาน (Basic Settings)**:

1. **รูปโปรไฟล์ (Profile Image):**
   * อัปโหลดไฟล์จากโปรเจกต์: [assets/line_oa_profile_icon.jpg](file:///Users/bossktt/Library/CloudStorage/GoogleDrive-bossktt@gmail.com/My%20Drive/AI%20in%20healthcare/AI-Project/AI-advice/assets/line_oa_profile_icon.jpg)
2. **รูปภาพปก (Cover Image):**
   * อัปโหลดไฟล์จากโปรเจกต์: [assets/line_oa_cover_photo.jpg](file:///Users/bossktt/Library/CloudStorage/GoogleDrive-bossktt@gmail.com/My%20Drive/AI%20in%20healthcare/AI-Project/AI-advice/assets/line_oa_cover_photo.jpg)
3. **ข้อความสถานะ (Status Message):**
   * `สรุปคำแนะนำหมอ ตารางจัดยา และสัญญาณเตือนฉุกเฉินส่งตรงถึงคุณ`

---

## 💬 ขั้นตอนที่ 3: ตั้งค่าข้อความต้อนรับเพื่อนใหม่ (Greeting Message)

ไปที่เมนู **ข้อความต้อนรับ (Greeting Message)** ➔ วางข้อความนี้:

```text
🏥 ยินดีต้อนรับสู่ "หมอบอก" (MedBridge AI)
ระบบสรุปคำแนะนำแพทย์และตารางบริหารยาจากห้องตรวจส่งตรงถึงคุณและครอบครัว

📌 เมื่อคุณหมอตรวจเสร็จเรียบร้อยแล้ว ท่านจะได้รับ:
1. 🩺 สรุปข้อวินิจฉัยโรค (ภาษาไทยเข้าใจง่าย)
2. 💊 ตารางการบริหารยาสำหรับผู้ดูแล (เริ่มใหม่ / หยุดยา / ปรับขนาด)
3. 🚨 อาการเตือนฉุกเฉินที่ต้องกลับมาโรงพยาบาลทันที
4. 🔊 ปุ่มกดฟังเสียงอ่านสรุปคำแนะนำ (Audio TTS)
5. 📄 ใบนัด & PDF ฉบับเต็มสำหรับพิมพ์
```

---

## 🔑 ขั้นตอนที่ 4: เปิดใช้งาน Messaging API (สำหรับนักพัฒนา & ระบบ AI Backend)

1. เข้าไปที่ [LINE Developers Console](https://developers.line.biz/)
2. เลือก Provider ของคุณ (หรือกด **Create a new provider** เช่น `MedBridge Health`)
3. เลือก Channel บัญชี LINE OA ของคุณ ➔ ไปที่แท็บ **Messaging API**
4. กด **Issue** เพื่อสร้าง **Channel Access Token (v2.1 / long-lived)**
5. คัดลอก **Channel Access Token** และ **Channel Secret** เก็บไว้

### การตั้งค่า Webhook:
* **Webhook URL:** `https://your-domain.com/api/v1/line/webhook` (หรือใช้ ngrok ทดสอบ: `https://xxxx.ngrok-free.app/api/v1/line/webhook`)
* สวิตช์ **Use Webhook:** เปลี่ยนเป็น `ON` (เปิดใช้งาน)
* สวิตช์ **Auto-response messages:** เปลี่ยนเป็น `OFF` (เพื่อให้ระบบ AI เป็นผู้ตอบกลับแทน)

---

## 💻 ขั้นตอนที่ 5: เชื่อมต่อ Token เข้ากับระบบ Doctor Approval Portal

1. เปิดเว็บแอปพลิเคชันไปที่หน้า [New Patient Encounter](http://localhost:3000/doctor/encounter/new)
2. กดเปิดเมนู `⚙️ เชื่อมต่อ LINE Official Account (Channel Token & Secret)`
3. วาง **Channel Access Token** ที่คัดลอกมาจาก LINE Developers Console
4. เมื่อคุณหมอกดอนุมัติเคส **"Approve & Send to LINE"** ระบบจะส่ง **Flex Message Card + เสียงพูด Audio TTS + ลิงก์ PDF** เข้า LINE OA ผู้ป่วยและผู้ดูแลโดยอัตโนมัติทันที!
