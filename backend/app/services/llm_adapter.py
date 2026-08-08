# backend/app/services/llm_adapter.py
"""
MorBok AI — Clinical LLM Adapter & Patient Summary Generation Engine
=====================================================================

Supported Providers:
  1. OpenRouter (google/gemini-2.5-flash) — Primary default.
  2. Gemini AI Studio — Direct fallback.

Pipeline: OpenRouter → Gemini → demo summary.
"""

from abc import ABC, abstractmethod
import json
import requests
from app.core.config import settings


class BaseLLMAdapter(ABC):
    @abstractmethod
    def generate_clinical_summary(self, sanitized_prompt: str) -> dict:
        pass


# Shared clinical prompt template
CLINICAL_SYSTEM_PROMPT = """คุณคือระบบช่วยแพทย์ในห้องฉุกเฉิน (Emergency Department, Thailand).
อ่านบทสนทนาห้องตรวจที่ถอดเสียง แล้วสร้างสรุปภาษาไทยที่คนทั่วไปอ่านเข้าใจ

⚠️ ห้ามเด็ดขาด:
- ห้ามใช้ความรู้ส่วนตัวแต่งข้อมูล หากบทสนทนาไม่ได้ระบุ ให้เว้นว่างหรือใช้ array เปล่า []
- ห้ามคาดเดาชื่อยา ตัวสะกดยา ขนาดยา วิธีทาน หรือวันนัดที่แพทย์ไม่ได้พู​ด
- ห้ามแปลศัพท์แพทย์เป็นไทยผิด — หากไม่แน่ใจ ให้คงคำภาษาอังกฤษไว้ในวงเล็บ
- ห้ามใส่คำแนะนำเกี่ยวกับยาใน key_instructions — ข้อมูลยาทั้งหมดต้องอยู่ใน medication_box

📐 ขั้นตอน:
1. วิเคราะห์บทสนทนา — มีการพูดถึงอะไรบ้าง: อาการ? ยา? การนัด?
2. สรุปเฉพาะสิ่งที่พบ หากไม่มีข้อมูลในส่วนใด ให้เว้นว่างหรือใส่ array เปล่า
3. เขียนเป็นภาษาไทยง่าย ๆ ที่คนอายุ 60+ อ่านเข้าใจ

📤 ส่ง JSON เท่านี้ (ห้ามใส่ข้อความอื่น):
{{
  "patient_view": {{
    "headline": "สรุปคำแนะนำ",
    "diagnosis": "ข้อวินิจฉัยภาษาไทย (อังกฤษในวงเล็บ) — ถ้าไม่ระบุ ให้ใช้ 'อาการทั่วไป (General Symptoms)'",
    "key_instructions": ["คำแนะนำ (ห้ามใส่ชื่อยา/ขนาดยา — ยาต้องอยู่ใน medication_box)"],
    "home_care": ["การดูแลที่บ้าน (ถ้าไม่มี = [])"],
    "red_flags": ["อาการที่ต้องกลับห้องฉุกเฉินทันที"],
    "follow_up": {{
      "date": "วันนัด (ถ้าไม่มี = 'ไม่มีนัด')",
      "location": "สถานที่",
      "reason": "เหตุผล"
    }}
  }},
  "medication_box": {{
    "start": [{{ "name": "ชื่อยาใหม่", "appearance": "ลักษณะเม็ด/สี", "how_to_take": "วิธีทาน" }}],
    "stop": [{{ "name": "ยาหยุด", "appearance": "ลักษณะ", "action": "หยุด/ทิ้ง", "reason": "เหตุผล" }}],
    "change": [{{ "name": "ยาปรับ", "appearance": "ลักษณะ", "new_instruction": "วิธีใหม่", "reason": "เหตุผล" }}]
  }}
}}

บทสนทนา:
{sanitized_prompt}
"""


