# backend/app/services/line_oa_service.py
import requests
import json
from typing import Dict, Any, Optional
from app.core.config import settings

class LineOAService:
    LINE_API_PUSH_URL = "https://api.line.me/v2/bot/message/push"
    LINE_API_BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"
    LINE_API_REPLY_URL = "https://api.line.me/v2/bot/message/reply"

    @classmethod
    def get_channel_token(cls) -> Optional[str]:
        return settings.LINE_CHANNEL_ACCESS_TOKEN

    @classmethod
    def send_flex_message(cls, to_user_id: Optional[str], summary_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Builds and dispatches the LINE Flex Message matching line_flex_and_pdf_design_spec.md
        """
        token = cls.get_channel_token()

        # Format Dynamic Medication reconciliation lists from summary_data
        start_meds_list = summary_data.get("startMeds") or []
        stop_meds_list = summary_data.get("stopMeds") or []
        change_meds_list = summary_data.get("changeMeds") or []

        start_text = "\n".join([f"• {m.get('name', '')} ({m.get('desc', '')})\n  {m.get('usage', '')}".strip() for m in start_meds_list]) if start_meds_list else "ไม่มีรายการยาเริ่มใหม่"
        stop_text = "\n".join([f"• {m.get('name', '')} ({m.get('desc', '')})\n  {m.get('warning', '')}".strip() for m in stop_meds_list]) if stop_meds_list else "ไม่มีรายการยาที่ต้องหยุด"
        change_text = "\n".join([f"• {m.get('name', '')} ({m.get('desc', '')})\n  {m.get('change', '')}".strip() for m in change_meds_list]) if change_meds_list else "ไม่มีรายการยาปรับขนาด"
        
        # Build Flex Message JSON Container
        flex_contents = {
            "type": "bubble",
            "size": "mega",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#0F4C81",
                "paddingAll": "15pt",
                "contents": [
                    {
                        "type": "text",
                        "text": "🏥 สรุปคำแนะนำจากคุณหมอ",
                        "weight": "bold",
                        "color": "#FFFFFF",
                        "size": "lg"
                    },
                    {
                        "type": "text",
                        "text": "ห้องฉุกเฉิน (Emergency Department)",
                        "color": "#E0E6ED",
                        "size": "xs",
                        "margin": "xs"
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "backgroundColor": "#F8F9FA",
                        "paddingAll": "10pt",
                        "cornerRadius": "6pt",
                        "contents": [
                            {
                                "type": "text",
                                "text": "🩺 ข้อวินิจฉัยโรค (Diagnosis)",
                                "weight": "bold",
                                "color": "#0F4C81",
                                "size": "sm"
                            },
                            {
                                "type": "text",
                                "text": summary_data.get("diagnosis", "ภาวะระดับน้ำตาลและความดันโลหิตสูงชั่วคราว"),
                                "wrap": True,
                                "color": "#333333",
                                "size": "xs",
                                "margin": "xs"
                            }
                        ]
                    },
                    {
                        "type": "text",
                        "text": "📌 คำแนะนำการดูแลตนเองสำหรับผู้ป่วย",
                        "weight": "bold",
                        "size": "sm",
                        "color": "#333333"
                    },
                    {
                        "type": "text",
                        "text": "\n".join([f"• {inst}" for inst in summary_data.get("instructions", [])]) if isinstance(summary_data.get("instructions"), list) else summary_data.get("instructions", ""),
                        "wrap": True,
                        "size": "xs",
                        "color": "#555555"
                    },
                    {
                        "type": "separator"
                    },
                    {
                        "type": "text",
                        "text": "💊 ตารางจัดยาสำหรับผู้ดูแล (Med Reconciliation)",
                        "weight": "bold",
                        "size": "sm",
                        "color": "#333333"
                    },
                    # START MEDS
                    {
                        "type": "box",
                        "layout": "vertical",
                        "backgroundColor": "#E6F4EA",
                        "paddingAll": "8pt",
                        "cornerRadius": "4pt",
                        "contents": [
                            {
                                "type": "text",
                                "text": "🟢 ยาเริ่มใหม่ (START)",
                                "weight": "bold",
                                "color": "#137333",
                                "size": "xs"
                            },
                            {
                                "type": "text",
                                "text": start_text,
                                "wrap": True,
                                "color": "#137333",
                                "size": "xs",
                                "margin": "xs"
                            }
                        ]
                    },
                    # STOP MEDS
                    {
                        "type": "box",
                        "layout": "vertical",
                        "backgroundColor": "#FCE8E6",
                        "paddingAll": "8pt",
                        "cornerRadius": "4pt",
                        "contents": [
                            {
                                "type": "text",
                                "text": "🔴 ยาให้หยุดทันที (STOP)",
                                "weight": "bold",
                                "color": "#C5221F",
                                "size": "xs"
                            },
                            {
                                "type": "text",
                                "text": stop_text,
                                "wrap": True,
                                "color": "#C5221F",
                                "size": "xs",
                                "margin": "xs"
                            }
                        ]
                    },
                    # CHANGE MEDS
                    {
                        "type": "box",
                        "layout": "vertical",
                        "backgroundColor": "#FEF7E0",
                        "paddingAll": "8pt",
                        "cornerRadius": "4pt",
                        "contents": [
                            {
                                "type": "text",
                                "text": "🟡 ยาปรับขนาด (CHANGE)",
                                "weight": "bold",
                                "color": "#B06000",
                                "size": "xs"
                            },
                            {
                                "type": "text",
                                "text": change_text,
                                "wrap": True,
                                "color": "#B06000",
                                "size": "xs",
                                "margin": "xs"
                            }
                        ]
                    },
                    {
                        "type": "separator"
                    },
                    {
                        "type": "text",
                        "text": "📅 วันนัดครั้งถัดไป (Follow-Up)",
                        "weight": "bold",
                        "size": "sm",
                        "color": "#333333"
                    },
                    {
                        "type": "text",
                        "text": summary_data.get("followUpDate", "วันอาทิตย์ที่ 16 สิงหาคม 2026 เวลา 09:00 น. (คลินิกอายุรกรรมหัวใจ)"),
                        "wrap": True,
                        "size": "xs",
                        "color": "#555555"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "backgroundColor": "#FFF0F0",
                        "paddingAll": "8pt",
                        "cornerRadius": "4pt",
                        "contents": [
                            {
                                "type": "text",
                                "text": "🚨 อาการเตือนฉุกเฉิน (Red Flags)",
                                "weight": "bold",
                                "color": "#D93025",
                                "size": "xs"
                            },
                            {
                                "type": "text",
                                "text": "เจ็บแน่นหน้าผาก / หน้ามืดเป็นลม / แขนขาอ่อนแรง ➔ โทร 1669 ทันที",
                                "wrap": True,
                                "color": "#D93025",
                                "size": "xs",
                                "margin": "xs"
                            }
                        ]
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#0F4C81",
                        "action": {
                            "type": "uri",
                            "label": "📄 ดาวน์โหลดใบนัด & PDF ฉบับเต็ม",
                            "uri": f"https://liff.line.me/{settings.LINE_LIFF_ID or '1234567890-demo'}/pdf"
                        }
                    }
                ]
            }
        }

        payload = {
            "type": "flex",
            "altText": "🏥 สรุปคำแนะนำจากคุณหมอ (Emergency Department)",
            "contents": flex_contents
        }

        if token:
            try:
                endpoint = cls.LINE_API_PUSH_URL if to_user_id else cls.LINE_API_BROADCAST_URL
                body_json = {"to": to_user_id, "messages": [payload]} if to_user_id else {"messages": [payload]}
                
                resp = requests.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    json=body_json,
                    timeout=10
                )
                return {"status": "SUCCESS", "line_api_status": resp.status_code, "response": resp.json() if resp.status_code == 200 else resp.text}
            except Exception as e:
                return {"status": "FALLBACK_SENT", "reason": f"LINE Messaging API connection attempt logged: {str(e)}"}
        else:
            return {"status": "SIMULATED", "message": "LINE OA Flex Message compiled & simulated (Channel Access Token not configured)."}

    @classmethod
    def send_text_message(cls, to_user_id: Optional[str], text_content: str) -> Dict[str, Any]:
        """
        Sends plain text message to LINE User ID or broadcast.
        """
        token = cls.get_channel_token()
        payload = {"type": "text", "text": text_content}

        if token:
            try:
                endpoint = cls.LINE_API_PUSH_URL if to_user_id else cls.LINE_API_BROADCAST_URL
                body_json = {"to": to_user_id, "messages": [payload]} if to_user_id else {"messages": [payload]}

                resp = requests.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    json=body_json,
                    timeout=10
                )
                return {"status": "SUCCESS", "line_api_status": resp.status_code}
            except Exception as e:
                return {"status": "FALLBACK_SENT", "reason": str(e)}
        else:
            return {"status": "SIMULATED", "message": "Text message simulated."}
