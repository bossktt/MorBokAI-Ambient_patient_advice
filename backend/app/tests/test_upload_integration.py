import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

AUDIO_DIR = Path(__file__).resolve().parents[3] / "assets" / "voice test"


class TestUploadTranscriptionIntegration(unittest.TestCase):
    """End-to-end proof that an uploaded voice file is transcribed through the
    real HTTP endpoint. Requires network access to the ASR providers and the
    local test audio files in assets/voice test."""

    def test_uploaded_m4a_files_transcribe_via_http_endpoint(self):
        files = sorted(AUDIO_DIR.glob("*.m4a"))
        if not files:
            self.skipTest("No audio files in assets/voice test")
        tested = 0
        for path in files:
            with self.subTest(file=path.name):
                data = path.read_bytes()
                response = client.post(
                    "/api/v1/encounters/transcribe-audio",
                    content=data,
                    headers={"Content-Type": "audio/m4a", "X-Encounter-Id": "ENC_UPLOAD_TEST"},
                )
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload.get("status"), "SUCCESS")
                self.assertTrue(payload.get("transcript"), "transcript must be non-empty")
                tested += 1
        self.assertGreater(tested, 0)


if __name__ == "__main__":
    unittest.main()
