import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

import config
from collectors.device_collector import get_device_info


ALLOWED_ORIGINS = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}


class AuthHandler(BaseHTTPRequestHandler):

    # ==========================================
    # CORS
    # ==========================================
    def _set_cors_headers(self):
        origin = self.headers.get("Origin")

        if origin in ALLOWED_ORIGINS:
            self.send_header(
                "Access-Control-Allow-Origin",
                origin,
            )
            self.send_header("Vary", "Origin")

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, DELETE, OPTIONS",
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type",
        )

    # ==========================================
    # 공통 JSON 응답
    # ==========================================
    def _respond(self, status_code, payload):
        body = json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(status_code)
        self._set_cors_headers()

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.end_headers()
        self.wfile.write(body)

    # ==========================================
    # 브라우저 요청 Origin 확인
    # Origin 없는 로컬 요청은 허용
    # ==========================================
    def _check_origin(self):
        origin = self.headers.get("Origin")

        if origin is not None and origin not in ALLOWED_ORIGINS:
            self._respond(
                403,
                {"error": "허용되지 않은 요청 출처입니다."},
            )
            return False

        return True

    # ==========================================
    # CORS Preflight
    # ==========================================
    def do_OPTIONS(self):
        if not self._check_origin():
            return

        if self.path not in ("/device-info", "/agent-auth"):
            self._respond(
                404,
                {"error": "요청 경로를 찾을 수 없습니다."},
            )
            return

        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    # ==========================================
    # 현재 PC 장치 정보 조회
    # ==========================================
    def do_GET(self):
        if not self._check_origin():
            return

        if self.path != "/device-info":
            self._respond(
                404,
                {"error": "요청 경로를 찾을 수 없습니다."},
            )
            return

        try:
            device_info = get_device_info()

            response_data = {
                "device_id": device_info["device_id"],
                "location": config.LOCATION,
            }

        except Exception:
            self._respond(
                500,
                {"error": "Agent 장치 정보 조회에 실패했습니다."},
            )
            return

        print("\nDevice 정보 요청 수신")
        print(f"Device ID : {response_data['device_id']}")

        self._respond(200, response_data)

    # ==========================================
    # 최종 로그인 토큰·세션 수신
    # 백엔드 검증 성공 후 저장
    # ==========================================
    def do_POST(self):
        if not self._check_origin():
            return

        if self.path != "/agent-auth":
            self._respond(
                404,
                {"error": "요청 경로를 찾을 수 없습니다."},
            )
            return

        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )

            if not 0 < content_length <= 65536:
                raise ValueError(
                    "인증 요청 본문 크기가 올바르지 않습니다."
                )

            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            if not isinstance(data, dict):
                raise ValueError(
                    "인증 요청은 JSON 객체여야 합니다."
                )

            access_token = data.get("access_token")
            session_id = data.get("session_id")

            if not isinstance(access_token, str):
                raise ValueError(
                    "access_token은 문자열이어야 합니다."
                )

            if not isinstance(session_id, str):
                raise ValueError(
                    "session_id는 문자열이어야 합니다."
                )

            access_token = access_token.strip()
            session_id = session_id.strip()

            if not access_token:
                raise ValueError(
                    "access_token이 없습니다."
                )

            if not session_id or len(session_id) > 36:
                raise ValueError(
                    "session_id가 올바르지 않습니다."
                )

        except (ValueError, UnicodeDecodeError):
            self._respond(
                400,
                {
                    "error":
                        "토큰·세션 또는 JSON 형식이 올바르지 않습니다."
                },
            )
            return

        # 새 인증을 검증하는 동안 이전 인증정보 제거
        config.clear_agent_auth()

        try:
            auth_test = requests.get(
                f"{config.BACKEND_URL}/api/auth/me",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                timeout=config.REQUEST_TIMEOUT,
                allow_redirects=False,
            )

        except requests.RequestException:
            print("Agent JWT 검증 요청 실패")

            self._respond(
                503,
                {
                    "error":
                        "백엔드에 연결할 수 없어 Agent 인증을 저장하지 않았습니다."
                },
            )
            return

        print(
            "Agent JWT 검증 상태 :",
            auth_test.status_code,
        )

        if auth_test.status_code in (401, 403):
            self._respond(
                auth_test.status_code,
                {
                    "error":
                        "최종 로그인 인증을 확인할 수 없습니다."
                },
            )
            return

        if auth_test.status_code != 200:
            self._respond(
                502,
                {
                    "error":
                        "백엔드 인증 확인에 실패했습니다."
                },
            )
            return

        try:
            current_user = auth_test.json()

            if (
                not isinstance(current_user, dict)
                or current_user.get("id") is None
                or current_user.get("role") not in ("USER", "ADMIN")
            ):
                raise ValueError(
                    "사용자 응답 형식이 올바르지 않습니다."
                )

        except ValueError:
            self._respond(
                502,
                {
                    "error":
                        "백엔드 사용자 응답 형식이 올바르지 않습니다."
                },
            )
            return

        try:
            # 검증 성공 후에만 인증정보 저장
            config.set_agent_auth(
                access_token,
                session_id,
            )

        except Exception:
            config.clear_agent_auth()

            self._respond(
                500,
                {"error": "Agent 인증정보 저장에 실패했습니다."},
            )
            return

        # 토큰 값은 출력하지 않는다.
        print("\nAgent 최종 인증정보 수신 완료")
        print(f"Session ID : {session_id}")

        self._respond(
            200,
            {"status": "ok"},
        )

    # ==========================================
    # 로그아웃·인증 대기 전환 시 인증정보 제거
    # ==========================================
    def do_DELETE(self):
        if not self._check_origin():
            return

        if self.path != "/agent-auth":
            self._respond(
                404,
                {"error": "요청 경로를 찾을 수 없습니다."},
            )
            return

        try:
            config.clear_agent_auth()

        except Exception:
            self._respond(
                500,
                {"error": "Agent 인증정보 제거에 실패했습니다."},
            )
            return

        print("\nAgent 로그아웃 정보 수신")
        print("Agent 인증정보 제거 완료")

        self._respond(
            200,
            {"status": "logged_out"},
        )


def start_auth_receiver():
    # React와 Agent는 같은 사용자 PC에서 통신
    server = HTTPServer(
        ("127.0.0.1", 8765),
        AuthHandler,
    )

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )

    thread.start()

    print(
        "Agent 인증 수신 서버 시작: "
        "http://127.0.0.1:8765"
    )