# LinkSpec OTP Service (Python)

A secure FastAPI-based OTP verification service supporting multiple email providers.

## Features
- **Dual Provider Support**: Use Gmail (SMTP) or Microsoft 365 (Azure Communication Services).
- **Security**: 5-minute OTP expiry and 3-attempt limit per OTP.
- **Async Execution**: Emails are sent in the background to keep API responses fast.

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configuration**:
   Copy `.env.example` to `.env` and fill in your credentials.
   ```bash
   cp .env.example .env
   ```

3. **Run the Server (HTTP)**:
   ```bash
   uvicorn main:app --reload
   ```

4. **Run the Server (Experimental HTTPS)**:
   First, generate self-signed certificates:
   ```bash
   python generate_certs.py
   ```
   Then start the server with SSL:
   ```bash
   uvicorn main:app --reload --ssl-keyfile key.pem --ssl-certfile cert.pem
   ```

## API Endpoints

### 1. Send OTP
**POST** `/send-otp`
```json
{
  "email": "ch.kishoryadav.03@gmail.com"
}
```

### 2. Verify OTP
**POST** `/verify-otp`
```json
{
  "email": "user@example.com",
  "otp_code": "123456"
}
```

## Testing the Endpoints

### Option A: Using PowerShell (Recommended for Windows)
```powershell
# Send OTP
Invoke-RestMethod -Uri http://127.0.0.1:8000/send-otp -Method Post -ContentType "application/json" -Body '{"email":"your-email@example.com"}'

# Verify OTP
Invoke-RestMethod -Uri http://127.0.0.1:8000/verify-otp -Method Post -ContentType "application/json" -Body '{"email":"your-email@example.com", "otp_code":"123456"}'
```

### Option B: Using curl.exe (Windows 10+)
If you use `curl.exe` directly, wrap the JSON in double quotes:
```powershell
curl.exe -X POST http://127.0.0.1:8000/send-otp -H "Content-Type: application/json" -d '{\"email\":\"test@example.com\"}'
```

## Running Logic Tests (Stand-alone Validation)
If you want to verify the OTP logic without sending real emails:
```powershell
python test_server.py
```

## Running with Gmail
Set `EMAIL_PROVIDER=gmail` and provide `GMAIL_USER` and `GMAIL_APP_PASSWORD`.

## Running with MS 365
Set `EMAIL_PROVIDER=azure` and provide `AZURE_CONNECTION_STRING` and `SENDER_ADDRESS` (support@applywizz.com).
