# backend/app/services/llm_adapter.py
"""
MorBok AI — Clinical LLM Adapter & Patient Summary Generation Engine
=====================================================================

Supported Providers:
  1. OpenRouter (google/gemini-2.5-flash) — Primary default.
  2. Gemini AI Studio — Direct fallback.

Pipeline: OpenRouter → Gemini → safe empty summary.
"""

from abc import ABC, abstractmethod
import json
import requests
from app.core.config import settings


class BaseLLMAdapter(ABC):
    @abstractmethod
    def generate_clinical_summary(self, sanitized_prompt: str) -> dict:
        pass


def empty_clinical_summary(reason: str = "") -> dict:
    """Safe result used when a provider is unavailable or output is invalid."""
    return {
        "patient_view": {
            "headline": "ต้องตรวจสอบข้อมูลก่อนออกเอกสาร",
            "diagnosis": "",
            "key_instructions": [],
            "home_care": [],
            "red_flags": [],
            "follow_up": {"date": "", "location": "", "reason": ""},
        },
        "medication_box": {"start": [], "stop": [], "change": []},
        "evidence": {},
        "_meta": {"status": "LLM_UNAVAILABLE", "reason": reason},
    }


def _normalise_for_evidence(value: str) -> str:
    return "".join(ch.lower() for ch in str(value or "") if ch.isalnum())


def _evidence_is_in_transcript(evidence: str, transcript: str) -> bool:
    evidence_norm = _normalise_for_evidence(evidence)
    transcript_norm = _normalise_for_evidence(transcript)
    return len(evidence_norm) >= 4 and evidence_norm in transcript_norm


def ground_summary_to_transcript(summary: dict, transcript: str) -> dict:
    """Drop every clinical fact that has no exact source evidence in the transcript."""
    if not isinstance(summary, dict):
        return empty_clinical_summary("LLM returned non-object JSON")

    patient_view = summary.get("patient_view") if isinstance(summary.get("patient_view"), dict) else {}
    medication_box = summary.get("medication_box") if isinstance(summary.get("medication_box"), dict) else {}
    evidence = summary.get("evidence") if isinstance(summary.get("evidence"), dict) else {}

    grounded = {
        "patient_view": {
            "headline": patient_view.get("headline") or "สรุปคำแนะนำ",
            "diagnosis": patient_view.get("diagnosis", "") if _evidence_is_in_transcript(evidence.get("diagnosis", ""), transcript) else "",
            "key_instructions": [],
            "home_care": [],
            "red_flags": [],
            "follow_up": {"date": "", "location": "", "reason": ""},
        },
        "medication_box": {"start": [], "stop": [], "change": []},
        "evidence": {},
    }

    instruction_evidence = evidence.get("key_instructions") if isinstance(evidence.get("key_instructions"), list) else []
    for index, instruction in enumerate(patient_view.get("key_instructions") or []):
        source = instruction_evidence[index] if index < len(instruction_evidence) else ""
        if _evidence_is_in_transcript(source, transcript):
            grounded["patient_view"]["key_instructions"].append(instruction)

    for field in ("home_care", "red_flags"):
        field_evidence = evidence.get(field) if isinstance(evidence.get(field), list) else []
        for index, item in enumerate(patient_view.get(field) or []):
            source = field_evidence[index] if index < len(field_evidence) else ""
            if _evidence_is_in_transcript(source, transcript):
                grounded["patient_view"][field].append(item)

    follow_up = patient_view.get("follow_up") if isinstance(patient_view.get("follow_up"), dict) else {}
    follow_up_source = evidence.get("follow_up", "")
    if _evidence_is_in_transcript(follow_up_source, transcript):
        grounded["patient_view"]["follow_up"] = follow_up

    for bucket in ("start", "stop", "change"):
        bucket_evidence = evidence.get(bucket) if isinstance(evidence.get(bucket), list) else []
        for index, item in enumerate(medication_box.get(bucket) or []):
            if not isinstance(item, dict):
                continue
            source = bucket_evidence[index] if index < len(bucket_evidence) else ""
            if _evidence_is_in_transcript(source, transcript):
                grounded["medication_box"][bucket].append(item)

    grounded["_meta"] = {
        "status": "GROUNDED",
        "dropped_unsupported_facts": True,
    }
    return grounded


