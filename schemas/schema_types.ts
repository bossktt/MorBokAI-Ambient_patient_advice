// src/types/schema_types.ts
/**
 * TypeScript Type Definitions for the Refined Clinical JSON Data Contract (ED Focus)
 */

export interface DoctorInfo {
  doctor_id: string;
  full_name: string;
  license_no: string;
}

export interface PatientInfo {
  patient_name: string; // Blinded for PDPA e.g. "คุณ[ผู้ป่วย-ปกปิดข้อมูล]"
  hn: string;           // Blinded e.g. "65-XXXXXX"
  age: number;
  gender?: string;
}

export interface CaregiverInfo {
  caregiver_name: string; // Blinded e.g. "คุณ[ผู้ดูแล-ปกปิดข้อมูล]"
  relationship: string;
  phone_number: string;   // Blinded e.g. "08X-XXX-XXXX"
}

export interface EncounterMetadata {
  hospital_name: string;
  department: string; // e.g. "ห้องฉุกเฉิน (Emergency Department)"
  visit_timestamp: string;
  doctor: DoctorInfo;
  patient: PatientInfo;
  caregiver: CaregiverInfo;
}

export interface FollowUpDetails {
  follow_up_date?: string;
  follow_up_date_thai: string;
  clinic_name: string;
  preparation_instructions: string[];
}

export interface PatientView {
  headline: string;
  diagnosis: string; // e.g. "ภาวะความดันโลหิตสูงและระดับน้ำตาลในเลือดสูงชั่วคราว"
  key_instructions: string[];
  follow_up: FollowUpDetails;
  audio_tts_url?: string;
}

export interface MedStart {
  med_name: string;
  physical_description: string; // e.g. "ยาเม็ดใหญ่สีขาว"
  dosage: string;
  timing: string;
  instructions: string;
}

export interface MedStop {
  med_name: string;
  physical_description: string; // e.g. "ยาเม็ดเล็กสีขาวซองเดิม"
  discard_instruction: string; // e.g. "หยิบทิ้งถังขยะทันที ห้ามทานซ้ำ"
  reason: string;
}

export interface MedChange {
  med_name: string;
  physical_description: string; // e.g. "ยาลดความดัน เม็ดสีเหลืองกลม"
  new_dosage: string;
  timing: string;
  change_summary: string;
}

export interface MedContinue {
  med_name: string;
  physical_description: string;
  dosage: string;
  timing: string;
}

export interface MedicationReconciliation {
  start: MedStart[];
  stop: MedStop[];
  change: MedChange[];
  continue: MedContinue[];
}

export interface CaregiverMatrix {
  medication_reconciliation: MedicationReconciliation;
  daily_home_tasks: string[];
}

export interface HotlineTrigger {
  national_emergency_number: '1669';
  hospital_direct_number: string;
}

export interface RedFlags {
  emergency_warnings: string[];
  hotline_call_trigger: HotlineTrigger;
}

export interface AudioEvidence {
  section_key: string;
  timestamp_start: string; // e.g. "01:42"
  timestamp_end: string;   // e.g. "01:58"
  audio_clip_url: string;
}

export interface EncounterDraftSchema {
  encounter_id: string;
  metadata: EncounterMetadata;
  patient_view: PatientView;
  caregiver_matrix: CaregiverMatrix;
  red_flags: RedFlags;
  audio_evidence: AudioEvidence[];
}
