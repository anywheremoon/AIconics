const API_BASE_URL = "";

export class AuthApiError extends Error {
  constructor(message, status, details = null) {
    super(message);
    this.name = "AuthApiError";
    this.status = status;
    this.details = details;
  }
}

async function request(path, options) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });
  } catch (error) {
    throw new AuthApiError("인증 서버에 연결할 수 없습니다.", 0, error);
  }

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const message = typeof body?.detail === "string" ? body.detail : "인증 요청에 실패했습니다.";
    throw new AuthApiError(message, response.status, body?.detail ?? null);
  }
  return body;
}

export function register(data) {
  return request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function login(data, deviceId = null) {
  const result = await request("/api/auth/login", {
    method: "POST",
    headers: deviceId ? { "X-Device-ID": deviceId } : {},
    body: JSON.stringify(data),
  });
  return result.access_token;
}