class OpenRouterAdapter(BaseLLMAdapter):
    """Primary adapter: OpenRouter API → Gemini models."""

    def generate_clinical_summary(self, sanitized_prompt: str) -> dict:
        api_key = settings.OPENROUTER_API_KEY
        if not api_key or api_key == "your_openrouter_api_key_here":
            print("OpenRouter API key missing, falling back to Gemini")
            return GeminiAdapter().generate_clinical_summary(sanitized_prompt)

        model_name = getattr(settings, "OPENROUTER_MODEL", "google/gemini-2.5-flash")
        prompt_text = CLINICAL_SYSTEM_PROMPT.format(sanitized_prompt=sanitized_prompt)

        req_payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt_text}],
            "response_format": {"type": "json_object"}
        }

        provider_pref = getattr(settings, "OPENROUTER_PROVIDER", None)
        if provider_pref:
            req_payload["provider"] = {
                "order": [provider_pref]
            }

        try:
            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=req_payload,
                timeout=15
            )
            raw_res = res.json()
            if "error" in raw_res:
                print(f"OpenRouter error: {raw_res['error']}, falling back to Gemini")
                return GeminiAdapter().generate_clinical_summary(sanitized_prompt)

            out_text = raw_res["choices"][0]["message"]["content"]
            clean_text = out_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            print(f"OpenRouter exception: {e}, falling back to Gemini")
            return GeminiAdapter().generate_clinical_summary(sanitized_prompt)


