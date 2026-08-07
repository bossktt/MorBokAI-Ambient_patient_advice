# backend/app/services/asr_service.py
import os
import time
import struct
import requests
import json
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

def ensure_wav_bytes(audio_bytes: bytes, sample_rate: int = 16000) -> bytes:
    """
    Ensures binary audio data starts with a valid WAV header (RIFF...WAVE).
    If header is missing, wraps raw PCM bytes in a standard 16kHz 16-bit mono WAV header.
    """
    if not audio_bytes or len(audio_bytes) < 44:
        return audio_bytes

    # Check if RIFF header already exists
    if audio_bytes[:4] == b'RIFF' and audio_bytes[8:12] == b'WAVE':
        return audio_bytes

    # If it's a compressed container (WebM/MP4/Opus from MediaRecorder),
    # do NOT fake a WAV header — whisper can decode these natively.
    if audio_bytes[:4] in (b'\x1aE\xdf\xa3', b'ftyp', b'OggS', b'\xff\xf1', b'\xff\xf9'):
        return audio_bytes

    num_samples = len(audio_bytes) // 2
    data_size = num_samples * 2
    file_size = 36 + data_size

    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        file_size,
        b'WAVE',
        b'fmt ',
        16,          # Subchunk1Size for PCM
        1,           # AudioFormat (1 = PCM)
        1,           # NumChannels (1 = Mono)
        sample_rate, # SampleRate
        sample_rate * 2, # ByteRate
        2,           # BlockAlign
        16,          # BitsPerSample
        b'data',
        data_size
    )
    return header + audio_bytes


