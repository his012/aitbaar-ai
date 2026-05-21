import os
import json
import time
import csv
import base64
import pathlib
import PyPDF2
import re
# pyrefly: ignore [missing-import]
from PIL import Image
from dotenv import load_dotenv
from google import genai

def extract_contact_info(text):
    info = {"phone": "", "url": "", "email": "", "sender_name": ""}
    if not text:
        return info
        
    # 1. Phone (03XX-XXXXXXX or 03XXXXXXXXX)
    phone_match = re.search(r'03\d{2}[-\s]?\d{7}', text)
    if phone_match:
        info["phone"] = phone_match.group(0).replace('-', '').replace(' ', '')
        
    # 2. URL/Domain (e.g., www.xxx.com, techpk.xyz, https://...)
    url_match = re.search(r'\b(?:https?://|www\.)[^\s]+|\b[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}\b', text)
    if url_match:
        info["url"] = url_match.group(0)
        
    # 3. Email (xxx@xxx.com)
    email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
    if email_match:
        info["email"] = email_match.group(0)
        
    # 4. Sender Name (From: John Doe or Sender: Tech HR)
    sender_match = re.search(r'(?:From|Sender):\s*([^\n\r]+)', text, re.IGNORECASE)
    if sender_match:
        info["sender_name"] = sender_match.group(1).strip()
        
    return info

# Import the 6 agents
from behavioral_agent import behavioral_agent
from identity_agent import identity_agent
from scam_pattern_agent import scam_pattern_agent
from reputation_agent import reputation_agent
from risk_scoring_agent import risk_scoring_agent
from action_agent import action_agent

# Load dotenv at top
load_dotenv()

