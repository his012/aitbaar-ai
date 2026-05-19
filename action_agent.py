import os
import json
# pyrefly: ignore [missing-import]
import google.generativeai as genai
from dotenv import load_dotenv

# 5. Loads dotenv at top
load_dotenv()

# 4. Gets API key from os.environ["GEMINI_API_KEY"]
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    print("Warning: GEMINI_API_KEY not found in environment variables.")

# 1. Reads skills/action_skill.md file at the start
def load_skill_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading skill file {filepath}: {e}")
        return ""

SKILL_FILE_PATH = os.path.join(os.path.dirname(__file__), "skills", "action_skill.md")
ACTION_SKILL_PROMPT = load_skill_file(SKILL_FILE_PATH)

# 2. Has function action_agent(trust_score, verdict, scam_type, key_reasons)
def action_agent(trust_score, verdict, scam_type, key_reasons):
    try:
        if not ACTION_SKILL_PROMPT:
            raise ValueError("Action skill prompt could not be loaded.")

        # 3. Uses gemini-2.5-flash model
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=ACTION_SKILL_PROMPT
        )

        # 7. Sends input data to Gemini
        input_data = {
            "trust_score": trust_score,
            "verdict": verdict,
            "scam_type": scam_type,
            "key_reasons": key_reasons
        }

        prompt = f"Please provide the protective action plan based on the following verdict details according to your skill instructions.\n\nInput Details:\n{json.dumps(input_data, indent=2)}"

        response = model.generate_content(prompt)
        response_text = response.text

        # 8. Cleans response and returns parsed JSON dict
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
            "actions": [], 
            "severity_level": "unknown", 
            "total_actions": 0, 
            "error": str(e)
        }

# At bottom if __name__ == "__main__": test
if __name__ == "__main__":
    test_trust_score = 18
    test_verdict = "CONFIRMED SCAM"
    test_scam_type = "JOB_SCAM"
    test_key_reasons = ["registration fee", "fake company", "urgency"]
    
    print("Testing Action Agent...")
    print(f"Trust Score: {test_trust_score}")
    print(f"Verdict: {test_verdict}")
    print(f"Scam Type: {test_scam_type}")
    print(f"Key Reasons: {test_key_reasons}\n")
    
    result = action_agent(
        trust_score=test_trust_score, 
        verdict=test_verdict, 
        scam_type=test_scam_type, 
        key_reasons=test_key_reasons
    )
    print("Result:")
    print(json.dumps(result, indent=2))
