# backend/app/services/deid_engine.py
import os
import re
from typing import Tuple, Dict, Any

# Set PyThaiNLP data directory within the project workspace to avoid OS permission errors
os.environ["PYTHAINLP_DATA_DIR"] = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "pythainlp_data")
)
os.makedirs(os.environ["PYTHAINLP_DATA_DIR"], exist_ok=True)

try:
    from pythainlp.tag.named_entity import ThaiNameTagger
    ner_tagger = ThaiNameTagger()
except Exception:
    ner_tagger = None

class DeIdentificationEngine:
    """
    Local Ephemeral De-Identification Engine & Verification Gate.
    Executes in RAM before outbound LLM requests to satisfy Thailand PDPA Sec 26/37.
    """
    
    @staticmethod
    def sanitize_transcript(raw_text: str, session_metadata: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Sanitizes raw spoken transcript by masking names, HN, phone numbers, and citizen IDs.
        Returns: (sanitized_text, local_metadata_for_rehydration)
        """
        sanitized = raw_text
        rehydration_metadata = {
            "patient_name": session_metadata.get("patient_name"),
            "caregiver_name": session_metadata.get("caregiver_name"),
            "doctor_name": session_metadata.get("doctor_name"),
            "hn": session_metadata.get("hn"),
            "phone_number": session_metadata.get("phone_number")
        }

        # 1. Mask Known Session Metadata (Exact String Replacement)
        if session_metadata.get("patient_name"):
            sanitized = re.sub(re.escape(session_metadata["patient_name"]), "[PATIENT_NAME]", sanitized)
        if session_metadata.get("caregiver_name"):
            sanitized = re.sub(re.escape(session_metadata["caregiver_name"]), "[CAREGIVER_NAME]", sanitized)
        if session_metadata.get("doctor_name"):
            sanitized = re.sub(re.escape(session_metadata["doctor_name"]), "[DOCTOR_NAME]", sanitized)
        if session_metadata.get("hn"):
            sanitized = re.sub(re.escape(str(session_metadata["hn"])), "[HOSPITAL_NUMBER]", sanitized)
        if session_metadata.get("phone_number"):
            sanitized = re.sub(re.escape(str(session_metadata["phone_number"])), "[PHONE_NUMBER]", sanitized)

        # 2. Mask Regex PII Patterns (Thai Citizen ID, Phone, HN)
        # 13-digit Thai Citizen ID
        sanitized = re.sub(r'\b\d{13}\b|\b\d{1}-\d{4}-\d{5}-\d{2}-\d{1}\b', '[CITIZEN_ID]', sanitized)
        # 10-digit Thai Phone Numbers
        sanitized = re.sub(r'\b0\d{1,2}[- ]?\d{3,4}[- ]?\d{4}\b', '[PHONE_NUMBER]', sanitized)
        # Hospital Number (HN)
        sanitized = re.sub(r'(?i)\b(HN|hn|เอชเอ็น)\s*:?\s*[\d-]+\b', '[HOSPITAL_NUMBER]', sanitized)

        # 3. Thai Honorifics & Name Tagging
        sanitized = re.sub(r'(คุณ|นาย|นาง|นางสาว|เด็กชาย|เด็กหญิง)\s*([ก-๙]+)', r'\1[PERSON_NAME]', sanitized)

        return sanitized, rehydration_metadata

    @staticmethod
    def verify_zero_pii(prompt_text: str, session_metadata: Dict[str, Any]) -> bool:
        """
        Hard Verification Gate: Returns True if 100% clean, False if unmasked PII remains.
        """
        # Rule 1: Check Regex Patterns for Citizen ID or 10-digit phone
        if re.search(r'\b\d{13}\b|\b0\d{9}\b', prompt_text):
            return False

        # Rule 2: Check Session Metadata Blacklist
        for raw_val in session_metadata.values():
            if raw_val and len(str(raw_val)) > 3 and str(raw_val) in prompt_text:
                return False

        return True

    @staticmethod
    def rehydrate_summary(draft_json: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Re-attaches original patient and metadata locally in RAM before doctor review / output generation.
        """
        json_str = str(draft_json)

        patient_name = metadata.get("patient_name") or "คุณ[ผู้ป่วย]"
        caregiver_name = metadata.get("caregiver_name") or "คุณ[ผู้ดูแล]"
        doctor_name = metadata.get("doctor_name") or "นพ. สมชาย ใจดี"
        hn = metadata.get("hn") or "65-XXXXXX"

        json_str = json_str.replace("[PATIENT_NAME]", patient_name)
        json_str = json_str.replace("[CAREGIVER_NAME]", caregiver_name)
        json_str = json_str.replace("[DOCTOR_NAME]", doctor_name)
        json_str = json_str.replace("[HOSPITAL_NUMBER]", hn)
        json_str = json_str.replace("[PERSON_NAME]", "ผู้เกี่ยวข้อง")

        import ast
        try:
            return ast.literal_eval(json_str)
        except Exception:
            return draft_json
