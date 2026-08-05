// frontend/src/app/doctor/encounter/[id]/scribe/page.tsx
'use client';

import { useState, useEffect, useRef, use } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

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

  const recognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

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

    const wsUrl = `ws://localhost:8080/ws/audio-stream/${encounterId}`;
    const socket = new WebSocket(wsUrl);
    wsRef.current = socket;

    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then((stream) => {
          const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
          mediaRecorderRef.current = mediaRecorder;

          mediaRecorder.ondataavailable = (event) => {
            if (!isPaused && event.data.size > 0 && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(event.data);
            }
          };

          mediaRecorder.start(500);
        })
        .catch((err) => {
          console.warn('Microphone notice:', err);
        });
    }

    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'th-TH';

      recognition.onresult = (event: any) => {
        if (isPaused) return;
        let currentTranscript = '';
        for (let i = 0; i < event.results.length; i++) {
          currentTranscript += event.results[i][0].transcript + ' ';
        }
        setTranscript(currentTranscript);
      };

      try {
        recognition.start();
        recognitionRef.current = recognition;
      } catch (err) {}
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

  const handleLoadPresetScenario = () => {
    const presetSpeech =
      'คุณหมอสั่งปรับเพิ่มขนาดยา Metformin เป็น 1000 มิลลิกรัม รับประทานครั้งละ 1 เม็ด เช้า-เย็น หลังอาหารทันที แล้วให้ทิ้งยา Metformin 500 มิลลิกรัม เม็ดสีขาวซองเก่าทันที ห้ามนำมารับประทานซ้ำ ส่วนยาลดความดัน Amlodipine 5 มิลลิกรัม ให้ปรับลดเหลือ 1 เม็ด ก่อนนอน นัดติดตามอาการคลินิกอายุรกรรมหัวใจ วันอาทิตย์ที่ 16 สิงหาคม 2026 เวลา 9:00 น.';
    setTranscript(presetSpeech);
  };

  const formatTimer = (sec: number) => {
    const m = Math.floor(sec / 60).toString().padStart(2, '0');
    const s = (sec % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const handleStopScribe = () => {
    setIsRecording(false);
    setIsProcessing(true);
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
    }

    const finalTranscript = transcript.trim();

    if (typeof window !== 'undefined') {
      localStorage.setItem(`pvs_transcript_${encounterId}`, finalTranscript);
    }

    setTimeout(() => {
      router.push(`/doctor/encounter/${encounterId}/review?model=${model}`);
    }, 1200);
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
          <span className="text-xs bg-[#003366] text-[#75F999] px-3 py-1 rounded-full font-bold">
            🤖 {model}
          </span>
        </div>
      </header>

      {/* Main Content Canvas */}
      <main className="flex-grow flex flex-col items-center justify-center px-4 py-6 max-w-[480px] mx-auto w-full pb-28">
        
        {/* Step Indicator */}
        <div className="w-full flex items-center justify-between mb-3">
          <span className="text-xs font-extrabold text-[#003366] uppercase tracking-wider bg-[#e6f0ff] px-3 py-1 rounded-full border border-[#b3c8ff]">
            ขั้นตอนที่ 3 จาก 5: อัดเสียงบันทึกบทสนทนา
          </span>
          <span className="text-xs font-bold text-slate-500">Step 3/5</span>
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
              👨‍⚕️ นพ./พญ. {doctorInfo.first_name} {doctorInfo.surname} (ว.{doctorInfo.license_no})
            </div>
          )}

          <h1 className="text-2xl font-extrabold text-[#001E40] leading-snug">
            {isPaused ? 'หยุดบันทึกเสียงชั่วคราว...' : 'กำลังรับฟังเสียงคำแนะนำจากแพทย์...'}
          </h1>
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
              stop
            </span>
            <span className="text-xs font-black tracking-wide mt-1">หยุดบันทึกเสียง</span>
          </button>
        </div>

        {/* Live Speech-to-Text Transcript Box */}
        <div className="w-full space-y-2 text-left bg-white border border-[#C3C6D1] rounded-2xl p-4 shadow-sm mb-6">
          <div className="flex items-center justify-between text-xs font-bold text-[#001E40]">
            <span>💬 ข้อความถอดเสียงสด (Live Transcript):</span>
            <button
              type="button"
              onClick={handleLoadPresetScenario}
              className="text-[#006D33] hover:underline bg-[#F0F3FF] px-2.5 py-1 rounded-lg border border-[#006D33]/30 font-semibold cursor-pointer text-[11px]"
            >
              ⚡ โหลดบทสนทนาตัวอย่าง ED
            </button>
          </div>

          <textarea
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="ลองพูดใส่ไมโครโฟนภาษาไทย หรือกดปุ่มด้านบนเพื่อใช้บทสนทนาตัวอย่าง..."
            rows={4}
            className="w-full bg-[#F0F3FF] border border-[#C3C6D1] rounded-xl p-3 text-xs text-[#111C2C] placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#006D33] font-medium leading-relaxed"
          />
        </div>

      </main>

      {/* Bottom Floating Control Bar with Pause Button */}
      <footer className="fixed bottom-0 w-full z-50 rounded-t-2xl bg-white shadow-[0_-4px_16px_rgba(0,51,102,0.1)] border-t border-[#C3C6D1] py-3 px-4">
        <div className="flex items-center justify-between max-w-[480px] mx-auto gap-3">
          {/* Pause / Resume Button */}
          <button
            type="button"
            onClick={handleTogglePause}
            className={`flex-1 py-3 px-4 rounded-xl font-bold text-sm flex items-center justify-center gap-2 border transition-all cursor-pointer shadow-sm ${
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

          {/* Main Stop Action in Bottom Bar */}
          <button
            type="button"
            onClick={handleStopScribe}
            disabled={isProcessing}
            className="flex-1 py-3 px-4 rounded-xl font-extrabold text-sm bg-[#BA1A1A] hover:bg-[#93000A] text-white flex items-center justify-center gap-2 shadow-md transition-all cursor-pointer"
          >
            <span className="material-symbols-outlined text-xl">stop</span>
            <span>{isProcessing ? 'กำลังประมวลผล...' : 'เสร็จสิ้น & ถัดไป'}</span>
          </button>
        </div>
      </footer>
    </div>
  );
}
