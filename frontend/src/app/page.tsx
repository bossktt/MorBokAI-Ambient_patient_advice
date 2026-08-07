// frontend/src/app/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function DoctorInputPage() {
  const router = useRouter();
  const [firstName, setFirstName] = useState('');
  const [surname, setSurname] = useState('');
  const [licenseNo, setLicenseNo] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  // Load existing saved doctor profile if present
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('morbok_doctor_info');
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          if (parsed.first_name) setFirstName(parsed.first_name);
          if (parsed.surname) setSurname(parsed.surname);
          if (parsed.license_no) {
            setLicenseNo(parsed.license_no.replace(/\D/g, ''));
          }
        } catch (e) {}
      }
    }
  }, []);

  const handleProceedToPDPA = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanFirstName = firstName.trim();
    const cleanSurname = surname.trim();
    const cleanLicenseInput = licenseNo.trim();

    if (!cleanFirstName || !cleanSurname || !cleanLicenseInput) {
      setErrorMsg('กรุณากรอกข้อมูลแพทย์ให้ครบถ้วนทุกช่อง (ชื่อ, นามสกุล, เลขประกอบวิชาชีพ)');
      return;
    }

    // Extract digits to validate 4 to 6 digits
    const digitsOnly = cleanLicenseInput.replace(/\D/g, '');
    if (digitsOnly.length < 4 || digitsOnly.length > 6) {
      setErrorMsg('เลขที่ใบประกอบวิชาชีพเวชกรรมต้องเป็นตัวเลข 4 ถึง 6 หลัก (เช่น 48912 หรือ 123456)');
      return;
    }

    const doctorProfile = {
      first_name: cleanFirstName,
      surname: cleanSurname,
      license_no: `ว.${digitsOnly}`,
    };

    if (typeof window !== 'undefined') {
      localStorage.setItem('morbok_doctor_info', JSON.stringify(doctorProfile));
    }

    router.push('/doctor/pdpa');
  };

  return (
    <div className="bg-[#f9f9ff] text-[#111c2c] font-sans min-h-screen flex flex-col items-center justify-between antialiased selection:bg-[#d5e3ff]">
      {/* TopAppBar */}
      <header className="w-full top-0 sticky bg-white/80 backdrop-blur-md border-b border-[#c3c6d1] flex justify-between items-center px-5 h-16 max-w-[480px] mx-auto z-40 shadow-sm">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#003366] to-[#006d33] flex items-center justify-center text-white shadow-md">
            <span className="material-symbols-outlined text-2xl">medical_services</span>
          </div>
          <div>
            <span className="text-xl font-black text-[#001e40] tracking-tight">MorBok</span>
            <span className="text-[10px] bg-[#d5e3ff] text-[#001e40] px-2 py-0.5 rounded-full ml-2 font-bold">
              Prototype
            </span>
          </div>
        </div>
      </header>

      {/* Main Form Canvas */}
      <main className="flex-grow flex flex-col items-center justify-center w-full max-w-[480px] mx-auto px-5 py-8 pb-16">
        
        {/* Step Indicator */}
        <div className="w-full flex items-center justify-between mb-6 px-1">
          <span className="text-xs font-extrabold text-[#003366] uppercase tracking-wider bg-[#e6f0ff] px-3 py-1 rounded-full border border-[#b3c8ff]">
            ขั้นตอนที่ 1: ข้อมูลแพทย์ผู้ตรวจ
          </span>
        </div>

        {/* Hero Banner */}
        <div className="w-full bg-gradient-to-br from-[#001e40] to-[#003366] rounded-2xl p-6 text-white shadow-xl mb-6 relative overflow-hidden">
          <div className="absolute -top-10 -right-10 w-32 h-32 bg-[#75f999] opacity-20 rounded-full blur-2xl pointer-events-none"></div>
          <h1 className="text-2xl font-extrabold mb-1 tracking-tight">ระบบสรุปคำแนะนำทางการแพทย์</h1>
          <p className="text-xs text-slate-200 leading-relaxed">
            กรุณาระบุข้อมูลแพทย์ผู้ตรวจเพื่อใช้ในการสร้างและอนุมัติสรุปคำแนะนำการดูแลตนเองสำหรับผู้ป่วย
          </p>
        </div>

        {/* Doctor Input Card Form */}
        <form onSubmit={handleProceedToPDPA} className="w-full bg-white border border-[#c3c6d1] rounded-2xl shadow-[0_8px_24px_rgba(0,51,102,0.06)] p-6 space-y-5">
          <h2 className="text-lg font-bold text-[#001e40] flex items-center gap-2 border-b border-slate-100 pb-3">
            <span className="material-symbols-outlined text-[#006d33]">badge</span>
            ลงทะเบียนข้อมูลแพทย์ผู้ตรวจ
          </h2>

          {errorMsg && (
            <div className="bg-[#fce8e6] border border-[#ba1a1a]/30 text-[#ba1a1a] p-3 rounded-xl text-xs font-semibold flex items-center gap-2">
              <span className="material-symbols-outlined text-base shrink-0">error</span>
              <span>{errorMsg}</span>
            </div>
          )}

          {/* First Name Input */}
          <div className="space-y-1.5 text-left">
            <label className="text-xs font-bold text-[#001e40] flex items-center gap-1">
              <span>ชื่อจริง (First Name) *</span>
            </label>
            <input
              type="text"
              required
              value={firstName}
              onChange={(e) => {
                setFirstName(e.target.value);
                setErrorMsg('');
              }}
              placeholder="กรอกชื่อจริงแพทย์..."
              className="w-full bg-[#f0f3ff] border border-[#c3c6d1] rounded-xl px-4 py-3 text-sm text-[#111c2c] placeholder-slate-400 font-medium focus:outline-none focus:ring-2 focus:ring-[#006d33] transition-all"
            />
          </div>

          {/* Surname Input */}
          <div className="space-y-1.5 text-left">
            <label className="text-xs font-bold text-[#001e40] flex items-center gap-1">
              <span>นามสกุล (Surname) *</span>
            </label>
            <input
              type="text"
              required
              value={surname}
              onChange={(e) => {
                setSurname(e.target.value);
                setErrorMsg('');
              }}
              placeholder="กรอกนามสกุลแพทย์..."
              className="w-full bg-[#f0f3ff] border border-[#c3c6d1] rounded-xl px-4 py-3 text-sm text-[#111c2c] placeholder-slate-400 font-medium focus:outline-none focus:ring-2 focus:ring-[#006d33] transition-all"
            />
          </div>

          {/* Medical License Number Input */}
          <div className="space-y-1.5 text-left">
            <label className="text-xs font-bold text-[#001e40] flex items-center justify-between">
              <span className="flex items-center gap-1">
                <span className="material-symbols-outlined text-sm text-[#003366]">pin</span>
                <span>เลขที่ใบประกอบวิชาชีพเวชกรรม *</span>
              </span>
              <span className="text-[10px] text-slate-500 font-normal">(ตัวเลข 4 - 6 หลัก)</span>
            </label>
            <div className="relative flex items-center">
              <span className="absolute left-4 font-bold text-[#003366] text-sm select-none">ว.</span>
              <input
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                required
                maxLength={6}
                value={licenseNo}
                onChange={(e) => {
                  const onlyNums = e.target.value.replace(/\D/g, '').slice(0, 6);
                  setLicenseNo(onlyNums);
                  setErrorMsg('');
                }}
                placeholder="กรอกตัวเลข 4 - 6 หลัก (เช่น 48912)"
                className="w-full bg-[#f0f3ff] border border-[#c3c6d1] rounded-xl pl-9 pr-4 py-3 text-sm text-[#111c2c] placeholder-slate-400 font-mono font-bold focus:outline-none focus:ring-2 focus:ring-[#006d33] transition-all"
              />
            </div>
          </div>

          {/* Quick Preset Doctor Button for Testing */}
          <div className="pt-1">
            <button
              type="button"
              onClick={() => {
                setFirstName('วินัย');
                setSurname('ให้คำแนะนำ');
                setLicenseNo('12345');
                setErrorMsg('');
              }}
              className="w-full text-center text-xs text-[#006d33] hover:underline bg-[#e6f4ea] py-2 rounded-lg font-bold border border-[#006d33]/20 cursor-pointer"
            >
              ⚡ ใช้ข้อมูลแพทย์ทดสอบ (แพทย์ วินัย ให้คำแนะนำ ว.12345)
            </button>
          </div>

          {/* Action Button */}
          <button
            type="submit"
            className="w-full py-4 px-6 rounded-xl font-extrabold text-base transition-all flex items-center justify-center gap-2 shadow-lg bg-[#006d33] hover:bg-[#005225] text-white active:scale-[0.98] cursor-pointer mt-2"
          >
            <span>ถัดไป: ยืนยันข้อตกลง PDPA</span>
            <span className="material-symbols-outlined text-xl">arrow_forward</span>
          </button>
        </form>

      </main>

      {/* Footer */}
      <footer className="w-full py-4 text-center text-xs text-slate-500 border-t border-[#c3c6d1] bg-white">
        MorBok Ambient Care Assistant • Step 1 Doctor Registration
      </footer>
    </div>
  );
}
