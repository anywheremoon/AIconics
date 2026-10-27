import argparse
import getpass
import sys

import requests


TIMEOUT = 10
BLOCKED_CODES = {401, 403}


def check(condition, message):
    if not condition:
        raise AssertionError(message)

    print(f"PASS: {message}")


def read_json(response):
    try:
        body = response.json()
    except ValueError:
        raise AssertionError(
            f"JSON 응답이 아닙니다. HTTP {response.status_code}"
        ) from None

    check(isinstance(body, dict), "응답이 JSON 객체임")
    return body


def call(base_url, method, path, token=None, **kwargs):
    headers = {}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    headers.update(kwargs.pop("headers", {}))

    response = requests.request(
        method,
        f"{base_url}{path}",
        headers=headers,
        timeout=TIMEOUT,
        allow_redirects=False,
        **kwargs,
    )

    # 토큰·비밀번호·인증번호는 출력하지 않는다.
    print(f"HTTP: {method} {path} -> {response.status_code}")

    return response


def check_protected_access(base_url, token, allowed):
    for path in ("/api/auth/me", "/api/accounts/me"):
        response = call(base_url, "GET", path, token=token)

        if allowed:
            check(
                response.status_code == 200,
                f"{path} 접근 허용",
            )
        else:
            check(
                response.status_code in BLOCKED_CODES,
                f"{path} 접근 차단",
            )


def check_completed_login(body):
    # 기존 정상 로그인 응답도 지원
    status = body.get("login_status", "AUTHENTICATED")

    check(status == "AUTHENTICATED", "최종 로그인 완료 상태")
    check(
        body.get("requires_verification") is not True,
        "추가 인증 대기가 아님",
    )
    check(
        isinstance(body.get("access_token"), str)
        and bool(body["access_token"].strip()),
        "일반 토큰 발급",
    )
    check(
        isinstance(body.get("session_id"), str)
        and bool(body["session_id"].strip()),
        "최종 세션 ID 반환",
    )
    check(
        isinstance(body.get("user"), dict)
        and body["user"].get("id") is not None,
        "사용자 정보 반환",
    )


def check_logout(base_url, body):
    token = body["access_token"]

    response = call(
        base_url,
        "POST",
        "/api/auth/logout",
        token=token,
        json={"session_id": body["session_id"]},
    )

    check(response.status_code == 204, "로그아웃 성공")

    # 종료된 세션의 토큰이 거부되는지 확인
    check_protected_access(base_url, token, allowed=False)


def run(args):
    base_url = args.base_url.rstrip("/")
    password = getpass.getpass("테스트 계정 비밀번호: ")

    response = call(
        base_url,
        "POST",
        "/api/auth/login",
        headers={"X-Device-ID": args.device_id},
        json={
            "username": args.username,
            "password": password,
            "device_id": args.device_id,
            "location": args.location,
        },
    )

    check(response.status_code == 200, "로그인 API 응답 성공")
    body = read_json(response)

    if args.case == "normal":
        check_completed_login(body)
        check_protected_access(
            base_url,
            body["access_token"],
            allowed=True,
        )
        check_logout(base_url, body)
        return

    expected_status = (
        "REQUIRE_VERIFICATION"
        if args.case == "verification"
        else "PENDING_REVIEW"
    )

    check(
        body.get("login_status") == expected_status,
        f"로그인 상태가 {expected_status}",
    )
    check(
        body.get("access_token") is None,
        "일반 토큰 미발급",
    )
    check(
        isinstance(body.get("reason_codes"), list),
        "사유 코드 목록 반환",
    )

    # 토큰 없이 일반 보호 API에 접근할 수 없어야 한다.
    check_protected_access(base_url, None, allowed=False)

    limited_token = body.get("verification_token")
    session_id = body.get("session_id")

    if limited_token:
        check_protected_access(
            base_url,
            limited_token,
            allowed=False,
        )

    if args.case == "pending":
        if not limited_token or not session_id:
            print(
                "SKIP: 보류 안내 조회 "
                "(제한 토큰 또는 세션 ID 없음)"
            )
            return

    else:
        check(
            body.get("requires_verification") is True,
            "추가 인증 필요 여부 반환",
        )
        check(bool(limited_token), "추가 인증 전용 토큰 반환")
        check(bool(session_id), "추가 인증 세션 ID 반환")

    # B의 안내 API: 제안 규격
    response = call(
        base_url,
        "GET",
        "/api/auth/guidance",
        token=limited_token,
        params={"session_id": session_id},
    )

    check(response.status_code == 200, "사용자 안내 조회 성공")
    guidance = read_json(response)

    for field in ("summary", "next_action"):
        check(
            isinstance(guidance.get(field), str)
            and bool(guidance[field].strip()),
            f"안내 {field} 반환",
        )

    if args.case == "pending":
        return

    # A의 추가 인증 API: 제안 규격
    response = call(
        base_url,
        "POST",
        "/api/auth/verification/request",
        token=limited_token,
        json={"session_id": session_id},
    )

    check(
        response.status_code in (200, 201, 202, 204),
        "인증번호 요청 성공",
    )

    if args.invalid_code is not None:
        response = call(
            base_url,
            "POST",
            "/api/auth/verification/confirm",
            token=limited_token,
            json={
                "session_id": session_id,
                "code": args.invalid_code,
            },
        )

        check(
            response.status_code in (400, 401, 403, 422),
            "잘못된 인증번호 거부",
        )

        check_protected_access(
            base_url,
            limited_token,
            allowed=False,
        )
    else:
        print("SKIP: 잘못된 인증번호 테스트 (--invalid-code 미지정)")

    code = getpass.getpass("실제로 발급된 인증번호: ").strip()
    check(bool(code), "인증번호 입력")

    response = call(
        base_url,
        "POST",
        "/api/auth/verification/confirm",
        token=limited_token,
        json={
            "session_id": session_id,
            "code": code,
        },
    )

    check(response.status_code == 200, "추가 인증 성공")
    completed = read_json(response)

    check_completed_login(completed)
    check_protected_access(
        base_url,
        completed["access_token"],
        allowed=True,
    )
    check_logout(base_url, completed)


def main():
    parser = argparse.ArgumentParser(
        description="C 로그인·추가 인증 API 통합 테스트"
    )

    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--case",
        required=True,
        choices=["normal", "verification", "pending"],
    )
    parser.add_argument("--username", required=True)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--location", default="Seoul")
    parser.add_argument(
        "--invalid-code",
        help="서버 규격에 맞는 확실히 잘못된 테스트 인증번호",
    )

    args = parser.parse_args()

    try:
        run(args)
    except (AssertionError, requests.RequestException) as error:
        print(f"\nFAIL: {error}")
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\n테스트를 중단했습니다.")
        return 1

    print(f"\n선택한 테스트 완료: {args.case}")
    return 0


if __name__ == "__main__":
    sys.exit(main())