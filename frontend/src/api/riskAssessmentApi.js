const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || ""
).replace(/\/$/, "");

export async function getRiskAssessment(transactionId) {
  if (transactionId === undefined || transactionId === null) {
    throw new Error("거래 ID가 없습니다.");
  }

  const token = localStorage.getItem("access_token");

  const response = await fetch(
    `${API_BASE_URL}/api/risk-assessments/${encodeURIComponent(transactionId)}`,
    {
      headers: {
        Accept: "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    }
  );

  if (response.status === 401) {
    localStorage.removeItem("access_token");
    throw new Error("로그인이 만료되었습니다. 다시 로그인해주세요.");
  }

  const data = await response.json().catch(() => null);

  if (response.status === 404) {
    const error = new Error("이 거래에는 위험 평가 기록이 없습니다.");
    error.status = 404;
    throw error;
}

  if (!response.ok) {
    throw new Error(
      typeof data?.detail === "string"
        ? data.detail
        : "위험 평가 정보를 불러오지 못했습니다."
    );
  }

  return data;
}