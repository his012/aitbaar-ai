from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import shutil
import os
import pathlib
import uvicorn

# Import the pipeline from main.py
from main import run_pipeline

app = FastAPI(title="Aitbaar AI API")

# Add CORS middleware for Flutter app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TextAnalyzeRequest(BaseModel):
    message_text: str = ""
    url: str = ""
    phone: str = ""
    sender_name: str = ""
    email: str = ""

@app.get("/health")
def health_check():
    return {"status": "running"}

@app.post("/analyze/text")
def analyze_text(request: TextAnalyzeRequest):
    try:
        # Pass the request as a dictionary to run_pipeline
        # Note: main.py has been updated to handle dict inputs
        raw_input = request.model_dump()
        result = run_pipeline(raw_input, input_type="JSON/Text")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/file")
def analyze_file(file: UploadFile = File(...)):
    try:
        # Create temp dir if not exists
        os.makedirs("temp_uploads", exist_ok=True)
        
        # Save file temporarily
        file_path = os.path.join("temp_uploads", file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Detect input type
        ext = pathlib.Path(file.filename).suffix.lower()
        if ext == ".pdf":
            input_type = "PDF"
        elif ext in [".png", ".jpg", ".jpeg"]:
            input_type = "Image"
        elif ext == ".csv":
            input_type = "CSV"
        else:
            input_type = "Unknown File"
            
        # Call pipeline
        result = run_pipeline(file_path, input_type=input_type)
        
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return result
    except Exception as e:
        # Cleanup on error
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
