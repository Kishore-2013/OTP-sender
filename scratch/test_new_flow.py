import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_signup_flow():
    email = "signup@example.com"
    with patch("main.get_email_provider") as mock_get_provider:
        mock_provider = MagicMock()
        mock_get_provider.return_value = mock_provider
        
        # Test /send-otp with default type
        response = client.post("/send-otp", json={"email": email})
        assert response.status_code == 200
        
        # Check if send_otp was called with "signup_verification"
        _, args, _ = mock_provider.send_otp.mock_calls[0]
        # recipient_email, otp_code, email_type
        assert args[2] == "signup_verification"
    print("Signup flow test (default): SUCCESS")

def test_work_verification_flow():
    email = "work@company.com"
    with patch("main.get_email_provider") as mock_get_provider:
        mock_provider = MagicMock()
        mock_get_provider.return_value = mock_provider
        
        # Test /send-otp with explicit type
        response = client.post("/send-otp", json={"email": email, "type": "work_email_verification"})
        assert response.status_code == 200
        
        # Check if send_otp was called with "work_email_verification"
        _, args, _ = mock_provider.send_otp.mock_calls[0]
        assert args[2] == "work_email_verification"
    print("Work verification flow test: SUCCESS")

if __name__ == "__main__":
    test_signup_flow()
    test_work_verification_flow()
    print("All template tests passed!")
