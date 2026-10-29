export const USE_RISK_TRANSFER_MOCK =
  import.meta.env.VITE_RISK_TRANSFER_MOCK !== "false";

const API_BASE_URL = (
  import.meta.env.VITE_RISK_TRANSFER_API_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

export async function analyzeRiskTransfer(
  payload,
  { accessToken, mockRiskLevel = 0 } = {}
) {
  if (USE_RISK_TRANSFER_MOCK) {
    const scores = [20, 50, 75, 90];

    return {
      transfer: {
        ...payload,
        riskScore: scores[mockRiskLevel],
        riskLevel: mockRiskLevel,
        requestId: randomBytes32(),
        nonce: randomBytes32(),
        deadline: Math.floor(Date.now() / 1000) + 300,
      },
      signature: null,
    };
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/risk-transfer/analyze`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(accessToken
            ? { Authorization: `Bearer ${accessToken}` }
            : {}),
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      }
    );

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      throw new Error(
        typeof data?.detail === "string"
          ? data.detail
          : `위험 분석 요청에 실패했습니다. (${response.status})`
      );
    }

    return data;
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error("위험 분석 요청 시간이 초과되었습니다.");
    }

    throw err;
  } finally {
    clearTimeout(timer);
  }
}

function randomBytes32() {
  const bytes = crypto.getRandomValues(new Uint8Array(32));

  return (
    "0x" +
    Array.from(bytes, (value) =>
      value.toString(16).padStart(2, "0")
    ).join("")
  );
}