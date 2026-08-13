//거래 관련 backend api 호출
const API_BASE_URL = "http://localhost:8000";

function getToken() {
  return localStorage.getItem("access_token");
}

async function request(path, options = {}) {
  const token = getToken();

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  if (response.status === 401) {
    localStorage.removeItem("access_token");
    throw new Error("로그인이 만료되었습니다. 다시 로그인해주세요.");
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      data?.detail ||
        data?.message ||
        "서버 요청 처리 중 오류가 발생했습니다."
    );
  }

  return data;
}

export async function getTransactions() {
  return request("/api/transactions");
}

export async function transferMoney(data) {
  return request("/api/transactions/transfer", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function withdrawMoney(data) {
  return request("/api/transactions/withdraw", {
    method: "POST",
    body: JSON.stringify(data),
  });
}