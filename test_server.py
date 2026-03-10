from fastapi.testclient import TestClient
from main import app, otp_storage
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
        assert response.json()["message"] == "OTP sent successfully"
        mock_get_provider.assert_called_once_with(email)
        mock_provider.send_otp.assert_called_once()
    
    # Check storage
    assert email in otp_storage
    correct_code = otp_storage[email]["code"]
    print(f"Generated OTP: {correct_code}")

    # 3. Test /verify-otp (Invalid Code)
    print("Testing /verify-otp with wrong code...")
    response = client.post("/verify-otp", json={"email": email, "otp_code": "000000"})
    assert response.status_code == 401
    assert "Invalid OTP code" in response.json()["detail"]
    assert otp_storage[email]["attempts"] == 1

    # 4. Test /verify-otp (Success)
    print("Testing /verify-otp with correct code...")
    response = client.post("/verify-otp", json={"email": email, "otp_code": correct_code})
    assert response.status_code == 200
    assert response.json()["verified"] is True
    assert email not in otp_storage  # Should be cleared on success
    print("Test cycle complete: SUCCESS")

def test_otp_expiry():
    email = "expiry@example.com"
    with patch("main.get_email_provider"):
        client.post("/send-otp", json={"email": email})
        
    # Manually expire it in storage
    otp_storage[email]["expiry"] = time.time() - 10
    
    print("Testing /verify-otp with expired code...")
    response = client.post("/verify-otp", json={"email": email, "otp_code": "123456"})
    assert response.status_code == 410
    assert "expired" in response.json()["detail"].lower()
    print("Expiry test: SUCCESS")

def test_too_many_attempts():
    email = "attempts@example.com"
    with patch("main.get_email_provider"):
        client.post("/send-otp", json={"email": email})
        
    print("Testing attempt limiting...")
    # 3 fails
    for i in range(3):
        client.post("/verify-otp", json={"email": email, "otp_code": "wrong"})
    
    # 4th hit should be 403
    response = client.post("/verify-otp", json={"email": email, "otp_code": "wrong"})
    assert response.status_code == 403
    assert "Too many attempts" in response.json()["detail"]
    print("Attempt limiting test: SUCCESS")

if __name__ == "__main__":
    print("--- Starting OTP Service Logic Tests ---")
    test_otp_lifecycle()
    test_otp_expiry()
    test_too_many_attempts()
    print("--- All Tests Passed! ---")
