# ASR golden set

This is the de-identified evaluation set for Thai and Thai-English clinical speech.
Each case has a reference transcript and the clinical facts that ASR must preserve.

The manifest is intentionally versioned separately from patient data. Audio must be
captured from consenting speakers, stripped of identifying details, and then reviewed
by a clinician before `approval_status` can change to `CLINICIAN_APPROVED`.

Run the evaluator only after the audio files named in `golden_set.json` are present:

```bash
cd backend
PYTHONPATH=. venv/bin/python scripts/evaluate_asr_golden_set.py \
  ../docs/evaluation/asr_golden_set/golden_set.json
```

Acceptance checks should include Thai WER/CER plus exact preservation of medication
names, doses, frequencies, and follow-up dates. The checked-in cases are currently
`PENDING_AUDIO_CAPTURE` / `PENDING_CLINICIAN_APPROVAL`; the system must not claim
clinical validation until a clinician signs each reference transcript.
