import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.asr_service import (
    ASRResult,
    MultiTierASRService,
    assess_dual_transcript_quality,
    assess_transcript_quality,
    deduplicate_repeated_sentences,
    detect_audio_file,
    ensure_wav_bytes,
)
from app.services.llm_adapter import ground_summary_to_transcript


client = TestClient(app)


class TestTranscriptConsistency(unittest.TestCase):
    def test_detect_m4a_magic_bytes(self):
        fake_m4a = b"\x00\x00\x00\x20ftypM4A " + b"\x00" * 100
        self.assertEqual(detect_audio_file(fake_m4a), ("audio.m4a", "audio/mp4"))
        self.assertEqual(ensure_wav_bytes(fake_m4a), fake_m4a)

    def test_detect_webm_magic_bytes(self):
        fake_webm = b"\x1aE\xdf\xa3" + b"\x00" * 100
        self.assertEqual(detect_audio_file(fake_webm), ("audio.webm", "audio/webm"))
        self.assertEqual(ensure_wav_bytes(fake_webm), fake_webm)

    def test_dual_asr_requires_agreement_on_critical_tokens(self):
        identical = assess_dual_transcript_quality(
            "แพทย์ปรับยา Metformin เป็น 1000 mg หลังอาหาร",
            "แพทย์ปรับยา Metformin เป็น 1000 mg หลังอาหาร",
        )
        numeric_diff = assess_dual_transcript_quality(
            "แพทย์ปรับยา Metformin เป็น 1000 mg หลังอาหาร",
            "แพทย์ปรับยา Metformin เป็น 500 mg หลังอาหาร",
        )
        self.assertEqual(identical["status"], "ACCEPT")
        self.assertEqual(identical["decision"], "ACCEPT")
        self.assertEqual(numeric_diff["status"], "ACCEPT")
        self.assertIn("numeric_disagreement", numeric_diff["warnings"])

    def test_length_gap_forces_review(self):
        result = assess_dual_transcript_quality(
            "หมอขอปรับเพิ่มยา Metformin เป็น 1000 mg เช้าเย็น หลังอาหารทันที "
            "แล้วให้ทิ้งยาตัวสีขาวเดิมซองเก่าทันทีเลยนะ ส่วนยาลดความดัน Amlodipine "
            "ให้ปรับลดเหลือ 1 เม็ดก่อนนอน นัดติดตามอาการคลินิกอายุรกรรมหัวใจ "
            "วันอาทิตย์ที่ 16 สิงหาคม 2026 เวลา 9:00 น.",
            "หมอสั่งยาครับ",
        )
        self.assertEqual(result["status"], "REJECT")
        self.assertEqual(result["decision"], "REVIEW_DISAGREEMENT")

    def test_poor_primary_transcript_is_rejected(self):
        result = assess_dual_transcript_quality(
            "!!!! ????? ....",
            "แพทย์บอกให้พักผ่อน",
        )
        self.assertEqual(result["status"], "REJECT")
        self.assertIn("primary_quality_rejected", result["reasons"])

    def test_missing_verifier_requires_review(self):
        result = assess_dual_transcript_quality(
            "แพทย์บอกให้พักผ่อนที่บ้าน",
            "!!!! ????? ....",
        )
        self.assertEqual(result["status"], "REJECT")
        self.assertEqual(result["decision"], "REVIEW_SINGLE_MODEL")
        self.assertIn("verifier_unavailable_or_poor", result["reasons"])

    def test_synonyms_and_fillers_do_not_block_agreement(self):
        result = assess_dual_transcript_quality(
            "สวัสดีครับ คนไข้เป็นโควิดนะครับ",
            "สวัสดีค่ะ ผู้ป่วยเป็นโควิดน่ะ",
        )
        self.assertEqual(result["critical_disagreement"], [])

    def test_low_agreement_without_critical_difference_is_accepted(self):
        result = assess_dual_transcript_quality(
            "ให้พักผ่อนมาก ๆ และทานยาตามเวลา",
            "หมอสั่งให้พักผ่อนและทานยาตามกำหนดเวลา",
        )
        self.assertEqual(result["critical_disagreement"], [])
        self.assertEqual(result["status"], "ACCEPT")
        self.assertIn(result["decision"], ("ACCEPT", "ACCEPT_LOW_AGREEMENT"))

    def test_repeated_asr_sentence_is_kept_once(self):
        repeated = "แพทย์บอกให้พักผ่อนที่บ้าน แพทย์บอกให้พักผ่อนที่บ้าน"
        self.assertEqual(deduplicate_repeated_sentences(repeated), "แพทย์บอกให้พักผ่อนที่บ้าน")

        punctuated = "ให้ดื่มน้ำมาก ๆ ครับ ให้ดื่มน้ำมาก ๆ ครับ"
        self.assertEqual(deduplicate_repeated_sentences(punctuated), "ให้ดื่มน้ำมาก ๆ ครับ")

    def test_quality_threshold_controls_acceptance(self):
        with patch.object(settings, "ASR_QUALITY_MIN_SCORE", 1.01):
            quality = assess_transcript_quality("แพทย์บอกให้พักผ่อนที่บ้าน")
        self.assertEqual(quality["status"], "REJECT")

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

    def test_process_transcript_proceeds_without_asr_quality_gate(self):
        with patch("app.main.get_llm_adapter") as get_adapter, patch("app.main.append_encounter_log"):
            get_adapter.return_value.generate_clinical_summary.return_value = {
                "patient_view": {"diagnosis": "พักผ่อน", "key_instructions": ["พักผ่อน"], "follow_up": {"date": "", "location": "", "reason": ""}},
                "medication_box": {},
                "evidence": {"diagnosis": "พักผ่อน", "key_instructions": ["พักผ่อน"]},
            }
            response = client.post(
                "/api/v1/encounters/process-transcript",
                json={"encounter_id": "ENC_LOW_ASR", "raw_transcript": "!!!! ????? ...."},
            )

        data = response.json()
        get_adapter.assert_called_once()

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
