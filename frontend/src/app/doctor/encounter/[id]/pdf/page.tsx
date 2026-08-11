// frontend/src/app/doctor/encounter/[id]/pdf/page.tsx
'use client';

import { useState, useEffect, use } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { QRCodeSVG } from 'qrcode.react';
import { API_BASE } from '@/lib/api';

export default function PDFDownloadPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const encounterId = resolvedParams.id;
  const router = useRouter();
  const searchParams = useSearchParams();

  const pdfId = searchParams.get('pdf_id') || `PDF_${encounterId}`;
  const downloadUrl = `${API_BASE}/api/v1/pdf/${pdfId}/download`;

  const [secondsRemaining, setSecondsRemaining] = useState(600); // 10 minutes = 600 seconds
  const [isExpired, setIsExpired] = useState(false);
  const [doctorInfo, setDoctorInfo] = useState<{ first_name: string; surname: string; license_no: string } | null>(null);

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

  // 10 minute live timer countdown
  useEffect(() => {
    const interval = setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          setIsExpired(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const formatCountdown = (totalSec: number) => {
    const mins = Math.floor(totalSec / 60).toString().padStart(2, '0');
    const secs = (totalSec % 60).toString().padStart(2, '0');
    return `${mins}:${secs}`;
  };

  const handleStartNextCase = () => {
    router.push('/');
  };

  return (
    <div className="bg-[#f9f9ff] text-[#111c2c] font-sans min-h-screen flex flex-col items-center justify-between antialiased selection:bg-[#d5e3ff]">
      {/* TopAppBar */}
      <header className="w-full top-0 sticky bg-white/80 backdrop-blur-md border-b border-[#c3c6d1] flex justify-between items-center px-5 h-16 max-w-[480px] mx-auto z-40 shadow-sm">
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={() => router.push(`/doctor/encounter/${encounterId}/review`)}
            className="text-[#43474F] hover:opacity-80 transition-opacity p-1.5 flex items-center justify-center cursor-pointer mr-1"
            title="ย้อนกลับไปแก้ไข Step 4"
          >
            <span className="material-symbols-outlined text-2xl">arrow_back</span>
          </button>
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#003366] to-[#006d33] flex items-center justify-center text-white shadow-md">
            <span className="material-symbols-outlined text-2xl">picture_as_pdf</span>
          </div>
          <div>
            <span className="text-xl font-black text-[#001e40] tracking-tight">MorBok</span>
            <span className="text-[10px] bg-[#75f999] text-[#007236] px-2 py-0.5 rounded-full ml-2 font-bold">
              PDF Ready
            </span>
          </div>
        </div>
      </header>

      {/* Main Canvas */}
      <main className="flex-grow flex flex-col items-center justify-center w-full max-w-[480px] mx-auto px-5 py-6 pb-16">
        
        {/* Step Indicator */}
        <div className="w-full flex items-center justify-between mb-4">
          <span className="text-xs font-extrabold text-[#003366] uppercase tracking-wider bg-[#e6f0ff] px-3 py-1 rounded-full border border-[#b3c8ff]">
            ขั้นตอนที่ 5: QR Code รับเอกสาร PDF
          </span>
          <button
            type="button"
            onClick={() => router.push(`/doctor/encounter/${encounterId}/review`)}
            className="text-xs font-bold text-[#003366] hover:bg-[#e6f0ff] bg-white px-2.5 py-1 rounded-lg border border-[#003366]/30 flex items-center gap-1 cursor-pointer shadow-2xs transition-colors"
          >
            <span className="material-symbols-outlined text-sm">arrow_back</span>
            แก้ไขขั้นตอนที่ 4
          </button>
        </div>

        {/* Expiry Timer Badge */}
        <div className="w-full mb-4">
          {isExpired ? (
            <div className="bg-[#fce8e6] border border-[#ba1a1a] text-[#ba1a1a] p-3 rounded-2xl flex items-center justify-center gap-2 font-bold text-xs shadow-sm">
              <span className="material-symbols-outlined text-lg">timer_off</span>
              <span>⚠️ เอกสารนี้หมดอายุ 10 นาทีแล้ว และถูกลบออกจากเซิร์ฟเวอร์เรียบร้อยแล้ว</span>
            </div>
          ) : (
            <div className="bg-[#e6f0ff] border border-[#003366]/30 text-[#003366] p-3 rounded-2xl flex items-center justify-between font-bold text-xs shadow-sm">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#006d33] animate-ping"></span>
                <span>เอกสาร PDF พร้อมดาวน์โหลด</span>
              </div>
              <div className="flex items-center gap-1 font-mono text-sm bg-white px-2.5 py-1 rounded-lg border border-[#003366]/20">
                <span className="material-symbols-outlined text-base text-[#ba1a1a]">schedule</span>
                <span className="text-[#ba1a1a]">{formatCountdown(secondsRemaining)}</span>
              </div>
            </div>
          )}
        </div>

        {/* QR Code Container Card */}
        <div className="w-full bg-white border border-[#c3c6d1] rounded-2xl shadow-[0_8px_24px_rgba(0,51,102,0.08)] p-6 space-y-5 flex flex-col items-center relative overflow-hidden">
          
          <div className="text-center space-y-1">
            <h1 className="text-xl font-extrabold text-[#001e40]">สแกน QR Code เพื่อรับเอกสาร PDF</h1>
            <p className="text-xs text-slate-500">
              ให้คนไข้หรือผู้ดูแลใช้กล้องถ่ายรูปบนโทรศัพท์มือถือ สแกน QR Code เพื่อเปิดเอกสารสรุปคำแนะนำ
            </p>
          </div>

          {/* QR Code Display */}
          <div className="bg-white p-4 rounded-2xl border-2 border-[#003366] shadow-md relative group flex flex-col items-center">
            {isExpired ? (
              <div className="w-48 h-48 bg-slate-100 flex flex-col items-center justify-center text-slate-400 text-xs font-bold rounded-xl text-center p-4">
                <span className="material-symbols-outlined text-4xl mb-2 text-slate-300">block</span>
                QR Code หมดอายุแล้ว
              </div>
            ) : (
              <QRCodeSVG
                value={downloadUrl}
                size={200}
                level="H"
                includeMargin={true}
                className="w-48 h-48"
              />
            )}
            <span className="text-[10px] text-slate-400 font-mono mt-2">Ref: {pdfId}</span>
          </div>

          {/* PDPA 10-Minute Storage Policy Notice */}
          <div className="bg-[#fff8e6] border border-[#b06000]/30 rounded-xl p-3.5 text-left space-y-1 text-xs text-[#b06000]">
            <div className="font-extrabold flex items-center gap-1.5">
              <span className="material-symbols-outlined text-base">lock</span>
              <span>นโยบายความปลอดภัยข้อมูลส่วนบุคคล (PDPA):</span>
            </div>
            <p className="text-slate-700 leading-relaxed">
              ไฟล์ PDF สรุปคำแนะนำนี้ <strong className="text-[#ba1a1a]">จะถูกเก็บไว้บนเซิร์ฟเวอร์ชั่วคราวเพียง 10 นาที</strong> นับจากเวลาที่อนุมัติ และจะถูกลบทิ้งอย่างถาวรเพื่อความปลอดภัย
            </p>
          </div>

          {/* Action Buttons */}
          <div className="w-full space-y-2.5 pt-1">
            {!isExpired && (
              <a
                href={downloadUrl}
                target="_blank"
                rel="noreferrer"
                className="w-full py-3.5 px-4 rounded-xl font-extrabold text-sm bg-[#006d33] hover:bg-[#005225] text-white flex items-center justify-center gap-2 shadow-lg transition-all cursor-pointer active:scale-[0.98]"
              >
                <span className="material-symbols-outlined text-xl">download</span>
                <span>เปิดดู / ดาวน์โหลดเอกสาร PDF (Download PDF)</span>
              </a>
            )}

            <button
              type="button"
              onClick={handleStartNextCase}
              className="w-full py-3.5 px-4 rounded-xl font-bold text-sm bg-white hover:bg-[#f0f3ff] text-[#001e40] border border-[#c3c6d1] flex items-center justify-center gap-2 shadow-sm transition-all cursor-pointer active:scale-[0.98]"
            >
              <span className="material-symbols-outlined text-xl">restart_alt</span>
              <span>เริ่มต้นตรวจเคสถัดไป (Start Next Case)</span>
            </button>
          </div>

        </div>

      </main>

      {/* Footer */}
      <footer className="w-full py-4 text-center text-xs text-slate-500 border-t border-[#c3c6d1] bg-white">
        MorBok Ambient Care Assistant • Step 5 PDF Delivery
      </footer>
    </div>
  );
}
