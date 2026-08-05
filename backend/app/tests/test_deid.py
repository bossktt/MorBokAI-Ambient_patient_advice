# backend/app/tests/test_deid.py
import unittest
from app.services.deid_engine import DeIdentificationEngine

class TestDeIdentificationEngine(unittest.TestCase):

    def test_sanitize_and_verify_pii(self):
        raw_text = "สวัสดีครับ คุณสมชาย ใจดี HN 65-982314 เบอร์โทร 0819876543 ทานยา Metformin 1000mg"
        session_meta = {
            "patient_name": "สมชาย ใจดี",
            "caregiver_name": "สมศักดิ์",
            "doctor_name": "นพ.สมหมาย",
            "hn": "65-982314",
            "phone_number": "0819876543"
        }

        sanitized, meta = DeIdentificationEngine.sanitize_transcript(raw_text, session_meta)
        
        # 1. Assert PII was masked
        self.assertNotIn("สมชาย ใจดี", sanitized)
        self.assertNotIn("65-982314", sanitized)
        self.assertNotIn("0819876543", sanitized)
        self.assertIn("[PATIENT_NAME]", sanitized)

        # 2. Assert Verification Gate passes on sanitized text
        is_safe = DeIdentificationEngine.verify_zero_pii(sanitized, session_meta)
        self.assertTrue(is_safe)

        # 3. Assert Re-hydration works
        mock_summary = {
            "patient_view": {
                "headline": "สรุปคำแนะนำสำหรับ [PATIENT_NAME]",
                "instructions": ["ทานยาปรับระดับน้ำตาล"]
            }
        }
        rehydrated = DeIdentificationEngine.rehydrate_summary(mock_summary, meta)
        self.assertIn("สมชาย ใจดี", str(rehydrated))

if __name__ == "__main__":
    unittest.main()
