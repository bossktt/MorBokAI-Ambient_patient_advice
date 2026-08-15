# backend/app/services/asr_service.py
import os
import time
import struct
import requests
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from difflib import SequenceMatcher
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
    alternatives: Optional[dict] = None

    def as_dict(self) -> dict:
        return {
            "transcript": self.transcript,
            "status": self.status,
            "provider": self.provider,
            "model": self.model,
            "error": self.error,
            "confidence": self.confidence,
            "quality": self.quality,
            "alternatives": self.alternatives,
        }


def deduplicate_repeated_sentences(transcript: str) -> str:
    """Keep one copy when an ASR provider repeats an adjacent sentence/phrase."""
    text = re.sub(r"\s+", " ", (transcript or "")).strip()
    if not text:
        return ""

    chunks = [
        chunk.strip()
        for chunk in re.split(r"(?<=[.!?。！？])\s*", text)
        if chunk.strip()
    ]
    unique_chunks = []
    previous_key = None
    for chunk in chunks:
        key = re.sub(r"[^\wก-๛]+", "", chunk.casefold())
        if key and key == previous_key:
            continue
        unique_chunks.append(chunk)
        previous_key = key
    text = " ".join(unique_chunks)

    # Common Thai ASR glitch: the same sentence transcribed twice with only a
    # space between (Thai has no sentence punctuation). Keep one copy.
    if " " in text:
        half = len(text) // 2
        left = text[:half].strip()
        right = text[half:].strip()
        if left and left == right:
            return left

    # Thai ASR output often has no punctuation. Remove adjacent duplicated
    # token runs while retaining the first occurrence.
    tokens = text.split()
    result = []
    index = 0
    while index < len(tokens):
        max_block = min((len(tokens) - index) // 2, 80)
        duplicate_size = 0
        for size in range(max_block, 1, -1):
            if tokens[index:index + size] == tokens[index + size:index + (size * 2)]:
                duplicate_size = size
                break
        if duplicate_size:
            result.extend(tokens[index:index + duplicate_size])
            index += duplicate_size * 2
        else:
            result.append(tokens[index])
            index += 1
    return " ".join(result)


THAI_FILLERS = {
    "ครับ", "ครับผม", "ค่ะ", "คะ", "นะ", "นะครับ", "นะคะ", "น่ะ", "หนา",
    "จ๊ะ", "จ้า", "อืม", "อือ", "เอ่อ", "เออ", "อ้อ", "อ๋อ", "โอเค", "ฮะ",
    "อ่า", "อ้า", "นั่นเอง", "งั้น", "เนอะ", "นะเนี่ย",
}

CLINICAL_UNITS = {
    "mg", "มิลลิกรัม", "มก", "กรัม", "เม็ด", "แคปซูล", "แคป", "ช้อน",
    "ช้อนชา", "ช้อนโต๊ะ", "วันละ", "ครั้งละ", "ก่อนนอน", "หลังอาหาร",
    "เช้า", "เย็น", "กลางวัน", "ชั่วโมง", "วัน", "สัปดาห์", "อาทิตย์",
}

THAI_NUMBER_WORDS = {
    "หนึ่ง", "สอง", "สาม", "สี่", "ห้า", "หก", "เจ็ด", "แปด", "เก้า", "สิบ",
    "ร้อย", "พัน", "หมื่น", "แสน", "ล้าน", "ครึ่ง",
}

THAI_SYNONYMS = {
    "คนไข้": "ผู้ป่วย",
    "หมอ": "แพทย์",
}


def _thai_word_tokenize(text: str) -> list:
    text = (text or "").strip()
    if not text:
        return []
    try:
        from pythainlp.tokenize import word_tokenize
        tokens = word_tokenize(text, engine="newmm", keep_whitespace=False)
        return [t for t in tokens if t and t.strip()]
    except Exception:
        return [t for t in re.findall(r"[a-zA-Z0-9]+|[ก-๛]+|[^\sก-๛a-zA-Z0-9]", text) if t.strip()]


def _normalize_tokens(text: str) -> list:
    """Tokenize then drop fillers and map synonyms, so agreement ignores style."""
    tokens = _thai_word_tokenize(text)
    out = []
    for token in tokens:
        token = THAI_SYNONYMS.get(token, token)
        if token in THAI_FILLERS or not token.strip():
            continue
        out.append(token)
    return out


def _dictionary_coverage(text: str) -> float:
    tokens = _thai_word_tokenize(text)
    if not tokens:
        return 0.0
    vocab = set()
    try:
        from pythainlp.corpus.common import thai_words
        vocab = thai_words() if callable(thai_words) else thai_words
    except Exception:
        vocab = set()
    if not vocab:
        known = sum(1 for t in tokens if re.search(r"[a-zA-Z0-9ก-๛]", t))
        return known / len(tokens)
    known = 0
    for token in tokens:
        if token in vocab or token.isdigit() or re.fullmatch(r"[a-zA-Z0-9\-\.%]+", token):
            known += 1
    return known / len(tokens)


def _extract_clinical_entities(text: str) -> set:
    entities = set()
    entities.update(re.findall(r"\d+(?:[.,]\d+)?", text))
    entities.update(re.findall(r"[๐-๙]+", text))
    entities.update(m.casefold() for m in re.findall(r"[a-z][a-z0-9\-]{1,}", text.casefold()))
    lowered = text.casefold()
    for unit in CLINICAL_UNITS:
        if unit in lowered:
            entities.add(unit)
    for word in THAI_NUMBER_WORDS:
        if word in text:
            entities.add(word)
    return entities


def compare_transcripts(primary: str, verifier: str) -> dict:
    """Compare clinical meaning, not raw wording."""
    primary_tokens = _normalize_tokens(primary)
    verifier_tokens = _normalize_tokens(verifier)
    token_ratio = SequenceMatcher(None, primary_tokens, verifier_tokens).ratio()

    primary_entities = _extract_clinical_entities(primary)
    verifier_entities = _extract_clinical_entities(verifier)
    union = primary_entities | verifier_entities
    entity_ratio = len(primary_entities & verifier_entities) / len(union) if union else 1.0
    critical_disagreement = sorted(primary_entities.symmetric_difference(verifier_entities))

    agreement_score = round(0.5 * token_ratio + 0.5 * entity_ratio, 3)
    min_agreement = getattr(settings, "ASR_MIN_MODEL_AGREEMENT", 0.85)
    return {
        "score": agreement_score,
        "threshold": min_agreement,
        "token_ratio": round(token_ratio, 3),
        "entity_ratio": round(entity_ratio, 3),
        "critical_disagreement": critical_disagreement,
        "agrees": agreement_score >= min_agreement and not critical_disagreement,
    }


def _quality_grade(score: float) -> tuple[str, str]:
    if score <= 0.35:
        return "POOR", "ระบบเสียงไม่ชัดพอ"
    if score <= 0.65:
        return "MEDIUM", "ระบบเสียงอยู่ระดับปานกลาง"
    return "GOOD", "ระบบเสียงดี"


def assess_transcript_quality(transcript: str, confidence: Optional[float] = None) -> dict:
    """Assess whether ASR text is safe to send to clinical extraction.

    This is a conservative pre-LLM gate, not a claim of word-level ASR accuracy.
    A golden-set evaluation remains necessary to calibrate the thresholds.
    """
    text = deduplicate_repeated_sentences(transcript)
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

    coverage = _dictionary_coverage(text)
    if text and coverage < getattr(settings, "ASR_MIN_DICTIONARY_COVERAGE", 0.4):
        reasons.append("low_dictionary_coverage")
        hard_fail = True

    if not text:
        score = 0.0
    elif hard_fail:
        # A hard quality failure belongs in the lowest grade even when a
        # provider happens to report a high confidence value.
        score = 0.35
    else:
        score = 0.5 + 0.5 * coverage
        score -= 0.15 if repeated_tokens else 0.0
    if confidence is not None:
        confidence = max(0.0, min(1.0, confidence))
        score = score if hard_fail else (score * 0.5) + (confidence * 0.5)
        if confidence < settings.ASR_QUALITY_MIN_CONFIDENCE:
            reasons.append("provider_confidence_below_threshold")
            hard_fail = True
            score = min(score, settings.ASR_QUALITY_MIN_SCORE)

    score = round(max(0.0, min(1.0, score)), 3)
    grade, grade_label = _quality_grade(score)

    # Only GOOD (> 0.65) is safe to send to the clinical LLM. A score of
    # exactly 0.65 remains MEDIUM by the requested grading bands.
    status = "ACCEPT" if not hard_fail and score >= settings.ASR_QUALITY_MIN_SCORE else "REJECT"
    if status == "REJECT" and not reasons:
        reasons.append("quality_score_below_threshold")
    return {
        "status": status,
        "decision": "ACCEPT" if status == "ACCEPT" else "REVIEW_LOW_QUALITY",
        "score": score,
        "grade": grade,
        "grade_label": grade_label,
        "confidence": confidence,
        "dictionary_coverage": round(coverage, 3),
        "reasons": reasons,
        "threshold": settings.ASR_QUALITY_MIN_SCORE,
    }


def assess_dual_transcript_quality(
    primary: str,
    verifier: str,
    primary_confidence: Optional[float] = None,
    verifier_confidence: Optional[float] = None,
) -> dict:
    """Accept only when both ASR outputs are individually usable and agree."""
    primary_quality = assess_transcript_quality(primary, primary_confidence)
    verifier_quality = assess_transcript_quality(verifier, verifier_confidence)
    agreement = compare_transcripts(primary, verifier)
    score = min(primary_quality["score"], verifier_quality["score"], agreement["score"])
    reasons = []
    if primary_quality["status"] != "ACCEPT":
        reasons.append("primary_quality_rejected")
    if verifier_quality["status"] != "ACCEPT":
        reasons.append("verifier_quality_rejected")
    if not agreement["agrees"]:
        reasons.append("model_disagreement")
        if agreement["critical_disagreement"]:
            reasons.append("critical_token_disagreement")

    score = round(max(0.0, min(1.0, score)), 3)
    grade, grade_label = _quality_grade(score)
    status = "ACCEPT" if not reasons and score >= settings.ASR_QUALITY_MIN_SCORE else "REJECT"
    if status == "REJECT" and not reasons:
        reasons.append("quality_score_below_threshold")

    if status == "ACCEPT":
        decision = "ACCEPT"
    elif "model_disagreement" in reasons or "critical_token_disagreement" in reasons:
        decision = "REVIEW_DISAGREEMENT"
    else:
        decision = "REVIEW_LOW_QUALITY"

    return {
        "status": status,
        "decision": decision,
        "score": score,
        "grade": grade,
        "grade_label": grade_label,
        "confidence": primary_quality.get("confidence"),
        "dictionary_coverage": primary_quality.get("dictionary_coverage"),
        "reasons": reasons,
        "threshold": settings.ASR_QUALITY_MIN_SCORE,
        "agreement_score": agreement["score"],
        "agreement_threshold": agreement["threshold"],
        "token_ratio": agreement["token_ratio"],
        "entity_ratio": agreement["entity_ratio"],
        "critical_disagreement": agreement["critical_disagreement"],
        "models": {
            "primary": getattr(settings, "OPENROUTER_ASR_MODEL", "x-ai/grok-stt-1.0"),
            "verifier": getattr(settings, "OPENROUTER_ASR_VERIFIER_MODEL", "openai/whisper-large-v3-turbo"),
        },
    }


def mark_single_model_quality(quality: dict) -> dict:
    """A fallback transcript must be reviewed because it lacks model agreement."""
    quality = dict(quality)
    quality["status"] = "REJECT"
    quality["decision"] = "REVIEW_SINGLE_MODEL"
    quality["reasons"] = list(quality.get("reasons") or [])
    if "single_model_only" not in quality["reasons"]:
        quality["reasons"].append("single_model_only")
    return quality


def _no_result_quality() -> dict:
    """Quality payload for cases where no transcript could be produced at all."""
    return {
        "status": "REJECT",
        "decision": "NO_RESULT",
        "score": 0.0,
        "grade": "POOR",
        "grade_label": "",
        "confidence": None,
        "dictionary_coverage": 0.0,
        "reasons": ["no_transcription_result"],
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
    - Step 1: Parallel OpenRouter ASR (Grok STT primary + Whisper verifier)
    - Step 2: AssemblyAI ASR (https://api.assemblyai.com/v2)
    - Step 3: Google Speech-to-Text (via gcp-key.json credentials)
    - No synthetic transcript fallback; failures are surfaced to the doctor.
    """

    @staticmethod
    def _transcribe_openrouter_model(
        api_key: str,
        model_name: str,
        filename: str,
        wav_bytes: bytes,
        content_type: str,
    ) -> Optional[dict]:
        try:
            request_data = {
                "model": model_name,
                "language": "th",
                "temperature": str(getattr(settings, "OPENROUTER_ASR_TEMPERATURE", 0)),
            }
            domain_prompt = getattr(settings, "ASR_DOMAIN_PROMPT", "") or ""
            if domain_prompt:
                request_data["prompt"] = domain_prompt
            response = requests.post(
                "https://openrouter.ai/api/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (filename, wav_bytes, content_type)},
                data=request_data,
                timeout=15,
            )
            if response.status_code != 200:
                logger.warning(f"OpenRouter ASR {model_name} failed with status {response.status_code}")
                return None
            response_data = response.json()
            text = deduplicate_repeated_sentences(response_data.get("text", ""))
            if not text:
                return None
            return {
                "transcript": text,
                "confidence": response_data.get("confidence"),
                "model": model_name,
            }
        except Exception as e:
            logger.warning(f"OpenRouter ASR with {model_name} failed: {e}")
            return None

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
            for attempt in range(10):
                if attempt:
                    time.sleep(0.75)
                poll_res = requests.get(
                    f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                    headers=headers,
                    timeout=5
                )
                if poll_res.status_code == 200:
                    data = poll_res.json()
                    status = data.get("status")
                    if status == "completed":
                        text = deduplicate_repeated_sentences(data.get("text", ""))
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
                quality=_no_result_quality(),
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
        # STEP 1: Parallel primary/verifier ASR - OpenRouter Audio Transcriptions
        # =========================================================================
        openrouter_key = settings.OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY")
        if openrouter_key:
            primary_model = getattr(settings, "OPENROUTER_ASR_MODEL", "x-ai/grok-stt-1.0")
            verifier_model = getattr(settings, "OPENROUTER_ASR_VERIFIER_MODEL", "openai/whisper-large-v3-turbo")
            model_results = {}
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = {
                    executor.submit(
                        MultiTierASRService._transcribe_openrouter_model,
                        openrouter_key,
                        model_name,
                        filename,
                        wav_bytes,
                        content_type,
                    ): model_name
                    for model_name in (primary_model, verifier_model)
                }
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        model_results[futures[future]] = result

            primary_result = model_results.get(primary_model)
            verifier_result = model_results.get(verifier_model)
            if primary_result and verifier_result:
                primary_text = primary_result["transcript"]
                verifier_text = verifier_result["transcript"]
                quality = assess_dual_transcript_quality(
                    primary_text,
                    verifier_text,
                    primary_result.get("confidence"),
                    verifier_result.get("confidence"),
                )
                logger.info(
                    "Step 1 dual ASR completed: agreement=%s status=%s",
                    quality["agreement_score"],
                    quality["status"],
                )
                return ASRResult(
                    transcript=primary_text,
                    status="SUCCESS",
                    provider="openrouter_dual",
                    model=primary_model,
                    confidence=primary_result.get("confidence"),
                    quality=quality,
                    alternatives={"primary": primary_text, "verifier": verifier_text},
                )
            if primary_result or verifier_result:
                single_result = primary_result or verifier_result
                single_model = primary_model if primary_result else verifier_model
                single_quality = mark_single_model_quality(
                    assess_transcript_quality(single_result["transcript"], single_result.get("confidence"))
                )
                single_quality["models"] = {"available": single_model, "missing": verifier_model if primary_result else primary_model}
                return ASRResult(
                    transcript=single_result["transcript"],
                    status="SUCCESS",
                    provider="openrouter",
                    model=single_model,
                    confidence=single_result.get("confidence"),
                    quality=single_quality,
                    alternatives={
                        "primary": primary_result["transcript"] if primary_result else "",
                        "verifier": verifier_result["transcript"] if verifier_result else "",
                    },
                )

        # =========================================================================
        # STEP 2: Secondary ASR - AssemblyAI Speech-to-Text API
        # =========================================================================
        assembly_text = MultiTierASRService._transcribe_assemblyai(wav_bytes)
        if assembly_text:
            quality = mark_single_model_quality(assess_transcript_quality(assembly_text))
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

                final_text = deduplicate_repeated_sentences(" ".join(results_text))
                if final_text:
                    provider_confidence = (sum(confidence_values) / len(confidence_values)) if confidence_values else None
                    logger.info("Step 3 (Google Speech-to-Text via gcp-key.json) succeeded.")
                    return ASRResult(
                        transcript=final_text,
                        status="SUCCESS",
                        provider="google",
                        model="google-speech-default-th-TH",
                        confidence=provider_confidence,
                        quality=mark_single_model_quality(assess_transcript_quality(final_text, provider_confidence)),
                    )
            except Exception as e:
                logger.warning(f"Step 3 (Google Speech-to-Text) failed: {e}")
        else:
            logger.info(f"GCP Key file not found at {gcp_key_path}, skipping Step 3 Google ASR.")

        return ASRResult(
            status="FAILED",
            error="ไม่สามารถถอดเสียงได้จากผู้ให้บริการ ASR ที่ตั้งค่าไว้",
            quality=_no_result_quality(),
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
