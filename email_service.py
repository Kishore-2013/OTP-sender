import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from abc import ABC, abstractmethod
from azure.communication.email import EmailClient
from dotenv import load_dotenv

load_dotenv()

class EmailProvider(ABC):
    @abstractmethod
    def send_otp(self, recipient_email: str, otp_code: str):
        pass

class GmailProvider(EmailProvider):
    def __init__(self):
        self.user = os.getenv("GMAIL_USER", "")
        self.password = os.getenv("GMAIL_APP_PASSWORD", "")
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    def send_otp(self, recipient_email: str, otp_code: str):
        try:
            print(f"--- [DEBUG] Attempting to send Gmail OTP to {recipient_email} ---")
            msg = MIMEMultipart()
            msg['From'] = self.user
            msg['To'] = recipient_email
            msg['Subject'] = "Your LinkSpec Verification Code"

            body = f"Your verification code is: {otp_code}. It will expire in 5 minutes."
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.set_debuglevel(1)  # Show SMTP traffic
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)
            print("--- [DEBUG] Gmail OTP sent successfully! ---")
        except Exception as e:
            print(f"--- [ERROR] Gmail SMTP failed: {str(e)} ---")
            raise e

class AzureMS365Provider(EmailProvider):
    def __init__(self):
        self.tenant_id = os.getenv("MS365_TENANT_ID", "")
        self.client_id = os.getenv("MS365_CLIENT_ID", "")
        self.client_secret = os.getenv("MS365_CLIENT_SECRET", "")
        self.sender_email = os.getenv("SENDER_EMAIL", "")
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.scope = ["https://graph.microsoft.com/.default"]

    def _get_access_token(self):
        import msal
        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret,
        )
        result = app.acquire_token_for_client(scopes=self.scope)
        if "access_token" in result:
            return result["access_token"]
        else:
            raise Exception(f"Failed to acquire token: {result.get('error_description')}")

    def send_otp(self, recipient_email: str, otp_code: str):
        import httpx
        access_token = self._get_access_token()
        
        url = f"https://graph.microsoft.com/v1.0/users/{self.sender_email}/sendMail"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        email_body = {
            "message": {
                "subject": "Your LinkSpec Verification Code",
                "body": {
                    "contentType": "Text",
                    "content": f"Your verification code is: {otp_code}. It will expire in 5 minutes."
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": recipient_email
                        }
                    }
                ]
            }
        }
        
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=email_body)
            if response.status_code != 202:
                raise Exception(f"Failed to send email via Graph API: {response.text}")
            return response.json() if response.content else None

def get_email_provider(recipient_email: str):
    email_lower = recipient_email.lower().strip()
    if email_lower.endswith("@gmail.com"):
        print(f"Routing to GmailProvider for {recipient_email}")
        return GmailProvider()
    else:
        print(f"Routing to AzureMS365Provider for {recipient_email}")
        return AzureMS365Provider()
