import os
import json
import re
import ast
# pyrefly: ignore [missing-import]
from google import genai
from dotenv import load_dotenv

# 5. Loads dotenv at top
load_dotenv()

# 4. Gets API key from os.environ["GEMINI_API_KEY_PATTERN"]
if "GEMINI_API_KEY_PATTERN" in os.environ:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY_PATTERN"])
else:
    print("Warning: GEMINI_API_KEY_PATTERN not found in environment variables.")
    client = None

# 1. Reads skills/scam_pattern_skill.md file at the start
def load_skill_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading skill file {filepath}: {e}")
        return ""

SKILL_FILE_PATH = os.path.join(os.path.dirname(__file__), "skills", "scam_pattern_skill.md")
# 6. Builds system prompt by reading the skill file content
PATTERN_SKILL_PROMPT = load_skill_file(SKILL_FILE_PATH)

def clean_json(text):
    text = text.strip()
    text = text.replace("```json", "").replace("```", "")
    text = text.strip()
    # Find first { and last } to extract only JSON part
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        text = text[start:end+1]
    return text

# 2. Has function scam_pattern_agent(message_text)
def scam_pattern_agent(message_text):
    try:
        if not PATTERN_SKILL_PROMPT:
            raise ValueError("Scam pattern skill prompt could not be loaded.")
        if not client:
            raise ValueError("Gemini client not initialized. Check GEMINI_API_KEY.")

        # 7. Sends message_text to Gemini
        full_prompt = f"{PATTERN_SKILL_PROMPT}\n\nPlease analyze the following message according to your skill instructions and return the JSON analysis.\n\nMessage:\n{message_text}"

        response = client.models.generate_content(model="gemini-2.5-flash", contents=full_prompt)
        response_text = response.text

        # 8. Cleans response
        cleaned_text = clean_json(response_text)

        # 1. Remove special unicode characters
        cleaned_text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', cleaned_text)

        # 2. Fix trailing commas before } or ]
        cleaned_text = re.sub(r',\s*([}\]])', r'\1', cleaned_text)

        # 3. Fix any apostrophes or smart quotes
        cleaned_text = cleaned_text.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")

        # 4. Make the JSON parsing more robust
        try:
            # 9. Returns parsed JSON dict
            result = json.loads(cleaned_text)
        except json.JSONDecodeError:
            try:
                # Fallback to ast.literal_eval to handle Python-like dict strings
                eval_text = cleaned_text.replace('true', 'True').replace('false', 'False').replace('null', 'None')
                result = ast.literal_eval(eval_text)
            except (ValueError, SyntaxError) as e:
                raise ValueError(f"Could not parse JSON even with robust fallback. Error: {e}")
                
        return result

    except Exception as e:
        # On any error return the specified dictionary
        return {
            "pattern_score": 0, 
            "scam_type": "UNKNOWN", 
            "confidence": "low", 
            "matched_patterns": [], 
            "suspicious_phrases": [], 
            "requests_money": False, 
            "requests_nic": False, 
            "requests_otp": False, 
            "explanation": "Error", 
            "error": str(e)
        }

# At bottom if __name__ == "__main__": test
if __name__ == "__main__":
    test_message = "Congratulations! Aap ko remote job mil gai hai salary 80,000 per month. Sirf 2000 registration fee send karo JazzCash 0300-1234567 par. Apply karo agly 24 ghanton mein warna offer cancel ho jaye ga."
    
    print("Testing Scam Pattern Agent with message:")
    print(f'"{test_message}"\n')
    
    result = scam_pattern_agent(test_message)
    print("Result:")
    print(json.dumps(result, indent=2))
