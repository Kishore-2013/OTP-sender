from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
import random
import time
from typing import Dict
from email_service import get_email_provider

app = FastAPI(title="LinkSpec OTP Service")

# OTP Storage Structure: { email: { "code": str, "expiry": float, "attempts": int } }
otp_storage: Dict[str, dict] = {}

class OTPRequest(BaseModel):
    email: EmailStr

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp_code: str

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "LinkSpec OTP Service",
        "endpoints": ["/send-otp", "/verify-otp"]
    }

def generate_otp() -> str:
    return str(random.randint(100000, 999999))

@app.post("/send-otp")
async def send_otp(request: OTPRequest, background_tasks: BackgroundTasks):
    email = request.email.lower()
    otp_code = generate_otp()
    expiry = time.time() + 300  # 5 minutes

    # Store OTP details
    otp_storage[email] = {
        "code": otp_code,
        "expiry": expiry,
        "attempts": 0
    }

    # Use provider to send email in background
    try:
        print(f"--- [DIAGNOSTIC] SENDING OTP TO: {email} ---")
        provider = get_email_provider(email)
        print(f"--- [DIAGNOSTIC] SELECTED PROVIDER: {type(provider).__name__} ---")
        background_tasks.add_task(provider.send_otp, email, otp_code)
        return {"message": "OTP sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@app.post("/verify-otp")
async def verify_otp(request: OTPVerifyRequest):
    email = request.email.lower()
    user_code = request.otp_code

    if email not in otp_storage:
        raise HTTPException(status_code=404, detail="No OTP found for this email")

    otp_data = otp_storage[email]

    # Security: Limit attempts
    if otp_data["attempts"] >= 3:
        del otp_storage[email]
        raise HTTPException(status_code=403, detail="Too many attempts. Please request a new OTP.")

    # Expiry Check
    if time.time() > otp_data["expiry"]:
        del otp_storage[email]
        raise HTTPException(status_code=410, detail="OTP has expired")

    # Code Validation
    if otp_data["code"] == user_code:
        # Success! Clear OTP
        del otp_storage[email]
        return {"message": "Verification successful", "verified": True}
    else:
        otp_data["attempts"] += 1
        remaining = 3 - otp_data["attempts"]
        raise HTTPException(
            status_code=401, 
            detail=f"Invalid OTP code. {remaining} attempts remaining."
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
