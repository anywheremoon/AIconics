import base64
import html
import os
from email.message import EmailMessage
from pathlib import Path

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


DEFAULT_FROM_EMAIL = "aiconics178@gmail.com"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CLIENT_FILE = BACKEND_DIR / "gmail-oauth-client.json"
DEFAULT_TOKEN_FILE = BACKEND_DIR / "gmail-oauth-token.json"


class EmailConfigurationError(RuntimeError):
    pass


class EmailDeliveryError(RuntimeError):
    pass


def _configured_path(variable: str, default: Path) -> Path:
    configured = os.getenv(variable, "").strip()
    return Path(configured).expanduser() if configured else default


def _credentials() -> Credentials:
    token_file = _configured_path("GMAIL_OAUTH_TOKEN_FILE", DEFAULT_TOKEN_FILE)
    if not token_file.is_file():
        raise EmailConfigurationError(
            "Gmail OAuth is not authorized. Run scripts/authorize_gmail.py."
        )

    try:
        credentials = Credentials.from_authorized_user_file(
            token_file,
            [GMAIL_SEND_SCOPE],
        )
    except (OSError, ValueError) as error:
        raise EmailConfigurationError("Gmail OAuth token is invalid") from error

    if credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
            token_file.write_text(credentials.to_json(), encoding="utf-8")
        except (OSError, GoogleAuthError) as error:
            raise EmailDeliveryError(
                "Could not refresh Gmail OAuth credentials"
            ) from error

    if not credentials.valid:
        raise EmailConfigurationError(
            "Gmail OAuth authorization is no longer valid"
        )

    return credentials


def send_verification_code(
    recipient: str,
    code: str,
    expires_in_seconds: int,
) -> None:
    from_email = os.getenv("GMAIL_FROM_EMAIL", DEFAULT_FROM_EMAIL).strip()
    if not from_email:
        raise EmailConfigurationError("GMAIL_FROM_EMAIL is not configured")

    expires_in_minutes = max(1, expires_in_seconds // 60)

    message = EmailMessage()
    message["Subject"] = "[AIconics] 로그인 인증번호"
    message["From"] = f"AIconics <{from_email}>"
    message["To"] = recipient
    message.set_content(
        "AIconics 로그인 인증번호는 "
        f"{code} 입니다. 이 번호는 {expires_in_minutes}분 동안 유효합니다.\n\n"
        "본인이 요청하지 않았다면 이 메일을 무시하세요."
    )
    message.add_alternative(
        """
        <html><body style="font-family:Arial,sans-serif;color:#172033">
          <h2>AIconics 로그인 인증</h2>
          <p>아래 인증번호를 로그인 화면에 입력해 주세요.</p>
          <p style="font-size:30px;font-weight:700;letter-spacing:8px">{code}</p>
          <p>인증번호는 {minutes}분 동안 유효합니다.</p>
          <p style="color:#657087">본인이 요청하지 않았다면 이 메일을 무시하세요.</p>
        </body></html>
        """.format(
            code=html.escape(code),
            minutes=expires_in_minutes,
        ),
        subtype="html",
    )

    encoded_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode("ascii")

    try:
        service = build(
            "gmail",
            "v1",
            credentials=_credentials(),
            cache_discovery=False,
        )
        service.users().messages().send(
            userId="me",
            body={"raw": encoded_message},
        ).execute()
    except EmailConfigurationError:
        raise
    except (OSError, GoogleAuthError, HttpError) as error:
        raise EmailDeliveryError(
            "Failed to deliver verification email through Gmail"
        ) from error


def mask_email(email: str) -> str:
    local, domain = email.rsplit("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "*" * max(1, len(local) - 1)
    else:
        masked_local = local[:2] + "*" * (len(local) - 2)
    return f"{masked_local}@{domain}"
