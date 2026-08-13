import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.asr_service import MultiTierASRService
from app.services.llm_adapter import ground_summary_to_transcript


client = TestClient(app)


class TestTranscriptConsistency(unittest.TestCase):
    def test_asr_failure_never_returns_demo_transcript(self):
        with patch.object(settings, "OPENROUTER_API_KEY", None), patch.object(settings, "ASSEMBLYAI_API_KEY", None), patch.object(settings, "GCP_KEY_PATH", "/tmp/does-not-exist-gcp-key.json"):
            result = MultiTierASRService.transcribe_audio_result(b"\x00\x01" * 200)

        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.transcript, "")
        self.assertEqual(MultiTierASRService.transcribe_audio_bytes(b"\x00\x01" * 200), "")

    def test_grounding_drops_facts_without_exact_source_evidence(self):
        transcript = "แพทย์ปรับยา Metformin เป็น 1000 mg หลังอาหาร"
        summary = {
            "patient_view": {
                "headline": "สรุป",
                "diagnosis": "โรคไตเรื้อรัง",
                "key_instructions": ["รับประทาน Metformin หลังอาหาร"],
                "follow_up": {"date": "วันพรุ่งนี้", "location": "", "reason": ""},
            },
            "medication_box": {
                "change": [{"name": "Metformin", "new_instruction": "1000 mg หลังอาหาร"}],
                "start": [{"name": "Amlodipine", "how_to_take": "ก่อนนอน"}],
            },
            "evidence": {
                "diagnosis": "โรคไตเรื้อรัง",
                "key_instructions": ["Metformin เป็น 1000 mg หลังอาหาร"],
                "follow_up": "วันพรุ่งนี้",
                "change": ["ปรับยา Metformin เป็น 1000 mg หลังอาหาร"],
                "start": ["Amlodipine ก่อนนอน"],
            },
        }

        grounded = ground_summary_to_transcript(summary, transcript)
        self.assertEqual(grounded["patient_view"]["diagnosis"], "")
        self.assertEqual(grounded["patient_view"]["follow_up"]["date"], "")
        self.assertEqual(len(grounded["medication_box"]["change"]), 1)
        self.assertEqual(grounded["medication_box"]["start"], [])

    def test_process_transcript_does_not_use_generic_advice(self):
        with patch("app.main.get_llm_adapter") as get_adapter, patch("app.main.append_encounter_log"):
            get_adapter.return_value.generate_clinical_summary.return_value = {
                "patient_view": {"diagnosis": "โรคที่ไม่ได้พูดถึง", "key_instructions": ["คำแนะนำที่เดาเอง"]},
                "medication_box": {},
                "evidence": {},
            }
            response = client.post(
                "/api/v1/encounters/process-transcript",
                json={"raw_transcript": "แพทย์บอกให้พักผ่อน", "encounter_id": "ENC_TEST"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["diagnosis"], "")
        self.assertEqual(data["instructions"], [])
        self.assertEqual(data["startMeds"], [])


if __name__ == "__main__":
    unittest.main()
