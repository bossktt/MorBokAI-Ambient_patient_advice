// frontend/src/app/patient/pair/page.tsx
'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';

function PatientPairContent() {
  const searchParams = useSearchParams();
  const [pin, setPin] = useState('');
  const [lineUserId, setLineUserId] = useState('');
  const [status, setStatus] = useState<'IDLE' | 'PAIRING' | 'SUCCESS' | 'ERROR'>('IDLE');
  const [message, setMessage] = useState('');
  const [encounterId, setEncounterId] = useState('');

  useEffect(() => {
    const urlPin = searchParams.get('pin');
    const urlToken = searchParams.get('token');
    if (urlPin) setPin(urlPin);
    else if (urlToken) setPin(urlToken);

    // Auto-generate a dummy LINE User ID for mobile test web browser
    if (typeof window !== 'undefined') {
      let savedUid = localStorage.getItem('pvs_patient_line_user_id');
      if (!savedUid) {
        savedUid = `U_CARE_GIVER_${Math.floor(100000 + Math.random() * 900000)}`;
        localStorage.setItem('pvs_patient_line_user_id', savedUid);
      }
      setLineUserId(savedUid);
    }
  }, [searchParams]);

  const handlePairSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pin.trim()) return;

    setStatus('PAIRING');
    try {
      const res = await fetch('http://localhost:8080/api/v1/encounters/pair', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pairing_pin: pin.trim(),
          line_user_id: lineUserId || 'U_TEST_USER_MOBILE'
        })
      });

      const data = await res.json();
      if (data.status === 'PAIRED') {
        setStatus('SUCCESS');
        setEncounterId(data.encounter_id);
        setMessage(`เชื่อมต่อสำเร็จ! รหัสเคส ${data.encounter_id}`);
      } else {
        setStatus('ERROR');
        setMessage(data.message || 'รหัส PIN ไม่ถูกต้องหรือหมดอายุ');
      }
    } catch (err) {
      setStatus('ERROR');
      setMessage('ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ กรุณาตรวจสอบอินเทอร์เน็ต');
    }
  };

  return (
    <div className="min-h-screen bg-[#F9F9FF] text-[#111C2C] flex flex-col items-center justify-center p-4 font-sans">
      <div className="max-w-[480px] w-full bg-white border border-[#C3C6D1] rounded-3xl p-6 sm:p-8 shadow-[0_4px_16px_rgba(0,51,102,0.08)] space-y-6 text-center">
        
        {/* Header Icon & Title */}
        <div className="space-y-2">
          <div className="w-16 h-16 bg-[#F0F3FF] border border-[#C3C6D1] rounded-2xl flex items-center justify-center mx-auto text-2xl shadow-sm text-[#001E40]">
            📲
          </div>
          <h1 className="text-2xl font-extrabold text-[#001E40]">
            หมอบอก (MorBok) LINE OA
          </h1>
          <p className="text-xs text-[#43474F] leading-relaxed">
            ระบบรับสรุปคำแนะนำการดูแลตนเองและตารางจัดบริหารยาทางการแพทย์สำหรับผู้ป่วยและผู้ดูแล
          </p>
        </div>

        {status === 'SUCCESS' ? (
          <div className="p-6 bg-[#E6F4EA] border border-[#006D33] rounded-2xl space-y-3 animate-fadeIn">
            <div className="text-4xl">🟢</div>
            <h2 className="text-lg font-extrabold text-[#006D33]">เชื่อมต่อรับข้อมูลสำเร็จ!</h2>
            <p className="text-xs text-[#111C2C]">
              เคสผู้ป่วยรหัส <span className="font-mono font-bold text-[#001E40] bg-white px-2 py-0.5 rounded border border-[#C3C6D1]">{encounterId}</span> ถูกจับคู่กับบัญชี LINE ของท่านเรียบร้อยแล้ว
            </p>
            <p className="text-[11px] text-[#43474F] pt-2 border-t border-[#006D33]/20 leading-relaxed">
              เมื่อคุณหมอตรวจเสร็จ สรุปคำแนะนำและใบนัด PDF จะถูกส่งเข้า LINE OA โดยอัตโนมัติ
            </p>
          </div>
        ) : (
          <form onSubmit={handlePairSubmit} className="space-y-4">
            <div className="space-y-1.5 text-left">
              <label className="text-xs font-bold text-[#001E40]">
                🔑 กรอกรหัส PIN 4 หลัก (เพื่อจับคู่รับสรุปคำแนะนำ):
              </label>
              <input
                type="text"
                maxLength={6}
                value={pin}
                onChange={(e) => setPin(e.target.value)}
                placeholder="กรอก PIN 4 หลัก (เช่น 4349)"
                className="w-full text-center tracking-widest text-3xl font-mono font-extrabold py-3.5 px-4 bg-[#F0F3FF] border border-[#C3C6D1] rounded-2xl focus:outline-none focus:ring-2 focus:ring-[#006D33] text-[#001E40] placeholder-slate-400"
              />
            </div>

            {status === 'ERROR' && (
              <div className="p-3 bg-[#FCE8E6] border border-[#BA1A1A] rounded-xl text-xs text-[#BA1A1A] font-bold">
                ⚠️ {message}
              </div>
            )}

            <button
              type="submit"
              disabled={status === 'PAIRING'}
              className="w-full py-4 bg-[#006D33] hover:bg-[#005225] text-white font-extrabold text-base rounded-xl shadow-md transition active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <span className="material-symbols-outlined">link</span>
              {status === 'PAIRING' ? '⏳ กำลังเชื่อมต่อข้อมูล...' : '✅ ยืนยันการเชื่อมต่อรับคำแนะนำ'}
            </button>
          </form>
        )}

        <div className="text-[10px] text-[#43474F] pt-3 border-t border-[#C3C6D1]">
          🛡️ สอดคล้องตาม พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล (PDPA) • ประมวลผลปลอดภัยบน RAM
        </div>
      </div>
    </div>
  );
}

export default function PatientPairPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-slate-950 text-white flex items-center justify-center">Loading...</div>}>
      <PatientPairContent />
    </Suspense>
  );
}
