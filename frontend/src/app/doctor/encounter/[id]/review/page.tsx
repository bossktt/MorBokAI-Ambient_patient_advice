// frontend/src/app/doctor/encounter/[id]/review/page.tsx
/**
 * Screen 4: Doctor Review & WYSIWYG Editor Page
 * ===============================================
 * This component presents the AI-extracted After-Visit Summary (AVS) draft to the attending physician.
 * 
 * Key Features & Responsibilities:
 *   1. Clinical Data Loading: Retrieves raw transcript from localStorage/backend cache and queries
 *      `/api/v1/encounters/process-transcript` to obtain structured JSON from the selected LLM Adapter.
 *   2. Single Combined Instruction Input (ลักษณะยา + วิธีรับประทาน / คำแนะนำ):
 *      Combines physical description, dosage, timing, and warning notes into full-width editable inputs
 *      for fast clinical editing by physicians.
 *   3. Medication Reconciliation Cards: START (🟢 ยาเริ่มใหม่), STOP (🔴 ยาให้หยุดทาน), CHANGE (🟡 ยาปรับขนาด).
 *   4. Screen 4 -> Screen 3 Back Button: Allows doctors to return to Screen 3 (`scribe/page.tsx`) to edit audio/transcript.
 *   5. Screen 4 -> Screen 5 PDF Export: Posts confirmed summary payload to `/export-pdf` and redirects to Screen 5 (`pdf/page.tsx`).
 */

'use client';

import { useState, useEffect, use } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { API_BASE } from '@/lib/api';

