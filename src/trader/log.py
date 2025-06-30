from loguru import logger
import os
import sys
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Path to the current script
script_path = os.path.abspath(__file__)
script_dir = os.path.dirname(script_path)
script_name = os.path.splitext(os.path.basename(script_path))[0]

# Create log file path: same directory, same name, .log extension
log_path = os.path.join(script_dir, f"{script_name}.log")

# Configure loguru
logger.remove()
logger.add(
    log_path,
    rotation="1 MB",
    retention="7 days",
    compression="zip",
    format="{time:YYYY-MM-DDTHH:mm:ssZ!UTC} | {level} | {message}",
)

# Get email configuration from environment
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO", EMAIL_USER)

# Log basic environment info (not password)
logger.debug(f"EMAIL_USER = {EMAIL_USER}")
logger.debug(f"EMAIL_TO = {EMAIL_TO}")
if not EMAIL_USER or not EMAIL_PASS:
    logger.warning("Email credentials are missing or incomplete.")

# Send email using SMTP (e.g., Gmail)
def send_email(subject, body):
    if not EMAIL_USER or not EMAIL_PASS:
        logger.warning("Email credentials not set. Skipping email send.")
        return

    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
    except Exception as e:
        logger.exception("Failed to send email")

# Add logger.email method
def email(self, message, *, subject="Loguru Email"):
    self.error(message)
    send_email(subject, message)

logger.__class__.email = email

# Handle uncaught exceptions
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.opt(exception=(exc_type, exc_value, exc_traceback)).error("Uncaught exception")

sys.excepthook = handle_exception
