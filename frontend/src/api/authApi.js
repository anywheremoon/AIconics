const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || ""
).replace(/\/$/, "");


export class AuthApiError extends Error {
  constructor(message, status, details = null) {
    super(message);
    this.name = "AuthApiError";
    this.status = status;
    this.details = details;
  }
}


async function request(path, options = {}) {
  let response;

  try {
    response = await fetch(
      `${API_BASE_URL}${path}`,
      {
        ...options,
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          ...options.headers,
        },
      }
    );
  } catch (error) {
    throw new AuthApiError(
      "인증 서버에 연결할 수 없습니다.",
      0,
      error
    );
  }

  const body = await response
    .json()
    .catch(() => null);

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


export function register(data) {
  return request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}


// ==========================================
// Agent 실제 Device 정보 조회
// ==========================================
export async function getAgentDeviceInfo() {
  let response;

  try {
    response = await fetch(
      "http://127.0.0.1:8765/device-info",
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

  const body = await response
    .json()
    .catch(() => null);

  if (!response.ok) {
    throw new AuthApiError(
      body?.error ||
        "Agent 기기 정보 조회에 실패했습니다.",
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


export async function login(data) {
  const result = await request(
    "/api/auth/login",
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );

  if (!result?.access_token) {
    throw new AuthApiError(
      "로그인 응답에 access_token이 없습니다.",
      500,
      result
    );
  }

  if (!result?.user) {
    throw new AuthApiError(
      "로그인 응답에 사용자 정보가 없습니다.",
      500,
      result
    );
  }

  return {
    access_token: result.access_token,
    token_type: result.token_type || "bearer",

    user: result.user,

    session_id: result.session_id || null,

    device_trust_status:
      result.device_trust_status || null,

    baseline_status:
      result.baseline_status || null,

    login_pattern:
      result.login_pattern || null,
  };
}


// ==========================================
// 로그인 후 JWT / Session ID를 Agent에 전달
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
      "http://127.0.0.1:8765/agent-auth",
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
      const body = await response
        .json()
        .catch(() => null);

      console.warn(
        "Agent 인증 전달 실패:",
        body
      );

      return false;
    }

    console.log(
      "Agent 인증정보 전달 완료"
    );

    return true;

  } catch (error) {
    console.warn(
      "Agent 인증 서버에 연결할 수 없습니다.",
      error
    );

    return false;
  }
}


export function getCurrentUser() {
  const token =
    localStorage.getItem("access_token");

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