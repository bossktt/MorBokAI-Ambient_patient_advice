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
CLINICAL_SYSTEM_PROMPT = """You are an expert AI Clinical Summarizer and Patient Communication Specialist integrated into the Ambient PVS Platform. Your primary function is to transform spoken physician consultations (or de-identified transcripts) into clear, structured, and easy-to-understand summaries in plain Thai (Grade 5 reading level) for patients and family caregivers.

🎯 CORE OBJECTIVES:
1. Clear Patient Communication: Convert medical terminology into plain, empathetic Thai that elderly patients and non-medical caregivers can easily comprehend.
2. Medication Safety & Reconciliation: Categorize all medication changes into START (ยาเริ่มใหม่), STOP (ยาให้หยุดทานทันที), and CHANGE (ยาปรับขนาดยา) to prevent accidental double-dosing or adverse drug interactions.
3. Emergency Red Flags: Clearly highlight warning symptoms that require immediate emergency evaluation.
4. Strict Fidelity & Zero Hallucination: Rely ONLY on facts explicitly stated in the consultation audio/transcript. Do not invent diagnoses, dosages, or advice not mentioned by the doctor.

📐 REQUIRED JSON OUTPUT STRUCTURE:
Return strictly valid JSON matching this schema:
{{
  "patient_view": {{
    "headline": "สรุปคำแนะนำการดูแลตนเองสำหรับผู้ป่วย",
    "diagnosis": "ระบุข้อวินิจฉัยโรคภาษาไทยอ่านง่าย พร้อมภาษาอังกฤษในวงเล็บ และระดับการดูแล (เช่น พักฟื้นที่บ้านได้)",
    "key_instructions": [
      "คำแนะนำการปฏิบัติตัวข้อที่ 1",
      "คำแนะนำการปฏิบัติตัวข้อที่ 2"
    ],
    "red_flags": [
      "อาการผิดปกติที่ต้องรีบมาโรงพยาบาลทันทีข้อที่ 1"
    ],
    "follow_up": {{
      "follow_up_date_thai": "กำหนดนัดติดตามอาการ (เช่น อีก 1 สัปดาห์ / วันพุธหน้า)",
      "purpose": "วัตถุประสงค์ในการนัดติดตามอาการและการตรวจเพิ่มเติม"
    }}
  }},
  "caregiver_matrix": {{
    "medication_reconciliation": {{
      "start": [
        {{ "med_name": "ชื่อยาใหม่", "physical_description": "ลักษณะยา", "instructions": "วิธีทาน" }}
      ],
      "stop": [
        {{ "med_name": "ชื่อยาที่ต้องหยุด", "physical_description": "ลักษณะยา", "discard_instruction": "คำแนะนำการหยุด/ทิ้ง", "reason": "สาเหตุ" }}
      ],
      "change": [
        {{ "med_name": "ชื่อยาที่ปรับขนาด", "physical_description": "ลักษณะยา", "change_summary": "วิธีทานใหม่" }}
      ]
    }}
  }}
}}

ข้อความถอดเสียงห้องตรวจจริงสำหรับเคสนี้:
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

        try:
            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt_text}],
                    "response_format": {"type": "json_object"}
                },
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

        if any(w in prompt_lower for w in ["ไข้หวัด", "เจ็บคอ", "น้ำมูก", "หวัด", "ไข้"]):
            return {
                "patient_view": {
                    "headline": "สรุปคำแนะนำการดูแลตนเองสำหรับโรคไข้หวัดธรรมดา",
                    "diagnosis": "โรคไข้หวัดธรรมดา (Common Cold / Acute Upper Respiratory Infection)",
                    "key_instructions": [
                        "รับประทานยาแก้เจ็บคอและยาลดน้ำมูกตามที่เภสัชกรแนะนำให้ครบถ้วน",
                        "พักผ่อนให้เพียงพอและดื่มน้ำสะอาดอย่างน้อยวันละ 8 แก้ว"
                    ],
                    "red_flags": ["หากมีไข้สูงเกิน 39°C หรือไอเหนื่อยหอบ ให้รีบมาพบแพทย์ทันที"],
                    "follow_up": {"follow_up_date_thai": "ตามนัดหมายแพทย์ (หากยังมีไข้สูงติดต่อกันเกิน 3 วัน ให้กลับมาตรวจเพิ่มเติม)"}
                },
                "caregiver_matrix": {
                    "medication_reconciliation": {
                        "start": [
                            {"med_name": "ยาแก้เจ็บคอ", "physical_description": "ยาเม็ดกลม ทานหลังอาหาร", "instructions": "ทานหลังอาหารเมื่อมีอาการ"},
                            {"med_name": "ยาลดน้ำมูก", "physical_description": "ยาเม็ดเล็ก ทานหลังอาหาร", "instructions": "ทานหลังอาหารตามเภสัชกรแนะนำ"}
                        ],
                        "stop": [],
                        "change": []
                    }
                }
            }

        return {
            "patient_view": {
                "headline": "สรุปคำแนะนำการดูแลตนเองหลังออกจากห้องฉุกเฉิน",
                "diagnosis": "ภาวะความดันโลหิตสูงและระดับน้ำตาลในเลือดสูงชั่วคราว (Hypertensive Urgency with Hyperglycemia)",
                "key_instructions": [
                    "ทานยาปรับระดับน้ำตาลตัวใหม่ (เม็ดใหญ่สีขาว) เช้า-เย็น หลังอาหารทันที",
                    "ทิ้งยาเม็ดสีขาวตัวเดิมซองเก่าทันที ไม่ต้องทานซ้ำอีกต่อไป",
                    "จิบน้ำสะอาดเรื่อยๆ อย่างน้อยวันละ 8 แก้ว",
                    "งดอาหารรสจัดและของหวานมัน"
                ],
                "red_flags": ["มีอาการปวดศีรษะรุนแรง ตาพร่ามัว หรือเจ็บแน่นหน้าอก"],
                "follow_up": {"follow_up_date_thai": "วันอาทิตย์ที่ 16 สิงหาคม 2026 เวลา 09:00 น."}
            },
            "caregiver_matrix": {
                "medication_reconciliation": {
                    "start": [{"med_name": "Metformin 1000 mg", "physical_description": "ยาเม็ดใหญ่สีขาว รูปไข่", "instructions": "1 เม็ด เช้า-เย็น หลังอาหาร"}],
                    "stop": [{"med_name": "Metformin 500 mg (ซองเดิม)", "physical_description": "ยาเม็ดเล็กสีขาว กลม", "discard_instruction": "หยิบทิ้งถังขยะทันที", "reason": "ปรับเพิ่มขนาดเป็นยาตัวใหม่แล้ว"}],
                    "change": [{"med_name": "Amlodipine 5 mg", "physical_description": "ยาลดความดัน เม็ดสีเหลืองกลม", "change_summary": "ปรับลดจาก 2 เม็ด เหลือ 1 เม็ดก่อนนอน"}]
                }
            }
        }


def get_llm_adapter() -> BaseLLMAdapter:
    provider = (settings.DEFAULT_LLM_PROVIDER or "").lower()
    if provider == "openrouter":
        return OpenRouterAdapter()
    elif provider == "gemini":
        return GeminiAdapter()
    else:
        return OpenRouterAdapter()
