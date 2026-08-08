'use client';

import React, { useState } from 'react';
import Link from 'next/link';

export default function PatientSurveyPage() {
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  // Form State
  const [csat, setCsat] = useState(5);
  const [languageClarity, setLanguageClarity] = useState(5);
  const [medMatrixClarity, setMedMatrixClarity] = useState(5);
  const [lineAudioConvenience, setLineAudioConvenience] = useState(5);
  const [reassurance, setReassurance] = useState(5);
  const [redFlagRecall, setRedFlagRecall] = useState(100);
  const [medRecall, setMedRecall] = useState(100);
  const [npsScore, setNpsScore] = useState(10);
  const [comments, setComments] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const payload = {
      role: 'PATIENT',
      channel: 'LINE_OA',
      overall_satisfaction_csat: Number(csat),
      language_clarity_satisfaction: Number(languageClarity),
      med_matrix_clarity_satisfaction: Number(medMatrixClarity),
      line_audio_convenience_satisfaction: Number(lineAudioConvenience),
      reassurance_peace_of_mind: Number(reassurance),
      patient_nps_score: Number(npsScore),
      red_flag_recall_score: Number(redFlagRecall),
      med_instruction_recall_score: Number(medRecall),
      comments: comments
    };

    try {
      const res = await fetch('/api/v1/telemetry/record', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        setSubmitted(true);
      } else {
        alert('เกิดข้อผิดพลาดในการบันทึกแบบประเมิน');
      }
    } catch (err) {
      console.error(err);
      alert('ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-4">
      <div className="max-w-lg w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-block p-3 bg-emerald-500/10 text-emerald-400 rounded-full text-2xl font-bold mb-1">
            🟢 MorBok AI
          </div>
          <h1 className="text-xl font-bold text-white">แบบประเมินความพึงพอใจและการรับฟังคำแนะนำหมอ</h1>
          <p className="text-xs text-slate-400">สำหรับผู้ป่วยและผู้ดูแล (Patient & Caregiver Feedback)</p>
        </div>

        {submitted ? (
          <div className="bg-emerald-950/40 border border-emerald-800 rounded-xl p-6 text-center space-y-4">
            <div className="text-4xl">🎉</div>
            <h2 className="text-lg font-bold text-emerald-400">ขอบคุณสำหรับข้อมูลประเมิน!</h2>
            <p className="text-sm text-slate-300">
              ความเห็นของท่านมีคุณค่าอย่างยิ่งในการพัฒนาคุณภาพการบริการและคำแนะนำทางการแพทย์
            </p>
            <button
              onClick={() => setSubmitted(false)}
              className="mt-4 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition"
            >
              ทบทวนหรือส่งแบบประเมินอีกครั้ง
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5 text-sm">
            {/* CSAT 1-5 */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-200">1. ความพึงพอใจภาพรวมต่อสรุปคำแนะนำแพทย์ (CSAT):</label>
              <select
                value={csat}
                onChange={(e) => setCsat(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
              >
                <option value={5}>⭐️⭐️⭐️⭐️⭐️ (5 - พึงพอใจมากที่สุด)</option>
                <option value={4}>⭐️⭐️⭐️⭐️ (4 - พึงพอใจมาก)</option>
                <option value={3}>⭐️⭐️⭐️ (3 - ปานกลาง)</option>
                <option value={2}>⭐️⭐️ (2 - น้อย)</option>
                <option value={1}>⭐️ (1 - น้อยที่สุด)</option>
              </select>
            </div>

            {/* Language Clarity */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-200">2. ภาษาไทยเข้าใจง่าย (ระดับ ป.5):</label>
              <select
                value={languageClarity}
                onChange={(e) => setLanguageClarity(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
              >
                <option value={5}>5 - ชัดเจนและเข้าใจง่ายมาก</option>
                <option value={4}>4 - เข้าใจง่าย</option>
                <option value={3}>3 - ปานกลาง</option>
                <option value={2}>2 - อ่านยากเล็กน้อย</option>
                <option value={1}>1 - เข้าใจยากมาก</option>
              </select>
            </div>

            {/* Med Matrix Clarity */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-200">3. ตารางยา 🟢เริ่ม 🔴หยุด 🟡ปรับขนาด ช่วยจัดยาง่ายขึ้น:</label>
              <select
                value={medMatrixClarity}
                onChange={(e) => setMedMatrixClarity(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
              >
                <option value={5}>5 - ช่วยป้องกันกินยาผิดได้ดีมาก</option>
                <option value={4}>4 - ชัดเจนดี</option>
                <option value={3}>3 - ปานกลาง</option>
                <option value={2}>2 - สับสนเล็กน้อย</option>
                <option value={1}>1 - ไม่ชัดเจน</option>
              </select>
            </div>

            {/* Reassurance */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-200">4. ความอุ่นใจและมั่นใจในการดูแลตนเองที่บ้าน:</label>
              <select
                value={reassurance}
                onChange={(e) => setReassurance(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
              >
                <option value={5}>5 - มั่นใจและอุ่นใจมากที่สุด</option>
                <option value={4}>4 - อุ่นใจ</option>
                <option value={3}>3 - ปานกลาง</option>
                <option value={2}>2 - ยังคงกังวล</option>
                <option value={1}>1 - กังวลมาก</option>
              </select>
            </div>

            {/* NPS */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-200">5. โอกาสที่จะแนะนำสรุปคำแนะนำนี้ให้ผู้อื่น (NPS 0-10):</label>
              <input
                type="number"
                min="0"
                max="10"
                value={npsScore}
                onChange={(e) => setNpsScore(Number(e.target.value))}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white"
              />
            </div>

            {/* Comments */}
            <div className="space-y-1">
              <label className="font-semibold text-slate-200">ข้อเสนอแนะเพิ่มเติม:</label>
              <textarea
                rows={3}
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                placeholder="เช่น อยากให้เพิ่มปุ่มกดอ่านเสียงพูด, อยากให้ส่งตารางเข้า LINE ทันที..."
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white text-xs"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 font-bold text-white rounded-xl shadow-lg transition"
            >
              {loading ? 'กำลังบันทึก...' : 'บันทึกแบบประเมิน'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
