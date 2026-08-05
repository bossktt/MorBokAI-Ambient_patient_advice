# scripts/download_models.py
"""
Pre-download script to cache both ASR model weights locally before running Docker or Backend.
- Step 1 Primary: typhoon-ai/typhoon-asr-realtime (Hugging Face)
- Step 2 Fallback: Systran/faster-whisper-small (Faster-Whisper)
"""

import os
import sys

def download_models():
    print("=" * 60)
    print(" 🚀 PRE-DOWNLOADING ASR MODELS FOR PVS PLATFORM")
    print("=" * 60)

    # 1. Pre-download Systran/faster-whisper-small
    print("\n[1/2] Downloading Step 2 Fallback: Systran/faster-whisper-small...")
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("small", device="cpu", compute_type="int8")
        print(" ✅ Systran/faster-whisper-small downloaded and cached successfully!")
    except ImportError:
        print(" ℹ️ 'faster_whisper' python package not installed locally. Docker container will auto-download on first launch.")
    except Exception as e:
        print(f" ⚠️ Notice: {e}")

    # 2. Pre-download bossktt/typhoon-asr-realtime-bucket
    print("\n[2/2] Checking Step 1 Primary: bossktt/typhoon-asr-realtime-bucket...")
    try:
        from huggingface_hub import snapshot_download
        hf_token = os.getenv("HF_TOKEN")
        print(" Downloading model weights from Hugging Face (bossktt/typhoon-asr-realtime-bucket)...")
        snapshot_download(repo_id="bossktt/typhoon-asr-realtime-bucket", token=hf_token)
        print(" ✅ bossktt/typhoon-asr-realtime-bucket downloaded and cached successfully!")
    except ImportError:
        print(" ℹ️ 'huggingface_hub' python package not installed locally. Docker container will auto-download on first launch.")
    except Exception as e:
        print(f" ⚠️ Notice: {e}")

    print("\n" + "=" * 60)
    print(" 🎉 Pre-download check complete! Ready for 'docker-compose up'")
    print("=" * 60)

if __name__ == "__main__":
    download_models()
