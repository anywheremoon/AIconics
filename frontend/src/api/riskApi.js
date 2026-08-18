const API_BASE_URL = "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const token =
    localStorage.getItem("access_token");

  const response = await fetch(
    `${API_BASE_URL}${path}`,
    {
      ...options,

      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",

        ...(token
          ? {
              Authorization:
                `Bearer ${token}`,
            }
          : {}),

        ...options.headers,
      },
    }
  );

  const data = await response
    .json()
    .catch(() => null);

  if (response.status === 401) {
    localStorage.removeItem(
      "access_token"
    );

    throw new Error(
      "로그인이 만료되었습니다. 다시 로그인해주세요."
    );
  }

  if (response.status === 403) {
    throw new Error(
      "관리자 권한이 필요합니다."
    );
  }

  if (!response.ok) {
    throw new Error(
      data?.detail ||
        "요청 처리에 실패했습니다."
    );
  }

  return data;
}

export function getEventLogs() {
  return request("/api/events");
}

export function getSuspiciousUsers() {
  return request("/api/suspicious-users");
}

export function deleteEventLog(eventId) {
  return request(`/api/events/${eventId}`, {
    method: "DELETE",
  });
}