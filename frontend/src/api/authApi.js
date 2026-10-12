const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || ""
).replace(/\/$/, "");

const AGENT_BASE_URL = "http://127.0.0.1:8765";

export const LOGIN_STATUS = Object.freeze({
  AUTHENTICATED: "AUTHENTICATED",
  REQUIRE_VERIFICATION: "REQUIRE_VERIFICATION",
  PENDING_REVIEW: "PENDING_REVIEW",
});


// ==========================================
// 인증 API 오류
// ==========================================

export class AuthApiError extends Error {
  constructor(message, status, details = null) {
    super(message);

    this.name = "AuthApiError";
    this.status = status;
    this.details = details;
  }
}


// ==========================================
// 공통 백엔드 요청
// ==========================================

async function request(path, options = {}) {
  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,

      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
  } catch (error) {
    throw new AuthApiError(
      "인증 서버에 연결할 수 없습니다.",
      0,
      error
    );
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      typeof body?.detail === "string"
        ? body.detail
        : "인증 요청에 실패했습니다.";

    throw new AuthApiError(
      message,
      response.status,
      body
    );
  }

  return body;
}


// ==========================================
// 회원가입
// ==========================================

export function register(data) {
  return request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}


// ==========================================
// Agent 장치 정보 조회
// ==========================================

export async function getAgentDeviceInfo() {
  let response;

  try {
    response = await fetch(
      `${AGENT_BASE_URL}/device-info`,
      {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
      }
    );
  } catch (error) {
    throw new AuthApiError(
      "Agent에서 기기 정보를 가져올 수 없습니다.",
      0,
      error
    );
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    throw new AuthApiError(
      body?.error || "Agent 기기 정보 조회에 실패했습니다.",
      response.status,
      body
    );
  }

  if (!body?.device_id) {
    throw new AuthApiError(
      "Agent 응답에 device_id가 없습니다.",
      500,
      body
    );
  }

  return {
    device_id: body.device_id,
    location: body.location || null,
  };
}


// ==========================================
// 로그인 응답 검증 및 정리
// ==========================================

export function normalizeLoginResult(result) {
  if (
    !result ||
    typeof result !== "object" ||
    Array.isArray(result)
  ) {
    throw new AuthApiError(
      "로그인 응답 형식이 올바르지 않습니다.",
      500,
      result
    );
  }

  // 상태 필드가 없는 기존 백엔드 응답도 지원한다.
  const loginStatus =
    result.login_status ??
    (
      result.requires_verification === true
        ? LOGIN_STATUS.REQUIRE_VERIFICATION
        : result.access_token
          ? LOGIN_STATUS.AUTHENTICATED
          : null
    );

  switch (loginStatus) {
    case LOGIN_STATUS.AUTHENTICATED:
      if (result.requires_verification === true) {
        throw new AuthApiError(
          "로그인 상태와 추가 인증 여부가 일치하지 않습니다.",
          500,
          result
        );
      }

      if (
        !result.access_token ||
        !result.session_id ||
        !result.user
      ) {
        throw new AuthApiError(
          "로그인 완료 응답에 토큰, 세션 또는 사용자 정보가 없습니다.",
          500,
          result
        );
      }

      break;

    case LOGIN_STATUS.REQUIRE_VERIFICATION:
      if (result.requires_verification === false) {
        throw new AuthApiError(
          "로그인 상태와 추가 인증 여부가 일치하지 않습니다.",
          500,
          result
        );
      }

      if (
        !result.verification_token ||
        !result.session_id
      ) {
        throw new AuthApiError(
          "추가 인증 응답에 인증 전용 토큰 또는 세션 ID가 없습니다.",
          500,
          result
        );
      }

      break;

    case LOGIN_STATUS.PENDING_REVIEW:
      break;

    default:
      throw new AuthApiError(
        "지원하지 않는 로그인 상태입니다.",
        500,
        result
      );
  }

  const isAuthenticated =
    loginStatus === LOGIN_STATUS.AUTHENTICATED;

  return {
    ...result,

    login_status: loginStatus,

    requires_verification:
      loginStatus === LOGIN_STATUS.REQUIRE_VERIFICATION,

    reason_codes: Array.isArray(result.reason_codes)
      ? result.reason_codes
      : [],

    // 일반 인증정보는 최종 로그인 완료 때만 사용한다.
    access_token: isAuthenticated
      ? result.access_token
      : null,

    user: isAuthenticated
      ? result.user
      : null,

    // 제한 토큰은 일반 access_token과 분리한다.
    verification_token: isAuthenticated
      ? null
      : result.verification_token ?? null,

    token_type: result.token_type || "bearer",
    session_id: result.session_id ?? null,
    device_trust_status: result.device_trust_status ?? null,
    baseline_status: result.baseline_status ?? null,
    login_pattern: result.login_pattern ?? null,
  };
}


// ==========================================
// 로그인
// ==========================================

export async function login(data) {
  const headers = {};

  if (data.device_id) {
    headers["X-Device-ID"] = data.device_id;
  }

  const result = await request("/api/auth/login", {
    method: "POST",
    headers,
    body: JSON.stringify(data),
  });

  return normalizeLoginResult(result);
}


