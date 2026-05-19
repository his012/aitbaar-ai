import os
import json
# pyrefly: ignore [missing-import]
from google import genai
from dotenv import load_dotenv

# Loads dotenv at top
load_dotenv()

# Gets API key from os.environ["GEMINI_API_KEY"]
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Warning: GEMINI_API_KEY not found in environment variables.")

# Reads skills/behavioral_skill.md file at the start
def load_skill_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading skill file {filepath}: {e}")
        return ""

SKILL_FILE_PATH = os.path.join(os.path.dirname(__file__), "skills", "behavioral_skill.md")
# Builds system prompt by reading the skill file content
BEHAVIORAL_SKILL_PROMPT = load_skill_file(SKILL_FILE_PATH)

# Has function behavioral_agent(message_text)
def behavioral_agent(message_text):
    try:
        if not BEHAVIORAL_SKILL_PROMPT:
            raise ValueError("Behavioral skill prompt could not be loaded.")

        # Initialize the new genai Client
        client = genai.Client(api_key=api_key)

        # Build full prompt
        full_prompt = f"System Instructions:\n{BEHAVIORAL_SKILL_PROMPT}\n\nPlease analyze the following message according to your skill instructions and return the JSON analysis.\n\nMessage:\n{message_text}"

        # Call API using gemini-2.5-flash
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt
        )
        
        # Get text
        response_text = response.text

        # Cleans response (remove ```json and ``` if present)
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
            
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]

        cleaned_text = cleaned_text.strip()

        # Returns parsed JSON dict
        result = json.loads(cleaned_text)
        return result

    except Exception as e:
        # On any error return the specified dictionary
        return {
            "manipulation_score": 0, 
            "tactics_detected": [], 
            "evidence": [], 
            "dominant_tactic": "none", 
            "explanation": "Error", 
            "error": str(e)
        }

# At bottom if __name__ == "__main__": test with this message and print result
if __name__ == "__main__":
    test_message = "Congratulations! Aap ko remote job mil gai hai salary 80,000 per month. Sirf 2000 registration fee send karo JazzCash 0300-1234567 par. Apply karo agly 24 ghanton mein warna offer cancel ho jaye ga."
    
    print("Testing Behavioral Agent with message:")
    print(f'"{test_message}"\n')
    
    result = behavioral_agent(test_message)
    print("Result:")
    print(json.dumps(result, indent=2))
