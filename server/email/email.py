"""SMTP client port of the former Go email package."""
from dataclasses import dataclass
import os
import smtplib
from email.message import EmailMessage

@dataclass(frozen=True)
class Config:
    host: str
    port: int
    username: str = ""
    password: str = ""
    sender: str = ""

class Client:
    def __init__(self, config: Config) -> None: self.config = config
    def send_simple(self, to: str, subject: str, body: str) -> None:
        message = EmailMessage(); message["From"] = self.config.sender; message["To"] = to; message["Subject"] = subject; message.set_content(body)
        with smtplib.SMTP(self.config.host, self.config.port) as smtp:
            if self.config.username: smtp.login(self.config.username, self.config.password)
            smtp.send_message(message)

def new_client_from_env() -> Client:
    return Client(Config(os.getenv("SMTP_HOST", ""), int(os.getenv("SMTP_PORT", "25")), os.getenv("SMTP_USERNAME", ""), os.getenv("SMTP_PASSWORD", ""), os.getenv("SMTP_FROM", "")))