# Shared clinical prompt template
CLINICAL_SYSTEM_PROMPT = """คุณคือระบบช่วยแพทย์ในห้องฉุกเฉิน (Emergency Department, Thailand).
อ่านบทสนทนาห้องตรวจที่ถอดเสียง แล้วสร้างสรุปภาษาไทยที่คนทั่วไปอ่านเข้าใจ

⚠️ ห้ามเด็ดขาด:
- ห้ามใช้ความรู้ส่วนตัวแต่งข้อมูล หากบทสนทนาไม่ได้ระบุ ให้เว้นว่างหรือใช้ array เปล่า []
- ห้ามคาดเดาชื่อยา ตัวสะกดยา ขนาดยา วิธีทาน หรือวันนัดที่แพทย์ไม่ได้พู​ด
- ห้ามแปลศัพท์แพทย์เป็นไทยผิด — หากไม่แน่ใจ ให้คงคำภาษาอังกฤษไว้ในวงเล็บ
- ห้ามใส่คำแนะนำเกี่ยวกับยาใน key_instructions — ข้อมูลยาทั้งหมดต้องอยู่ใน medication_box
- ห้ามเติมคำแนะนำทั่วไปที่ไม่ได้พูดถึงในบทสนทนาเด็ดขาด เช่น "ดื่มน้ำมาก ๆ" "พักผ่อนให้เพียงพอ" "รับประทานยาตามที่แพทย์หรือเภสัชกรแนะนำ" "กลับมาพบแพทย์หากมีไข้สูงติดต่อกัน 3 วัน" "ดื่มน้ำวันละ 8 แก้ว" — หากคำแนะนำนั้นไม่ได้ยินในบทสนทนา ให้ key_instructions เป็น [] และ red_flags เป็น []
- ห้ามตั้งชื่อยา หรือวินิจฉัยโรคเอง หากบทสนทนาไม่ได้พูดถึง ให้ใช้ค่าว่าง ""
- ทุกข้อเท็จจริงทางคลินิกต้องมีหลักฐานในช่อง evidence เป็นข้อความคัดลอกตรง ๆ จากบทสนทนา
- หากหา evidence ที่คัดลอกตรง ๆ ไม่ได้ ให้เว้นค่าข้อเท็จจริงนั้นว่าง และห้ามเดา
- ห้ามย่อ ตัดทอน หรือรวมคำแนะนำของแพทย์จนรายละเอียดหายไป
- ต้องเก็บคำแนะนำทุกข้อให้ครบทีละข้อ รวมตัวเลข ขนาดยา เวลา ความถี่ เงื่อนไข ข้อยกเว้น และคำเตือน
- หากมีคำแนะนำหลายข้อ ให้แยกเป็นหลายรายการตามต้นฉบับ ห้ามรวมเป็นประโยคสั้น ๆ เดียว

📐 ขั้นตอน:
1. วิเคราะห์บทสนทนา — มีการพูดถึงอะไรบ้าง: อาการ? ยา? การนัด? คำแนะนำแต่ละข้อ?
2. ถอดความครบทุกคำแนะนำโดยไม่ทำให้รายละเอียดลดลง หากไม่มีข้อมูลในส่วนใด ให้เว้นว่างหรือใส่ array เปล่า
3. เขียนเป็นภาษาไทยง่าย ๆ ที่คนอายุ 60+ อ่านเข้าใจ แต่ต้องรักษารายละเอียดทางคลินิกทั้งหมด

📤 ส่ง JSON เท่านี้ (ห้ามใส่ข้อความอื่น):
{{
  "patient_view": {{
    "headline": "สรุปคำแนะนำ",
    "diagnosis": "ข้อวินิจฉัยภาษาไทย (อังกฤษในวงเล็บ) — ถ้าไม่ระบุ ให้ใช้ค่าว่าง \"\",
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
  }},
  "evidence": {{
    "diagnosis": "ข้อความต้นฉบับที่รองรับ diagnosis หรือเว้นว่าง",
    "key_instructions": ["ข้อความต้นฉบับตามลำดับ หรือ []"],
    "home_care": ["ข้อความต้นฉบับตามลำดับ หรือ []"],
    "red_flags": ["ข้อความต้นฉบับตามลำดับ หรือ []"],
    "follow_up": "ข้อความต้นฉบับที่รองรับวันนัด หรือเว้นว่าง",
    "start": ["ข้อความต้นฉบับของยาเริ่มตามลำดับ หรือ []"],
    "stop": ["ข้อความต้นฉบับของยาหยุดตามลำดับ หรือ []"],
    "change": ["ข้อความต้นฉบับของยาปรับตามลำดับ หรือ []"]
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
            "response_format": {"type": "json_object"},
            "temperature": settings.SUMMARY_GENERATION_TEMPERATURE,
            "seed": settings.SUMMARY_GENERATION_SEED,
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
            print("Gemini API key missing/invalid, returning safe empty summary")
            return empty_clinical_summary("Gemini API key missing or invalid")

        model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash-lite")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        prompt_text = CLINICAL_SYSTEM_PROMPT.format(sanitized_prompt=sanitized_prompt)

        try:
            res = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt_text}]}],
                    "generationConfig": {
                        "temperature": settings.SUMMARY_GENERATION_TEMPERATURE,
                        "seed": settings.SUMMARY_GENERATION_SEED,
                        "responseMimeType": "application/json",
                    },
                },
                timeout=15
            )
            raw_res = res.json()
            if "error" in raw_res:
                print(f"Gemini error: {raw_res['error'].get('message', raw_res['error'])}")
                return empty_clinical_summary("Gemini provider error")

            out_text = raw_res["candidates"][0]["content"]["parts"][0]["text"]
            clean_text = out_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            print(f"Gemini exception: {e}")
            return empty_clinical_summary("Gemini response was invalid")


def get_llm_adapter() -> BaseLLMAdapter:
    provider = (settings.DEFAULT_LLM_PROVIDER or "").lower()
    if provider == "openrouter":
        return OpenRouterAdapter()
    elif provider == "gemini":
        return GeminiAdapter()
    else:
        return OpenRouterAdapter()
