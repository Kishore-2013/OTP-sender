import requests
import json

url = "https://localhost:8443/send-otp"
data = {
    "email": "test@gmail.com",
    "type": "work_email_verification"
}

try:
    response = requests.post(url, json=data, verify=False)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
