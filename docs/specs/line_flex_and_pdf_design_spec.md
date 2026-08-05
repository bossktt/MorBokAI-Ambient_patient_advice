# LINE OA Flex Message & PDF Visual Design Specifications

---

## 🎯 Overview

This document specifies the exact visual design layouts and structural schemas for the two primary delivery channels:
1. **LINE OA Flex Message Card**: Interactive JSON Flex Message delivered inside the patient/caregiver LINE chat window.
2. **Downloadable PDF Advice Sheet**: High-contrast, single-page A4 PDF compiled via Jinja2 + Playwright using Google Font **Sarabun**.

Both outputs match the **WYSIWYG single-card layout** approved in the Doctor Approval Portal.

---

## 📱 1. LINE OA Flex Message Specification (`flex_message_template.json`)

Below is the complete, valid LINE Messaging API Flex Template JSON:

```json
{
  "type": "flex",
  "altText": "🏥 สรุปคำแนะนำจากคุณหมอ (Emergency Department)",
  "contents": {
    "type": "bubble",
    "size": "mega",
    "header": {
      "type": "box",
      "layout": "vertical",
      "backgroundColor": "#0F4C81",
      "paddingAll": "15pt",
      "contents": [
        {
          "type": "text",
          "text": "🏥 สรุปคำแนะนำจากคุณหมอ",
          "weight": "bold",
          "color": "#FFFFFF",
          "size": "lg"
        },
        {
          "type": "text",
          "text": "ห้องฉุกเฉิน (Emergency Department)",
          "color": "#E0E6ED",
          "size": "xs",
          "margin": "xs"
        }
      ]
    },
    "body": {
      "type": "box",
      "layout": "vertical",
      "spacing": "md",
      "contents": [
        {
          "type": "box",
          "layout": "vertical",
          "backgroundColor": "#F8F9FA",
          "paddingAll": "10pt",
          "cornerRadius": "6pt",
          "contents": [
            {
              "type": "text",
              "text": "🩺 ข้อวินิจฉัยโรค (Diagnosis)",
              "weight": "bold",
              "color": "#0F4C81",
              "size": "sm"
            },
            {
              "type": "text",
              "text": "ภาวะความดันโลหิตสูงและระดับน้ำตาลในเลือดสูงชั่วคราว",
              "wrap": true,
              "color": "#333333",
              "size": "xs",
              "margin": "xs"
            }
          ]
        },
        {
          "type": "text",
          "text": "📌 คำแนะนำการดูแลตนเองสำหรับผู้ป่วย",
          "weight": "bold",
          "size": "sm",
          "color": "#333333"
        },
        {
          "type": "text",
          "text": "• ทานยาปรับระดับน้ำตาลตัวใหม่ (เม็ดใหญ่สีขาว) เช้า-เย็น หลังอาหารทันที\n• จิบน้ำสะอาดเรื่อยๆ อย่างน้อยวันละ 8 แก้ว\n• งดอาหารรสจัดและของหวานมัน",
          "wrap": true,
          "size": "xs",
          "color": "#555555",
          "lineSpacing": "4pt"
        },
        {
          "type": "separator"
        },
        {
          "type": "text",
          "text": "💊 ตารางจัดยาสำหรับผู้ดูแล (Med Reconciliation)",
          "weight": "bold",
          "size": "sm",
          "color": "#333333"
        },
        {
          "type": "box",
          "layout": "vertical",
          "backgroundColor": "#E6F4EA",
          "paddingAll": "8pt",
          "cornerRadius": "4pt",
          "contents": [
            {
              "type": "text",
              "text": "🟢 ยาเริ่มใหม่ (START)",
              "weight": "bold",
              "color": "#137333",
              "size": "xs"
            },
            {
              "type": "text",
              "text": "Metformin 1000mg (ยาเม็ดใหญ่สีขาว รูปไข่)\nทาน 1 เม็ด เช้า-เย็น หลังอาหารทันที",
              "wrap": true,
              "color": "#137333",
              "size": "xs",
              "margin": "xs"
            }
          ]
        },
        {
          "type": "box",
          "layout": "vertical",
          "backgroundColor": "#FCE8E6",
          "paddingAll": "8pt",
          "cornerRadius": "4pt",
          "contents": [
            {
              "type": "text",
              "text": "🔴 ยาให้หยุดทันที (STOP)",
              "weight": "bold",
              "color": "#C5221F",
              "size": "xs"
            },
            {
              "type": "text",
              "text": "Metformin 500mg (ยาเม็ดเล็กสีขาวซองเดิม)\n⚠️ หยิบทิ้งถังขยะทันที ห้ามนำมารับประทานซ้ำ!",
              "wrap": true,
              "color": "#C5221F",
              "size": "xs",
              "margin": "xs"
            }
          ]
        },
        {
          "type": "box",
          "layout": "vertical",
          "backgroundColor": "#FEF7E0",
          "paddingAll": "8pt",
          "cornerRadius": "4pt",
          "contents": [
            {
              "type": "text",
              "text": "🟡 ยาปรับขนาด (CHANGE)",
              "weight": "bold",
              "color": "#B06000",
              "size": "xs"
            },
            {
              "type": "text",
              "text": "Amlodipine 5mg (ยาลดความดัน เม็ดสีเหลือง)\nปรับลดเหลือ 1 เม็ด ก่อนนอน (จากเดิม 2 เม็ด)",
              "wrap": true,
              "color": "#B06000",
              "size": "xs",
              "margin": "xs"
            }
          ]
        },
        {
          "type": "separator"
        },
        {
          "type": "text",
          "text": "📅 วันนัดครั้งถัดไป (Follow-Up)",
          "weight": "bold",
          "size": "sm",
          "color": "#333333"
        },
        {
          "type": "text",
          "text": "วันอาทิตย์ที่ 16 สิงหาคม 2026 เวลา 09:00 น.\nคลินิกอายุรกรรมหัวใจและหลอดเลือด (งดน้ำก่อนเจาะเลือด)",
          "wrap": true,
          "size": "xs",
          "color": "#555555"
        },
        {
          "type": "box",
          "layout": "vertical",
          "backgroundColor": "#FFF0F0",
          "paddingAll": "8pt",
          "cornerRadius": "4pt",
          "contents": [
            {
              "type": "text",
              "text": "🚨 อาการเตือนฉุกเฉิน (Red Flags)",
              "weight": "bold",
              "color": "#D93025",
              "size": "xs"
            },
            {
              "type": "text",
              "text": "เจ็บแน่นหน้าผาก / หน้ามืดเป็นลม ➔ โทร 1669 ทันที",
              "wrap": true,
              "color": "#D93025",
              "size": "xs",
              "margin": "xs"
            }
          ]
        }
      ]
    },
    "footer": {
      "type": "box",
      "layout": "vertical",
      "spacing": "sm",
      "contents": [
        {
          "type": "button",
          "style": "primary",
          "color": "#0F4C81",
          "action": {
            "type": "uri",
            "label": "📄 ดาวน์โหลดใบนัด & PDF ฉบับเต็ม",
            "uri": "https://liff.line.me/1234567890-AbCdEfGh/pdf?enc=ENC_9823"
          }
        },
        {
          "type": "button",
          "style": "secondary",
          "action": {
            "type": "uri",
            "label": "🔊 กดฟังเสียงอ่านสรุปคำแนะนำ",
            "uri": "https://api.pvs-health.org/media/tts/tts_ENC_9823.mp3"
          }
        }
      ]
    }
  }
}
```

