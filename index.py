from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests, json, fitz, base64

app = FastAPI(title="VerifiX AI - AWS Local")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- USER LOGIN (DEMO) ----------------
USERS = {
    "admin@example.com": "123456"
}

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/login")
def login(data: LoginRequest):
    if data.email in USERS and USERS[data.email] == data.password:
        return {"success": True}
    return {"success": False, "error": "Invalid credentials"}

# ---------------- AI HELPERS ----------------
def ask_mistral(prompt):
    res = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "mistral", "prompt": prompt, "stream": False}
    )
    return res.json()["response"]

# ---------------- TEXT ----------------
class TextRequest(BaseModel):
    content: str

@app.post("/verify/text")
def verify_text(data: TextRequest):
    prompt = f"""
Check this claim:

"{data.content}"

Reply ONLY in JSON:
{{
  "verdict": "True | False | Misleading | Unverified",
  "confidence": 0-100,
  "explanation": "clear explanation"
}}
"""
    ai_text = ask_mistral(prompt)
    try:
        return json.loads(ai_text)
    except:
        return {"verdict":"Unverified","confidence":50,"explanation":ai_text}

# ---------------- LINK ----------------
class LinkRequest(BaseModel):
    url: str

@app.post("/verify/link")
def verify_link(data: LinkRequest):
    prompt = f"""
Check the credibility of this link:

{data.url}

Reply ONLY in JSON.
"""
    ai_text = ask_mistral(prompt)
    try:
        return json.loads(ai_text)
    except:
        return {"verdict":"Unverified","confidence":50,"explanation":ai_text}

# ---------------- PDF ----------------
@app.post("/verify/pdf")
async def verify_pdf(file: UploadFile = File(...)):
    pdf_bytes = await file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = "".join(p.get_text() for p in doc)

    prompt = f"Analyze this document:\n{text[:4000]}"
    ai_text = ask_mistral(prompt)

    try:
        return json.loads(ai_text)
    except:
        return {"verdict":"Unverified","confidence":50,"explanation":ai_text}

# ---------------- IMAGE ----------------
@app.post("/verify/image")
async def verify_image(file: UploadFile = File(...)):
    img_bytes = await file.read()
    img_base64 = base64.b64encode(img_bytes).decode()

    res = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llava",
            "prompt": "Analyze this image for misinformation or manipulation",
            "images": [img_base64],
            "stream": False
        }
    )

    return {
        "verdict": "Analysis Complete",
        "confidence": 70,
        "explanation": res.json()["response"]
    }
