from fastapi.testclient import TestClient
from main import app
import time
from unittest.mock import patch, MagicMock

# Use with context manager or ensure compatibility
client = TestClient(app)

def test_otp_lifecycle():
    email = "test@example.com"
    
    # 1. Mock the email provider to skip actual sending
    with patch("main.get_email_provider") as mock_get_provider:
        mock_provider = MagicMock()
        mock_get_provider.return_value = mock_provider
        
        # 2. Test /send-otp
        print(f"Testing /send-otp for {email}...")
        response = client.post("/send-otp", json={"email": email})
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "OTP sent successfully"
        assert "token" in data
        token = data["token"]
        
        mock_get_provider.assert_called_once()
        # Find the OTP code that was sent from the mock call
        # args, kwargs = mock_provider.send_otp.call_args
        # recipient, otp_code = args
        _, args, _ = mock_provider.send_otp.mock_calls[0]
        recipient, otp_code = args
        print(f"Intercepted OTP: {otp_code}")

    # 3. Test /verify-otp (Invalid Code)
    print("Testing /verify-otp with wrong code...")
    response = client.post("/verify-otp", json={
        "email": email, 
        "otp_code": "000000",
        "token": token
    })
    assert response.status_code == 401
    assert "Invalid OTP code" in response.json()["detail"]

    # 4. Test /verify-otp (Success)
    print("Testing /verify-otp with correct code...")
    response = client.post("/verify-otp", json={
        "email": email, 
        "otp_code": otp_code,
        "token": token
    })
    assert response.status_code == 200
    assert response.json()["verified"] is True
    print("Test cycle complete: SUCCESS")

def test_otp_expiry():
    email = "expiry@example.com"
    with patch("main.get_email_provider"):
        response = client.post("/send-otp", json={"email": email})
        token = response.json()["token"]
        
    # We can't easily "manually expire" in the signed token without 
    # re-signing it with a past expiry.
    # Since we use a secret key, we'd need to mock time.time()
    
    print("Testing /verify-otp with mocked expiry...")
    with patch("time.time", return_value=time.time() + 600): # Mock future time
        response = client.post("/verify-otp", json={
            "email": email, 
            "otp_code": "123456",
            "token": token
        })
        assert response.status_code == 410
        assert "expired" in response.json()["detail"].lower()
    print("Expiry test: SUCCESS")

if __name__ == "__main__":
    print("--- Starting OTP Service Logic Tests (Stateless) ---")
    try:
        test_otp_lifecycle()
        test_otp_expiry()
        print("--- All Tests Passed! ---")
    except Exception as e:
        print(f"--- Test Failed: {e} ---")
        import traceback
        traceback.print_exc()
