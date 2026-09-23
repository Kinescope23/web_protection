import os
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)


async def send_verification_code(email: str, code: str, username: str):
    """Отправляет код подтверждения на email"""
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"[EMAIL] SMTP не настроен. Код для {email}: {code}")
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = "Код подтверждения Net Protector"
    message["From"] = SMTP_FROM
    message["To"] = email

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #2c3e50;">Код подтверждения Net Protector</h2>
        <p>Здравствуйте, <strong>{username}</strong>!</p>
        <p>Ваш код для входа:</p>
        <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
            <span style="font-size: 32px; font-weight: bold; color: #0369a1; letter-spacing: 8px;">{code}</span>
        </div>
        <p style="color: #666; font-size: 14px;">
            Код действителен в течение 5 минут.<br>
            Если вы не запрашивали код, просто проигнорируйте это письмо.
        </p>
    </body>
    </html>
    """

    message.attach(MIMEText(html, "html"))

    try:
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            use_tls=True,
            start_tls=True
        )
        print(f"[EMAIL] Код отправлен на {email}")
        return True
    except Exception as e:
        print(f"[EMAIL] Ошибка отправки: {e}")
        return False