export default function ReviewEncounterPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const encounterId = resolvedParams.id;
  const router = useRouter();
  const searchParams = useSearchParams();

  const selectedModel = searchParams.get('model') || 'google/gemini-2.5-flash';
  const [isExporting, setIsExporting] = useState(false);
  const [rawTranscript, setRawTranscript] = useState<string>('');
  const [doctorInfo, setDoctorInfo] = useState<{ first_name: string; surname: string; license_no: string }>({
    first_name: 'วินัย',
    surname: 'ให้คำแนะนำ',
    license_no: 'ว.12345',
  });

  // 1:1 Dynamic WYSIWYG State (Editable by Doctor)
  const [diagnosis, setDiagnosis] = useState('');
  const [instructions, setInstructions] = useState<string[]>([]);

  // Medication Reconciliation Matrix States (START / STOP / CHANGE)
  const [startMeds, setStartMeds] = useState<{ name: string; desc: string; usage: string }[]>([]);
  const [stopMeds, setStopMeds] = useState<{ name: string; desc: string; warning: string }[]>([]);
  const [changeMeds, setChangeMeds] = useState<{ name: string; desc: string; change: string }[]>([]);

  const [followUpDate, setFollowUpDate] = useState('');
  const [isAnonymous, setIsAnonymous] = useState(false);

  const [isGeneratingLLM, setIsGeneratingLLM] = useState(false);
  const [diagnosisError, setDiagnosisError] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Read recorded transcript & Doctor Info, then process through Clinical LLM Adapter
  useEffect(() => {
    if (typeof window !== 'undefined') {
      let docInfoObj = { first_name: 'วินัย', surname: 'ให้คำแนะนำ', license_no: 'ว.12345' };
      const savedDoc = localStorage.getItem('morbok_doctor_info');
      if (savedDoc) {
        try {
          docInfoObj = JSON.parse(savedDoc);
          setDoctorInfo(docInfoObj);
        } catch (e) { }
      }

      const savedTranscript =
        localStorage.getItem(`pvs_transcript_${encounterId}`) ||
        localStorage.getItem('pvs_transcript_latest');

      if (savedTranscript) {
        setRawTranscript(savedTranscript);

        // Trigger Clinical LLM Adapter (Gemini 2.5 Flash Lite ZDR)
        setIsGeneratingLLM(true);
        fetch(`${API_BASE}/api/v1/encounters/process-transcript`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            encounter_id: encounterId,
            raw_transcript: savedTranscript,
            doctor_info: docInfoObj
          })
        })
          .then((res) => res.json())
          .then((data) => {
            if (data.status === 'SUCCESS') {
              const rawDiag = (data.diagnosis || '').trim();
              const invalidDiags = ['ไม่ระบุ', 'ไม่มี', 'ไม่พบข้อมูล', 'ไม่พบคำวินิจฉัย', 'ไม่พบข้อวินิจฉัย', 'ไม่ระบุข้อวินิจฉัย', '-', 'N/A'];
              if (rawDiag && !invalidDiags.includes(rawDiag)) {
                setDiagnosis(rawDiag);
                setDiagnosisError(false);
              } else {
                setDiagnosis('');
              }
              if (data.instructions && data.instructions.length > 0) setInstructions(data.instructions);
              if (data.startMeds) setStartMeds(data.startMeds);
              if (data.stopMeds) setStopMeds(data.stopMeds);
              if (data.changeMeds) setChangeMeds(data.changeMeds);
              if (data.followUpDate) setFollowUpDate(data.followUpDate);
            }
          })
          .catch((err) => {
            console.error('LLM Processing error:', err);
          })
          .finally(() => {
            setIsGeneratingLLM(false);
          });
      }
    }
  }, [encounterId]);

  // Instruction Handlers
  const handleAddInstruction = () => {
    setInstructions((prev) => [...prev, '']);
  };
  const handleRemoveInstruction = (index: number) => {
    setInstructions((prev) => prev.filter((_, i) => i !== index));
  };

  // Med Handlers
  const handleAddStartMed = () => {
    setStartMeds((prev) => [...prev, { name: '', desc: '', usage: '' }]);
  };
  const handleRemoveStartMed = (index: number) => {
    setStartMeds((prev) => prev.filter((_, i) => i !== index));
  };

  const handleAddStopMed = () => {
    setStopMeds((prev) => [...prev, { name: '', desc: '', warning: '' }]);
  };
  const handleRemoveStopMed = (index: number) => {
    setStopMeds((prev) => prev.filter((_, i) => i !== index));
  };

  const handleAddChangeMed = () => {
    setChangeMeds((prev) => [...prev, { name: '', desc: '', change: '' }]);
  };
  const handleRemoveChangeMed = (index: number) => {
    setChangeMeds((prev) => prev.filter((_, i) => i !== index));
  };

  // Export note to PDF & proceed to Screen 5
  const handleExportPDF = async () => {
    if (!diagnosis || !diagnosis.trim()) {
      setDiagnosisError(true);
      setErrorMsg('กรุณากรอกวินิจฉัยโรค (Diagnosis) ก่อนดำเนินการต่อ');
      const el = document.getElementById('diagnosis-textarea');
      if (el) el.focus();
      return;
    }

    setDiagnosisError(false);
    setErrorMsg('');
    setIsExporting(true);
    const summaryData = {
      diagnosis,
      instructions,
      startMeds,
      stopMeds,
      changeMeds,
      followUpDate
    };

    const finalDoctorInfo = {
      ...doctorInfo,
      is_anonymous: isAnonymous,
    };

    try {
      const res = await fetch(`${API_BASE}/api/v1/encounters/${encounterId}/export-pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doctor_info: finalDoctorInfo,
          summary_data: summaryData
        })
      });
      const data = await res.json();
      const pdfId = data.pdf_id || `PDF_${Math.floor(100000 + Math.random() * 900000)}`;

      router.push(`/doctor/encounter/${encounterId}/pdf?pdf_id=${pdfId}`);
    } catch (e) {
      const mockPdfId = `PDF_MOCK_${Math.floor(100000 + Math.random() * 900000)}`;
      router.push(`/doctor/encounter/${encounterId}/pdf?pdf_id=${mockPdfId}`);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="bg-[#F9F9FF] text-[#111C2C] font-sans min-h-screen flex flex-col justify-between antialiased">
      {/* TopAppBar */}
      <header className="w-full top-0 sticky z-50 bg-white border-b border-[#C3C6D1] shadow-sm">
        <div className="flex justify-between items-center px-4 h-14 max-w-[480px] mx-auto">
          <button
            onClick={() => router.push(`/doctor/encounter/${encounterId}/scribe`)}
            className="text-[#43474F] hover:opacity-80 transition-opacity p-2 flex items-center justify-center cursor-pointer"
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

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto px-4 py-6 max-w-[480px] mx-auto w-full pb-24 flex flex-col gap-5">

        {/* Step Indicator */}
        <div className="w-full flex items-center justify-between">
          <span className="text-xs font-extrabold text-[#003366] uppercase tracking-wider bg-[#e6f0ff] px-3 py-1 rounded-full border border-[#b3c8ff]">
            ขั้นตอนที่ 4: ตรวจสอบ & ยืนยันโน้ต
          </span>
        </div>

        {/* Doctor Info Header Banner */}
        <div className="bg-gradient-to-r from-[#001e40] to-[#003366] text-white rounded-2xl p-4 shadow-md flex items-center justify-between">
          <div className="space-y-0.5 text-left">
            <div className="text-xs text-slate-300 font-bold uppercase tracking-wide">แพทย์ผู้ยืนยันโน้ต</div>
            <div className="text-base font-extrabold">
              {isAnonymous ? 'ไม่ระบุชื่อและนามสกุล' : `แพทย์ ${doctorInfo.first_name} ${doctorInfo.surname}`}
            </div>
            <div className="text-xs text-slate-200">
              เลขประกอบวิชาชีพ: <span className="font-mono font-bold text-[#75f999]">{isAnonymous ? 'ไม่เปิดเผย' : (doctorInfo.license_no.replace(/\D/g, '') ? `ว.${doctorInfo.license_no.replace(/\D/g, '')}` : doctorInfo.license_no)}</span>
            </div>
          </div>
          <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center border border-white/20">
            <span className="material-symbols-outlined text-2xl">
              {isAnonymous ? 'visibility_off' : 'verified_user'}
            </span>
          </div>
        </div>

        {/* Header Title */}
        <div className="flex flex-col gap-1 text-left">
          <h1 className="text-2xl font-extrabold text-[#001E40]">แก้ไขและอนุมัติสรุปคำแนะนำ</h1>
          <p className="text-xs text-[#43474F]">
            กรุณาตรวจสอบและแก้ไขความถูกต้องของคำแนะนำ ก่อนกดออกเอกสาร PDF ให้คนไข้
          </p>
        </div>



        {/* LLM Processing Overlay */}
        {isGeneratingLLM && (
          <div className="bg-[#Eefdf2] border border-[#C3E8D1] rounded-2xl p-6 flex flex-col items-center justify-center text-center space-y-4 shadow-sm animate-pulse">
            <span className="material-symbols-outlined text-4xl text-[#10A352] animate-spin">autorenew</span>
            <span className="text-[#10A352] font-bold">✨ AI กำลังประมวลผล คำแนะนำทางการแพทย์อยู่...</span>
          </div>
        )}

        {/* Bento Cards Layout */}
        <div className="grid grid-cols-1 gap-4 text-left">

          {/* Card 1: Diagnosis & Doctor's Advice */}
          <div className={`bg-white border ${diagnosisError ? 'border-red-500 ring-2 ring-red-200' : 'border-[#C3C6D1]'} rounded-2xl p-4 shadow-sm space-y-3 transition-all`}>
            <div className="flex justify-between items-center border-b border-[#C3C6D1]/60 pb-2.5">
              <div className="flex items-center gap-2 text-[#003366]">
                <span className="material-symbols-outlined text-xl">stethoscope</span>
                <h2 className="font-bold text-sm text-[#001E40]">
                  1. วินิจฉัยโรค (Diagnosis) <span className="text-red-500 font-extrabold">*</span>
                </h2>
              </div>
              {diagnosisError && (
                <span className="text-xs font-bold text-red-600 animate-pulse">
                  ⚠️ จำเป็นต้องกรอก
                </span>
              )}
            </div>
            <textarea
              id="diagnosis-textarea"
              value={diagnosis}
              onChange={(e) => {
                setDiagnosis(e.target.value);
                if (e.target.value.trim()) {
                  setDiagnosisError(false);
                  setErrorMsg('');
                }
              }}
              placeholder="วินิจฉัยโรค"
              className={`w-full bg-[#F0F3FF] border ${diagnosisError ? 'border-red-400 focus:ring-red-500' : 'border-[#C3C6D1] focus:ring-[#006D33]'} rounded-xl p-3 text-xs text-[#111C2C] focus:ring-2 font-bold leading-relaxed placeholder-slate-400`}
              rows={2}
            />
            {diagnosisError && (
              <p className="text-xs font-bold text-red-600 flex items-center gap-1">
                <span className="material-symbols-outlined text-sm">error</span>
                กรุณากรอกวินิจฉัยโรคก่อนสร้างเอกสาร PDF
              </p>
            )}
          </div>

          {/* Card 2: Patient Self-Care Guide */}
          <div className="bg-white border border-[#C3C6D1] rounded-2xl p-4 shadow-sm space-y-3">
            <div className="flex justify-between items-center border-b border-[#C3C6D1]/60 pb-2.5">
              <div className="flex items-center gap-2 text-[#003366]">
                <span className="material-symbols-outlined text-xl">person</span>
                <h2 className="font-bold text-sm text-[#001E40]">2. คำแนะนำการดูแลตนเอง (Medical instruction)</h2>
              </div>
              <button
                type="button"
                onClick={handleAddInstruction}
                className="text-xs text-[#006D33] hover:underline font-bold cursor-pointer"
              >
                + เพิ่ม
              </button>
            </div>

            <div className="space-y-2">
              {instructions.map((inst, idx) => (
                <div key={idx} className="flex items-center gap-2 bg-[#F0F3FF] p-2.5 rounded-xl border border-[#C3C6D1]">
                  <span className="text-[#006D33] font-bold text-sm shrink-0">•</span>
                  <input
                    type="text"
                    value={inst}
                    placeholder="ระบุข้อแนะนำการดูแลตนเอง..."
                    onChange={(e) => {
                      const newInst = [...instructions];
                      newInst[idx] = e.target.value;
                      setInstructions(newInst);
                    }}
                    className="w-full bg-white border border-[#C3C6D1] rounded-lg px-2.5 py-1.5 text-xs text-[#111C2C] focus:ring-1 focus:ring-[#006D33] font-medium placeholder:text-slate-400"
                  />
                  <button
                    type="button"
                    onClick={() => handleRemoveInstruction(idx)}
                    className="text-red-500 hover:text-red-700 text-xs px-1 cursor-pointer font-bold"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Card 3: Medication Instructions */}
          <div className="bg-white border border-[#C3C6D1] rounded-2xl p-4 shadow-sm space-y-3">
            <div className="flex justify-between items-center border-b border-[#C3C6D1]/60 pb-2.5">
              <div className="flex items-center gap-2 text-[#003366]">
                <span className="material-symbols-outlined text-xl">pill</span>
                <h2 className="font-bold text-sm text-[#001E40]">3. ตารางจัดบริหารยา (Medication)</h2>
              </div>
            </div>

            {/* 🟢 START MEDS */}
            <div className="bg-[#E6F4EA] border-l-4 border-[#006D33] p-3.5 rounded-r-xl space-y-2 text-xs text-[#006D33]">
              <div className="flex items-center justify-between font-bold">
                <span>🟢 ยาเริ่มใหม่ (START):</span>
                <button type="button" onClick={handleAddStartMed} className="text-[11px] underline cursor-pointer">+ เพิ่มรายการ</button>
              </div>

              {startMeds.map((med, idx) => (
                <div key={idx} className="bg-white p-3 rounded-xl border border-[#006D33]/30 shadow-xs space-y-2 relative">
                  <div className="flex justify-between items-center gap-2">
                    <div className="flex items-center gap-1.5 flex-1">
                      <span className="text-[11px] font-bold text-[#006D33] shrink-0">ชื่อยา:</span>
                      <input
                        type="text"
                        value={med.name}
                        placeholder="ระบุชื่อยา (เช่น ยาละลายเสมหะ)"
                        onChange={(e) => {
                          const updated = [...startMeds];
                          updated[idx].name = e.target.value;
                          setStartMeds(updated);
                        }}
                        className="font-bold text-xs w-full text-[#006D33] bg-[#f8fafc] border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#006D33]"
                      />
                    </div>
                    <button type="button" onClick={() => handleRemoveStartMed(idx)} className="text-red-500 text-xs shrink-0 cursor-pointer font-bold hover:bg-red-50 p-1 rounded">✕</button>
                  </div>

                  <div>
                    <span className="text-[10px] text-slate-500 font-semibold block mb-0.5">ลักษณะยา / วิธีรับประทาน / คำแนะนำ:</span>
                    <input
                      type="text"
                      value={med.usage || med.desc || ''}
                      placeholder="เช่น น้ำเชื่อมใส — 1 ช้อนโต๊ะ วันละ 3 ครั้ง หลังอาหาร"
                      onChange={(e) => {
                        const updated = [...startMeds];
                        updated[idx].usage = e.target.value;
                        setStartMeds(updated);
                      }}
                      className="w-full bg-[#f8fafc] border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 font-medium focus:outline-none focus:ring-1 focus:ring-[#006D33]"
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* 🔴 STOP MEDS */}
            <div className="bg-[#FCE8E6] border-l-4 border-[#BA1A1A] p-3.5 rounded-r-xl space-y-2 text-xs text-[#BA1A1A]">
              <div className="flex items-center justify-between font-bold">
                <span>🔴 ยาให้หยุดทานทันที (STOP):</span>
                <button type="button" onClick={handleAddStopMed} className="text-[11px] underline cursor-pointer">+ เพิ่มรายการ</button>
              </div>

              {stopMeds.map((med, idx) => (
                <div key={idx} className="bg-white p-3 rounded-xl border border-[#BA1A1A]/30 shadow-xs space-y-2 relative">
                  <div className="flex justify-between items-center gap-2">
                    <div className="flex items-center gap-1.5 flex-1">
                      <span className="text-[11px] font-bold text-[#BA1A1A] shrink-0">ชื่อยา:</span>
                      <input
                        type="text"
                        value={med.name}
                        placeholder="ระบุชื่อยาที่ให้หยุด (เช่น Metformin 500mg)"
                        onChange={(e) => {
                          const updated = [...stopMeds];
                          updated[idx].name = e.target.value;
                          setStopMeds(updated);
                        }}
                        className="font-bold text-xs w-full text-[#BA1A1A] bg-[#fff5f5] border border-red-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#BA1A1A] placeholder:text-red-300"
                      />
                    </div>
                    <button type="button" onClick={() => handleRemoveStopMed(idx)} className="text-red-500 text-xs shrink-0 cursor-pointer font-bold hover:bg-red-50 p-1 rounded">✕</button>
                  </div>

                  <div>
                    <span className="text-[10px] text-red-600 font-semibold block mb-0.5">ลักษณะยา / คำเตือน / คำสั่งหยุด:</span>
                    <input
                      type="text"
                      value={med.warning !== undefined ? med.warning : (med.desc || '')}
                      placeholder="หยุดใช้ยาทันที"
                      onChange={(e) => {
                        const updated = [...stopMeds];
                        updated[idx].warning = e.target.value;
                        setStopMeds(updated);
                      }}
                      className="w-full bg-[#fff5f5] border border-red-200 rounded-lg px-2.5 py-1.5 text-xs text-red-700 font-bold focus:outline-none focus:ring-1 focus:ring-[#BA1A1A] placeholder:text-red-300"
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* 🟡 CHANGE MEDS */}
            <div className="bg-[#FEF7E0] border-l-4 border-[#B06000] p-3.5 rounded-r-xl space-y-2 text-xs text-[#B06000]">
              <div className="flex items-center justify-between font-bold">
                <span>🟡 ยาปรับขนาดยา (CHANGE):</span>
                <button type="button" onClick={handleAddChangeMed} className="text-[11px] underline cursor-pointer">+ เพิ่มรายการ</button>
              </div>

              {changeMeds.map((med, idx) => (
                <div key={idx} className="bg-white p-3 rounded-xl border border-[#B06000]/30 shadow-xs space-y-2 relative">
                  <div className="flex justify-between items-center gap-2">
                    <div className="flex items-center gap-1.5 flex-1">
                      <span className="text-[11px] font-bold text-[#B06000] shrink-0">ชื่อยา:</span>
                      <input
                        type="text"
                        value={med.name}
                        placeholder="ระบุชื่อยาที่ปรับขนาด (เช่น Amlodipine 5mg)"
                        onChange={(e) => {
                          const updated = [...changeMeds];
                          updated[idx].name = e.target.value;
                          setChangeMeds(updated);
                        }}
                        className="font-bold text-xs w-full text-[#B06000] bg-[#fffdf0] border border-amber-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#B06000]"
                      />
                    </div>
                    <button type="button" onClick={() => handleRemoveChangeMed(idx)} className="text-red-500 text-xs shrink-0 cursor-pointer font-bold hover:bg-red-50 p-1 rounded">✕</button>
                  </div>

                  <div>
                    <span className="text-[10px] text-amber-700 font-semibold block mb-0.5">ลักษณะยา / ขนาดยาใหม่ / วิธีรับประทานใหม่:</span>
                    <input
                      type="text"
                      value={med.change || med.desc || ''}
                      placeholder="เช่น ยาลดความดัน เม็ดสีเหลือง — ปรับลดเหลือ 1 เม็ด ก่อนนอน"
                      onChange={(e) => {
                        const updated = [...changeMeds];
                        updated[idx].change = e.target.value;
                        setChangeMeds(updated);
                      }}
                      className="w-full bg-[#fffdf0] border border-amber-200 rounded-lg px-2.5 py-1.5 text-xs text-amber-900 font-semibold focus:outline-none focus:ring-1 focus:ring-[#B06000]"
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Card 4: Follow-up */}
          <div className="bg-white border border-[#C3C6D1] rounded-2xl p-4 shadow-sm space-y-2">
            <div className="flex items-center gap-2 text-[#003366] border-b border-[#C3C6D1]/60 pb-2">
              <span className="material-symbols-outlined text-xl">event</span>
              <h2 className="font-bold text-sm text-[#001E40]">4. นัดหมายติดตามอาการครั้งถัดไป</h2>
            </div>
            <input
              type="text"
              value={followUpDate}
              onChange={(e) => setFollowUpDate(e.target.value)}
              className="w-full bg-[#F0F3FF] border border-[#C3C6D1] rounded-xl px-3 py-2 text-xs text-[#111C2C] focus:ring-1 focus:ring-[#006D33] font-bold"
            />
          </div>

        </div>

        {/* Checkbox for Anonymous Doctor Name */}
        <div className="bg-white border border-[#C3C6D1] rounded-2xl p-4 shadow-sm flex items-center gap-3 cursor-pointer hover:bg-[#F0F3FF] transition-colors mt-2">
          <input
            type="checkbox"
            id="anonymous-doctor-checkbox"
            checked={isAnonymous}
            onChange={(e) => setIsAnonymous(e.target.checked)}
            className="w-5 h-5 text-[#006D33] rounded focus:ring-[#006D33] border-gray-300 cursor-pointer accent-[#006D33]"
          />
          <label htmlFor="anonymous-doctor-checkbox" className="text-xs font-bold text-[#001E40] cursor-pointer flex-1 select-none leading-relaxed">
            ท่านไม่ประสงค์เปิดเผยชื่อและเลขประกอบวิชาชีพ ในสรุปคำแนะนำ
          </label>
        </div>

        {/* Error Alert Message */}
        {errorMsg && (
          <div className="bg-red-50 border border-red-300 text-red-700 text-xs font-bold rounded-xl p-3 flex items-center gap-2 animate-bounce">
            <span className="material-symbols-outlined text-lg">warning</span>
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Primary Action Button to Export PDF */}
        <div className="pt-2">
          <button
            onClick={handleExportPDF}
            disabled={isExporting}
            className="w-full bg-[#006D33] text-white font-extrabold text-base py-4 px-6 rounded-xl flex items-center justify-center gap-2 hover:bg-[#005225] active:scale-[0.98] transition-all shadow-lg cursor-pointer disabled:bg-slate-400"
          >
            <span className="material-symbols-outlined">picture_as_pdf</span>
            {isExporting ? '⏳ กำลังสร้างเอกสาร PDF...' : 'ถัดไป: ยืนยัน & สร้าง QR Code เอกสาร PDF'}
          </button>
        </div>

      </main>

      <footer className="w-full py-3 text-center text-xs text-slate-500 border-t border-[#c3c6d1] bg-white">
        MorBok • Step 4 Review & Edit Note
      </footer>
    </div>
  );
}
