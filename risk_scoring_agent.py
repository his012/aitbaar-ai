import os
import json
# pyrefly: ignore [missing-import]
from google import genai
from dotenv import load_dotenv

# 6. Loads dotenv at top
load_dotenv()

# 5. Gets API key from os.environ["GEMINI_API_KEY"]
if "GEMINI_API_KEY" in os.environ:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
else:
    print("Warning: GEMINI_API_KEY not found in environment variables.")
    client = None

# 1. Reads skills/risk_scoring_skill.md file at the start
def load_skill_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading skill file {filepath}: {e}")
        return ""

SKILL_FILE_PATH = os.path.join(os.path.dirname(__file__), "skills", "risk_scoring_skill.md")
RISK_SCORING_SKILL_PROMPT = load_skill_file(SKILL_FILE_PATH)

# 2. Has function risk_scoring_agent(identity_result, pattern_result, behavioral_result, reputation_result)
def risk_scoring_agent(identity_result, pattern_result, behavioral_result, reputation_result):
    try:
        if not RISK_SCORING_SKILL_PROMPT:
            raise ValueError("Risk scoring skill prompt could not be loaded.")
        if not client:
            raise ValueError("Gemini client not initialized. Check GEMINI_API_KEY.")

        # 8. Sends all 4 results combined as JSON to Gemini
        combined_inputs = {
            "identity_agent_result": identity_result,
            "pattern_agent_result": pattern_result,
            "behavioral_agent_result": behavioral_result,
            "reputation_agent_result": reputation_result
        }

        prompt = f"Please analyze the following agent results according to your skill instructions and calculate the final risk score and verdict. Return the JSON analysis.\n\nAgent Results:\n{json.dumps(combined_inputs, indent=2)}"
        full_prompt = f"{RISK_SCORING_SKILL_PROMPT}\n\n{prompt}"

        response = client.models.generate_content(model="gemini-2.5-flash", contents=full_prompt)
        response_text = response.text

        # 9. Cleans response and returns parsed JSON dict
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
            
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]

        cleaned_text = cleaned_text.strip()

        result = json.loads(cleaned_text)
        return result

    except Exception as e:
        # On any error return
        return {
            "trust_score": 50, 
            "verdict": "SUSPICIOUS", 
            "verdict_urdu": "Mashkook", 
            "scam_probability": 50, 
            "confidence": "low", 
            "contradiction_found": False, 
            "contradiction_explanation": None, 
            "key_reasons": [], 
            "override_applied": False, 
            "override_reason": None, 
            "error": str(e)
        }

# At bottom if __name__ == "__main__": create fake results for all 4 agents and test
if __name__ == "__main__":
    # Fake results for testing
    fake_identity = {
        "identity_risk_score": 80,
        "red_flags": ["Using generic gmail for bank", "Misspelled domain"],
        "is_impersonating_brand": True,
        "brand_being_impersonated": "HBL",
        "explanation": "High risk of impersonation detected."
    }
    
    fake_pattern = {
        "pattern_score": 90,
        "scam_type": "JOB_SCAM",
        "confidence": "high",
        "matched_patterns": ["Job Scam", "Advance Fee"],
        "suspicious_phrases": ["80,000 salary", "registration fee 2000"],
        "requests_money": True,
        "requests_nic": False,
        "requests_otp": False,
        "explanation": "Classic job scam pattern with advance fee."
    }
    
    fake_behavioral = {
        "manipulation_score": 85,
        "tactics_detected": ["URGENCY", "REWARD", "MONEY REQUEST"],
        "evidence": ["apply in 24 hours", "80,000 salary", "fee send karo"],
        "dominant_tactic": "URGENCY",
        "explanation": "High manipulation using urgency and reward to extract fee."
    }
    
    fake_reputation = {
        "reputation_score": 60,
        "times_reported": 3,
        "last_reported": "2023-10-20T10:00:00Z",
        "known_scammer": True,
        "explanation": "Phone number has been reported multiple times recently."
    }
    
    print("Testing Risk Scoring Agent...")
    result = risk_scoring_agent(
        identity_result=fake_identity, 
        pattern_result=fake_pattern, 
        behavioral_result=fake_behavioral, 
        reputation_result=fake_reputation
    )
    print("\nResult:")
    print(json.dumps(result, indent=2))
