const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || ""
).replace(/\/$/, "");

async function requestAnalysis(analysisId, endpoint, { signal } = {}) {
  const id = String(analysisId).trim();

  if (!/^[1-9]\d*$/.test(id)) {
    throw new Error("분석 ID는 1 이상의 정수로 입력해 주세요.");
  }

  const token = localStorage.getItem("access_token");

  if (!token) {
    throw new Error("로그인이 필요합니다.");
  }

  let response;

  try {
    response = await fetch(
      `${API_BASE_URL}/api/admin/analyses/${id}/${endpoint}`,
      {
        method: "GET",
        headers: {
          Accept: "application/json",
          Authorization: `Bearer ${token}`,
        },
        signal,
      }
    );
  } catch (error) {
    if (error.name === "AbortError") throw error;

    throw new Error("서버에 연결할 수 없습니다.");
  }

  const data = await response.json().catch(() => null);

  if (response.status === 401) {
    throw new Error("로그인이 만료되었거나 세션이 종료되었습니다.");
  }

  if (response.status === 403) {
    throw new Error("관리자 권한이 필요합니다.");
  }

  if (!response.ok) {
    throw new Error(
      typeof data?.detail === "string"
        ? data.detail
        : "요청을 처리하지 못했습니다."
    );
  }

  const allowedStatuses =
    endpoint === "integrity"
      ? ["MATCH", "MISMATCH", "NOT_RECORDED"]
      : ["RECORDED", "NOT_RECORDED"];

  if (!data || !allowedStatuses.includes(data.status)) {
    throw new Error("서버 응답 형식이 올바르지 않습니다.");
  }

  return data;
}

export function getChainRecord(analysisId, options) {
  return requestAnalysis(analysisId, "chain-record", options);
}

export function verifyAnalysisIntegrity(analysisId, options) {
  return requestAnalysis(analysisId, "integrity", options);
}