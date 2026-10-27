import { useEffect, useRef, useState } from "react";

import {
  getChainRecord,
  verifyAnalysisIntegrity,
} from "../api/integrityApi.js";

const RESULT_LABELS = {
  RECORDED: "블록체인 기록 있음",
  NOT_RECORDED: "블록체인 기록 없음",
  MATCH: "정상",
  MISMATCH: "데이터 변경 탐지",
};

export default function IntegrityCheckPanel() {
  const [analysisId, setAnalysisId] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const controllerRef = useRef(null);

  useEffect(() => {
    return () => controllerRef.current?.abort();
  }, []);

  async function runRequest(mode) {
    if (controllerRef.current) return;

    const id = analysisId.trim();

    if (!/^[1-9]\d*$/.test(id)) {
      setResult(null);
      setError("분석 ID는 1 이상의 정수로 입력해 주세요.");
      return;
    }

    const controller = new AbortController();
    controllerRef.current = controller;

    setLoading(true);
    setResult(null);
    setError("");

    try {
      const request =
        mode === "verify" ? verifyAnalysisIntegrity : getChainRecord;

      const data = await request(id, {
        signal: controller.signal,
      });

      if (!controller.signal.aborted) {
        setResult(data);
      }
    } catch (requestError) {
      if (!controller.signal.aborted) {
        setError(requestError.message || "요청에 실패했습니다.");
      }
    } finally {
      if (!controller.signal.aborted) {
        controllerRef.current = null;
        setLoading(false);
      }
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    runRequest("verify");
  }

  function handleIdChange(event) {
    setAnalysisId(event.target.value);
    setResult(null);
    setError("");
  }

  const buttonStyle = {
    padding: "12px 20px",
    border: 0,
    borderRadius: "8px",
    color: "#fff",
    cursor: loading ? "wait" : "pointer",
    opacity: loading || !analysisId.trim() ? 0.6 : 1,
  };

  const resultColor =
    result?.status === "MISMATCH"
      ? "#b42318"
      : result?.status === "MATCH"
        ? "#067647"
        : "#172033";

  return (
    <section
      aria-labelledby="integrity-panel-title"
      style={{
        marginTop: "24px",
        padding: "24px",
        border: "1px solid #dbe3ed",
        borderRadius: "16px",
        background: "#fff",
        color: "#172033",
      }}
    >
      <h2 id="integrity-panel-title" style={{ marginTop: 0 }}>
        분석 결과 무결성 검증
      </h2>

      <p style={{ color: "#526176", lineHeight: 1.6 }}>
        위험 분석 ID를 입력하면 현재 DB 데이터와 블록체인 기록을
        비교합니다. 거래 ID와는 다른 값입니다.
      </p>

      <form onSubmit={handleSubmit}>
        <label
          htmlFor="integrity-analysis-id"
          style={{ display: "block", marginBottom: "8px" }}
        >
          분석 ID
        </label>

        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <input
            id="integrity-analysis-id"
            type="text"
            inputMode="numeric"
            pattern="[1-9][0-9]*"
            value={analysisId}
            onChange={handleIdChange}
            placeholder="예: 1"
            required
            disabled={loading}
            style={{
              flex: "1 1 180px",
              minWidth: 0,
              padding: "12px",
              border: "1px solid #b8c5d6",
              borderRadius: "8px",
            }}
          />

          <button
            type="button"
            disabled={loading || !analysisId.trim()}
            onClick={() => runRequest("read")}
            style={{ ...buttonStyle, background: "#526176" }}
          >
            기록 조회
          </button>

          <button
            type="submit"
            disabled={loading || !analysisId.trim()}
            style={{ ...buttonStyle, background: "#2457d6" }}
          >
            무결성 검증
          </button>
        </div>
      </form>

      {loading && (
        <p role="status">요청을 처리하고 있습니다…</p>
      )}

      {error && (
        <p role="alert" style={{ color: "#b42318" }}>
          {error}
        </p>
      )}

      {result && (
        <div
          role="status"
          style={{
            marginTop: "20px",
            padding: "16px",
            background: "#f3f6fb",
            borderRadius: "10px",
            overflowWrap: "anywhere",
          }}
        >
          <strong style={{ color: resultColor }}>
            {RESULT_LABELS[result.status]}
          </strong>

          <p>분석 ID: {result.analysis_id}</p>

          {result.status !== "NOT_RECORDED" && (
            <p>거래 ID: {result.transaction_id}</p>
          )}

          {result.status === "RECORDED" && (
            <>
              <p>해시: <code>{result.digest}</code></p>
              <p>
                기록 시각:{" "}
                {new Date(
                  result.recorded_at * 1000
                ).toLocaleString("ko-KR")}
              </p>
              <p>기록 조회 결과입니다. DB 데이터와의 비교는 수행하지 않았습니다.</p>
            </>
          )}

          {["MATCH", "MISMATCH"].includes(result.status) && (
            <>
              <p>
                현재 DB 해시: <code>{result.current_hash}</code>
              </p>
              <p>
                블록체인 해시: <code>{result.chain_hash}</code>
              </p>
              <p>
                {result.status === "MATCH"
                  ? "해시와 거래 ID가 블록체인 기록과 일치합니다."
                  : "해시 또는 거래 ID가 블록체인 기록과 다릅니다."}
              </p>
            </>
          )}

          {result.status === "NOT_RECORDED" && (
            <p>
              블록체인 기록이 없어 무결성을 판정할 수 없습니다.
            </p>
          )}
        </div>
      )}
    </section>
  );
}