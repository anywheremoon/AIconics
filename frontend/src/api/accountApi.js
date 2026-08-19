//임시로 제작 B
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

export async function getMyAccount() {
  const token = localStorage.getItem("access_token");

  if (!token) {
    throw new Error("로그인이 필요합니다.");
  }

  const response = await fetch(
    `${API_BASE_URL}/api/accounts/me`,
    {
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (response.status === 401) {
    localStorage.removeItem("access_token");
    throw new Error("로그인이 만료되었습니다.");
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      data?.detail || "계좌 조회에 실패했습니다."
    );
  }

  return data;
}
