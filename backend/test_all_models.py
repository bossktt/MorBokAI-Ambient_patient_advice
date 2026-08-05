import sys
import os
import json

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.services.llm_adapter import (
    TyphoonMedicalAdapter,
    GeminiZDRAdapter,
    AzureOpenAIZDRAdapter,
    LocalOnPremZDRAdapter,
)

def evaluate_models():
    transcript = "คนไข้มีอาการปวดหัวตึบๆ มีไข้สูง 39 องศาเซลเซียส ไอมีเสมหะสีเขียว มา 3 วัน กินยาพาราเซตามอลแล้วไข้ไม่ลด แพทย์แนะนำให้พักผ่อน ดื่มน้ำมากๆ และจ่ายยาฆ่าเชื้อ amoxicillin 500mg กินเช้าเย็นหลังอาหาร"
    
    print("=========================================")
    print("        EVALUATING ALL LLM MODELS        ")
    print("=========================================")
    print(f"Transcript: {transcript}\n")
    
    models_to_test = [
        ("Typhoon Medical", TyphoonMedicalAdapter()),
        ("Gemini 2.5 Flash Lite ZDR", GeminiZDRAdapter()),
        # AzureOpenAIZDRAdapter might fail if credentials are not fully set, let's test anyway
        ("Azure OpenAI ZDR", AzureOpenAIZDRAdapter()),
        ("Local On-Prem ZDR", LocalOnPremZDRAdapter())
    ]
    
    for name, adapter in models_to_test:
        print(f"--- Testing {name} ---")
        try:
            result = adapter.generate_clinical_summary(transcript)
            print("Status: SUCCESS ✅")
            print("Keys found:", list(result.keys()))
            if "advice" in result:
                print("Advice (preview):", str(result["advice"])[:150] + "...")
            else:
                print("⚠️ No 'advice' key found in the response!")
        except Exception as e:
            print(f"Status: FAILED ❌")
            print(f"Error: {e}")
        print("\n")

if __name__ == "__main__":
    evaluate_models()
