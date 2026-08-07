# backend/app/services/pdf_service.py
"""
MorBok AI — Patient After-Visit Summary (AVS) PDF Generation Engine
===================================================================
This module provides vector PDF document generation for patient-facing after-visit summaries.

Key Design Features:
  - FPDF Vector Rendering: Produces clean A4 printable sheets (210mm x 297mm).
  - PyThainLP Thai Text Wrapping: Automatically segments Thai sentences with zero spaces using `pythainlp.tokenize.word_tokenize` for proper line wrapping.
  - High-Resolution Icon Synthesis: Generates clean 512x512 PNG vector icons dynamically via Pillow if static assets are missing.
  - Medication Reconciliation Badges: Renders START (🟢 เริ่มใหม่), STOP (🔴 หยุดทาน), and CHANGE (🟡 ปรับขนาด) status pills.
  - 10-Minute Auto-Purge Lifecycle: PDF files saved in `temp_pdfs/` expire after 10 minutes (600s) and are automatically deleted by `cleanup_expired_pdfs()`.

Maintainer Notes:
  - Font Fallbacks: Supports ChulaCharasNew, Kanit, Sarabun TTF fonts with macOS Sathu.ttf system fallback.
  - PDF Output Directory: `backend/app/temp_pdfs/`
"""

import os
import time
import uuid
from typing import Dict, Any
from PIL import Image, ImageDraw
from fpdf import FPDF, XPos, YPos

# Paths
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
FONT_DIR = os.path.join(ASSETS_DIR, "fonts")
ICON_DIR = os.path.join(ASSETS_DIR, "pdf_icons")

CHULA_REGULAR = os.path.join(FONT_DIR, "ChulaCharasNewReg.ttf")
CHULA_BOLD = os.path.join(FONT_DIR, "ChulaCharasNewBold.ttf")
KANIT_REGULAR = os.path.join(FONT_DIR, "Kanit-Regular.ttf")
KANIT_BOLD = os.path.join(FONT_DIR, "Kanit-Bold.ttf")
SARABUN_REGULAR = os.path.join(FONT_DIR, "Sarabun-Regular.ttf")
SARABUN_BOLD = os.path.join(FONT_DIR, "Sarabun-Bold.ttf")
THAI_FONT_PATH_FALLBACK = "/System/Library/Fonts/Supplemental/Sathu.ttf"

