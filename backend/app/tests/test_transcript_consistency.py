import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.asr_service import ASRResult, MultiTierASRService, assess_transcript_quality
from app.services.llm_adapter import ground_summary_to_transcript


client = TestClient(app)


class TestTranscriptConsistency(unittest.TestCase):
    def test_asr_quality_gate_accepts_clinical_text_and_rejects_noise(self):
        accepted = assess_transcript_quality("แพทย์บอกให้พักผ่อนที่บ้าน")
        rejected = assess_transcript_quality("!!!! ????? ....")
        medium = assess_transcript_quality("แพทย์บอกให้พักผ่อนที่บ้าน", confidence=0.3)
        self.assertEqual(accepted["status"], "ACCEPT")
        self.assertEqual(accepted["grade"], "GOOD")
        self.assertGreaterEqual(accepted["score"], settings.ASR_QUALITY_MIN_SCORE)
        self.assertEqual(rejected["status"], "REJECT")
        self.assertEqual(rejected["grade"], "POOR")
        self.assertIn("too_much_non_speech_noise", rejected["reasons"])
        self.assertEqual(medium["grade"], "MEDIUM")
        self.assertEqual(medium["status"], "REJECT")

    def test_low_asr_quality_blocks_llm_call(self):
        with patch("app.main.get_llm_adapter") as get_adapter, patch("app.main.append_encounter_log"):
            response = client.post(
                "/api/v1/encounters/process-transcript",
                json={"encounter_id": "ENC_LOW_ASR", "raw_transcript": "!!!! ????? ...."},
            )

        data = response.json()
        self.assertEqual(data["status"], "CANNOT_EXTRACT_SAFELY")
        self.assertEqual(data["asr_quality"]["status"], "REJECT")
        get_adapter.assert_not_called()

    def test_asr_quality_result_is_written_to_encounter_log(self):
        quality = assess_transcript_quality("!!!! ????? ....")
        fake_result = ASRResult(
            transcript="!!!! ????? ....",
            status="SUCCESS",
            provider="test",
            model="test-model",
            quality=quality,
        )
        with patch("app.main.MultiTierASRService.transcribe_audio_result", return_value=fake_result), patch("app.main.append_encounter_log") as append_log:
            response = client.post(
                "/api/v1/encounters/transcribe-audio",
                headers={"X-Encounter-Id": "ENC_ASR_LOG"},
                content=b"audio-bytes",
            )

        self.assertEqual(response.status_code, 200)
        logged = append_log.call_args.args[0]
        self.assertEqual(logged["event"], "ASR_QUALITY_EVALUATED")
        self.assertEqual(logged["encounter_id"], "ENC_ASR_LOG")
        self.assertEqual(logged["asr_quality"]["status"], "REJECT")
        self.assertEqual(logged["asr_result"]["quality"]["status"], "REJECT")
        self.assertEqual(logged["asr_result"]["quality"]["score"], quality["score"])

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
        self.assertEqual(data["status"], "CANNOT_EXTRACT_SAFELY")
        self.assertEqual(data["clinical_extraction_status"], "CANNOT_EXTRACT_SAFELY")
        self.assertTrue(data["message"])

    def test_empty_transcript_returns_explicit_safe_empty_contract(self):
        response = client.post("/api/v1/encounters/process-transcript", json={"raw_transcript": ""})
        data = response.json()
        self.assertEqual(data["status"], "CANNOT_EXTRACT_SAFELY")
        self.assertEqual(data["clinical_extraction_status"], "CANNOT_EXTRACT_SAFELY")
        self.assertEqual(data["diagnosis"], "")
        self.assertEqual(data["instructions"], [])
        self.assertEqual(data["startMeds"], [])
        self.assertEqual(data["stopMeds"], [])
        self.assertEqual(data["changeMeds"], [])
        self.assertEqual(data["followUpDate"], "")

    def test_same_approved_transcript_returns_cached_summary(self):
        transcript = "แพทย์บอกให้พักผ่อนที่บ้าน"
        adapter_summary = {
            "patient_view": {
                "diagnosis": "พักผ่อนที่บ้าน",
                "key_instructions": ["ให้พักผ่อนที่บ้าน"],
                "follow_up": {"date": "", "location": "", "reason": ""},
            },
            "medication_box": {"start": [], "stop": [], "change": []},
            "evidence": {
                "diagnosis": "พักผ่อนที่บ้าน",
                "key_instructions": ["ให้พักผ่อนที่บ้าน"],
            },
        }
        with patch("app.main.get_llm_adapter") as get_adapter, patch("app.main.append_encounter_log"):
            get_adapter.return_value.generate_clinical_summary.return_value = adapter_summary
            payload = {"encounter_id": "ENC_CACHE_CONSISTENCY", "raw_transcript": transcript}
            first = client.post("/api/v1/encounters/process-transcript", json=payload).json()
            second = client.post("/api/v1/encounters/process-transcript", json=payload).json()

        self.assertEqual(first["summary_cache"]["status"], "MISS")
        self.assertEqual(second["summary_cache"]["status"], "HIT")
        self.assertEqual(get_adapter.return_value.generate_clinical_summary.call_count, 1)
        self.assertEqual(first["diagnosis"], second["diagnosis"])
        self.assertEqual(first["instructions"], second["instructions"])


if __name__ == "__main__":
    unittest.main()
