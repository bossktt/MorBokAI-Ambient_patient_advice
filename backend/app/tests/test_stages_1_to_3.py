# backend/app/tests/test_stages_1_to_3.py
import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.services.asr_service import MultiTierASRService
from app.services.deid_engine import DeIdentificationEngine

client = TestClient(app)

class TestStages1To3(unittest.TestCase):

    def test_screen_1_and_2_encounter_creation(self):
        """
        Test Screen 1 & 2: Doctor Input & PDPA Consent creates encounter session.
        """
        print("\n--- Testing Screen 1 & 2: Encounter Creation with Doctor Info ---")
        doctor_payload = {
            "doctor_info": {
                "first_name": "วินัย",
                "surname": "ให้คำแนะนำ",
                "license_no": "12345"
            }
        }
        response = client.post("/api/v1/encounters/create", json=doctor_payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("encounter_id", data)
        self.assertEqual(data["status"], "CREATED")
        self.assertEqual(data["doctor_info"]["first_name"], "วินัย")
        self.assertEqual(data["doctor_info"]["license_no"], "12345")

        encounter_id = data["encounter_id"]
        print(f"✅ Screen 1 & 2 Passed: Created encounter {encounter_id} for Dr. วินัย ให้คำแนะนำ (ว.12345)!")

    def test_screen_3_asr_pipeline_and_deid(self):
        """
        Test Screen 3: Ambient Speech Transcription via Multi-Tier ASR & De-ID Engine.
        """
        print("\n--- Testing Screen 3: Ambient ASR & De-ID Engine ---")

        # Sample raw audio bytes simulation
        mock_audio_bytes = b"\x00\x01\x02\x03" * 100

        # Test Multi-Tier ASR Engine
        transcribed_text = MultiTierASRService.transcribe_audio_bytes(mock_audio_bytes)
        self.assertIsInstance(transcribed_text, str)
        self.assertGreater(len(transcribed_text), 0)

        # Test De-Identification Engine
        session_meta = {
            "patient_name": "คุณสมศรี ใจดี",
            "caregiver_name": "คุณสมศักดิ์ ใจดี",
            "doctor_name": "นพ. สมชาย ใจดี",
            "hn": "65-982314",
            "phone_number": "081-987-6543"
        }
        sanitized_text, meta = DeIdentificationEngine.sanitize_transcript(transcribed_text, session_meta)
        is_safe = DeIdentificationEngine.verify_zero_pii(sanitized_text, session_meta)

        self.assertTrue(is_safe)
        self.assertNotIn("คุณสมศรี", sanitized_text)
        self.assertNotIn("65-982314", sanitized_text)
        print(f"✅ Screen 3 Passed: Multi-Tier ASR transcribed text and De-ID Engine scrubbed all PHI safely!")

if __name__ == "__main__":
    unittest.main()
