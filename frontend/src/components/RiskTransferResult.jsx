const LEVELS = [
  {
    name: "LOW",
    color: "#15803d",
    message: "송금 가능한 거래입니다. 내용을 확인하고 송금을 진행해 주세요.",
  },
  {
    name: "MEDIUM",
    color: "#a16207",
    message: "추가 인증이 필요한 거래입니다. 현재 화면에서는 송금하지 않습니다.",
  },
  {
    name: "HIGH",
    color: "#c2410c",
    message: "관리자 검토가 필요한 거래입니다. 송금이 제한됩니다.",
  },
  {
    name: "CRITICAL",
    color: "#b91c1c",
    message: "계정 검토가 필요한 거래입니다. 송금이 제한됩니다.",
  },
];

export default function RiskTransferResult({
  analysis,
  result,
  busy,
  stage,
  error,
  mock,
  onExecute,
}) {
  const transfer = analysis?.transfer;
  const level = transfer ? LEVELS[transfer.riskLevel] : null;

  return (
    <section aria-live="polite" style={{ marginTop: 24 }}>
      {busy && <p role="status">{stage}…</p>}

      {error && <p role="alert" style={{ color: "#b91c1c" }}>{error}</p>}

      {level && (
        <div style={{ border: `1px solid ${level.color}`, padding: 16 }}>
          <strong style={{ color: level.color }}>
            {level.name} / 위험 점수 {transfer.riskScore}
          </strong>

          <p>{level.message}</p>
          <p style={{ overflowWrap: "anywhere" }}>
            수신 주소: {transfer.recipient}
          </p>

          {transfer.riskLevel === 0 && !result && (
            <button onClick={onExecute} disabled={busy}>
              {mock ? "Mock 송금 결과 확인" : "승인 후 송금 진행"}
            </button>
          )}
        </div>
      )}

      {result && (
        <div>
          <p>
            {result.mock
              ? "Mock 송금 성공 — 실제 토큰은 이동하지 않았습니다."
              : "블록체인 송금이 완료되었습니다."}
          </p>

          {result.transactionHash && (
            <p style={{ overflowWrap: "anywhere" }}>
              트랜잭션 해시: {result.transactionHash}
            </p>
          )}
        </div>
      )}
    </section>
  );
}