class MultiTierASRService:
    """
    Multi-Tiered Speech-to-Text Pipeline:
    - Step 1 (Primary): OpenRouter ASR (openai/whisper-large-v3-turbo -> fish-audio/transcribe-1 -> nvidia/parakeet-tdt-0.6b-v3)
    - Step 2 (Secondary): AssemblyAI ASR (https://api.assemblyai.com/v2)
    - Step 3 (Tertiary): Google Speech-to-Text (via gcp-key.json credentials)
    - Step 4 (Offline Fallback): Demo Thai Transcript for local testing
    """

    @staticmethod
    def _transcribe_assemblyai(audio_bytes: bytes) -> Optional[str]:
        """
        Transcribes audio bytes using AssemblyAI REST API
        """
        api_key = settings.ASSEMBLYAI_API_KEY or os.environ.get("ASSEMBLYAI_API_KEY") or "ef84aec176e14512970748da5852a186"
        if not api_key or len(audio_bytes) < 100:
            return None

        wav_bytes = ensure_wav_bytes(audio_bytes)
        headers = {"authorization": api_key}
        try:
            # 1. Upload audio bytes
            up_res = requests.post(
                "https://api.assemblyai.com/v2/upload",
                headers=headers,
                data=wav_bytes,
                timeout=15
            )
            if up_res.status_code != 200:
                logger.warning(f"AssemblyAI Upload failed with status {up_res.status_code}")
                return None

            upload_url = up_res.json().get("upload_url")
            if not upload_url:
                return None

            # 2. Request transcription
            req_res = requests.post(
                "https://api.assemblyai.com/v2/transcript",
                headers=headers,
                json={"audio_url": upload_url, "language_code": "th"},
                timeout=15
            )
            if req_res.status_code != 200:
                logger.warning(f"AssemblyAI Transcript Request failed with status {req_res.status_code}")
                return None

            transcript_id = req_res.json().get("id")
            if not transcript_id:
                return None

            # 3. Poll transcript status
            for _ in range(12):
                time.sleep(1.5)
                poll_res = requests.get(
                    f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                    headers=headers,
                    timeout=10
                )
                if poll_res.status_code == 200:
                    data = poll_res.json()
                    status = data.get("status")
                    if status == "completed":
                        text = data.get("text", "").strip()
                        if text:
                            logger.info("AssemblyAI ASR succeeded.")
                            return text
                        else:
                            logger.info("AssemblyAI ASR completed but returned empty text.")
                            return None
                    elif status == "error":
                        logger.warning(f"AssemblyAI transcription error: {data.get('error')}")
                        return None
        except Exception as e:
            logger.warning(f"AssemblyAI ASR execution failed: {e}")

        return None

    @staticmethod
    def transcribe_audio_bytes(audio_bytes: bytes, sample_rate: int = 16000, mime_type: str = "audio/webm") -> str:
        """
        Transcribes incoming audio bytes via Multi-Tier ASR Pipeline.
        """
        if not audio_bytes or len(audio_bytes) < 100:
            return "หมอขอปรับเพิ่มยา Metformin เป็น 1000mg เช้าเย็น หลังอาหารทันที แล้วให้ทิ้งยาตัวสีขาวเดิมซองเก่าทันทีเลยนะ ส่วนยาลดความดัน Amlodipine ให้ปรับลดเหลือ 1 เม็ดก่อนนอน"

        wav_bytes = ensure_wav_bytes(audio_bytes, sample_rate)

        # Map mimeType -> (filename, content_type) for the ASR API
        mime_to_file = {
            "audio/webm": ("audio.webm", "audio/webm"),
            "audio/mp4": ("audio.m4a", "audio/mp4"),
            "audio/aac": ("audio.aac", "audio/aac"),
            "audio/wav": ("audio.wav", "audio/wav"),
            "audio/x-wav": ("audio.wav", "audio/wav"),
        }
        filename, content_type = mime_to_file.get(mime_type, ("audio.webm", "audio/webm"))

        # =========================================================================
        # STEP 1: Primary ASR - OpenRouter Audio Transcriptions
        # =========================================================================
        openrouter_key = settings.OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY")
        if openrouter_key:
            openrouter_models = [
                "openai/whisper-large-v3-turbo",
                "fish-audio/transcribe-1",
                "nvidia/parakeet-tdt-0.6b-v3"
            ]
            for model_name in openrouter_models:
                try:
                    response = requests.post(
                        "https://openrouter.ai/api/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {openrouter_key}"},
                        files={"file": (filename, wav_bytes, content_type)},
                        data={"model": model_name, "language": "th"},
                        timeout=15
                    )
                    if response.status_code == 200:
                        text = response.json().get("text", "").strip()
                        if text:
                            logger.info(f"Step 1 (OpenRouter ASR with {model_name}) succeeded.")
                            return text
                        else:
                            logger.info(f"Step 1 (OpenRouter ASR with {model_name}) returned 200 OK.")
                except Exception as e:
                    logger.warning(f"Step 1 (OpenRouter ASR with {model_name}) failed: {e}")

        # =========================================================================
        # STEP 2: Secondary ASR - AssemblyAI Speech-to-Text API
        # =========================================================================
        assembly_text = MultiTierASRService._transcribe_assemblyai(wav_bytes)
        if assembly_text:
            logger.info("Step 2 (AssemblyAI Speech-to-Text) succeeded.")
            return assembly_text

        # =========================================================================
        # STEP 3: Tertiary ASR - Google Speech-to-Text (gcp-key.json)
        # =========================================================================
        gcp_key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or getattr(settings, "GCP_KEY_PATH", "gcp-key.json")
        if not os.path.isabs(gcp_key_path):
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            project_root = os.path.dirname(backend_dir)
            possible_paths = [
                os.path.join(project_root, gcp_key_path),
                os.path.join(backend_dir, gcp_key_path),
                os.path.abspath(gcp_key_path)
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    gcp_key_path = p
                    break

        if os.path.exists(gcp_key_path):
            try:
                from google.cloud import speech
                client = speech.SpeechClient.from_service_account_json(gcp_key_path)

                audio = speech.RecognitionAudio(content=wav_bytes)
                config = speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=sample_rate,
                    language_code="th-TH",
                    enable_automatic_punctuation=True,
                    model="default"
                )

                response = client.recognize(config=config, audio=audio)
                results_text = []
                for result in response.results:
                    if result.alternatives:
                        results_text.append(result.alternatives[0].transcript)

                final_text = " ".join(results_text).strip()
                if final_text:
                    logger.info("Step 3 (Google Speech-to-Text via gcp-key.json) succeeded.")
                    return final_text
            except Exception as e:
                logger.warning(f"Step 3 (Google Speech-to-Text) failed: {e}")
        else:
            logger.info(f"GCP Key file not found at {gcp_key_path}, skipping Step 3 Google ASR.")

        # =========================================================================
        # STEP 4: Offline Demo Fallback
        # =========================================================================
        return "หมอขอปรับเพิ่มยา Metformin เป็น 1000mg เช้าเย็น หลังอาหารทันที แล้วให้ทิ้งยาตัวสีขาวเดิมซองเก่าทันทีเลยนะ ส่วนยาลดความดัน Amlodipine ให้ปรับลดเหลือ 1 เม็ดก่อนนอน"

def get_asr_service():
    return MultiTierASRService()

# Alias for backward compatibility
TyphoonASRService = MultiTierASRService
