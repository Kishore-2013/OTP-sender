from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import random
import time
import json
import os
import hmac
import hashlib
import base64
from email_service import get_email_provider
from dotenv import load_dotenv

load_dotenv()


# ── Secret key for signing tokens (set OTP_SECRET_KEY in Vercel env vars) ─────
OTP_SECRET = os.getenv("OTP_SECRET_KEY", "linkspec-otp-default-secret")
OTP_TTL    = 300  # 5 minutes

app = FastAPI(title="LinkSpec OTP Service")

# ── Stateless signed token helpers ─────────────────────────────────────────────

def _sign(payload: dict) -> str:
    """Encode payload + HMAC-SHA256 signature → no server storage needed."""
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode()
    sig = hmac.new(OTP_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"

def _decode(token: str) -> dict:
    """Verify signature and return payload. Raises ValueError if invalid."""
    try:
        payload_b64, sig = token.rsplit(".", 1)
    except ValueError:
        raise ValueError("Malformed token")
    expected = hmac.new(OTP_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise ValueError("Token signature mismatch")
    return json.loads(base64.urlsafe_b64decode(payload_b64.encode()))

# ── 422 debug handler ──────────────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = await request.body()
    try:
        body_str = body.decode()
    except Exception:
        body_str = str(body)
    print(f"[422] errors={exc.errors()} body={body_str[:200]}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body_preview": body_str[:200]},
    )

# ── CORS ───────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Models ─────────────────────────────────────────────────────────────────────

class OTPRequest(BaseModel):
    email: EmailStr

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp_code: str
    token: str          # signed token returned by /send-otp

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "LinkSpec OTP Service",
        "endpoints": ["/send-otp", "/verify-otp"],
    }

def generate_otp() -> str:
    return str(random.randint(100000, 999999))

@app.post("/send-otp")
async def send_otp(request: OTPRequest, background_tasks: BackgroundTasks):
    email     = request.email.lower().strip()
    otp_code  = generate_otp()

    # Embed the OTP inside a signed token — nothing stored on the server
    token = _sign({
        "email": email,
        "otp":   otp_code,
        "exp":   int(time.time()) + OTP_TTL,
    })

    print(f"[send-otp] OTP signed for {email}")

    try:
        provider = get_email_provider(email)
        background_tasks.add_task(provider.send_otp, email, otp_code)
        # Return token to Flutter — Flutter holds it and sends back on verify
        return {"message": "OTP sent successfully", "token": token}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@app.post("/verify-otp")
async def verify_otp(request: OTPVerifyRequest):
    email     = request.email.lower().strip()
    user_code = request.otp_code.strip()

    print(f"[verify-otp] Attempt for {email}")

    # 1. Decode + verify token signature
    try:
        payload = _decode(request.token)
    except ValueError as e:
        print(f"[verify-otp] Token error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token. Please request a new OTP.")

    # 2. Email must match what's in the token
    if payload.get("email") != email:
        raise HTTPException(status_code=401, detail="Token does not match this email.")

    # 3. Expiry check
    if int(time.time()) > payload.get("exp", 0):
        print(f"[verify-otp] Token expired for {email}")
        raise HTTPException(status_code=410, detail="OTP has expired. Please request a new one.")

    # 4. Code check
    if payload.get("otp") == user_code:
        print(f"[verify-otp] SUCCESS for {email}")
        return {"message": "Verification successful", "verified": True, "email": email}
    else:
        print(f"[verify-otp] Wrong code for {email}")
        raise HTTPException(status_code=401, detail="Invalid OTP code. Please check your email.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
