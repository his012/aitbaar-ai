import os
import json
from google import genai
from dotenv import load_dotenv

# 5. Loads dotenv at top
load_dotenv()

# 4. Gets API key from os.environ["GEMINI_API_KEY"]
if "GEMINI_API_KEY" in os.environ:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
else:
    print("Warning: GEMINI_API_KEY not found in environment variables.")

# 1. Reads skills/identity_skill.md file at the start
def load_skill_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading skill file {filepath}: {e}")
        return ""

SKILL_FILE_PATH = os.path.join(os.path.dirname(__file__), "skills", "identity_skill.md")
# 6. Builds system prompt by reading the skill file content
IDENTITY_SKILL_PROMPT = load_skill_file(SKILL_FILE_PATH)

# 2. Has function identity_agent(url, phone, sender_name, email)
def identity_agent(url, phone, sender_name, email):
    try:
        if not IDENTITY_SKILL_PROMPT:
            raise ValueError("Identity skill prompt could not be loaded.")
        if not client:
            raise ValueError("Gemini client not initialized. Check GEMINI_API_KEY.")

        # 7. Sends combined input to Gemini
        full_prompt = f"{IDENTITY_SKILL_PROMPT}\n\nPlease analyze the following identity information according to your skill instructions and return the JSON analysis.\n\nURL: {url}\nPhone: {phone}\nSender: {sender_name}\nEmail: {email}"

        response = client.models.generate_content(model="gemini-2.5-flash", contents=full_prompt)
        response_text = response.text

        # 8. Cleans response (remove ```json and ``` if present)
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
            
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]

        cleaned_text = cleaned_text.strip()

        # 9. Returns parsed JSON dict
        result = json.loads(cleaned_text)
        return result

    except Exception as e:
        # On any error return the specified dictionary
        return {
            "identity_risk_score": 0, 
            "red_flags": [], 
            "is_impersonating_brand": False, 
            "brand_being_impersonated": None, 
            "explanation": "Error", 
            "error": str(e)
        }

# At bottom if __name__ == "__main__": test
if __name__ == "__main__":
    test_url = "hbl-secure-login.xyz"
    test_phone = "03001234567"
    test_sender_name = "HBL Bank Officer"
    test_email = "hbl.officer@gmail.com"
    
    print("Testing Identity Agent with:")
    print(f"URL: {test_url}")
    print(f"Phone: {test_phone}")
    print(f"Sender: {test_sender_name}")
    print(f"Email: {test_email}\n")
    
    result = identity_agent(url=test_url, phone=test_phone, sender_name=test_sender_name, email=test_email)
    print("Result:")
    print(json.dumps(result, indent=2))
