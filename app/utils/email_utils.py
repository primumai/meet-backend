import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def send_password_reset_email(recipient_email: str, reset_token: str, username: str):
    """
    Send a password reset email to the user.
    
    Args:
        recipient_email (str): The email address of the recipient
        reset_token (str): The reset token to include in the email
        username (str): The username of the recipient
    """
    try:
        # Create message container
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Password Reset Request"
        msg['From'] = settings.EMAIL_FROM
        msg['To'] = recipient_email

        # Create the body of the message (a plain-text and an HTML version)
        reset_url = f"{settings.FRONTEND_RESET_PASSWORD_URL}?token={reset_token}"
        text = f"""
        Hi {username},
        
        You requested to reset your password. Please click on the following link to reset your password:
        {reset_url}
        
        This link will expire in 15 minutes.
        
        If you did not request a password reset, please ignore this email.
        """
        
        html = f"""
        <html>
        <body>
            <p>Hi {username},</p>
            <p>You requested to reset your password. Please click on the button below to reset your password:</p>
            <p><a href="{reset_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-align: center; text-decoration: none; display: inline-block; border-radius: 5px;">
                Reset Password
            </a></p>
            <p>Or copy and paste this link into your browser:<br>
            <code>{reset_url}</code></p>
            <p>This link will expire in 15 minutes.</p>
            <p>If you did not request a password reset, please ignore this email.</p>
            <p>Best regards,<br>Your App Team</p>
        </body>
        </html>
        """
        
        # Record the MIME types of both parts - text/plain and text/html.
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')
        
        # Attach parts into message container.
        msg.attach(part1)
        msg.attach(part2)
        
        # ✅ Proper indentation here
        with smtplib.SMTP("smtpout.secureserver.net", settings.EMAIL_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
            server.send_message(msg)

        logger.info(f"Password reset email sent to {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {recipient_email}: {str(e)}")
        return False
