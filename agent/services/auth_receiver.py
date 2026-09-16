import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

import config
from collectors.device_collector import get_device_info


class AuthHandler(BaseHTTPRequestHandler):

    def _set_cors_headers(self):
        self.send_header(
            "Access-Control-Allow-Origin",
            "http://localhost:5173"
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, DELETE, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

    # ==========================================
    # CORS Preflight
    # ==========================================
    def do_OPTIONS(self):

        self.send_response(200)

        self._set_cors_headers()

        self.end_headers()


    # ==========================================
    # React에서 현재 PC의 device_id 조회
    # ==========================================
    def do_GET(self):

        if self.path != "/device-info":

            self.send_response(404)

            self._set_cors_headers()

            self.end_headers()

            return


        try:

            device_info = get_device_info()

            response_data = {
                "device_id":
                    device_info["device_id"],

                "location":
                    config.LOCATION,
            }


            print(
                "\nDevice 정보 요청 수신"
            )

            print(
                f"Device ID : "
                f"{response_data['device_id']}"
            )


            self.send_response(200)

            self._set_cors_headers()

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.end_headers()


            self.wfile.write(
                json.dumps(
                    response_data
                ).encode("utf-8")
            )


        except Exception as e:

            self.send_response(500)

            self._set_cors_headers()

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.end_headers()


            self.wfile.write(
                json.dumps({
                    "error": str(e)
                }).encode("utf-8")
            )


    # ==========================================
    # React 로그인 후
    # JWT / session_id 수신
    # ==========================================
    def do_POST(self):

        if self.path != "/agent-auth":

            self.send_response(404)

            self._set_cors_headers()

            self.end_headers()

            return


        content_length = int(
            self.headers.get(
                "Content-Length",
                0
            )
        )


        body = self.rfile.read(
            content_length
        )


        try:

            data = json.loads(
                body.decode("utf-8")
            )


            access_token = data.get(
                "access_token"
            )

            session_id = data.get(
                "session_id"
            )


            if not access_token:

                raise ValueError(
                    "access_token이 없습니다."
                )


            if not session_id:

                raise ValueError(
                    "session_id가 없습니다."
                )


            access_token = (
                access_token.strip()
            )

            session_id = (
                session_id.strip()
            )


            # Agent 인증정보 저장
            config.set_agent_auth(
                access_token,
                session_id
            )


            print(
                "\nAgent 인증정보 수신 완료"
            )

            print(
                f"Session ID : "
                f"{session_id}"
            )

            # 토큰 전체는 출력하지 않음
            print(
                f"Token length : "
                f"{len(access_token)}"
            )

            print(
                f"Token prefix : "
                f"{access_token[:20]}..."
            )

            print(
                f"Token suffix : "
                f"...{access_token[-20:]}"
            )


            # ==================================
            # 받은 JWT가 Backend에서
            # 유효한지 확인
            # ==================================

            try:

                auth_test = requests.get(
                    "http://127.0.0.1:8000"
                    "/api/auth/me",

                    headers={
                        "Authorization":
                            f"Bearer "
                            f"{access_token}"
                    },

                    timeout=5
                )


                print(
                    "Agent JWT 검증 상태 :",
                    auth_test.status_code
                )

                print(
                    "Agent JWT 검증 응답 :",
                    auth_test.text
                )


            except requests.RequestException as e:

                print(
                    "Agent JWT 검증 요청 실패 :",
                    e
                )


            self.send_response(200)

            self._set_cors_headers()

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.end_headers()


            self.wfile.write(
                json.dumps({
                    "status": "ok"
                }).encode("utf-8")
            )


        except Exception as e:

            self.send_response(400)

            self._set_cors_headers()

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.end_headers()


            self.wfile.write(
                json.dumps({
                    "error": str(e)
                }).encode("utf-8")
            )


    # ==========================================
    # React 로그아웃 후
    # Agent 인증정보 제거
    # ==========================================
    def do_DELETE(self):

        if self.path != "/agent-auth":

            self.send_response(404)

            self._set_cors_headers()

            self.end_headers()

            return


        try:

            # Agent 인증정보 제거
            config.clear_agent_auth()


            print(
                "\nAgent 로그아웃 정보 수신"
            )

            print(
                "Agent 인증정보 제거 완료"
            )


            self.send_response(200)

            self._set_cors_headers()

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.end_headers()


            self.wfile.write(
                json.dumps({
                    "status": "logged_out"
                }).encode("utf-8")
            )


        except Exception as e:

            self.send_response(500)

            self._set_cors_headers()

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.end_headers()


            self.wfile.write(
                json.dumps({
                    "error": str(e)
                }).encode("utf-8")
            )


def start_auth_receiver():

    server = HTTPServer(
        ("127.0.0.1", 8765),
        AuthHandler
    )


    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True
    )


    thread.start()


    print(
        "Agent 인증 수신 서버 시작: "
        "http://127.0.0.1:8765"
    )