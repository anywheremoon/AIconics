const API_BASE_URL = "";

async function request(path, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      let errorMessage = `API 요청 실패: ${response.status}`;

      try {
        const errorData = await response.json();

        if (errorData.detail) {
          errorMessage = errorData.detail;
        }
      } catch {
        // JSON 오류 응답이 아니면 기본 메시지를 사용한다.
      }

      throw new Error(errorMessage);
    }

    return await response.json();
  } catch (error) {
    console.error("API 요청 오류:", error);

    if (error instanceof TypeError) {
      throw new Error(
        "API 요청에 실패했습니다. FastAPI 서버와 Vite 프록시 설정을 확인하세요."
      );
    }

    throw error;
  }
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