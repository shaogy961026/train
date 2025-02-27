import smtplib
from email.mime.text import MIMEText

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

def send_email(recipient, subject, body, smtp_username, smtp_app_password):
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = smtp_username
        msg['To'] = recipient

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(smtp_username, smtp_app_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"寄送 Email 失敗: {str(e)}")
        return False