---

## 📄 2. HTML PDF Advice Sheet Template (`pvs_pdf_template.html`)

This HTML Jinja2 template is compiled by **Playwright (Python)** into a high-contrast A4 PDF:

```html
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>สรุปคำแนะนำการดูแลตนเองหลังออกจากห้องฉุกเฉิน</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&display=swap');
        
        body {
            font-family: 'Sarabun', sans-serif;
            color: #222222;
            line-height: 1.5;
            margin: 0;
            padding: 20px;
        }
        .header {
            border-bottom: 3px solid #0F4C81;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }
        .header h1 {
            color: #0F4C81;
            font-size: 20pt;
            margin: 0;
        }
        .meta-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            background: #F4F6F8;
            padding: 10px;
            border-radius: 6px;
            font-size: 11pt;
            margin-bottom: 15px;
        }
        .section-title {
            font-size: 13pt;
            font-weight: 700;
            color: #0F4C81;
            margin-top: 15px;
            margin-bottom: 5px;
        }
        .med-box {
            padding: 10px;
            border-radius: 6px;
            margin-bottom: 8px;
            font-size: 11pt;
        }
        .med-start { background-color: #E6F4EA; border-left: 5px solid #137333; color: #137333; }
        .med-stop { background-color: #FCE8E6; border-left: 5px solid #C5221F; color: #C5221F; }
        .med-change { background-color: #FEF7E0; border-left: 5px solid #B06000; color: #B06000; }
        .red-flag-box {
            background-color: #FFF0F0;
            border: 2px solid #D93025;
            padding: 10px;
            border-radius: 6px;
            color: #D93025;
            font-weight: bold;
            font-size: 11pt;
            margin-top: 15px;
        }
        .watermark {
            position: fixed;
            top: 45%;
            left: 10%;
            font-size: 36pt;
            color: rgba(0, 0, 0, 0.06);
            transform: rotate(-30deg);
            pointer-events: none;
            font-weight: 700;
        }
    </style>
</head>
<body>

    <div class="watermark">CONFIDENTIAL — VERIFIED VIA LINE OA</div>

    <div class="header">
        <h1>🏥 สรุปคำแนะนำจากคุณหมอ (Emergency Department)</h1>
        <div>โรงพยาบาลตัวอย่าง | วันที่: {{ data.metadata.visit_timestamp }}</div>
    </div>

    <div class="meta-grid">
        <div><strong>ผู้ป่วย:</strong> {{ data.metadata.patient.patient_name }} (HN: {{ data.metadata.patient.hn }})</div>
        <div><strong>ผู้ดูแล:</strong> {{ data.metadata.caregiver.caregiver_name }} ({{ data.metadata.caregiver.relationship }})</div>
        <div><strong>แพทย์ผู้ตรวจ:</strong> {{ data.metadata.doctor.full_name }}</div>
        <div><strong>แผนก:</strong> {{ data.metadata.department }}</div>
    </div>

    <div class="section-title">🩺 ข้อวินิจฉัยโรค (Diagnosis)</div>
    <div>{{ data.patient_view.diagnosis }}</div>

    <div class="section-title">📌 คำแนะนำการดูแลตนเองสำหรับผู้ป่วย</div>
    <ul>
        {% for item in data.patient_view.key_instructions %}
            <li>{{ item }}</li>
        {% endfor %}
    </ul>

    <div class="section-title">💊 ตารางการบริหารยาสำหรับผู้ดูแล (Caregiver Medication Reconciliation Matrix)</div>
    
    {% for med in data.caregiver_matrix.medication_reconciliation.start %}
    <div class="med-box med-start">
        <strong>🟢 เริ่มใหม่:</strong> {{ med.med_name }} ({{ med.physical_description }}) — {{ med.dosage }} {{ med.timing }} {{ med.instructions }}
    </div>
    {% endfor %}

    {% for med in data.caregiver_matrix.medication_reconciliation.stop %}
    <div class="med-box med-stop">
        <strong>🔴 ให้หยุดทันที:</strong> {{ med.med_name }} ({{ med.physical_description }}) — ⚠️ {{ med.discard_instruction }}
    </div>
    {% endfor %}

    {% for med in data.caregiver_matrix.medication_reconciliation.change %}
    <div class="med-box med-change">
        <strong>🟡 ปรับขนาด:</strong> {{ med.med_name }} ({{ med.physical_description }}) — {{ med.change_summary }}
    </div>
    {% endfor %}

    <div class="section-title">📅 วันนัดครั้งถัดไป (Follow-Up Schedule)</div>
    <div><strong>วันที่:</strong> {{ data.patient_view.follow_up.follow_up_date_thai }}</div>
    <div><strong>สถานที่:</strong> {{ data.patient_view.follow_up.clinic_name }}</div>
    <ul>
        {% for prep in data.patient_view.follow_up.preparation_instructions %}
            <li>{{ prep }}</li>
        {% endfor %}
    </ul>

    <div class="red-flag-box">
        🚨 อาการเตือนฉุกเฉินที่ต้องกลับมาโรงพยาบาลทันที (Red Flags):
        <ul>
            {% for warning in data.red_flags.emergency_warnings %}
                <li>{{ warning }}</li>
            {% endfor %}
        </ul>
        📞 สายด่วนฉุกเฉิน: {{ data.red_flags.hotline_call_trigger.national_emergency_number }} หรือ โทร: {{ data.red_flags.hotline_call_trigger.hospital_direct_number }}
    </div>

</body>
</html>
```

---

## 🎨 3. Visual Layout Comparison

| Element | LINE OA Flex Card | PDF Advice Sheet |
| :--- | :--- | :--- |
| **Primary Container** | LINE In-App Bubble (`mega` size) | A4 Portrait Document (Printable) |
| **Typography** | Native Mobile System Font (Dynamic) | Google Font **Sarabun** (14pt / 18pt) |
| **Color Coding** | Green `#E6F4EA`, Red `#FCE8E6`, Yellow `#FEF7E0` | Matching Light Container & Dark Border Colors |
| **Interactivity** | Live Tap Buttons (*"Download PDF"*, *"TTS"*)| Static Pre-Signed URL Gate + Security Watermark |
