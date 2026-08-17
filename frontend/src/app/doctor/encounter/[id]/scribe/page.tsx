// frontend/src/app/doctor/encounter/[id]/scribe/page.tsx
'use client';

import { useState, useEffect, useRef, use } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { API_BASE, WS_BASE, deduplicateRepeatedSentences } from '@/lib/api';

export default function AmbientScribePage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const encounterId = resolvedParams.id;
  const router = useRouter();
  const searchParams = useSearchParams();

  const model = searchParams.get('model') || 'google/gemini-2.5-flash';
  const [seconds, setSeconds] = useState(0);
  const [isRecording, setIsRecording] = useState(true);
  const [isPaused, setIsPaused] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState<string>('');
  const [doctorInfo, setDoctorInfo] = useState<{ first_name: string; surname: string; license_no: string } | null>(null);
  const [asrError, setAsrError] = useState<string>('');
  const [uploadedFileName, setUploadedFileName] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const recognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const mimeTypeRef = useRef<string>('audio/webm');
  const isPausedRef = useRef(false);
  const isStoppedRef = useRef(false);
  const [debugInfo, setDebugInfo] = useState<string>('');

  // Keep isPaused in sync for stale-closure-free handlers
  useEffect(() => {
    isPausedRef.current = isPaused;
  }, [isPaused]);

  // Load Doctor Info
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('morbok_doctor_info');
      if (saved) {
        try {
          setDoctorInfo(JSON.parse(saved));
        } catch (e) {}
      }
    }
  }, []);

  // Live Timer (Pauses when isPaused is true)
  useEffect(() => {
    if (!isRecording || isPaused) return;

    const timer = setInterval(() => {
      setSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [isRecording, isPaused]);

  // Web Audio API & WebSocket Setup
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const wsUrl = `${WS_BASE}/ws/audio-stream/${encounterId}`;
    const socket = new WebSocket(wsUrl);
    wsRef.current = socket;

    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      // Pick a mimeType the browser actually supports:
      // Android Chrome/Edge -> audio/webm;codecs=opus
      // iPad Safari          -> audio/mp4 (no webm support)
      const candidates = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/mp4',
        'audio/aac',
        '',
      ];
      let mimeType = '';
      if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported) {
        for (const c of candidates) {
          if (!c || MediaRecorder.isTypeSupported(c)) {
            mimeType = c;
            break;
          }
        }
      }
      mimeTypeRef.current = mimeType || 'audio/webm';

      navigator.mediaDevices
        .getUserMedia({
          audio: {
            channelCount: 1,
            sampleRate: 16000,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        })
        .then((stream) => {
          setDebugInfo((d) => `${d}\n✅ mic OK, mime=${mimeTypeRef.current}`);
          const mediaRecorder = mimeType
            ? new MediaRecorder(stream, { mimeType })
            : new MediaRecorder(stream);
          mediaRecorderRef.current = mediaRecorder;

          mediaRecorder.ondataavailable = (event) => {
            if (isStoppedRef.current) return;
            if (event.data.size > 0) {
              chunksRef.current.push(event.data);
              setDebugInfo((d) => `${d}\n🎤 chunks=${chunksRef.current.length}`);
              if (!isPausedRef.current && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(event.data);
              }
            }
          };

          mediaRecorder.start(500);
        })
        .catch((err) => {
          console.warn('Microphone notice:', err);
          const micErr = err instanceof Error ? err.name : String(err);
          setDebugInfo((d) => `${d}\n❌ mic denied: ${micErr}`);
        });
    }

    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'th-TH';
      recognition.maxAlternatives = 1;

      recognition.onresult = (event: any) => {
        if (isPausedRef.current || isStoppedRef.current) return;
        let currentTranscript = '';
        for (let i = 0; i < event.results.length; i++) {
          currentTranscript += event.results[i][0].transcript + ' ';
        }
        setTranscript(currentTranscript.trim());
      };

      // Android Chrome auto-stops after a few seconds of silence.
      // Restart unless explicitly paused/stopped — otherwise recording
      // appears live but nothing is transcribed.
      recognition.onend = () => {
        if (!isPausedRef.current && !isStoppedRef.current) {
          try {
            recognition.start();
          } catch (err) {
            console.warn('SpeechRecognition restart failed:', err);
          }
        }
      };

      recognition.onerror = (event: any) => {
        // 'no-speech' / 'aborted' are expected on silence/stop — ignore them.
        if (event.error === 'no-speech' || event.error === 'aborted') return;
        console.warn('SpeechRecognition error:', event.error);
      };

      try {
        recognition.start();
        recognitionRef.current = recognition;
      } catch (err) {
        console.warn('SpeechRecognition start failed:', err);
      }
    }

    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        try { mediaRecorderRef.current.stop(); } catch (e) {}
      }
      if (wsRef.current) {
        try { wsRef.current.close(); } catch (e) {}
      }
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (e) {}
      }
    };
  }, [encounterId]);

  const handleTogglePause = () => {
    setIsPaused((prev) => {
      const nextState = !prev;
      isPausedRef.current = nextState;
      if (nextState) {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
          try { mediaRecorderRef.current.pause(); } catch (e) {}
        }
        if (recognitionRef.current) {
          try { recognitionRef.current.stop(); } catch (e) {}
        }
      } else {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'paused') {
          try { mediaRecorderRef.current.resume(); } catch (e) {}
        }
        if (recognitionRef.current) {
          try { recognitionRef.current.start(); } catch (e) {}
        }
      }
      return nextState;
    });
  };

  const formatTimer = (sec: number) => {
    const m = Math.floor(sec / 60).toString().padStart(2, '0');
    const s = (sec % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const transcribeAndPersist = (blob: Blob, mimeType: string, fallbackText: string, requestId: string) => {
    void (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/encounters/transcribe-audio`, {
          method: 'POST',
          headers: {
            'Content-Type': mimeType,
            'X-Encounter-Id': encounterId,
          },
          body: blob,
        });
        if (!res.ok) throw new Error(`ASR HTTP ${res.status}`);
        const data = await res.json();
        const hasTranscript = data.status === 'SUCCESS' && data.transcript && data.transcript.trim();
        const finalTranscript = hasTranscript
          ? deduplicateRepeatedSentences(data.transcript.trim())
          : fallbackText;
        const error = hasTranscript
          ? null
          : data.error || 'ไม่สามารถถอดเสียงจากไฟล์เสียงได้ กรุณาตรวจสอบหรือแก้ไขข้อความก่อนสร้างสรุป';
        if (localStorage.getItem(`pvs_asr_request_${encounterId}`) !== requestId) return;
        localStorage.setItem(`pvs_transcript_${encounterId}`, finalTranscript);
        localStorage.setItem('pvs_transcript_latest', finalTranscript);
        localStorage.setItem(`pvs_transcript_source_${encounterId}`, hasTranscript ? 'backend_asr' : 'browser_preview_after_asr_failure');
        localStorage.setItem(`pvs_asr_result_${encounterId}`, JSON.stringify({
          status: hasTranscript ? 'SUCCESS' : 'FAILED',
          provider: data.provider || null,
          model: data.model || null,
          error,
          quality: data.quality || null,
          alternatives: data.alternatives || null,
        }));
      } catch (e) {
        console.warn('Backend transcription failed:', e);
        if (localStorage.getItem(`pvs_asr_request_${encounterId}`) !== requestId) return;
        localStorage.setItem(`pvs_transcript_source_${encounterId}`, 'browser_preview_after_asr_failure');
        localStorage.setItem(`pvs_asr_result_${encounterId}`, JSON.stringify({
          status: 'FAILED',
          provider: null,
          model: null,
          error: 'การเชื่อมต่อบริการถอดเสียงล้มเหลว กรุณาตรวจสอบหรือแก้ไขข้อความก่อนสร้างสรุป',
          quality: null,
          alternatives: null,
        }));
      }
    })();
  };

  const stopLiveCapture = () => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) {}
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try { mediaRecorderRef.current.stop(); } catch (e) {}
    }
    if (wsRef.current) {
      try { wsRef.current.close(); } catch (e) {}
    }
    chunksRef.current = [];
    setTranscript('');
  };

  const handleStopScribe = async () => {
    setIsRecording(false);
    isStoppedRef.current = true;
    setIsProcessing(true);

    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) {}
    }
    const mediaRecorder = mediaRecorderRef.current;
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      // MediaRecorder emits the final dataavailable event immediately before
      // stop. Waiting here prevents uploading an incomplete recording.
      await new Promise<void>((resolve) => {
        const onStop = () => resolve();
        mediaRecorder.addEventListener('stop', onStop, { once: true });
        try {
          mediaRecorder.stop();
        } catch (e) {
          resolve();
        }
      });
    }

    const typedText = deduplicateRepeatedSentences(transcript.trim());
    const chunks = chunksRef.current;
    const audioBlob = chunks.length > 0 ? new Blob(chunks, { type: mimeTypeRef.current }) : null;
    const requestId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;

    if (typeof window !== 'undefined') {
      localStorage.setItem(`pvs_asr_request_${encounterId}`, requestId);
      localStorage.setItem(`pvs_transcript_${encounterId}`, typedText);
      localStorage.setItem('pvs_transcript_latest', typedText);
      localStorage.setItem(`pvs_transcript_source_${encounterId}`, audioBlob ? 'backend_asr_pending' : 'browser_preview_no_audio');
      localStorage.setItem(`pvs_asr_result_${encounterId}`, JSON.stringify({
        status: audioBlob ? 'PROCESSING' : 'NO_AUDIO',
        provider: null,
        model: null,
        error: audioBlob ? null : 'ไม่พบไฟล์เสียงจากเครื่องบันทึก',
        quality: null,
      }));
    }

    // Move to Screen 4 now. ASR continues in the background and Screen 4
    // starts clinical analysis as soon as the canonical result is available.
    router.push(`/doctor/encounter/${encounterId}/review?model=${model}`);
    if (audioBlob) {
      transcribeAndPersist(audioBlob, mimeTypeRef.current, typedText, requestId);
    }
  };

  const handleUploadFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (e.target.value) e.target.value = '';
    if (!file) return;
    // The uploaded file is the only audio source: stop and ignore the
    // microphone immediately (guards in the mic handlers use isStoppedRef).
    isStoppedRef.current = true;
    stopLiveCapture();
    setIsRecording(false);
    setIsProcessing(true);
    const mimeType = file.type || 'audio/webm';
    const emptyText = '';
    const requestId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    if (typeof window !== 'undefined') {
      localStorage.setItem(`pvs_asr_request_${encounterId}`, requestId);
      localStorage.setItem(`pvs_transcript_${encounterId}`, emptyText);
      localStorage.setItem('pvs_transcript_latest', emptyText);
      localStorage.setItem(`pvs_transcript_source_${encounterId}`, 'backend_asr_pending');
      localStorage.setItem(`pvs_asr_result_${encounterId}`, JSON.stringify({
        status: 'PROCESSING',
        provider: null,
        model: null,
        error: null,
        quality: null,
      }));
    }
    setUploadedFileName(file.name);
    router.push(`/doctor/encounter/${encounterId}/review?model=${model}`);
    transcribeAndPersist(file, mimeType, emptyText, requestId);
  };

  return (
    <div className="bg-[#F9F9FF] text-[#111C2C] font-sans min-h-screen flex flex-col justify-between antialiased">
      {/* TopAppBar */}
      <header className="w-full top-0 sticky z-50 bg-white border-b border-[#C3C6D1] shadow-sm">
        <div className="flex justify-between items-center px-4 h-14 max-w-[480px] mx-auto">
          <button
            onClick={() => router.push('/doctor/pdpa')}
            className="text-[#43474F] hover:opacity-80 transition-opacity p-1 cursor-pointer flex items-center justify-center"
          >
            <span className="material-symbols-outlined text-2xl">arrow_back</span>
          </button>
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[#001E40] text-2xl">medical_services</span>
            <span className="font-extrabold text-xl text-[#001E40]">MorBok</span>
          </div>
          <div className="w-8"></div>
        </div>
      </header>

      {/* Main Content Canvas */}
      <main className="flex-grow flex flex-col items-center justify-center px-4 py-6 max-w-[480px] mx-auto w-full pb-28">
        
        {/* Step Indicator */}
        <div className="w-full flex items-center justify-between mb-3">
          <span className="text-xs font-extrabold text-[#003366] uppercase tracking-wider bg-[#e6f0ff] px-3 py-1 rounded-full border border-[#b3c8ff]">
            ขั้นตอนที่ 3: อัดเสียงบันทึกบทสนทนา
          </span>
        </div>

        {/* PDPA Warning Reminder Banner */}
        <div className="w-full bg-[#fff8e6] border border-[#b06000]/40 rounded-xl p-2.5 mb-5 flex items-center justify-between text-xs text-[#b06000]">
          <div className="flex items-center gap-1.5 font-bold">
            <span className="material-symbols-outlined text-base shrink-0">shield</span>
            <span>ข้อควรระวัง: หลีกเลี่ยงการเอ่ย ชื่อคนไข้ / ญาติ / HN / เลข 13 หลัก</span>
          </div>
        </div>
        
        {/* Status Area */}
        <div className="flex flex-col items-center mb-6 text-center space-y-2">
          <div className="bg-[#F0F3FF] border border-[#C3C6D1] rounded-full px-4 py-2 flex items-center gap-2 shadow-sm">
            {isPaused ? (
              <div className="w-2.5 h-2.5 rounded-full bg-[#b06000]"></div>
            ) : (
              <div className="w-2.5 h-2.5 rounded-full bg-[#BA1A1A] animate-ping"></div>
            )}
            <span className="font-bold text-xs text-[#111C2C]">
              {isPaused ? '⏸️ ชั่วคราว (Paused)' : 'กำลังบันทึกเสียงบทสนทนา'}
            </span>
            <span className="font-mono text-xs font-extrabold text-[#001E40] ml-2">⏱️ {formatTimer(seconds)}</span>
          </div>

          {doctorInfo && (
            <div className="text-xs text-[#003366] font-bold">
              👨‍⚕️ แพทย์ {doctorInfo.first_name} {doctorInfo.surname} ({doctorInfo.license_no.replace(/\D/g, '') ? `ว.${doctorInfo.license_no.replace(/\D/g, '')}` : doctorInfo.license_no})
            </div>
          )}

          <h1 className="text-2xl font-extrabold text-[#001E40] leading-snug">
            {isPaused ? 'หยุดบันทึกเสียงชั่วคราว...' : 'กำลังรับฟังเสียงคำแนะนำจากแพทย์...'}
          </h1>
          {asrError && (
            <div className="w-full rounded-xl border border-[#BA1A1A]/40 bg-[#FFF0F0] px-3 py-2 text-left text-xs font-bold text-[#8A0000]">
              ⚠️ {asrError}
            </div>
          )}
        </div>

        {/* Central Recording Interaction — MAIN BUTTON IS STOP */}
        <div className="relative flex items-center justify-center w-64 h-64 mb-6">
          {/* Pulsing Rings */}
          {!isPaused && (
            <>
              <div className="absolute inset-0 rounded-full border-4 border-[#BA1A1A]/20 pulse-ring delay-1"></div>
              <div className="absolute inset-4 rounded-full border-4 border-[#BA1A1A]/40 pulse-ring delay-3"></div>
            </>
          )}
          
          {/* Main Central Button = STOP */}
          <button
            onClick={handleStopScribe}
            disabled={isProcessing}
            className="relative z-10 w-36 h-36 rounded-full bg-[#BA1A1A] hover:bg-[#93000A] text-white shadow-[0_8px_24px_rgba(186,26,26,0.35)] flex flex-col items-center justify-center transition-transform hover:scale-105 active:scale-95 group cursor-pointer border-4 border-red-200"
          >
            <span className="material-symbols-outlined text-[52px] group-hover:scale-110 transition-transform duration-300">
              {isProcessing ? 'sync' : 'stop'}
            </span>
            <span className="text-xs font-black tracking-wide mt-1 text-center px-1">
              {isProcessing ? 'กำลังประมวลผล...' : 'บันทึกเสียงเสร็จสิ้น (End)'}
            </span>
          </button>
        </div>



      </main>

      {/* Bottom Floating Control Bar with Pause Button */}
      <footer className="fixed bottom-0 w-full z-50 rounded-t-2xl bg-white shadow-[0_-4px_16px_rgba(0,51,102,0.1)] border-t border-[#C3C6D1] py-3 px-4">
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*,.webm,.mp3,.mp4,.m4a,.wav,.ogg,.aac,.flac"
          className="hidden"
          onChange={handleUploadFile}
        />
        <div className="flex flex-col gap-2 max-w-[480px] mx-auto">
          {/* Test with Uploaded Audio File */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isProcessing}
            className="w-full py-2.5 px-4 rounded-xl font-bold text-sm flex items-center justify-center gap-2 border transition-all cursor-pointer shadow-sm bg-[#eef2ff] text-[#003366] border-[#003366]/30 hover:bg-[#e0e7ff] disabled:opacity-40"
          >
            <span className="material-symbols-outlined text-xl">upload_file</span>
            <span>{uploadedFileName ? `ถอดเสียงจากไฟล์: ${uploadedFileName}` : 'ทดสอบด้วยไฟล์เสียง (อัปโหลด)'}</span>
          </button>
          {/* Pause / Resume Button */}
          <button
            type="button"
            onClick={handleTogglePause}
            className={`w-full py-3 px-4 rounded-xl font-bold text-sm flex items-center justify-center gap-2 border transition-all cursor-pointer shadow-sm ${
              isPaused
                ? 'bg-[#006D33] text-white border-[#006D33] hover:bg-[#005225]'
                : 'bg-[#FEF7E0] text-[#B06000] border-[#B06000]/40 hover:bg-[#fdeec2]'
            }`}
          >
            <span className="material-symbols-outlined text-xl">
              {isPaused ? 'play_arrow' : 'pause'}
            </span>
            <span>{isPaused ? 'บันทึกเสียงต่อ (Resume)' : 'พักการบันทึกเสียง (Pause)'}</span>
          </button>
        </div>
      </footer>
    </div>
  );
}
