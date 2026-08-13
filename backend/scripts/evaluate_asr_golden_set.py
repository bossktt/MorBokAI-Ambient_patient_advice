"""Replay the ASR golden set and report transcript and clinical-fact errors."""

import argparse
import json
from pathlib import Path

from app.services.asr_service import MultiTierASRService


def error_rate(reference: str, hypothesis: str, *, characters: bool = False) -> float:
    ref = list(reference) if characters else reference.split()
    hyp = list(hypothesis) if characters else hypothesis.split()
    previous = list(range(len(hyp) + 1))
    for i, ref_item in enumerate(ref, 1):
        current = [i]
        for j, hyp_item in enumerate(hyp, 1):
            current.append(min(
                current[-1] + 1,
                previous[j] + 1,
                previous[j - 1] + (ref_item != hyp_item),
            ))
        previous = current
    return previous[-1] / max(len(ref), 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    root = args.manifest.parent
    results = []

    for case in manifest["cases"]:
        audio_path = root / case["audio_file"]
        if not audio_path.exists():
            results.append({"id": case["id"], "status": case["audio_status"], "approval_status": case["approval_status"]})
            continue

        result = MultiTierASRService.transcribe_audio_result(audio_path.read_bytes(), mime_type="audio/webm")
        reference = case["reference_transcript"]
        missing_facts = [
            fact
            for values in case.get("required_facts", {}).values()
            for fact in values
            if fact not in result.transcript
        ]
        results.append({
            "id": case["id"],
            "status": result.status,
            "provider": result.provider,
            "model": result.model,
            "wer": round(error_rate(reference, result.transcript), 4),
            "cer": round(error_rate(reference, result.transcript, characters=True), 4),
            "missing_required_facts": missing_facts,
            "approval_status": case["approval_status"],
        })

    print(json.dumps({"manifest": str(args.manifest), "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