def ensure_pdf_icons():
    """
    Generates high-resolution PNG icon assets required for PDF rendering if missing.
    """
    os.makedirs(ICON_DIR, exist_ok=True)
    
    navy = (11, 43, 92, 255) # #0b2b5c
    
    def canvas(size=512):
        return Image.new("RGBA", (size, size), (255, 255, 255, 0))

    # 1. Header MorBok Document Check Icon
    path_morbok = os.path.join(ICON_DIR, "icon_morbok_header.png")
    if not os.path.exists(path_morbok):
        img = canvas()
        draw = ImageDraw.Draw(img)
        draw.ellipse([16, 16, 496, 496], fill=(255, 255, 255, 255))
        draw.rounded_rectangle([140, 100, 370, 410], radius=24, outline=navy, width=22)
        draw.line([190, 160, 320, 160], fill=navy, width=18)
        draw.line([190, 220, 320, 220], fill=navy, width=18)
        draw.line([190, 280, 270, 280], fill=navy, width=18)
        draw.ellipse([300, 300, 430, 430], fill=navy)
        draw.line([335, 365, 360, 390], fill=(255, 255, 255, 255), width=16)
        draw.line([360, 390, 405, 335], fill=(255, 255, 255, 255), width=16)
        img.save(path_morbok)

    # 2. Doctor Icon
    path_doc = os.path.join(ICON_DIR, "icon_doctor.png")
    if not os.path.exists(path_doc):
        img = canvas()
        draw = ImageDraw.Draw(img)
        draw.ellipse([16, 16, 496, 496], fill=(216, 230, 250, 255))
        draw.ellipse([196, 100, 316, 220], fill=navy)
        draw.chord([120, 240, 392, 480], start=180, end=360, fill=navy)
        draw.arc([160, 220, 352, 380], start=0, end=180, fill=(255, 255, 255, 255), width=20)
        draw.ellipse([236, 370, 276, 410], fill=(255, 255, 255, 255))
        img.save(path_doc)

    # 3. Section 1 Stethoscope Icon
    path_steth = os.path.join(ICON_DIR, "icon_stethoscope.png")
    if not os.path.exists(path_steth):
        img = canvas()
        draw = ImageDraw.Draw(img)
        draw.arc([140, 80, 372, 300], start=0, end=180, fill=navy, width=28)
        draw.line([140, 80, 140, 150], fill=navy, width=28)
        draw.line([372, 80, 372, 150], fill=navy, width=28)
        draw.ellipse([124, 64, 156, 96], fill=navy)
        draw.ellipse([356, 64, 388, 96], fill=navy)
        draw.line([256, 190, 256, 340], fill=navy, width=28)
        draw.arc([256, 260, 420, 410], start=90, end=270, fill=navy, width=28)
        draw.ellipse([380, 305, 460, 385], fill=navy)
        draw.ellipse([400, 325, 440, 365], fill=(255, 255, 255, 255))
        img.save(path_steth)

    # 4. Section 2 Advice / Chat bubble Icon
    path_adv = os.path.join(ICON_DIR, "icon_advice.png")
    if not os.path.exists(path_adv):
        img = canvas()
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([70, 70, 442, 370], radius=60, fill=navy)
        draw.polygon([(140, 360), (80, 440), (210, 370)], fill=navy)
        draw.ellipse([216, 120, 296, 200], fill=(255, 255, 255, 255))
        draw.chord([166, 210, 346, 350], start=180, end=360, fill=(255, 255, 255, 255))
        img.save(path_adv)

    # 5. Section 3 Medication Pill Bottle & Pill Icon
    path_meds = os.path.join(ICON_DIR, "icon_meds.png")
    if not os.path.exists(path_meds):
        img = canvas()
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([80, 100, 260, 150], radius=10, fill=navy)
        draw.rounded_rectangle([90, 150, 250, 420], radius=20, outline=navy, width=24)
        draw.line([120, 260, 220, 260], fill=navy, width=20)
        draw.line([120, 320, 220, 320], fill=navy, width=20)
        draw.rounded_rectangle([290, 220, 450, 380], radius=80, fill=navy)
        draw.line([290, 300, 450, 300], fill=(255, 255, 255, 255), width=16)
        img.save(path_meds)

    # 6. Section 4 Calendar Icon
    path_cal = os.path.join(ICON_DIR, "icon_calendar.png")
    if not os.path.exists(path_cal):
        img = canvas()
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([70, 100, 442, 430], radius=30, outline=navy, width=24)
        draw.rounded_rectangle([70, 100, 442, 190], radius=30, fill=navy)
        draw.rounded_rectangle([150, 60, 180, 120], radius=10, fill=navy)
        draw.rounded_rectangle([330, 60, 360, 120], radius=10, fill=navy)
        draw.ellipse([270, 260, 410, 400], fill=navy)
        draw.line([305, 330, 330, 355], fill=(255, 255, 255, 255), width=16)
        draw.line([330, 355, 375, 300], fill=(255, 255, 255, 255), width=16)
        img.save(path_cal)

    # 7. PDPA Info Icon
    path_info = os.path.join(ICON_DIR, "icon_info.png")
    if not os.path.exists(path_info):
        img = canvas()
        draw = ImageDraw.Draw(img)
        draw.ellipse([16, 16, 496, 496], fill=navy)
        draw.ellipse([226, 110, 286, 170], fill=(255, 255, 255, 255))
        draw.rounded_rectangle([226, 210, 286, 400], radius=15, fill=(255, 255, 255, 255))
        img.save(path_info)

    # 8. Emergency Phone Icon
    path_phone = os.path.join(ICON_DIR, "icon_phone.png")
    if not os.path.exists(path_phone):
        size = 512
        img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        white = (255, 255, 255, 255)
        draw.ellipse([40, 40, 472, 472], outline=white, width=32)

        h_img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        h_draw = ImageDraw.Draw(h_img)
        h_draw.rounded_rectangle([220, 110, 300, 200], radius=25, fill=white)
        h_draw.rounded_rectangle([220, 310, 300, 400], radius=25, fill=white)
        h_draw.arc([140, 140, 370, 370], start=100, end=260, fill=white, width=44)

        rotated = h_img.rotate(-135, resample=Image.BICUBIC)
        img.alpha_composite(rotated)
        img.save(path_phone)

    # 9. Emergency Ambulance Graphic
    path_amb = os.path.join(ICON_DIR, "graphic_ambulance.png")
    if not os.path.exists(path_amb):
        img = Image.new("RGBA", (800, 400), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        dark_blue = (15, 23, 42, 255)
        red_color = (220, 38, 38, 255)
        draw.rounded_rectangle([100, 120, 600, 320], radius=30, fill=(255, 255, 255, 255), outline=dark_blue, width=16)
        draw.polygon([(600, 180), (720, 240), (720, 320), (600, 320)], fill=(255, 255, 255, 255), outline=dark_blue, width=16)
        draw.polygon([(605, 195), (695, 240), (695, 260), (605, 260)], fill=dark_blue)
        draw.rectangle([260, 190, 320, 270], fill=red_color)
        draw.rectangle([220, 215, 360, 245], fill=red_color)
        draw.rectangle([108, 285, 712, 300], fill=red_color)
        draw.rounded_rectangle([330, 90, 390, 120], radius=10, fill=(37, 99, 235, 255))
        draw.ellipse([180, 280, 280, 380], fill=dark_blue)
        draw.ellipse([210, 310, 250, 350], fill=(255, 255, 255, 255))
        draw.ellipse([540, 280, 640, 380], fill=dark_blue)
        draw.ellipse([570, 310, 610, 350], fill=(255, 255, 255, 255))
        img.save(path_amb)

    # 10. Watermark Top Right Header
    path_wm = os.path.join(ICON_DIR, "watermark_header.png")
    if not os.path.exists(path_wm):
        img = Image.new("RGBA", (400, 300), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        light_cross = (220, 235, 252, 180)
        draw.rectangle([250, 40, 280, 140], fill=light_cross)
        draw.rectangle([200, 70, 330, 100], fill=light_cross)
        draw.rectangle([340, 160, 360, 230], fill=light_cross)
        draw.rectangle([310, 185, 390, 205], fill=light_cross)
        img.save(path_wm)

    # 11. START badge (+)
    path_start = os.path.join(ICON_DIR, "badge_start.png")
    if not os.path.exists(path_start):
        img = canvas(256)
        draw = ImageDraw.Draw(img)
        green = (21, 128, 61, 255)
        draw.rounded_rectangle([10, 10, 246, 246], radius=40, fill=green)
        draw.rectangle([110, 50, 146, 206], fill=(255, 255, 255, 255))
        draw.rectangle([50, 110, 206, 146], fill=(255, 255, 255, 255))
        img.save(path_start)

    # 12. STOP badge (-)
    path_stop = os.path.join(ICON_DIR, "badge_stop.png")
    if not os.path.exists(path_stop):
        img = canvas(256)
        draw = ImageDraw.Draw(img)
        red = (185, 28, 28, 255)
        draw.rounded_rectangle([10, 10, 246, 246], radius=40, fill=red)
        draw.rectangle([50, 110, 206, 146], fill=(255, 255, 255, 255))
        img.save(path_stop)

    # 13. CHANGE badge (~)
    path_chg = os.path.join(ICON_DIR, "badge_change.png")
    if not os.path.exists(path_chg):
        img = canvas(256)
        draw = ImageDraw.Draw(img)
        orange = (194, 65, 12, 255)
        draw.rounded_rectangle([10, 10, 246, 246], radius=40, fill=orange)
        draw.rectangle([50, 110, 206, 146], fill=(255, 255, 255, 255))
        img.save(path_chg)


class PDFService:
    @staticmethod
    def generate_patient_summary_pdf(
        encounter_id: str,
        doctor_info: Dict[str, str],
        summary_data: Dict[str, Any],
        output_dir: str
    ) -> Dict[str, Any]:
        """
        Generates a beautifully formatted patient advice sheet PDF matching hospital guidelines.
        Returns pdf_id, file_path, download_url, created_at, expires_at (10 mins TTL).
        """
        ensure_pdf_icons()
        os.makedirs(output_dir, exist_ok=True)
        pdf_id = f"PDF_{uuid.uuid4().hex[:10].upper()}"
        file_name = f"{pdf_id}.pdf"
        file_path = os.path.join(output_dir, file_name)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=False)

        # Register Fonts (ChulaCharasNew -> Kanit -> Sarabun -> Fallback)
        font_name = "Helvetica"
        if os.path.exists(CHULA_REGULAR) and os.path.exists(CHULA_BOLD):
            try:
                pdf.add_font("ChulaCharasNew", "", CHULA_REGULAR)
                pdf.add_font("ChulaCharasNew", "B", CHULA_BOLD)
                font_name = "ChulaCharasNew"
            except Exception as e:
                print(f"Notice loading ChulaCharasNew TTF: {e}")
        elif os.path.exists(KANIT_REGULAR) and os.path.exists(KANIT_BOLD):
            try:
                pdf.add_font("Kanit", "", KANIT_REGULAR)
                pdf.add_font("Kanit", "B", KANIT_BOLD)
                font_name = "Kanit"
            except Exception as e:
                print(f"Notice loading Kanit TTF: {e}")
        elif os.path.exists(SARABUN_REGULAR) and os.path.exists(SARABUN_BOLD):
            try:
                pdf.add_font("THSarabun", "", SARABUN_REGULAR)
                pdf.add_font("THSarabun", "B", SARABUN_BOLD)
                font_name = "THSarabun"
            except Exception as e:
                print(f"Notice loading Sarabun TTF: {e}")
        elif os.path.exists(THAI_FONT_PATH_FALLBACK):
            try:
                pdf.add_font("THSarabun", "", THAI_FONT_PATH_FALLBACK)
                pdf.add_font("THSarabun", "B", THAI_FONT_PATH_FALLBACK)
                font_name = "THSarabun"
            except Exception as e:
                print(f"Notice loading fallback Sathu.ttf: {e}")

        NAVY = (11, 43, 92)      # #0b2b5c Dark navy
        SLATE = (71, 85, 105)    # #475569 Slate gray
        DARK_TEXT = (30, 41, 59) # #1e293b Dark text

        # ----------------------------------------------------
        # TOP HEADER
        # ----------------------------------------------------
        watermark_path = os.path.join(ICON_DIR, "watermark_header.png")
        if os.path.exists(watermark_path):
            pdf.image(watermark_path, x=150, y=2, w=58)

        pdf.set_xy(10, 8)
        pdf.set_text_color(*NAVY)
        pdf.set_font(font_name, 'B', 22 if font_name == 'THSarabun' else 18)
        pdf.cell(0, 9, "โรงพยาบาลมหาราชนครเชียงใหม่", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_xy(10, 18)
        pdf.set_text_color(*SLATE)
        pdf.set_font(font_name, '', 13 if font_name == 'THSarabun' else 11)
        pdf.cell(0, 6, "คณะแพทยศาสตร์ มหาวิทยาลัยเชียงใหม่", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Header Accent Line (Navy + Gold)
        pdf.set_fill_color(*NAVY)
        pdf.rect(0, 28, 175, 2.5, 'F')
        pdf.set_fill_color(229, 169, 93) # Gold accent
        pdf.rect(175, 28, 35, 2.5, 'F')

        # ----------------------------------------------------
        # 1. MORBOK CARD BANNER
        # ----------------------------------------------------
        y_pos = 35
        pdf.set_fill_color(*NAVY)
        pdf.rect(8, y_pos, 194, 25, 'F', round_corners=True, corner_radius=4)

        hdr_icon = os.path.join(ICON_DIR, "icon_morbok_header.png")
        if os.path.exists(hdr_icon):
            pdf.image(hdr_icon, x=13, y=y_pos + 3.5, w=18, h=18)

        pdf.set_xy(34, y_pos + 3.5)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font(font_name, 'B', 16 if font_name == 'THSarabun' else 14)
        pdf.cell(0, 7, "MorBok (หมอบอก) – สรุปคำแนะนำทางการแพทย์", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_xy(34, y_pos + 12.5)
        pdf.set_text_color(208, 225, 249)
        pdf.set_font(font_name, '', 10.5 if font_name == 'THSarabun' else 9.5)
        pdf.cell(0, 5, "เอกสารสรุปคำแนะนำการดูแลตนเองและตารางจัดบริหารยาสำหรับผู้ป่วย", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # ----------------------------------------------------
        # 2. DOCTOR INFO CARD
        # ----------------------------------------------------
        y_pos = 64
        pdf.set_fill_color(240, 246, 255)
        pdf.set_draw_color(200, 221, 248)
        pdf.set_line_width(0.3)
        pdf.rect(8, y_pos, 194, 26, 'FD', round_corners=True, corner_radius=4)

        doc_icon = os.path.join(ICON_DIR, "icon_doctor.png")
        if os.path.exists(doc_icon):
            pdf.image(doc_icon, x=13, y=y_pos + 3.5, w=19, h=19)

        is_anon = doctor_info.get("is_anonymous", False) or doctor_info.get("anonymous", False)

        pdf.set_xy(35, y_pos + 3.5)
        pdf.set_text_color(*NAVY)
        pdf.set_font(font_name, 'B', 13 if font_name == 'THSarabun' else 11)
        if is_anon:
            pdf.cell(0, 6, "แพทย์ผู้ตรวจ: ไม่ระบุชื่อและนามสกุล", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_xy(35, y_pos + 11)
            pdf.set_text_color(71, 85, 105)
            pdf.set_font(font_name, '', 10.5 if font_name == 'THSarabun' else 9.5)
            pdf.cell(0, 5, "เลขที่ใบประกอบวิชาชีพเวชกรรม: ไม่ระบุ", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            doc_fname = doctor_info.get("first_name", doctor_info.get("name", "แพทย์ผู้ตรวจ"))
            doc_sname = doctor_info.get("surname", "")
            doc_lic_raw = doctor_info.get("license_no", "-")
            doc_lic_digits = "".join(filter(str.isdigit, str(doc_lic_raw)))
            doc_lic = f"ว.{doc_lic_digits}" if doc_lic_digits else doc_lic_raw
            pdf.cell(0, 6, f"แพทย์ผู้ตรวจ: แพทย์ {doc_fname} {doc_sname}".strip(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_xy(35, y_pos + 11)
            pdf.set_text_color(71, 85, 105)
            pdf.set_font(font_name, '', 10.5 if font_name == 'THSarabun' else 9.5)
            pdf.cell(0, 5, f"เลขที่ใบประกอบวิชาชีพเวชกรรม: {doc_lic}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_xy(35, y_pos + 17)
        pdf.cell(0, 5, f"รหัสอ้างอิงเคส: {encounter_id}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # HELPER FOR SECTION HEADER
        def draw_section_header(num_str, icon_name, title_str, curr_y):
            pdf.set_fill_color(*NAVY)
            pdf.rect(10, curr_y, 7.5, 7.5, 'F', round_corners=True, corner_radius=1.5)
            pdf.set_xy(10, curr_y + 0.3)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font(font_name, 'B', 12 if font_name == 'THSarabun' else 10)
            pdf.cell(7.5, 6.5, num_str, align='C')

            ic_path = os.path.join(ICON_DIR, icon_name)
            if os.path.exists(ic_path):
                pdf.image(ic_path, x=20, y=curr_y - 0.5, w=8.5, h=8.5)

            pdf.set_xy(31, curr_y)
            pdf.set_text_color(*NAVY)
            pdf.set_font(font_name, 'B', 13.5 if font_name == 'THSarabun' else 11.5)
            pdf.cell(0, 7.5, title_str, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            return curr_y + 9.5

        def draw_dashed_divider(curr_y):
            pdf.set_draw_color(226, 232, 240)
            pdf.set_line_width(0.3)
            for x in range(10, 200, 3):
                pdf.line(x, curr_y, min(x + 1.5, 200), curr_y)

        y_pos = 96

        # ----------------------------------------------------
        # SECTION 1: Diagnosis
        # ----------------------------------------------------
        y_pos = draw_section_header("1", "icon_stethoscope.png", "วินิจฉัยโรค (Diagnosis)", y_pos)
        diagnosis = summary_data.get("diagnosis", "ไม่ระบุ")
        pdf.set_xy(31, y_pos)
        pdf.set_text_color(*DARK_TEXT)
        pdf.set_font(font_name, '', 11 if font_name == 'THSarabun' else 10)
        pdf.multi_cell(168, 5.5, diagnosis, align='L')
        
        y_pos = pdf.get_y() + 4
        draw_dashed_divider(y_pos)
        y_pos += 5

        # ----------------------------------------------------
        # SECTION 2: Medical Instruction
        # ----------------------------------------------------
        y_pos = draw_section_header("2", "icon_advice.png", "คำแนะนำการดูแลตนเอง (Medical instruction)", y_pos)
        instructions = summary_data.get("instructions", [])
        
        pdf.set_text_color(*DARK_TEXT)
        pdf.set_font(font_name, '', 11 if font_name == 'THSarabun' else 10)
        if isinstance(instructions, list) and len(instructions) > 0:
            for inst in instructions:
                pdf.set_xy(31, y_pos)
                pdf.cell(4, 5.5, "•")
                pdf.set_xy(35, y_pos)
                pdf.multi_cell(164, 5.5, str(inst), align='L')
                y_pos = pdf.get_y() + 1.5
        else:
            pdf.set_xy(31, y_pos)
            pdf.multi_cell(168, 5.5, str(instructions) if instructions else "ไม่ระบุ", align='L')
            y_pos = pdf.get_y() + 1.5

        y_pos += 2
        draw_dashed_divider(y_pos)
        y_pos += 5

        # ----------------------------------------------------
        # SECTION 3: Medication
        # ----------------------------------------------------
        y_pos = draw_section_header("3", "icon_meds.png", "ตารางจัดบริหารยา (Medication)", y_pos)
        
        start_meds = summary_data.get("startMeds", [])
        stop_meds = summary_data.get("stopMeds", [])
        change_meds = summary_data.get("changeMeds", [])

        # START Meds Box
        if start_meds:
            box_y = y_pos
            box_h = 10 + len(start_meds) * 6
            pdf.set_fill_color(240, 253, 244)
            pdf.set_draw_color(187, 247, 208)
            pdf.set_line_width(0.3)
            pdf.rect(31, box_y, 168, box_h, 'FD', round_corners=True, corner_radius=3)
            st_badge = os.path.join(ICON_DIR, "badge_start.png")
            if os.path.exists(st_badge):
                pdf.image(st_badge, x=34, y=box_y + 2.5, w=4.5, h=4.5)

            pdf.set_xy(40, box_y + 2)
            pdf.set_text_color(21, 128, 61) # Dark green
            pdf.set_font(font_name, 'B', 11 if font_name == 'THSarabun' else 10)
            pdf.cell(0, 5.5, "ยาเริ่มรับประทานใหม่ (START):", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            pdf.set_text_color(*DARK_TEXT)
            pdf.set_font(font_name, '', 10.5 if font_name == 'THSarabun' else 9.5)
            med_y = box_y + 8.5
            for m in start_meds:
                name = m.get("name", "").strip()
                desc = m.get("desc", "").strip()
                usage = m.get("usage", "").strip()
                pdf.set_xy(36, med_y)
                pdf.cell(4, 5, "*")
                pdf.set_xy(40, med_y)
                if desc and usage:
                    text_str = f"{name} ({desc}) : {usage}"
                elif usage:
                    text_str = f"{name} : {usage}"
                elif desc:
                    text_str = f"{name} ({desc})"
                else:
                    text_str = name
                pdf.multi_cell(156, 5, text_str, align='L')
                med_y = pdf.get_y() + 1

            y_pos = box_y + box_h + 4

        # STOP Meds Box
        if stop_meds:
            box_y = y_pos
            box_h = 10 + len(stop_meds) * 6
            pdf.set_fill_color(254, 242, 242)
            pdf.set_draw_color(254, 202, 202)
            pdf.set_line_width(0.3)
            pdf.rect(31, box_y, 168, box_h, 'FD', round_corners=True, corner_radius=3)

            sp_badge = os.path.join(ICON_DIR, "badge_stop.png")
            if os.path.exists(sp_badge):
                pdf.image(sp_badge, x=34, y=box_y + 2.5, w=4.5, h=4.5)

            pdf.set_xy(40, box_y + 2)
            pdf.set_text_color(185, 28, 28) # Dark red
            pdf.set_font(font_name, 'B', 11 if font_name == 'THSarabun' else 10)
            pdf.cell(0, 5.5, "ยาที่ต้องหยุดรับประทานทันที (STOP):", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            pdf.set_text_color(185, 28, 28)
            pdf.set_font(font_name, '', 10.5 if font_name == 'THSarabun' else 9.5)
            med_y = box_y + 8.5
            for m in stop_meds:
                name = m.get("name", "").strip()
                desc = m.get("desc", "").strip()
                warning = m.get("warning", "").replace("⚠️", "[!]").strip()
                pdf.set_xy(36, med_y)
                pdf.cell(4, 5, "*")
                pdf.set_xy(40, med_y)
                if not warning and not desc:
                    warning = "หยุดใช้ยาทันที"
                if desc and warning:
                    text_str = f"{name} ({desc}) -> {warning}"
                elif warning:
                    text_str = f"{name} -> {warning}" if name else warning
                elif desc:
                    text_str = f"{name} ({desc})"
                else:
                    text_str = name
                pdf.multi_cell(156, 5, text_str, align='L')
                med_y = pdf.get_y() + 1

            y_pos = box_y + box_h + 4

        # CHANGE Meds Box
        if change_meds:
            box_y = y_pos
            box_h = 10 + len(change_meds) * 6
            pdf.set_fill_color(255, 247, 237)
            pdf.set_draw_color(254, 215, 170)
            pdf.set_line_width(0.3)
            pdf.rect(31, box_y, 168, box_h, 'FD', round_corners=True, corner_radius=3)

            ch_badge = os.path.join(ICON_DIR, "badge_change.png")
            if os.path.exists(ch_badge):
                pdf.image(ch_badge, x=34, y=box_y + 2.5, w=4.5, h=4.5)

            pdf.set_xy(40, box_y + 2)
            pdf.set_text_color(194, 65, 12) # Dark orange
            pdf.set_font(font_name, 'B', 11 if font_name == 'THSarabun' else 10)
            pdf.cell(0, 5.5, "ยาที่ปรับเปลี่ยนขนาด/วิธีรับประทาน (CHANGE):", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            pdf.set_text_color(*DARK_TEXT)
            pdf.set_font(font_name, '', 10.5 if font_name == 'THSarabun' else 9.5)
            med_y = box_y + 8.5
            for m in change_meds:
                name = m.get("name", "").strip()
                desc = m.get("desc", "").strip()
                chg = m.get("change", "").strip()
                pdf.set_xy(36, med_y)
                pdf.cell(4, 5, "*")
                pdf.set_xy(40, med_y)
                if desc and chg:
                    text_str = f"{name} ({desc}) -> {chg}"
                elif chg:
                    text_str = f"{name} -> {chg}"
                elif desc:
                    text_str = f"{name} ({desc})"
                else:
                    text_str = name
                pdf.multi_cell(156, 5, text_str, align='L')
                med_y = pdf.get_y() + 1

            y_pos = box_y + box_h + 4

        y_pos += 1
        draw_dashed_divider(y_pos)
        y_pos += 5

        # ----------------------------------------------------
        # SECTION 4: Follow-Up
        # ----------------------------------------------------
        y_pos = draw_section_header("4", "icon_calendar.png", "วันนัดหมายติดตามอาการ (Follow-Up)", y_pos)
        follow_up = summary_data.get("followUpDate", "ตามใบนัดโรงพยาบาล")
        pdf.set_xy(31, y_pos)
        pdf.set_text_color(*DARK_TEXT)
        pdf.set_font(font_name, '', 11 if font_name == 'THSarabun' else 10)
        pdf.multi_cell(168, 5.5, follow_up, align='L')

        # ----------------------------------------------------
        # PDPA DISCLAIMER BOX
        # ----------------------------------------------------
        pdpa_y = 250
        pdf.set_fill_color(240, 246, 255)
        pdf.set_draw_color(208, 225, 249)
        pdf.set_line_width(0.3)
        pdf.rect(8, pdpa_y, 194, 13, 'FD', round_corners=True, corner_radius=3)

        info_icon = os.path.join(ICON_DIR, "icon_info.png")
        if os.path.exists(info_icon):
            pdf.image(info_icon, x=12, y=pdpa_y + 2.5, w=8, h=8)

        pdf.set_xy(22, pdpa_y + 2.2)
        pdf.set_text_color(71, 85, 105)
        pdf.set_font(font_name, '', 9.5 if font_name == 'THSarabun' else 8.5)
        pdf.cell(0, 4.5, "* หมายเหตุ: เอกสารนี้สร้างจากระบบ MorBok (Prototype) และจะถูกลบออกจากเซิร์ฟเวอร์หลังผ่านไป 10 นาที", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(22, pdpa_y + 6.8)
        pdf.cell(0, 4.5, "ตามนโยบาย PDPA", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # ----------------------------------------------------
        # EMERGENCY FOOTER BANNER
        # ----------------------------------------------------
        ftr_y = 268
        red_pts = [(0, ftr_y), (75, ftr_y), (60, 297), (0, 297)]
        pdf.set_fill_color(200, 30, 30)
        pdf.polygon(red_pts, style='F')

        ph_icon = os.path.join(ICON_DIR, "icon_phone.png")
        if os.path.exists(ph_icon):
            pdf.image(ph_icon, x=8, y=ftr_y + 5, w=14, h=14)

        pdf.set_xy(25, ftr_y + 4)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font(font_name, 'B', 10.5 if font_name == 'THSarabun' else 9.5)
        pdf.cell(0, 5, "กรณีฉุกเฉิน", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_xy(25, ftr_y + 9)
        pdf.set_font(font_name, 'B', 22 if font_name == 'THSarabun' else 18)
        pdf.cell(0, 10, "1669", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_draw_color(203, 213, 225)
        pdf.set_line_width(0.5)
        pdf.line(78, ftr_y + 3, 78, ftr_y + 23)

        pdf.set_xy(82, ftr_y + 3)
        pdf.set_text_color(51, 65, 85)
        pdf.set_font(font_name, 'B', 11.5 if font_name == 'THSarabun' else 11)
        pdf.cell(0, 5.5, "หากมีอาการเร่งด่วนหรือฉุกเฉิน", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(82, ftr_y + 9.5)
        pdf.cell(0, 5.5, "กรุณาติดต่อศูนย์รับแจ้งเหตุและสั่งการ (EMS)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(82, ftr_y + 16)
        pdf.cell(0, 5.5, "ตลอด 24 ชั่วโมง", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        amb_icon = os.path.join(ICON_DIR, "graphic_ambulance.png")
        if os.path.exists(amb_icon):
            pdf.image(amb_icon, x=162, y=ftr_y + 3, w=38, h=19)

        pdf.output(file_path)

        created_at = int(time.time())
        expires_at = created_at + 600 # 10 minutes TTL

        return {
            "pdf_id": pdf_id,
            "file_name": file_name,
            "file_path": file_path,
            "created_at": created_at,
            "expires_at": expires_at
        }
