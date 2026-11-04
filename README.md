### AIconics
😎

#### 이메일 인증 설정

추가 로그인 인증번호는 Gmail API OAuth를 통해 사용자의 가입 이메일로 전송됩니다.
발신 계정은 기본적으로 `aiconics178@gmail.com`입니다.

1. Google Cloud에서 Gmail API를 켜고 데스크톱 OAuth 클라이언트를 생성합니다.
2. 다운로드한 파일을 `backend/gmail-oauth-client.json`으로 저장합니다.
3. `python scripts/authorize_gmail.py`를 실행해 발신 계정 권한을 승인합니다.
4. 생성되는 `backend/gmail-oauth-token.json`은 서버에서 자동 갱신됩니다.
5. 기존 PostgreSQL DB에는 `backend/migrations/add_user_email.sql`을 한 번 적용합니다.

OAuth 클라이언트와 토큰 파일은 저장소에 커밋하거나 채팅으로 공유하지 마세요. 운영 환경에서는
`VERIFICATION_EXPOSE_CODE=false`를 유지해야 합니다.