// ==========================================
// 최종 로그인 토큰·세션을 Agent에 전달
// ==========================================

export async function sendAgentAuth(
  accessToken,
  sessionId
) {
  if (!accessToken || !sessionId) {
    console.warn(
      "Agent 인증 전달에 필요한 정보가 없습니다."
    );
    return false;
  }

  try {
    const response = await fetch(
      `${AGENT_BASE_URL}/agent-auth`,
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body: JSON.stringify({
          access_token: accessToken,
          session_id: sessionId,
        }),
      }
    );

    if (!response.ok) {
      const body = await response.json().catch(() => null);

      console.warn("Agent 인증 전달 실패:", body);
      return false;
    }

    console.log("Agent 인증정보 전달 완료");
    return true;
  } catch (error) {
    console.warn(
      "Agent 인증 서버에 연결할 수 없습니다.",
      error
    );
    return false;
  }
}


// ==========================================
// Agent 인증정보 제거
// ==========================================

export async function clearAgentAuth() {
  try {
    const response = await fetch(
      `${AGENT_BASE_URL}/agent-auth`,
      {
        method: "DELETE",

        headers: {
          Accept: "application/json",
        },
      }
    );

    if (!response.ok) {
      const body = await response.json().catch(() => null);

      console.warn("Agent 로그아웃 전달 실패:", body);
      return false;
    }

    console.log("Agent 인증정보 제거 완료");
    return true;
  } catch (error) {
    console.warn(
      "Agent 인증 서버에 연결할 수 없습니다.",
      error
    );
    return false;
  }
}


// ==========================================
// 현재 사용자 조회
// ==========================================

export function getCurrentUser() {
  const token = localStorage.getItem("access_token");

  if (!token) {
    throw new AuthApiError(
      "로그인이 필요합니다.",
      401
    );
  }

  return request("/api/auth/me", {
    method: "GET",

    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}


// ==========================================
// 백엔드 로그인 세션 종료
// ==========================================

export function logoutSession(
  accessToken,
  sessionId
) {
  if (!accessToken || !sessionId) {
    throw new AuthApiError(
      "로그아웃에 필요한 토큰 또는 세션 ID가 없습니다.",
      400
    );
  }

  return request("/api/auth/logout", {
    method: "POST",

    headers: {
      Authorization: `Bearer ${accessToken}`,
    },

    body: JSON.stringify({
      session_id: sessionId,
    }),

    signal: AbortSignal.timeout(10000),
  });
}


// ==========================================
// 제한 토큰 인증 헤더
// ==========================================

function verificationHeaders(verificationToken) {
  if (!verificationToken) {
    throw new AuthApiError(
      "추가 인증 정보가 없습니다. 다시 로그인해주세요.",
      401
    );
  }

  return {
    Authorization: `Bearer ${verificationToken}`,
  };
}


// ==========================================
// 인증번호 요청
// A와 합의할 제안 규격
// ==========================================

export function requestVerification(
  verificationToken,
  sessionId
) {
  if (!sessionId) {
    throw new AuthApiError(
      "추가 인증 세션 정보가 없습니다.",
      400
    );
  }

  return request("/api/auth/verification/request", {
    method: "POST",
    headers: verificationHeaders(verificationToken),

    body: JSON.stringify({
      session_id: sessionId,
    }),
  });
}


// ==========================================
// 인증번호 확인
// A와 합의할 제안 규격
// ==========================================

export async function confirmVerification(
  verificationToken,
  sessionId,
  code
) {
  const trimmedCode =
    typeof code === "string" ? code.trim() : "";

  if (!sessionId || !trimmedCode) {
    throw new AuthApiError(
      "세션 정보와 인증번호가 필요합니다.",
      400
    );
  }

  const result = await request(
    "/api/auth/verification/confirm",
    {
      method: "POST",
      headers: verificationHeaders(verificationToken),

      body: JSON.stringify({
        session_id: sessionId,
        code: trimmedCode,
      }),
    }
  );

  const normalized = normalizeLoginResult(result);

  if (
    normalized.login_status !==
    LOGIN_STATUS.AUTHENTICATED
  ) {
    throw new AuthApiError(
      "인증 완료 응답을 받지 못했습니다.",
      500,
      result
    );
  }

  return normalized;
}


// ==========================================
// 사용자용 보안 안내 조회
// B와 합의할 제안 규격
// ==========================================

export async function getLoginGuidance(
  verificationToken,
  sessionId,
  signal
) {
  if (!verificationToken || !sessionId) {
    throw new AuthApiError(
      "안내 조회에 필요한 인증정보가 없습니다.",
      401
    );
  }

  const query = new URLSearchParams({
    session_id: sessionId,
  });

  const result = await request(
    `/api/auth/guidance?${query.toString()}`,
    {
      method: "GET",
      headers: verificationHeaders(verificationToken),
      signal,
    }
  );

  if (
    typeof result?.summary !== "string" ||
    !result.summary.trim() ||
    typeof result?.next_action !== "string" ||
    !result.next_action.trim()
  ) {
    throw new AuthApiError(
      "안내 응답 형식이 올바르지 않습니다.",
      502,
      result
    );
  }

  return {
    summary: result.summary.trim(),
    next_action: result.next_action.trim(),
  };
}