class GeminiAdapter(BaseLLMAdapter):
    """Fallback: Google Gemini via AI Studio API key."""

    def generate_clinical_summary(self, sanitized_prompt: str) -> dict:
        api_key = settings.GEMINI_API_KEY
        if not api_key or api_key.startswith("AIzaSy_your") or api_key.startswith("AQ."):
            print("Gemini API key missing/invalid, falling back to demo")
            return self._fallback_demo_summary(sanitized_prompt)

        model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash-lite")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        prompt_text = CLINICAL_SYSTEM_PROMPT.format(sanitized_prompt=sanitized_prompt)

        try:
            res = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt_text}]}]},
                timeout=15
            )
            raw_res = res.json()
            if "error" in raw_res:
                print(f"Gemini error: {raw_res['error'].get('message', raw_res['error'])}, falling back to demo")
                return self._fallback_demo_summary(sanitized_prompt)

            out_text = raw_res["candidates"][0]["content"]["parts"][0]["text"]
            clean_text = out_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            print(f"Gemini exception: {e}, falling back to demo")
            return self._fallback_demo_summary(sanitized_prompt)

    @staticmethod
    def _fallback_demo_summary(sanitized_prompt: str = "") -> dict:
        prompt_lower = (sanitized_prompt or "").lower()

        base = {
            "patient_view": {
                "headline": "สรุปคำแนะนำหลังออกจากห้องฉุกเฉิน",
                "diagnosis": "อาการทั่วไปที่พบในห้องฉุกเฉิน (General ED Discharge)",
                "key_instructions": [
                    "สังเกตอาการตนเองอย่างใกล้ชิด หากอาการแย่ลง ให้กลับมาพบแพทย์ทันที",
                    "พักผ่อนให้เพียงพอและดื่มน้ำสะอาดอย่างน้อยวันละ 8 แก้ว",
                    "รับประทานยาตามที่แพทย์หรือเภสัชกรแนะนำอย่างเคร่งครัด"
                ],
                "red_flags": ["มีอาการผิดปกติรุนแรงขึ้น เช่น เจ็บแน่นหน้าอก หายใจลำบาก ซึมลง หรือหมดสติ"],
                "follow_up": {"date": "กลับมาพบแพทย์หากอาการไม่ดีขึ้น", "location": "", "reason": ""}
            },
            "medication_box": {"start": [], "stop": [], "change": []}
        }

        # Respiratory
        if any(w in prompt_lower for w in ["หอบ", "เหนื่อย", "หายใจ", "หอบหืด", "หลอดลม", "asthma", "dyspnea"]):
            return {
                **base,
                "patient_view": {
                    "headline": "สรุปคำแนะนำสำหรับอาการหอบเหนื่อย",
                    "diagnosis": "หลอดลมอักเสบเฉียบพลันหรือหอบหืดกำเริบ (Acute Bronchitis / Asthma Exacerbation)",
                    "key_instructions": ["พ่นยาขยายหลอดลมตามแพทย์สั่งเมื่อมีอาการ", "หลีกเลี่ยงควันบุหรี่และฝุ่นละออง", "ดื่มน้ำอุ่นเพื่อช่วยละลายเสมหะ"],
                    "red_flags": ["หายใจมีเสียงหวีดรุนแรง พูดเป็นประโยคไม่ได้ ริมฝีปากเขียว"],
                    "follow_up": {"date": "กลับมาพบแพทย์หากหอบไม่ดีขึ้นใน 24 ชั่วโมง", "location": "", "reason": ""}
                },
                "medication_box": {"start": [], "stop": [], "change": []}
            }

        # Cardiac
        if any(w in prompt_lower for w in ["หน้าอก", "แน่นหน้าอก", "เจ็บหน้าอก", "หัวใจ", "chest pain", "ใจสั่น", "palpitations"]):
            return {
                **base,
                "patient_view": {
                    "headline": "สรุปคำแนะนำสำหรับอาการเจ็บแน่นหน้าอก",
                    "diagnosis": "อาการเจ็บแน่นหน้าอกหรือใจสั่น (Chest Pain / Palpitations — Rule out ACS)",
                    "key_instructions": ["พักผ่อน หลีกเลี่ยงการออกแรงหนัก", "งดกาแฟ ชา บุหรี่ และเครื่องดื่มชูกำลัง", "หากมีอาการแน่นหน้าอกให้นั่งพักและรีบไปโรงพยาบาล"],
                    "red_flags": ["เจ็บแน่นหน้าอกรุนแรง เหงื่อออกตัวเย็น ร้าวไปแขนซ้ายหรือกราม ให้โทร 1669 ทันที"],
                    "follow_up": {"date": "กลับมาพบแพทย์หากมีอาการอีก", "location": "", "reason": ""}
                },
                "medication_box": {"start": [], "stop": [], "change": []}
            }

        # Abdominal
        if any(w in prompt_lower for w in ["ปวดท้อง", "กระเพาะ", "ท้องเสีย", "ถ่ายเหลว", "อาเจียน", "คลื่นไส้", "abdominal pain"]):
            return {
                **base,
                "patient_view": {
                    "headline": "สรุปคำแนะนำสำหรับอาการปวดท้อง",
                    "diagnosis": "กระเพาะอาหารและลำไส้อักเสบเฉียบพลัน (Acute Gastroenteritis / Gastritis)",
                    "key_instructions": ["จิบน้ำเกลือแร่ ORS ทีละน้อยตลอดวัน", "รับประทานอาหารอ่อนย่อยง่าย หลีกเลี่ยงอาหารมันและนม"],
                    "red_flags": ["ถ่ายอุจจาระมีมูกเลือด ปวดท้องรุนแรง หรือมีไข้สูง"],
                    "follow_up": {"date": "กลับมาพบแพทย์หากถ่ายเหลวเกิน 3 วัน", "location": "", "reason": ""}
                },
                "medication_box": {"start": [], "stop": [], "change": []}
            }

        # Dizziness
        if any(w in prompt_lower for w in ["ความดัน", "เวียนหัว", "เวียนศีรษะ", "บ้านหมุน", "ปวดหัว", "ปวดศีรษะ", "hypertension"]):
            return {
                **base,
                "patient_view": {
                    "headline": "สรุปคำแนะนำสำหรับอาการเวียนศีรษะ",
                    "diagnosis": "อาการเวียนศีรษะหรือภาวะความดันโลหิตสูง (Vertigo / Hypertensive Urgency)",
                    "key_instructions": ["ลุกจากที่นอนช้า ๆ", "หลีกเลี่ยงการขับรถขณะมีอาการ", "พักในที่เงียบสงบ"],
                    "red_flags": ["มีอาการแขนขาอ่อนแรง ปากเบี้ยว พูดไม่ชัด หรือปวดศีรษะรุนแรง"],
                    "follow_up": {"date": "กลับมาพบแพทย์หากอาการไม่ดีขึ้น", "location": "", "reason": ""}
                },
                "medication_box": {"start": [], "stop": [], "change": []}
            }

        # Fever
        if any(w in prompt_lower for w in ["ไข้", "หนาวสั่น", "ไข้หวัด", "เจ็บคอ", "น้ำมูก", "หวัด", "fever"]):
            return {
                **base,
                "patient_view": {
                    "headline": "สรุปคำแนะนำสำหรับไข้หวัด",
                    "diagnosis": "โรคไข้หวัดใหญ่เฉียบพลัน (Common Cold / Acute URI)",
                    "key_instructions": ["เช็ดตัวลดไข้ด้วยน้ำธรรมดา", "พักผ่อนให้เพียงพอและดื่มน้ำสะอาด", "หลีกเลี่ยงการสัมผัสใกล้ชิด"],
                    "red_flags": ["ไข้สูงเกิน 39°C ติดต่อกันเกิน 3 วัน หรือมีจุดเลือดออกตามผิวหนัง"],
                    "follow_up": {"date": "กลับมาพบแพทย์หากอาการไม่ดีขึ้นใน 3 วัน", "location": "", "reason": ""}
                },
                "medication_box": {"start": [], "stop": [], "change": []}
            }

        # Diabetes
        if any(w in prompt_lower for w in ["เบาหวาน", "น้ำตาล", "diabetes", "hyperglycemia"]):
            return {
                **base,
                "patient_view": {
                    "headline": "สรุปคำแนะนำสำหรับภาวะน้ำตาลในเลือดสูง",
                    "diagnosis": "ภาวะระดับน้ำตาลในเลือดสูง (Uncontrolled Diabetes Mellitus)",
                    "key_instructions": ["รับประทานยาคุมระดับน้ำตาลตามแพทย์สั่ง", "งดเครื่องดื่มรสหวาน", "จิบน้ำสะอาดอย่างน้อยวันละ 8 แก้ว"],
                    "red_flags": ["หอบหายใจลึก ลมหายใจมีกลิ่นหวาน ซึมลง หรือหมดสติ ให้โทร 1669"],
                    "follow_up": {"date": "กลับมาพบแพทย์ตามนัดเพื่อตรวจระดับน้ำตาล", "location": "", "reason": ""}
                },
                "medication_box": {"start": [], "stop": [], "change": []}
            }

        # Trauma
        if any(w in prompt_lower for w in ["อุบัติเหตุ", "แผล", "ล้ม", "ชน", "กระดูก", "trauma", "wound"]):
            return {
                **base,
                "patient_view": {
                    "headline": "สรุปคำแนะนำสำหรับแผลและการบาดเจ็บ",
                    "diagnosis": "แผลฉีกขาดและการบาดเจ็บเนื้อเยื่ออ่อน (Laceration / Soft Tissue Injury)",
                    "key_instructions": ["ดูแลแผลไม่ให้โดนน้ำ", "มาตรวจแผลตามนัด", "สังเกตอาการผิดปกติของแผลทุกวัน"],
                    "red_flags": ["แผลบวมแดงร้อน มีหนองไหล ปวดรุนแรงขึ้น หรือมีไข้สูง"],
                    "follow_up": {"date": "มาตรวจแผลตามนัดหมาย", "location": "", "reason": ""}
                },
                "medication_box": {"start": [], "stop": [], "change": []}
            }

        # Allergy
        if any(w in prompt_lower for w in ["แพ้", "ผื่น", "คัน", "บวม", "allergy", "urticaria"]):
            return {
                **base,
                "patient_view": {
                    "headline": "สรุปคำแนะนำสำหรับอาการแพ้",
                    "diagnosis": "ภาวะผื่นคันภูมิแพ้เฉียบพลัน (Acute Urticaria / Allergic Reaction)",
                    "key_instructions": ["หยุดรับประทานยาหรืออาหารที่สงสัยว่าเป็นสาเหตุ", "หลีกเลี่ยงการเกา", "หลีกเลี่ยงสารก่อภูมิแพ้"],
                    "red_flags": ["มีอาการแน่นหน้าอก หายใจมีเสียงหวีด ปากบวม ตาบวม หรือกลืนลำบาก"],
                    "follow_up": {"date": "กลับมาพบแพทย์หากผื่นไม่ลดลงใน 3 วัน", "location": "", "reason": ""}
                },
                "medication_box": {"start": [], "stop": [], "change": []}
            }


        # Head Injury (common in motorcycle accidents)
        if any(w in prompt_lower for w in ["หัว", "ศีรษะ", "head injury", "concussion"]):
            return {
                **base,
                "patient_view": {
                    "headline": "สรุปคำแนะนำสำหรับผู้บาดเจ็บที่ศีรษะ",
                    "diagnosis": "การบาดเจ็บที่ศีรษะ (Head Injury / Concussion — observe at home)",
                    "key_instructions": [
                        "ให้ผู้ป่วยนอนพัก โดยมีผู้ดูแลเฝ้าสังเกตอาการตลอด 24 ชั่วโมง",
                        "ปลุกทุก 2-3 ชั่วโมงเพื่อเช็คว่ารู้สึกตัวดี พูดคุยรู้เรื่องหรือไม่",
                        "ห้ามขับขี่ยานพาหนะหรือทำงานกับเครื่องจักรอย่างน้อย 48 ชั่วโมง",
                        "งดแอลกอฮอล์และยาที่มีฤทธิ์กดประสาททุกชนิด"
                    ],
                    "red_flags": ["ปวดศีรษะรุนแรงขึ้นเรื่อย ๆ", "อาเจียนพุ่งหรืออาเจียนหลายครั้ง",
                        "ซึมลง ปลุกไม่ตื่น พูดไม่รู้เรื่อง แขนขาอ่อนแรงครึ่งซีก",
                        "มีน้ำใสหรือเลือดไหลออกจากหูหรือจมูก",
                        "ตามัว เห็นภาพซ้อน หรือ pupil สองข้างไม่เท่ากัน"],
                    "follow_up": {"date": "กลับมาพบแพทย์หากมีอาการผิดปกติตาม red flags ข้างต้น", "location": "", "reason": ""}
                },
                "medication_box": {"start": [], "stop": [], "change": []}
            }

        # UTI / Urinary tract infection
        if any(w in prompt_lower for w in ["ปัสสาวะ", "แสบขัด", "uti", "urinary", "ปวดเบ่ง"]):
            return {
                **base,
                "patient_view": {
                    "headline": "สรุปคำแนะนำสำหรับผู้ป่วยติดเชื้อทางเดินปัสสาวะ",
                    "diagnosis": "การติดเชื้อทางเดินปัสสาวะ (Urinary Tract Infection / UTI)",
                    "key_instructions": [
                        "ดื่มน้ำสะอาดมาก ๆ อย่างน้อยวันละ 2-3 ลิตร",
                        "รับประทานยาฆ่าเชื้อจนหมดตามแพทย์สั่ง ห้ามหยุดยาเอง",
                        "ไม่กลั้นปัสสาวะ ควรเข้าห้องน้ำทันทีที่ปวด",
                        "ทำความสะอาดจากด้านหน้าไปด้านหลังทุกครั้ง"
                    ],
                    "red_flags": ["มีไข้สูงหนาวสั่น (อาจลามเป็นกรวยไตอักเสบ)",
                        "ปวดหลังหรือสีข้างรุนแรง",
                        "คลื่นไส้อาเจียนมากจนรับประทานยาไม่ได้",
                        "ปัสสาวะเป็นเลือดหรือมีหนองมากขึ้น"],
                    "follow_up": {"date": "กลับมาพบแพทย์หากอาการไม่ดีขึ้นใน 2-3 วัน", "location": "", "reason": ""}
                },
                "medication_box": {"start": [], "stop": [], "change": []}
            }

        # Cellulitis / Skin infection
        if any(w in prompt_lower for w in ["บวม", "แดง", "ร้อน", "cellulitis", "ฝี", "หนอง", "infection"]):
            return {
                **base,
                "patient_view": {
                    "headline": "สรุปคำแนะนำสำหรับผู้ป่วยที่มีการอักเสบของผิวหนัง",
                    "diagnosis": "ผิวหนังอักเสบติดเชื้อ (Cellulitis / Skin Abscess)",
                    "key_instructions": [
                        "ประคบด้วยน้ำอุ่นสะอาดบริเวณที่บวมแดง วันละ 3-4 ครั้ง",
                        "ยกส่วนที่บวมให้สูงกว่าระดับหัวใจเพื่อลดอาการบวม",
                        "รับประทานยาฆ่าเชื้อจนหมดตามแพทย์สั่ง ห้ามหยุดก่อน",
                        "รักษาความสะอาดบริเวณแผล หลีกเลี่ยงการแกะเกา"
                    ],
                    "red_flags": ["บริเวณบวมแดงขยายวงกว้างขึ้นอย่างรวดเร็ว หรือลามเป็นเส้นสีแดง",
                        "มีไข้สูงหนาวสั่น",
                        "ปวดรุนแรงมากขึ้นหรือมีหนองไหลมากขึ้น",
                        "มีอาการของภาวะติดเชื้อในกระแสเลือด: ไข้สูง สับสน ความดันต่ำ"],
                    "follow_up": {"date": "กลับมาตรวจดูแผลตามนัด หรือมาทันทีหากอาการแย่ลง", "location": "", "reason": ""}
                },
                "medication_box": {"start": [], "stop": [], "change": []}
            }

        # Animal bite / Rabies PEP
        if any(w in prompt_lower for w in ["หมากัด", "แมวกัด", "สุนัข", "rabies", "สัตว์กัด", "bite"]):
            return {
                **base,
                "patient_view": {
                    "headline": "สรุปคำแนะนำสำหรับผู้ถูกสัตว์กัด",
                    "diagnosis": "แผลถูกสัตว์กัด (Animal Bite — Rabies Observation Protocol)",
                    "key_instructions": [
                        "ล้างแผลด้วยสบู่และน้ำสะอาดอย่างน้อย 15 นาทีทันที",
                        "ไปรับวัคซีนป้องกันพิษสุนัขบ้าทุกครั้งตามนัด ห้ามขาด",
                        "หากสัตว์มีเจ้าของ ให้กักขังสังเกตอาการสัตว์ 10 วัน",
                        "หากสัตว์เป็นสัตว์จรจัดหรือตายภายใน 10 วัน ให้รีบพบแพทย์เพื่อรับ Rabies Immunoglobulin"
                    ],
                    "red_flags": ["มีอาการทางระบบประสาท เช่น กลืนลำบาก กลัวน้ำ สับสน",
                        "แผลมีอาการบวมแดงร้อน มีหนอง หรือมีไข้",
                        "หากสัตว์ที่กัดตายภายใน 10 วัน ให้รีบมาพบแพทย์ทันที"],
                    "follow_up": {"date": "มาตรวจแผลและรับวัคซีนตามนัดทุกครั้ง", "location": "", "reason": ""}
                },
                "medication_box": {"start": [], "stop": [], "change": []}
            }

        # Back pain / Musculoskeletal
        if any(w in prompt_lower for w in ["ปวดหลัง", "back pain", "ปวดกล้ามเนื้อ", "เคล็ด", "แพลง", "sciatica"]):
            return {
                **base,
                "patient_view": {
                    "headline": "สรุปคำแนะนำสำหรับอาการปวดหลังหรือกล้ามเนื้อ",
                    "diagnosis": "อาการปวดหลังหรือกล้ามเนื้อและเส้นเอ็นอักเสบ (Back Pain / Musculoskeletal Strain)",
                    "key_instructions": [
                        "ประคบเย็นในช่วง 48 ชั่วโมงแรก แล้วจึงเปลี่ยนเป็นประคบร้อน",
                        "หลีกเลี่ยงการยกของหนักหรือก้มเงยเป็นเวลา 1-2 สัปดาห์",
                        "บริหารร่างกายเบา ๆ ด้วยท่าที่ไม่ทำให้ปวดเพิ่มขึ้น",
                        "หากนั่งทำงานนาน ควรลุกเดินยืดเส้นทุก 1 ชั่วโมง"
                    ],
                    "red_flags": ["ปวดร้าวลงขาทั้งสองข้าง", "มีอาการชาหรืออ่อนแรงของขาทั้งสองข้าง",
                        "กลั้นปัสสาวะหรืออุจจาระไม่ได้", "ปวดรุนแรงมากขึ้นจนเดินไม่ได้",
                        "มีไข้ร่วมด้วยหรือประวัติอุบัติเหตุรุนแรง"],
                    "follow_up": {"date": "กลับมาพบแพทย์หากอาการไม่ดีขึ้นใน 1 สัปดาห์", "location": "", "reason": ""}
                },
                "medication_box": {"start": [], "stop": [], "change": []}
            }

        return {
            **base,
            "patient_view": {
                "headline": "สรุปคำแนะนำหลังออกจากห้องฉุกเฉิน",
                "diagnosis": "อาการทั่วไปที่พบในห้องฉุกเฉิน (General ED Discharge)",
                "key_instructions": [
                    "สังเกตอาการตนเองอย่างใกล้ชิด หากอาการแย่ลง ให้กลับมาพบแพทย์ทันที",
                    "พักผ่อนให้เพียงพอและดื่มน้ำสะอาดอย่างน้อยวันละ 8 แก้ว",
                    "รับประทานอาหารอ่อนย่อยง่าย หลีกเลี่ยงอาหารรสจัดและเครื่องดื่มแอลกอฮอล์"
                ],
                "red_flags": ["มีอาการผิดปกติรุนแรงขึ้น เช่น เจ็บแน่นหน้าอก หายใจลำบาก ซึมลง หรือหมดสติ"],
                "follow_up": {"date": "กลับมาพบแพทย์หากอาการไม่ดีขึ้น", "location": "", "reason": ""}
            },
            "medication_box": {"start": [], "stop": [], "change": []}
        }




def get_llm_adapter() -> BaseLLMAdapter:
    provider = (settings.DEFAULT_LLM_PROVIDER or "").lower()
    if provider == "openrouter":
        return OpenRouterAdapter()
    elif provider == "gemini":
        return GeminiAdapter()
    else:
        return OpenRouterAdapter()