def process_input(raw_input):
    # Initialize fields with empty strings
    inputs = {
        "message_text": "",
        "url": "",
        "phone": "",
        "sender_name": "",
        "email": ""
    }
    
    # 4. URL (starts with http:// or https://)
    if isinstance(raw_input, str) and (raw_input.startswith("http://") or raw_input.startswith("https://")):
        inputs["url"] = raw_input
        inputs["message_text"] = "URL provided for analysis"
        
    # Check if raw_input is a path to a file
    elif isinstance(raw_input, str) and os.path.isfile(raw_input):
        ext = pathlib.Path(raw_input).suffix.lower()
        
        # 1. PDF file (.pdf extension)
        if ext == ".pdf":
            try:
                extracted_text = ""
                with open(raw_input, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        extracted_text += page.extract_text() + "\n"
                inputs["message_text"] = extracted_text.strip()
            except Exception as e:
                inputs["message_text"] = f"Error reading PDF: {str(e)}"
            
        # 2. Image file (.png .jpg .jpeg)
        elif ext in [".png", ".jpg", ".jpeg"]:
            try:
                # Read image as base64
                with open(raw_input, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                
                # Send to Gemini with prompt
                prompt = "Extract all text visible in this image. Return only the text, nothing else."
                
                # Setup client
                api_key = os.environ.get("GEMINI_API_KEY")
                client = genai.Client(api_key=api_key) if api_key else genai.Client()
                
                # We can use the base64 format natively via a dictionary or use PIL
                mime_type = "image/png" if ext == ".png" else "image/jpeg"
                contents = [
                    prompt, 
                    # Using base64 data as a Part dictionary
                    {"mime_type": mime_type, "data": base64_image}
                ]
                
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents
                )
                inputs["message_text"] = response.text.strip()
            except Exception as e:
                inputs["message_text"] = f"Error reading image: {str(e)}"
            
        # 3. CSV file (.csv extension)
        elif ext == ".csv":
            try:
                extracted_text = ""
                with open(raw_input, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        extracted_text += " ".join(row) + "\n"
                inputs["message_text"] = extracted_text.strip()
            except Exception as e:
                inputs["message_text"] = f"Error reading CSV: {str(e)}"
    else:
        # 5. Plain text (anything else)
        inputs["message_text"] = str(raw_input)

    # Extract contact info and merge
    extracted = extract_contact_info(inputs["message_text"])
    for key in ["phone", "url", "email", "sender_name"]:
        if extracted.get(key) and not inputs.get(key):
            inputs[key] = extracted[key]

    return inputs

def show_before_after(input_type, raw_input, final_result):
    print("\n" + "="*50)
    print("                BEFORE vs AFTER")
    print("="*50)
    
    # Preview input string up to 50 chars
    preview = str(raw_input)
    if len(preview) > 50:
        preview = preview[:47] + "..."
        
    print(f"BEFORE: Input received: {input_type} - {preview}")
    
    trust_score = final_result.get("risk_scoring", {}).get("final_trust_score", final_result.get("risk_scoring", {}).get("trust_score", 50))
    verdict = final_result.get("risk_scoring", {}).get("verdict_english", final_result.get("risk_scoring", {}).get("verdict", "UNKNOWN"))
    
    print(f"AFTER: Result: Trust Score {trust_score}, Verdict: {verdict}")
    print("="*50 + "\n")

def baseline_comparison(message_text):
    keywords = [
        "registration fee", "OTP", "prize", "lottery", "fee send karo", 
        "JazzCash", "EasyPaisa", "account band", "NADRA", "FBR", 
        "click here", "verify now", "2000", "5000"
    ]
    
    text_lower = str(message_text).lower()
    count = 0
    found = []
    
    for kw in keywords:
        if kw.lower() in text_lower:
            count += 1
            found.append(kw)
            
    if count <= 1:
        verdict = "SAFE"
    elif count <= 3:
        verdict = "SUSPICIOUS"
    else:
        verdict = "SCAM"
        
    return {
        "keyword_count": count,
        "keywords_found": found,
        "baseline_verdict": verdict
    }

def execute_actions(actions):
    print("\n--- EXECUTING ACTIONS ---")
    results = []
    
    actions_list = actions if isinstance(actions, list) else actions.get("actions_to_take", [])

    for action in actions_list:
        action_name = action.get("action_name", "unknown_action")
        simulate_failure = action.get("simulate_failure", False)
        
        print(f"\nExecuting: {action_name}...")
        
        if simulate_failure:
            print("ERROR: Action failed! Retrying...")
            time.sleep(1)
            fallback_msg = f"Simulated fallback successful for {action_name}."
            print(f"Fallback activated: {fallback_msg}")
            results.append({
                "action_name": action_name,
                "status": "FAILED_FALLBACK",
                "message": fallback_msg
            })
        else:
            success_msg = f"{action_name} completed successfully."
            print(f"SUCCESS: {success_msg}")
            results.append({
                "action_name": action_name,
                "status": "SUCCESS",
                "message": success_msg
            })
            
    return results

def run_pipeline(raw_input, input_type="Plain Text", **kwargs):
    print("\n==============================================")
    print("   AITBAAR AI - Scam Detection Starting...")
    print("==============================================\n")
    
    # 1. Process Input
    inputs = process_input(raw_input)
    
    message_text = inputs.get("message_text", "")
    url = kwargs.get("url", inputs.get("url", ""))
    phone = kwargs.get("phone", inputs.get("phone", ""))
    sender_name = kwargs.get("sender_name", inputs.get("sender_name", ""))
    email = kwargs.get("email", inputs.get("email", ""))

    # 2. Call baseline comparison
    print(">>> 0. Running Baseline Comparison (No AI)...")
    baseline_res = baseline_comparison(message_text)
    print(json.dumps(baseline_res, indent=2))

    # 3. Run all 6 agents
    print("\n>>> 1. Running Behavioral Agent...")
    behavioral_res = behavioral_agent(message_text)
    print(json.dumps(behavioral_res, indent=2))
    time.sleep(15)
    
    print("\n>>> 2. Running Identity Agent...")
    identity_res = identity_agent(url, phone, sender_name, email)
    print(json.dumps(identity_res, indent=2))
    time.sleep(15)
    
    print("\n>>> 3. Running Scam Pattern Agent...")
    pattern_res = scam_pattern_agent(message_text)
    print(json.dumps(pattern_res, indent=2))
    time.sleep(15)
    
    print("\n>>> 4. Running Reputation Agent...")
    reputation_res = reputation_agent(phone, url)
    print(json.dumps(reputation_res, indent=2))
    time.sleep(15)
    
    print("\n>>> 5. Running Risk Scoring Agent (Synthesizing Results)...")
    scoring_res = risk_scoring_agent(
        identity_result=identity_res,
        pattern_result=pattern_res,
        behavioral_result=behavioral_res,
        reputation_result=reputation_res
    )
    print(json.dumps(scoring_res, indent=2))
    time.sleep(15)
    
    print("\n>>> 6. Running Action Agent (Planning Protective Measures)...")
    trust_score = scoring_res.get("final_trust_score", scoring_res.get("trust_score", 50))
    verdict = scoring_res.get("verdict_english", scoring_res.get("verdict", "SUSPICIOUS"))
    
    scam_type = pattern_res.get("scam_type", "UNKNOWN")
    if scam_type == "UNKNOWN" and pattern_res.get("detected_categories"):
        scam_type = pattern_res.get("detected_categories")[0].get("category_name", "UNKNOWN")
        
    key_reasons = []
    if "key_reasons" in scoring_res:
        key_reasons = scoring_res["key_reasons"]
    else:
        if pattern_res.get("suspicious_amounts"): key_reasons.extend(pattern_res["suspicious_amounts"])
        if behavioral_res.get("dominant_tactic"): key_reasons.append(f"Manipulation: {behavioral_res['dominant_tactic']}")
        if identity_res.get("is_impersonating_brand"): key_reasons.append(f"Impersonating {identity_res.get('brand_being_impersonated')}")
    
    action_res = action_agent(trust_score, verdict, scam_type, key_reasons)
    print(json.dumps(action_res, indent=2))
    time.sleep(15)
    
    execution_results = execute_actions(action_res)
    
    print("\n==============================================")
    print("             FINAL SUMMARY                    ")
    print("==============================================")
    print(f"VERDICT: {verdict}")
    print(f"TRUST SCORE: {trust_score}/100")
    print(f"SCAM PROBABILITY: {100 - trust_score}%")
    print("==============================================\n")
    
    final_result = {
        "inputs": inputs,
        "baseline_comparison": baseline_res,
        "behavioral_analysis": behavioral_res,
        "identity_analysis": identity_res,
        "scam_pattern_analysis": pattern_res,
        "reputation_analysis": reputation_res,
        "risk_scoring": scoring_res,
        "action_plan": action_res,
        "execution_results": execution_results
    }
    
    # Show Before/After Comparison
    show_before_after(input_type, raw_input, final_result)
    
    return final_result

if __name__ == "__main__":
    print("\nRunning Tests for all 5 Input Types:")
    
    # 1. Plain text
    test_text = "Congratulations! Aap ko remote job mil gai hai salary 80,000 per month. Sirf 2000 registration fee send karo JazzCash 0300-1234567 par. Apply karo agly 24 ghanton mein warna offer cancel ho jaye ga."
    run_pipeline(
        test_text, 
        "Plain Text",
        url="techpk-jobs.xyz",
        phone="03001234567",
        sender_name="TechPk HR",
        email="hr@gmail.com"
    )
    
    # 2. URL
    # run_pipeline("https://hbl-secure-login.xyz", "URL")
    
    # 3. PDF
    # if os.path.exists("test.pdf"):
    #     run_pipeline("test.pdf", "PDF")
    # else:
    #     print("\nSkipping PDF test: test.pdf not found.")
        
    # 4. Image
    # if os.path.exists("test.png"):
    #     run_pipeline("test.png", "Image")
    # else:
    #     print("\nSkipping Image test: test.png not found.")
        
    # 5. CSV
    # test_csv = "test.csv"
    # with open(test_csv, "w", encoding="utf-8") as f:
    #     f.write("id,message\n1,Win lottery today click here\n2,Account block verify NADRA")
    # 
    # run_pipeline(test_csv, "CSV")
    # 
    # if os.path.exists(test_csv):
    #     os.remove(test_csv)
