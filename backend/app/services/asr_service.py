# backend/app/services/asr_service.py
import os
import time
import struct
import requests
import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ASRResult:
    """One canonical ASR result; an empty transcript is never a success."""

    transcript: str = ""
    status: str = "FAILED"
    provider: Optional[str] = None
    model: Optional[str] = None
    error: Optional[str] = None
    confidence: Optional[float] = None
    quality: Optional[dict] = None

    def as_dict(self) -> dict:
        return {
            "transcript": self.transcript,
            "status": self.status,
            "provider": self.provider,
            "model": self.model,
            "error": self.error,
            "confidence": self.confidence,
            "quality": self.quality,
        }


def assess_transcript_quality(transcript: str, confidence: Optional[float] = None) -> dict:
    """Assess whether ASR text is safe to send to clinical extraction.

    This is a conservative pre-LLM gate, not a claim of word-level ASR accuracy.
    A golden-set evaluation remains necessary to calibrate the thresholds.
    """
    text = (transcript or "").strip()
    try:
        confidence = float(confidence) if confidence is not None else None
    except (TypeError, ValueError):
        confidence = None
    compact = re.sub(r"\s+", "", text)
    reasons = []
    hard_fail = False

    if len(compact) < settings.ASR_QUALITY_MIN_CHARS:
        reasons.append("transcript_too_short")
        hard_fail = True

    if not text:
        reasons.append("transcript_empty")
        hard_fail = True

    # Common ASR noise/placeholder output must never become clinical input.
    if re.search(r"(?i)(\[inaudible\]|\[เสียงไม่ชัด\]|<unk>)", text):
        reasons.append("asr_noise_or_placeholder")
        hard_fail = True

    meaningful_chars = sum(1 for ch in text if ch.isalnum() or "ก" <= ch <= "๛")
    meaningful_ratio = meaningful_chars / max(len(text), 1)
    if meaningful_ratio < 0.55:
        reasons.append("too_much_non_speech_noise")
        hard_fail = True

    repeated_tokens = re.findall(r"(?i)\b([a-zก-๙]{2,})\s+\1(?:\s+\1)+\b", text)
    if repeated_tokens:
        reasons.append("repeated_tokens")

    score = 1.0
    score -= 0.35 if hard_fail else 0.0
    score -= 0.15 if repeated_tokens else 0.0
    if confidence is not None:
        score = (score * 0.5) + (max(0.0, min(1.0, confidence)) * 0.5)
        if confidence < settings.ASR_QUALITY_MIN_CONFIDENCE:
            reasons.append("provider_confidence_below_threshold")
            hard_fail = True

    score = round(max(0.0, min(1.0, score)), 3)
    status = "REJECT" if hard_fail or score < settings.ASR_QUALITY_MIN_SCORE else "ACCEPT"
    if status == "REJECT" and not reasons:
        reasons.append("quality_score_below_threshold")
    return {
        "status": status,
        "score": score,
        "confidence": confidence,
        "reasons": reasons,
        "threshold": settings.ASR_QUALITY_MIN_SCORE,
    }

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
    - No synthetic transcript fallback; failures are surfaced to the doctor.
    """

    @staticmethod
    def _transcribe_assemblyai(audio_bytes: bytes) -> Optional[str]:
        """
        Transcribes audio bytes using AssemblyAI REST API
        """
        api_key = settings.ASSEMBLYAI_API_KEY or os.environ.get("ASSEMBLYAI_API_KEY")
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
    def transcribe_audio_result(audio_bytes: bytes, sample_rate: int = 16000, mime_type: str = "audio/webm") -> ASRResult:
        """Transcribe audio and retain enough metadata to explain failures."""
        if not audio_bytes or len(audio_bytes) < 100:
            return ASRResult(
                status="EMPTY",
                error="เสียงสั้นเกินไปหรือไม่มีข้อมูลเสียง",
                quality=assess_transcript_quality(""),
            )

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
                        response_data = response.json()
                        text = response_data.get("text", "").strip()
                        if text:
                            provider_confidence = response_data.get("confidence")
                            quality = assess_transcript_quality(text, provider_confidence)
                            logger.info(f"Step 1 (OpenRouter ASR with {model_name}) succeeded.")
                            return ASRResult(
                                transcript=text,
                                status="SUCCESS",
                                provider="openrouter",
                                model=model_name,
                                confidence=provider_confidence,
                                quality=quality,
                            )
                        else:
                            logger.info(f"Step 1 (OpenRouter ASR with {model_name}) returned 200 OK.")
                except Exception as e:
                    logger.warning(f"Step 1 (OpenRouter ASR with {model_name}) failed: {e}")

        # =========================================================================
        # STEP 2: Secondary ASR - AssemblyAI Speech-to-Text API
        # =========================================================================
        assembly_text = MultiTierASRService._transcribe_assemblyai(wav_bytes)
        if assembly_text:
            quality = assess_transcript_quality(assembly_text)
            logger.info("Step 2 (AssemblyAI Speech-to-Text) succeeded.")
            return ASRResult(
                transcript=assembly_text,
                status="SUCCESS",
                provider="assemblyai",
                model="assemblyai-th",
                quality=quality,
            )

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
                confidence_values = []
                for result in response.results:
                    if result.alternatives:
                        results_text.append(result.alternatives[0].transcript)
                        if getattr(result.alternatives[0], "confidence", None) is not None:
                            confidence_values.append(result.alternatives[0].confidence)

                final_text = " ".join(results_text).strip()
                if final_text:
                    provider_confidence = (sum(confidence_values) / len(confidence_values)) if confidence_values else None
                    logger.info("Step 3 (Google Speech-to-Text via gcp-key.json) succeeded.")
                    return ASRResult(
                        transcript=final_text,
                        status="SUCCESS",
                        provider="google",
                        model="google-speech-default-th-TH",
                        confidence=provider_confidence,
                        quality=assess_transcript_quality(final_text, provider_confidence),
                    )
            except Exception as e:
                logger.warning(f"Step 3 (Google Speech-to-Text) failed: {e}")
        else:
            logger.info(f"GCP Key file not found at {gcp_key_path}, skipping Step 3 Google ASR.")

        return ASRResult(
            status="FAILED",
            error="ไม่สามารถถอดเสียงได้จากผู้ให้บริการ ASR ที่ตั้งค่าไว้",
            quality=assess_transcript_quality(""),
        )

    @staticmethod
    def transcribe_audio_bytes(audio_bytes: bytes, sample_rate: int = 16000, mime_type: str = "audio/webm") -> str:
        """Backward-compatible text-only wrapper for existing callers."""
        return MultiTierASRService.transcribe_audio_result(
            audio_bytes, sample_rate=sample_rate, mime_type=mime_type
        ).transcript

def get_asr_service():
    return MultiTierASRService()

# Alias for backward compatibility
TyphoonASRService = MultiTierASRService
