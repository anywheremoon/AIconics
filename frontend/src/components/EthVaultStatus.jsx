const STATUS_LABELS = {
  PENDING: "진행 중",
  EXECUTED: "송금 완료",
  REFUNDED: "거절 · 환불 완료",
  CANCELLED: "만료 취소 · 환불 완료",
};

export default function EthVaultStatus({ transfer }) {
  return (
    <div className="ev-status">
      <span className={`ev-badge ev-${transfer.riskLevel.toLowerCase()}`}>
        {transfer.riskLevel}
      </span>

      <span>위험 점수 {transfer.riskScore}</span>

      <strong>
        {STATUS_LABELS[transfer.status] || transfer.status}
      </strong>
    </div>
  );
}