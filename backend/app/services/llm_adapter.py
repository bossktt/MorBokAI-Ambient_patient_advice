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
    "diagnosis": "ระบุข้อวินิจฉัยโรคภาษาไทยอ่านง่าย พร้อมภาษาอังกฤษในวงเล็บ",
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
        """
        Emergency Department (ED) Fallback Clinical Summaries.
        Covers 8 common ED chief complaint patterns + 1 default general fallback condition.
        """
        prompt_lower = (sanitized_prompt or "").lower()

        # Palpitations Pattern (ใจสั่น / หัวใจเต้นเร็ว)
        if any(w in prompt_lower for w in ["ใจสั่น", "palpitations"]):
            return {
                "patient_view": {
                    "headline": "สรุปคำแนะนำการดูแลตนเองสำหรับอาการใจสั่น",
                    "diagnosis": "ภาวะใจสั่นและหัวใจเต้นผิดจังหวะชั่วคราว (Palpitations / Rule out Arrhythmia)",
                    "key_instructions": [
                        "พักผ่อนในที่อากาศถ่ายเทสะดวก หลีกเลี่ยงกาแฟ ชา เครื่องดื่มชูกำลัง และบุหรี่",
                        "สังเกตอาการหากมีอาการเวียนศีรษะหรือหน้ามืดให้นั่งพักทันที"
                    ],
                    "red_flags": ["มีอาการเจ็บแน่นหน้าอก หายใจลำบาก หรือหน้ามืดหมดสติ ให้มารพ. ทันที"],
                    "follow_up": {"follow_up_date_thai": "นัดตรวจคลินิกโรคหัวใจ 1 สัปดาห์"}
                },
                "caregiver_matrix": {
                    "medication_reconciliation": {
                        "start": [], "stop": [], "change": []
                    }
                }
            }

        # Pattern 1: Chest Pain / Cardiopulmonary (ปวดแน่นหน้าอก / กล้ามเนื้อหัวใจ)
        if any(w in prompt_lower for w in ["หน้าอก", "แน่นหน้าอก", "เจ็บหน้าอก", "หัวใจ", "chest pain"]):
            return {
                "patient_view": {
                    "headline": "สรุปคำแนะนำการดูแลตนเองสำหรับอาการเจ็บแน่นหน้าอก",
                    "diagnosis": "ภาวะเจ็บแน่นหน้าอกชั่วคราว (unstable angina / Rule out Chronic Coronary Syndrome)",
                    "key_instructions": [
                        "อมยาใต้ลิ้น ทันที 1 เม็ด เมื่อเริ่มมีอาการเจ็บแน่นหน้าอก ทานได้ทุก 15 นาที แต่ถ้าไม่หายเลยให้มารพ ",
                        "หลีกเลี่ยงการออกกำลังหนัก การยกของหนัก และภาวะเครียดบวมตระหนก",
                        "พักผ่อนให้เพียงพอ งดสูบบุหรี่ และงดอาหารที่มีไขมันสูง"
                    ],
                    "red_flags": ["หากมีอาการแน่นหน้าอกรุนแรง เหงื่อออกตัวเย็น ร้าวไปที่แขนซ้ายหรือกราม ให้โทร 1669 มาโรงพยาบาลทันที"],
                    "follow_up": {"follow_up_date_thai": "เดี๋ยวถ้ามีอาการให้มาโรงพยบาล"}
                },
                "caregiver_matrix": {
                    "medication_reconciliation": {
                        "start": [
                            {"med_name": "Isordil 5 mg", "physical_description": "ยาเม็ดเล็กสีขาว", "instructions": "อมใต้ลิ้น 1 เม็ด ทันทีที่มีอาการเจ็บแน่นหน้าอก"}
                        ],
                        "stop": [
                            {"med_name": "ยาแก้ปวดคลายกล้ามเนื้อเดิม (NSAIDs)", "physical_description": "ซองเดิม", "discard_instruction": "หยุดทานทันที", "reason": "อาจเพิ่มความเสี่ยงต่อโรคหัวใจและหลอดเลือด"}
                        ],
                        "change": [
                            
                        ]
                    }
                }
            }

        # Pattern 2: Acute Abdominal Pain / GI (ปวดท้องเฉียบพลัน / กระเพาะอักเสบ / ลำไส้อักเสบ)
        if any(w in prompt_lower for w in ["ปวดท้อง", "กระเพาะ", "ท้องเสีย", "ถ่ายเหลว", "อาเจียน", "คลื่นไส้", "abdominal pain"]):
            return {
                "patient_view": {
                    "headline": "สรุปคำแนะนำการดูแลตนเองสำหรับอาการปวดท้อง / ลำไส้อักเสบ",
                    "diagnosis": "ภาวะกระเพาะอาหารและลำไส้อักเสบเฉียบพลัน (Acute Gastroenteritis / Acute Gastritis)",
                    "key_instructions": [
                        "จิบน้ำเกลือแร่ ORS ทีละน้อยตลอดทั้งวัน เพื่อป้องกันร่างกายช็อกจากการขาดน้ำ",
                        "รับประทานอาหารอ่อน ย่อยง่าย รสไม่จัด เช่น โจ๊ก ข้าวต้ม งดนมและอาหารมันจัด",
                        "ทานยาแก้ปวดเกร็งท้อง (Hyoscine) ก่อนอาหารเมื่อมีอาการปวดเกร็ง"
                    ],
                    "red_flags": ["ถ่ายอุจจาระมีมูกเลือด ปวดท้องรุนแรงกดเจ็บด้านขวาล่าง หรือมีไข้สูงหนาวสั่น"],
                    "follow_up": {"follow_up_date_thai": "ยังไม่มีนัด (หากถ่ายเหลวเกิน 3 วัน หรือกินอาหารไม่ได้ ให้กลับมาพบแพทย์)"}
                },
                "caregiver_matrix": {
                    "medication_reconciliation": {
                        "start": [
                            {"med_name": "ผงเกลือแร่ ORS", "physical_description": "ซองผงชงน้ำ", "instructions": "ละลายน้ำสะอาด 1 ซอง จิบแทนน้ำเมื่อถ่ายเหลว"},
                            {"med_name": "Hyoscine 10 mg", "physical_description": "ยาเม็ดกลมสีขาว", "instructions": "1 เม็ด ก่อนอาหาร 3 มื้อ เวลามีอาการปวดเกร็ง"}
                        ],
                        "stop": [
                            {"med_name": "ยาแก้ปวดกลุ่ม NSAIDs เดิม", "physical_description": "ซองเดิม", "discard_instruction": "หยุดทานทันที", "reason": "ระคายเคืองกระเพาะอาหารและทำให้ปวดท้องรุนแรงขึ้น"}
                        ],
                        "change": [
                            
                        ]
                    }
                }
            }

        # Pattern 3:  Dizziness / Severe Headache (เวียนศีรษะ / ปวดศีรษะ)
        if any(w in prompt_lower for w in ["ความดัน", "เวียนหัว", "เวียนศีรษะ", "บ้านหมุน", "ปวดหัว", "ปวดศีรษะ", "hypertension"]):
            return {
                "patient_view": {
                    "headline": "สรุปคำแนะนำการดูแลตนเองสำหรับภาวะความดันโลหิตสูงและเวียนศีรษะ",
                    "diagnosis": "  อาการเวียนศีรษะ (Vertigo)",
                    "key_instructions": [
                        "ลุกจากที่นอนช้าๆ",
                        "หลีกเลี่ยงการขับรถ หรือทำงานกับเครื่องจักร ช่วงที่มีอาการ",
                        "หากมีอาการปวดศีรษะร่วมด้วย ให้รีบมาพบแพทย์"
                    ],
                    "red_flags": ["มีอาการแขนขาอ่อนแรงครึ่งซีก ปากเบี้ยว พูดไม่ชัด หรือปวดศีรษะรุนแรงเฉียบพลัน"],
                    "follow_up": {"follow_up_date_thai": "นัดห้องตรวจหู คอ จมูก สัปดาห์หน้า"}
                },
                "caregiver_matrix": {
                    "medication_reconciliation": {
                        "start": [
                            {"med_name": "Dimenhydrinate 50 mg", "physical_description": "ยาเม็ดสีเหลืองกลม", "instructions": "1 เม็ด ทานได้ทุก 8 ชั่วโมง"}
                        ],
                        "stop": [
                            {"med_name": "ยาแก้เวียนศีรษะซองเก่า", "physical_description": "ซองเดิม", "discard_instruction": "หยุดทานเมื่อหายเวียนศีรษะ", "reason": "รับประทานเฉพาะเมื่อมีอาการเท่านั้น"}
                        ],
                        "change": [
                           
                        ]
                    }
                }
            }

        # Pattern 4: Respiratory / Asthma / Shortness of Breath (หอบหืด / หายใจเหนื่อย / หลอดลมอักเสบ)
        if any(w in prompt_lower for w in ["หอบ", "เหนื่อย", "หายใจ", "หอบหืด", "หลอดลม", "asthma", "dyspnea"]):
            return {
                "patient_view": {
                    "headline": "สรุปคำแนะนำการดูแลตนเองสำหรับโรคหอบหืดและทางเดินหายใจ",
                    "diagnosis": "โรคหอบหืดกำเริบเฉียบพลัน / หลอดลมอักเสบ (Acute Asthma Exacerbation / Acute Bronchitis)",
                    "key_instructions": [
                        "สูดพ่นยาขยายหลอดลม (Ventolin Evohaler) 2 ปั๊ม ทันทีที่มีอาการหอบเหนื่อย",
                        "บ้วนปากและคอด้วยน้ำสะอาดทุกครั้งหลังใช้สูดยาสเตียรอยด์เพื่อป้องกันเชื้อราในปาก",
                        "หลีกเลี่ยงควันบุหรี่ ควันธูป ควันไฟ ฝุ่น PM2.5 และสารก่อภูมิแพ้"
                    ],
                    "red_flags": ["หายใจมีเสียงหวีดรุนแรง พูดได้ไม่เป็นประโยค หายใจปีกจมูกบาน หรือริมฝีปากเขียวคล้ำ ให้มาโรงพยาบาล"],
                    "follow_up": {"follow_up_date_thai": "นัดดูอาการคลินิกโรคระบบหายใจ สัปดาห์หน้า"}
                },
                "caregiver_matrix": {
                    "medication_reconciliation": {
                        "start": [
                            {"med_name": "Ventolin Inhaler 100 mcg", "physical_description": "หลอดพ่นสีฟ้า", "instructions": "สูดพ่น 2 ปั๊ม เวลามีอาการหอบเหนื่อย"},
                            {"med_name": "Prednisolone 5 mg", "physical_description": "ยาเม็ดสีขาวเล็ก", "change_summary": "ทาน 6 เม็ด หลังอาหารเช้าทันที ติดต่อกัน 5 วันแล้วหยุด"}
                        ],
                        "stop": [
                            {"med_name": "ยาแก้ไอชนิดน้ำเชื่อมที่มีโคเดอีน", "physical_description": "ขวดเดิม", "discard_instruction": "หยุดทานทันที", "reason": "อาจกดการหายใจทำให้หอบเหนื่อยมากขึ้น"}
                        ],
                        "change": [
                            
                        ]
                    }
                }
            }

        # Pattern 5: Fever / Infection / Flu (ไข้สูง / ไข้หวัดใหญ่ / ติดเชื้อ)
        if any(w in prompt_lower for w in ["ไข้", "หนาวสั่น", "ไข้หวัด", "เจ็บคอ", "น้ำมูก", "หวัด", "fever"]):
            return {
                "patient_view": {
                    "headline": "สรุปคำแนะนำการดูแลตนเองสำหรับโรคไข้หวัดธรรมดา / ไข้สูง",
                    "diagnosis": "โรคไข้หวัดธรรมดา / ไข้หวัดใหญ่เฉียบพลัน (Common Cold / Acute Upper Respiratory Infection)",
                    "key_instructions": [
                        "เช็ดตัวลดไข้ด้วยน้ำธรรมดาอย่างสม่ำเสมอเมื่อมีไข้สูง",
                        "รับประทานยาพาราเซตามอลเมื่อมีไข้ ห้ามทานเกินวันละ 8 เม็ด",
                        "พักผ่อนให้เพียงพอและดื่มน้ำสะอาดวันละ 8-10 แก้ว"
                    ],
                    "red_flags": ["หากมีไข้สูงเกิน 39°C ติดต่อกันเกิน 3 วัน หรือมีจุดเลือดออกตามผิวหนัง ให้กลับมาพบแพทย์ทันที"],
                    "follow_up": {"follow_up_date_thai": "ตามนัดหมายแพทย์ (หากอาการไม่ดีขึ้นใน 3 วัน ให้มาตรวจเพิ่มเติม)"}
                },
                "caregiver_matrix": {
                    "medication_reconciliation": {
                        "start": [
                            {"med_name": "Paracetamol 500 mg", "physical_description": "ยาเม็ดสีขาวกลม", "instructions": "1 เม็ด ทุก 4-6 ชั่วโมง เวลามีไข้สูง"},
                            {"med_name": "Loratadine 10 mg", "physical_description": "ยาเม็ดเล็กสีขาว", "instructions": "1 เม็ด ก่อนนอน แก้แพ้ลดน้ำมูก"}
                        ],
                        "stop": [
                            {"med_name": "ยาแก้ปวด Ibuprofen / Naproxen", "physical_description": "ซองเดิม", "discard_instruction": "งดรับประทานชั่วคราว", "reason": "ระวังภาวะเลือดออกง่ายในกรณีเป็นไข้เลือดออก"}
                        ],
                        "change": []
                    }
                }
            }

        # Pattern 6: Diabetes / Hyperglycemia (เบาหวาน / น้ำตาลในเลือดสูง)
        if any(w in prompt_lower for w in ["เบาหวาน", "น้ำตาล", "ปัสสาวะบ่อย", "หิวน้ำ", "diabetes", "hyperglycemia"]):
            return {
                "patient_view": {
                    "headline": "สรุปคำแนะนำการดูแลตนเองสำหรับภาวะระดับน้ำตาลในเลือดสูง",
                    "diagnosis": "ภาวะระดับน้ำตาลในเลือดสูงชั่วคราวในผู้ป่วยเบาหวาน (Uncontrolled Diabetes Mellitus with Hyperglycemia)",
                    "key_instructions": [
                        "รับประทานยาคุมระดับน้ำตาลอย่างเคร่งครัดตรงเวลาทุกมื้อ",
                        "งดเครื่องดื่มชานม น้ำหวาน ผลไม้รสหวานจัด และขนมเบเกอรี่",
                        "จิบน้ำสะอาดเรื่อยๆ อย่างน้อยวันละ 8 แก้ว"
                    ],
                    "red_flags": ["มีอาการหอบหายใจลึก ลมหายใจมีกลิ่นหวานคล้ายผลไม้ ซึม สับสน หรือหมดสติ"],
                    "follow_up": {"follow_up_date_thai": "วันอาทิตย์ที่ 16 สิงหาคม 2026 เวลา 09:00 น. คลินิกเบาหวาน"}
                },
                "caregiver_matrix": {
                    "medication_reconciliation": {
                        "start": [
                            {"med_name": "Metformin 1000 mg", "physical_description": "ยาเม็ดใหญ่สีขาว รูปไข่", "instructions": "1 เม็ด เช้า-เย็น หลังอาหารทันที"}
                        ],
                        "stop": [
                            {"med_name": "Metformin 500 mg (ซองเดิม)", "physical_description": "ยาเม็ดเล็กสีขาว กลม", "discard_instruction": "หยิบทิ้งถังขยะทันที", "reason": "ปรับเพิ่มขนาดเป็นยาตัวใหม่แล้ว"}
                        ],
                        "change": [
                            {"med_name": "Glipizide 5 mg", "physical_description": "ยาเม็ดสีขาวแบ่งครึ่ง", "change_summary": "ปรับเพิ่มเป็น 1 เม็ด ก่อนอาหารเช้า 30 นาที"}
                        ]
                    }
                }
            }

        # Pattern 7: Trauma / Wounds / Injuries (อุบัติเหตุ / แผล / เลือดออก / กระดูก)
        if any(w in prompt_lower for w in ["อุบัติเหตุ", "แผล", "ล้ม", "ชน", "กระดูก", "ฟกช้ำ", "trauma", "wound"]):
            return {
                "patient_view": {
                    "headline": "สรุปคำแนะนำการดูแลตนเองสำหรับแผลอุบัติเหตุและการบาดเจ็บ",
                    "diagnosis": "แผลฉีกขาดและบาดเจ็บจากการล้ม/อุบัติเหตุ (Laceration Wound with Soft Tissue Contusion)",
                    "key_instructions": [
                        "ระวังอย่าให้แผลโดนน้ำเป็นเวลา 7 วัน จนกว่าแผลจะแห้งสนิทหรือตัดไหม",
                        "มาทำแผลที่สถานพยาบาลใกล้บ้านทุก 1-2 วันตามแพทย์สั่ง",
                        "ทานยาปฏิชีวนะ (ยาฆ่าเชื้อ) ให้หมดครบตามจำนวนเม็ดที่จ่าย ห้ามหยุดยาเอง"
                    ],
                    "red_flags": ["บริเวณแผลมีอาการบวมแดงร้อน มีมูกหนองไหล ปวดแผลรุนแรงขึ้น หรือมีไข้สูง"],
                    "follow_up": {"follow_up_date_thai": "วันอาทิตย์ที่ 16 สิงหาคม 2026 เวลา 09:00 น. เพื่อตัดไหมและตรวจแผล"}
                },
                "caregiver_matrix": {
                    "medication_reconciliation": {
                        "start": [
                            {"med_name": "Dicloxacillin 250 mg", "physical_description": "แคปซูลสีฟ้า-ขาว", "instructions": "1 แคปซูล ก่อนอาหาร 4 มื้อ (เช้า เที่ยง เย็น ก่อนนอน)"},
                            {"med_name": "Paracetamol 500 mg", "physical_description": "ยาเม็ดสีขาวกลม", "instructions": "1 เม็ด ทุก 6 ชั่วโมง เวลามีอาการปวดแผล"}
                        ],
                        "stop": [
                            
                        ],
                        "change": []
                    }
                }
            }

        # Pattern 8: Allergy / Anaphylaxis / Urticaria (แพ้ยา / แพ้อาหาร / ผื่นคัน)
        if any(w in prompt_lower for w in ["แพ้", "ผื่น", "คัน", "บวม", "แพ้อาหาร", "แพ้อย่างรุนแรง", "allergy", "urticaria"]):
            return {
                "patient_view": {
                    "headline": "สรุปคำแนะนำการดูแลตนเองสำหรับอาการแพ้และผื่นคันเฉียบพลัน",
                    "diagnosis": "ภาวะผื่นคันภูมิแพ้เฉียบพลัน / สงสัยอาการแพ้ยาหรืออาหาร (Acute Urticaria / Allergic Reaction)",
                    "key_instructions": [
                        "หยุดรับประทานยาหรืออาหารที่สงสัยว่าเป็นสาเหตุของการแพ้ทันที",
                        "รับประทานยาแก้แพ้ (Cetirizine) วันละ 1 เม็ดก่อนนอน เพื่อลดอาการคันและผื่นบวม",
                        "หลีกเลี่ยงการเกาบริเวณผื่นคันเพื่อป้องกันแผลติดเชื้อแบคทีเรียแทรกซ้อน"
                    ],
                    "red_flags": ["มีอาการแน่นหน้าอก หายใจเสียงหวีด ตาบวม ปากบวม หรือกลืนอาหารลำบาก (รีบมาห้องฉุกเฉินทันที)"],
                    "follow_up": {"follow_up_date_thai": "ตามนัดหมายแพทย์ (หากผื่นไม่ลดลงใน 3 วัน ให้กลับมาตรวจเพิ่มเติม)"}
                },
                "caregiver_matrix": {
                    "medication_reconciliation": {
                        "start": [
                            {"med_name": "Cetirizine 10 mg", "physical_description": "ยาเม็ดเล็กสีขาว", "instructions": "1 เม็ด ก่อนนอน เพื่อลดอาการคันและผื่น"}
                        ],
                        "stop": [
                            {"med_name": "ยาอาหารสงสัยแพ้ตัวใหม่", "physical_description": "ตัวยาใหม่ที่เพิ่งเริ่มทาน", "discard_instruction": "หยุดรับประทานทันที", "reason": "สงสัยเป็นสาเหตุของการเกิดผื่นแพ้"}
                        ],
                        "change": []
                    }
                }
            }

        # Pattern 9: Default Fallback (ภาวะฉุกเฉินทั่วไป / General Emergency Discharge)
        return {
            "patient_view": {
                "headline": "สรุปคำแนะนำการดูแลตนเองหลังออกจากห้องฉุกเฉิน",
                "diagnosis": "ภาวะความดันโลหิตสูงและระดับน้ำตาลในเลือดสูงชั่วคราว (Hypertensive Urgency with Hyperglycemia)",
                "key_instructions": [
                    "รับประทานยาปรับระดับน้ำตาลและยาลดความดันตามคำสั่งแพทย์อย่างเคร่งครัด",
                    "ทิ้งยาเม็ดสีขาวตัวเดิมซองเก่าทันที ไม่นำกลับมารับประทานซ้ำ",
                    "จิบน้ำสะอาดเรื่อยๆ อย่างน้อยวันละ 8 แก้ว และพักผ่อนให้เพียงพอ",
                    "งดอาหารรสเค็มจัด อาหารมัน และของหวานทุกชนิด"
                ],
                "red_flags": ["มีอาการปวดศีรษะรุนแรง ตาพร่ามัว เจ็บแน่นหน้าอก หรือซึมลง ให้กลับมาห้องฉุกเฉินทันที"],
                "follow_up": {"follow_up_date_thai": "วันอาทิตย์ที่ 16 สิงหาคม 2026 เวลา 09:00 น. คลินิกอายุรกรรม"}
            },
            "caregiver_matrix": {
                "medication_reconciliation": {
                    "start": [{"med_name": "Metformin 1000 mg", "physical_description": "ยาเม็ดใหญ่สีขาว รูปไข่", "instructions": "1 เม็ด เช้า-เย็น หลังอาหารทันที"}],
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
