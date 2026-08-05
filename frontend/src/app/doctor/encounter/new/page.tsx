// frontend/src/app/doctor/encounter/new/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { QRCodeSVG } from 'qrcode.react';

export default function NewEncounterPage() {
  const router = useRouter();
  const [encounterId, setEncounterId] = useState<string | null>(null);
  const [pairingPin, setPairingPin] = useState<string>('');
  const [qrCodeUrl, setQrCodeUrl] = useState<string>('');
  const [isConsentGiven, setIsConsentGiven] = useState(true); // Default checked for fluid test UX
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedModel, setSelectedModel] = useState<string>('google/gemini-2.5-flash');
  const [lineToken, setLineToken] = useState<string>('');
  const [isTokenSaved, setIsTokenSaved] = useState<boolean>(false);

  useEffect(() => {
    // Load saved LINE token from localStorage
    if (typeof window !== 'undefined') {
      const savedToken = localStorage.getItem('line_channel_access_token');
      if (savedToken) setLineToken(savedToken);
    }

    // Create session via FastAPI backend
    fetch('http://localhost:8080/api/v1/encounters/create', { method: 'POST' })
      .then((res) => res.json())
      .then((data) => {
        setEncounterId(data.encounter_id);
        setPairingPin(data.pairing_pin || '7658');
        setQrCodeUrl(data.qr_code_url || `http://localhost:3000/patient/pair?pin=${data.pairing_pin}`);
        setIsLoading(false);
      })
      .catch(() => {
        const mockId = `ENC_${Math.floor(100000 + Math.random() * 900000)}`;
        const randomPin = `${Math.floor(1000 + Math.random() * 9000)}`;
        setEncounterId(mockId);
        setPairingPin(randomPin);
        setQrCodeUrl(`http://localhost:3000/patient/pair?pin=${randomPin}`);
        setIsLoading(false);
      });
  }, []);

  // Poll pairing status from backend every 2 seconds
  useEffect(() => {
    if (!encounterId) return;
    const interval = setInterval(() => {
      fetch(`http://localhost:8080/api/v1/encounters/${encounterId}`)
        .then((res) => res.json())
        .then((data) => {
          if (data.status === 'PAIRED' || data.status === 'REVIEW' || data.status === 'DELIVERED') {
            setIsConnected(true);
          }
        })
        .catch(() => {});
    }, 2000);
    return () => clearInterval(interval);
  }, [encounterId]);

  const handleStartScribe = () => {
    if (encounterId && isConsentGiven) {
      // Store selected AI model in localStorage for session continuity
      if (typeof window !== 'undefined') {
        localStorage.setItem('pvs_selected_model', selectedModel);
      }
      router.push(`/doctor/encounter/${encounterId}/scribe?model=${selectedModel}`);
    }
  };

  const handleTogglePairing = () => {
    setIsConnected((prev) => !prev);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#F9F9FF] text-[#001E40] flex items-center justify-center p-4">
        <div className="flex items-center space-x-3 text-[#006D33] font-bold text-sm">
          <div className="w-5 h-5 border-2 border-[#006D33] border-t-transparent rounded-full animate-spin" />
          <span>กำลังสร้าง Session สำหรับเคสใหม่...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#f9f9ff] text-[#111c2c] font-sans h-full min-h-screen flex flex-col items-center antialiased selection:bg-[#d5e3ff] selection:text-[#001b3c]">
      {/* TopAppBar */}
      <header className="w-full top-0 sticky bg-[#f9f9ff] border-b border-[#c3c6d1] flex justify-between items-center px-[20px] h-14 max-w-[480px] mx-auto z-40">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[#001e40] text-2xl">medical_services</span>
          <span className="text-[20px] font-bold text-[#001e40]">MorBok</span>
        </div>
        <button
          onClick={() => router.push('/')}
          aria-label="Close"
          className="text-[#43474f] hover:opacity-80 transition-opacity active:scale-95 cursor-pointer"
        >
          <span className="material-symbols-outlined">close</span>
        </button>
      </header>

      {/* Main Canvas: Verify PIN */}
      <main className="flex-grow flex flex-col items-center justify-center w-full max-w-[480px] mx-auto px-[20px] py-[24px] pb-12 relative">
        
        {/* Status Indicator */}
        <div className="w-full flex flex-col items-center justify-center mb-6">
          {isConnected ? (
            <div className="inline-flex items-center gap-2 bg-[#75f999] text-[#007236] px-4 py-2 rounded-full font-semibold text-[14px] shadow-sm border border-[#78fc9c]">
              <span className="w-2.5 h-2.5 rounded-full bg-[#006d33] animate-pulse"></span>
              🟢 เชื่อมต่อสำเร็จ: คุณสมศักดิ์ (ผู้ดูแล)
            </div>
          ) : (
            <div className="inline-flex items-center gap-2 bg-[#75f999] text-[#007236] px-4 py-2 rounded-full font-semibold text-[14px] pulse-ring shadow-sm border border-[#78fc9c]">
              <span className="w-2.5 h-2.5 rounded-full bg-[#006d33] block"></span>
              Waiting for connection...
            </div>
          )}
        </div>

        {/* Connection Card */}
        <div className="w-full bg-white border border-[#c3c6d1] rounded-xl shadow-[0_4px_12px_rgba(0,51,102,0.08)] p-[24px] flex flex-col items-center relative overflow-hidden space-y-4">
          
          {/* Logo Decoration */}
          <div className="absolute -top-12 -right-12 w-32 h-32 bg-[#d5e3ff] opacity-20 rounded-full blur-2xl pointer-events-none"></div>
          <div className="absolute -bottom-12 -left-12 w-32 h-32 bg-[#75f999] opacity-20 rounded-full blur-2xl pointer-events-none"></div>

          {/* Profile Avatar */}
          <div className="w-24 h-24 shrink-0 rounded-full overflow-hidden border-4 border-white shadow-md z-10 bg-white flex items-center justify-center">
            <img
              src="/line_oa_profile_icon.jpg"
              alt="LINE OA Profile Icon"
              width={96}
              height={96}
              style={{ width: '96px', height: '96px', objectFit: 'cover' }}
              className="w-full h-full object-cover"
            />
          </div>

          <h1 className="text-[24px] leading-[32px] font-bold text-[#001e40] text-center z-10">
            Link Your Account
          </h1>
          <p className="text-[16px] leading-[24px] text-[#43474f] text-center z-10">
            Enter this 4-digit PIN in the MorBok LINE Official Account (<span className="font-bold text-[#006d33]">@791cmoeh</span>) to verify your identity.
          </p>

          {/* Dynamic QR Code Container */}
          <div className="bg-[#f0f3ff] p-3 rounded-xl border border-[#c3c6d1] z-10 flex flex-col items-center shadow-inner">
            <QRCodeSVG value={qrCodeUrl || 'https://line.me'} size={140} className="w-36 h-36" />
          </div>

          {/* PIN Display Boxes */}
          {pairingPin && (
            <div className="w-full bg-[#f0f3ff] border border-[#c3c6d1] rounded-lg p-[16px] flex items-center justify-center z-10">
              <div className="flex gap-2">
                {pairingPin.split('').map((digit, idx) => (
                  <span
                    key={idx}
                    className="w-12 h-14 flex items-center justify-center bg-white border border-[#c3c6d1] rounded text-[24px] font-bold text-[#001e40] shadow-sm font-mono"
                  >
                    {digit}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Timer Expiry */}
          <div className="flex items-center gap-1 text-[#43474f] text-[14px] z-10">
            <span className="material-symbols-outlined text-[16px]">timer</span>
            <span>Code expires in <span className="font-semibold text-[#001e40]">04:59</span></span>
          </div>

          {/* AI Model Selector */}
          <div className="w-full bg-[#f0f3ff] border border-[#c3c6d1] rounded-lg p-3 z-10 text-left space-y-1">
            <label className="text-[12px] font-bold text-[#001e40] flex items-center gap-1">
              <span className="material-symbols-outlined text-[16px]">smart_toy</span>
              AI Model:
            </label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full bg-white border border-[#c3c6d1] rounded-md px-3 py-1.5 text-[14px] text-[#001e40] font-semibold focus:outline-none focus:ring-2 focus:ring-[#006d33]"
            >
              <option value="google/gemini-2.5-flash">✨ Gemini 2.5 Flash (OpenRouter)</option>
              <option value="google/gemini-2.5-pro">🧠 Gemini 2.5 Pro (OpenRouter)</option>
              <option value="google/gemini-2.5-flash-lite">⚡ Gemini 2.5 Flash Lite</option>
            </select>
          </div>

          {/* PDPA Consent Checkbox */}
          <label className="flex items-start gap-2.5 cursor-pointer bg-[#f0f3ff] p-3 rounded-lg border border-[#c3c6d1] text-left w-full z-10">
            <input
              type="checkbox"
              checked={isConsentGiven}
              onChange={(e) => setIsConsentGiven(e.target.checked)}
              className="mt-0.5 w-4 h-4 text-[#006d33] rounded focus:ring-[#006d33] shrink-0 cursor-pointer"
            />
            <span className="text-[12px] text-[#111c2c] leading-relaxed">
              ผู้ป่วย/ผู้ดูแลยินยอมให้ใช้ระบบ AI สรุปคำแนะนำทางการแพทย์ (ตาม พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล PDPA มาตรา 26/37)
            </span>
          </label>

          {/* Toggle / Mobile Link */}
          <div className="w-full space-y-2 z-10">
            <a
              href={qrCodeUrl}
              target="_blank"
              rel="noreferrer"
              className="w-full flex items-center justify-center gap-1.5 py-2.5 px-4 rounded-lg border border-[#001e40] text-[#001e40] font-semibold text-[14px] hover:bg-[#f0f3ff] active:scale-[0.98] transition-all"
            >
              <span className="material-symbols-outlined text-[18px]">open_in_new</span>
              เปิดหน้าเว็บจับคู่สำหรับผู้ป่วย/ผู้ดูแลบนมือถือ
            </a>

            <button
              type="button"
              onClick={handleTogglePairing}
              className="w-full text-center text-[12px] text-[#3a5f94] hover:underline font-semibold cursor-pointer py-1"
            >
              {isConnected ? '🔴 จำลองตัดการเชื่อมต่อ' : '⚡ กดเพื่อจำลองสแกนสำเร็จ'}
            </button>
          </div>

          {/* Primary Action Button */}
          <button
            onClick={handleStartScribe}
            disabled={!isConsentGiven || !encounterId}
            className={`w-full py-3.5 px-4 rounded-lg font-semibold text-[16px] transition-all flex items-center justify-center gap-2 shadow-md z-10 ${
              isConsentGiven && encounterId
                ? 'bg-[#006d33] text-white hover:opacity-90 active:scale-[0.98] cursor-pointer'
                : 'bg-slate-300 text-slate-500 cursor-not-allowed'
            }`}
          >
            <span className="material-symbols-outlined text-[20px]">edit_note</span>
            Start Scribe Session (เริ่มกรอกบทสนทนา)
          </button>

        </div>

        {/* Need Help Bottom Action */}
        <div className="mt-6 text-center w-full">
          <a
            className="inline-flex items-center gap-1 text-[14px] font-semibold text-[#3a5f94] hover:opacity-80 transition-opacity"
            href="#"
          >
            <span className="material-symbols-outlined text-[18px]">help</span>
            Need help connecting?
          </a>
        </div>

      </main>
    </div>
  );
}


