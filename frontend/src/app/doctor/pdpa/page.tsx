// frontend/src/app/doctor/pdpa/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { API_BASE } from '@/lib/api';

export default function PDPADisclaimerPage() {
  const router = useRouter();
  const [doctorInfo, setDoctorInfo] = useState<{ first_name: string; surname: string; license_no: string } | null>(null);
  const [isChecked, setIsChecked] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

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

  const handleStartEncounter = async () => {
    if (!isChecked) return;
    setIsCreating(true);

    try {
      const res = await fetch(`${API_BASE}/api/v1/encounters/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doctor_info: doctorInfo })
      });
      const data = await res.json();
      const encounterId = data.encounter_id || `ENC_${Math.floor(100000 + Math.random() * 900000)}`;

      // Navigate to Screen 3 (Scribe)
      router.push(`/doctor/encounter/${encounterId}/scribe`);
    } catch (err) {
      const mockId = `ENC_${Math.floor(100000 + Math.random() * 900000)}`;
      router.push(`/doctor/encounter/${mockId}/scribe`);
    }
  };

  return (
    <div className="bg-[#f9f9ff] text-[#111c2c] font-sans min-h-screen flex flex-col items-center justify-between antialiased selection:bg-[#d5e3ff]">
      {/* TopAppBar */}
      <header className="w-full top-0 sticky bg-white/80 backdrop-blur-md border-b border-[#c3c6d1] flex justify-between items-center px-5 h-16 max-w-[480px] mx-auto z-40 shadow-sm">
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => router.push('/')}
            aria-label="Back"
            className="text-[#43474f] hover:opacity-80 transition-opacity p-1 cursor-pointer flex items-center justify-center"
          >
            <span className="material-symbols-outlined text-2xl">arrow_back</span>
          </button>
          <div>
            <span className="text-xl font-black text-[#001e40] tracking-tight">MorBok</span>
            <span className="text-[10px] bg-[#d5e3ff] text-[#001e40] px-2 py-0.5 rounded-full ml-2 font-bold">
              PDPA Safety
            </span>
          </div>
        </div>
      </header>

      {/* Main Canvas */}
      <main className="flex-grow flex flex-col items-center justify-center w-full max-w-[480px] mx-auto px-5 py-8 pb-16">
        
        {/* Step Indicator */}
        <div className="w-full flex items-center justify-between mb-6 px-1">
          <span className="text-xs font-extrabold text-[#003366] uppercase tracking-wider bg-[#e6f0ff] px-3 py-1 rounded-full border border-[#b3c8ff]">
            ขั้นตอนที่ 2 จาก 5: คำยืนยัน PDPA & ความปลอดภัย
          </span>
          <span className="text-xs font-bold text-slate-500">Step 2/5</span>
        </div>

        {/* Doctor Summary Tag */}
        {doctorInfo && (
          <div className="w-full bg-[#f0f3ff] border border-[#c3c6d1] rounded-xl p-3 mb-4 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 font-bold text-[#001e40]">
              <span className="material-symbols-outlined text-[#006d33]">account_circle</span>
              <span>นพ./พญ. {doctorInfo.first_name} {doctorInfo.surname}</span>
            </div>
            <span className="bg-white px-2 py-0.5 rounded border border-[#c3c6d1] font-mono font-bold text-[#003366]">
              {doctorInfo.license_no}
            </span>
          </div>
        )}

        {/* PDPA Disclaimer Card */}
        <div className="w-full bg-white border border-[#c3c6d1] rounded-2xl shadow-[0_8px_24px_rgba(0,51,102,0.06)] p-6 space-y-5">
          
          <div className="flex items-center gap-3 border-b border-slate-100 pb-3">
            <div className="w-10 h-10 rounded-full bg-[#fce8e6] text-[#ba1a1a] flex items-center justify-center shrink-0">
              <span className="material-symbols-outlined text-2xl">security</span>
            </div>
            <div>
              <h1 className="text-lg font-bold text-[#001e40] leading-snug">
                ข้อตกลงและคำชี้แจงความเป็นส่วนตัว (PDPA Disclaimer)
              </h1>
              <p className="text-[11px] text-slate-500">พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562</p>
            </div>
          </div>

          {/* Prototype De-identification Notice Box */}
          <div className="bg-[#fff8e6] border-l-4 border-[#b06000] p-4 rounded-r-xl space-y-2 text-left">
            <div className="flex items-center gap-2 text-[#b06000] font-extrabold text-sm">
              <span className="material-symbols-outlined text-lg">warning</span>
              <span>แจ้งเตือนสำคัญ: ระบบยังอยู่ในช่วงทดสอบต้นแบบ (Prototype Stage)</span>
            </div>
            <p className="text-xs text-slate-800 leading-relaxed font-medium">
              เนื่องจากระบบ MorBok ยังอยู่ในระหว่างการพัฒนาและทดสอบต้นแบบ ทำให้การปกปิดตัวตนของระบบ (De-identification Engine) <strong className="text-[#ba1a1a] underline">ยังไม่สมบูรณ์ 100%</strong>
            </p>
          </div>

          {/* Prohibited items during recording */}
          <div className="space-y-3 text-left bg-[#f0f3ff] p-4 rounded-xl border border-[#c3c6d1]">
            <h2 className="text-xs font-extrabold text-[#001e40] uppercase tracking-wide">
              ⚠️ ข้อปฏิบัติระหว่างการกรอกบทสนทนา:
            </h2>
            <p className="text-xs text-slate-700 leading-relaxed font-medium">
              เพื่อป้องกันการหลุดรอดของข้อมูลส่วนบุคคลที่มีความอ่อนไหว ขอความกรุณาแพทย์ผู้ตรวจ <strong className="text-[#ba1a1a]">หลีกเลี่ยงการพิมพ์ข้อมูลต่อไปนี้</strong> ระหว่างการกรอกข้อความ:
            </p>
            
            <ul className="space-y-2 text-xs font-semibold text-slate-800 pl-1">
              <li className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-[#fce8e6] text-[#ba1a1a] flex items-center justify-center text-xs shrink-0">✕</span>
                <span>ชื่อ-นามสกุลจริงของผู้ป่วย</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-[#fce8e6] text-[#ba1a1a] flex items-center justify-center text-xs shrink-0">✕</span>
                <span>ชื่อ-นามสกุลของญาติ หรือผู้ดูแล</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-[#fce8e6] text-[#ba1a1a] flex items-center justify-center text-xs shrink-0">✕</span>
                <span>หมายเลขประจำตัวผู้ป่วย (HN)</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-[#fce8e6] text-[#ba1a1a] flex items-center justify-center text-xs shrink-0">✕</span>
                <span>เลขประจำตัวประชาชน 13 หลัก</span>
              </li>
            </ul>
          </div>

          {/* Confirmation Checkbox */}
          <label className="flex items-start gap-3 bg-[#e6f4ea] border border-[#006d33]/30 p-4 rounded-xl cursor-pointer text-left transition-colors hover:bg-[#d5eedc]">
            <input
              type="checkbox"
              checked={isChecked}
              onChange={(e) => setIsChecked(e.target.checked)}
              className="mt-0.5 w-5 h-5 text-[#006d33] rounded border-slate-300 focus:ring-[#006d33] shrink-0 cursor-pointer"
            />
            <span className="text-xs text-[#003366] font-bold leading-relaxed">
              ข้าพเจ้ารับทราบ และจะหลีกเลี่ยงการพิมพ์ชื่อคนไข้, ญาติ, HN และเลข 13 หลัก ระหว่างการกรอกข้อความ
            </span>
          </label>

          {/* Action Button */}
          <button
            onClick={handleStartEncounter}
            disabled={!isChecked || isCreating}
            className={`w-full py-4 px-6 rounded-xl font-extrabold text-base transition-all flex items-center justify-center gap-2 shadow-lg ${
              isChecked && !isCreating
                ? 'bg-[#006d33] hover:bg-[#005225] text-white active:scale-[0.98] cursor-pointer'
                : 'bg-slate-300 text-slate-500 cursor-not-allowed shadow-none'
            }`}
          >
            <span className="material-symbols-outlined text-xl">edit_note</span>
            <span>{isCreating ? 'กำลังสร้าง Session...' : 'ถัดไป: เริ่มกรอกบทสนทนาตรวจเคส (Start Scribe)'}</span>
          </button>

        </div>

      </main>

      {/* Footer */}
      <footer className="w-full py-4 text-center text-xs text-slate-500 border-t border-[#c3c6d1] bg-white">
        MorBok Ambient Care Assistant • Step 2 PDPA Confirmation
      </footer>
    </div>
  );
}
