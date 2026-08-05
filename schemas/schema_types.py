# app/schemas/schema_types.py
"""
Pydantic v2 Models for backend validation of the Refined Clinical JSON Contract.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class DoctorInfo(BaseModel):
    doctor_id: str = Field(..., example="DOC_1048")
    full_name: str = Field(..., example="นพ. สมชาย ใจดี")
    license_no: str = Field(..., example="ว.49281")

class PatientInfo(BaseModel):
    patient_name: str = Field(..., example="คุณ[ผู้ป่วย-ปกปิดข้อมูล PDPA]")
    hn: str = Field(..., example="65-XXXXXX")
    age: int = Field(..., example=72)
    gender: Optional[str] = Field(None, example="หญิง")

class CaregiverInfo(BaseModel):
    caregiver_name: str = Field(..., example="คุณ[ผู้ดูแล-ปกปิดข้อมูล PDPA]")
    relationship: str = Field(..., example="ลูกชาย")
    phone_number: str = Field(..., example="08X-XXX-XXXX")

class EncounterMetadata(BaseModel):
    hospital_name: str = Field(..., example="โรงพยาบาลตัวอย่าง (Sample Hospital)")
    department: str = Field("ห้องฉุกเฉิน (Emergency Department)", example="ห้องฉุกเฉิน (Emergency Department)")
    visit_timestamp: str = Field(..., example="2026-08-02T11:30:00Z")
    doctor: DoctorInfo
    patient: PatientInfo
    caregiver: CaregiverInfo

class FollowUpDetails(BaseModel):
    follow_up_date: Optional[str] = Field(None, example="2026-08-16T09:00:00Z")
    follow_up_date_thai: str = Field(..., example="วันอาทิตย์ที่ 16 สิงหาคม 2026 เวลา 09:00 น.")
    clinic_name: str = Field(..., example="คลินิกอายุรกรรมหัวใจและหลอดเลือด (ห้องตรวจ 4)")
    preparation_instructions: List[str] = Field(
        ...,
        example=[
            "งดน้ำและอาหารหลังเที่ยงคืนก่อนวันตรวจเพื่อเจาะเลือด",
            "นำสมุดบันทึกความดันโลหิตและซองยาที่กำลังทานอยู่มาด้วยทุกครั้ง"
        ]
    )

class PatientView(BaseModel):
    headline: str = Field(..., example="สรุปคำแนะนำการดูแลตนเองหลังออกจากห้องฉุกเฉิน (2 ส.ค. 2026)")
    diagnosis: str = Field(..., example="ภาวะความดันโลหิตสูงและระดับน้ำตาลในเลือดสูงชั่วคราว (Hypertensive Urgency with Hyperglycemia)")
    key_instructions: List[str] = Field(..., example=["ทานยาปรับระดับน้ำตาลตัวใหม่...", "ทิ้งยาเม็ดสีขาวตัวเดิม..."])
    follow_up: FollowUpDetails
    audio_tts_url: Optional[str] = Field(None, example="https://api.pvs-health.org/media/tts/tts_ENC_9823.mp3")

class MedStart(BaseModel):
    med_name: str = Field(..., example="Metformin 1000 mg")
    physical_description: str = Field(..., example="ยาเม็ดใหญ่สีขาว รูปไข่")
    dosage: str = Field(..., example="1 เม็ด")
    timing: str = Field(..., example="เช้า - เย็น")
    instructions: str = Field(..., example="ทานหลังอาหารทันที")

class MedStop(BaseModel):
    med_name: str = Field(..., example="Metformin 500 mg (ซองเดิม)")
    physical_description: str = Field(..., example="ยาเม็ดเล็กสีขาว กลม")
    discard_instruction: str = Field(..., example="หยิบทิ้งถังขยะทันที ห้ามนำมารับประทานซ้ำ")
    reason: str = Field(..., example="ปรับเพิ่มขนาดเป็นยาตัวใหม่แล้ว")

class MedChange(BaseModel):
    med_name: str = Field(..., example="Amlodipine 5 mg")
    physical_description: str = Field(..., example="ยาลดความดัน เม็ดสีเหลืองกลม")
    new_dosage: str = Field(..., example="1 เม็ด (วันละ 1 ครั้ง)")
    timing: str = Field(..., example="ก่อนนอน")
    change_summary: str = Field(..., example="ปรับลดจากเดิมวันละ 2 เม็ด เหลือ 1 เม็ดก่อนนอน")

class MedContinue(BaseModel):
    med_name: str = Field(..., example="Aspirin 81 mg")
    physical_description: str = Field(..., example="ยาเม็ดเล็กสีชมพู เคลือบแป้ง")
    dosage: str = Field(..., example="1 เม็ด")
    timing: str = Field(..., example="หลังอาหารเช้า")

class MedicationReconciliation(BaseModel):
    start: List[MedStart]
    stop: List[MedStop]
    change: List[MedChange]
    continue_: List[MedContinue] = Field(..., alias="continue")

class CaregiverMatrix(BaseModel):
    medication_reconciliation: MedicationReconciliation
    daily_home_tasks: List[str]

class HotlineTrigger(BaseModel):
    national_emergency_number: str = Field("1669", example="1669")
    hospital_direct_number: str = Field(..., example="02-XXX-XXXX ต่อ ER")

class RedFlags(BaseModel):
    emergency_warnings: List[str]
    hotline_call_trigger: HotlineTrigger

class AudioEvidence(BaseModel):
    section_key: str = Field(..., example="medication_reconciliation.stop[0]")
    timestamp_start: str = Field(..., example="01:42")
    timestamp_end: str = Field(..., example="01:58")
    audio_clip_url: str = Field(..., example="https://api.pvs-health.org/media/clips/clip_0142_0158.mp3")

class EncounterDraftSchema(BaseModel):
    encounter_id: str = Field(..., example="ENC_20260802_9823")
    metadata: EncounterMetadata
    patient_view: PatientView
    caregiver_matrix: CaregiverMatrix
    red_flags: RedFlags
    audio_evidence: List[AudioEvidence]
