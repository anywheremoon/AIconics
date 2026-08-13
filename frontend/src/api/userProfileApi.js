//사용자 초기 프로필 조회 
const API_BASE_URL = "http://localhost:8000";

export async function getMyUserProfile() {
  const token = localStorage.getItem("access_token");

  if (!token) {
    throw new Error("로그인이 필요합니다.");
  }

  const response = await fetch(
    `${API_BASE_URL}/api/user-profiles/me`,
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
      data?.detail || "사용자 프로필 조회에 실패했습니다."
    );
  }

  return data;
}