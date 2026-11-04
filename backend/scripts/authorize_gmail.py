import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


BACKEND_DIR = Path(__file__).resolve().parents[1]
CLIENT_FILE = Path(
    os.getenv(
        "GMAIL_OAUTH_CLIENT_FILE",
        str(BACKEND_DIR / "gmail-oauth-client.json"),
    )
)
TOKEN_FILE = Path(
    os.getenv(
        "GMAIL_OAUTH_TOKEN_FILE",
        str(BACKEND_DIR / "gmail-oauth-token.json"),
    )
)
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def main() -> None:
    if not CLIENT_FILE.is_file():
        raise SystemExit(f"OAuth client file not found: {CLIENT_FILE}")

    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_FILE,
        SCOPES,
    )
    credentials = flow.run_local_server(
        host="127.0.0.1",
        port=0,
        access_type="offline",
        prompt="consent",
        open_browser=True,
    )
    TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")
    print(f"Gmail OAuth authorization saved to {TOKEN_FILE.name}")


if __name__ == "__main__":
    main()
