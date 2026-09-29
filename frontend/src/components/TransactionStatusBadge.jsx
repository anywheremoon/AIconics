const LABELS = {
  COMPLETED: "거래 완료",
  PENDING_VERIFICATION: "추가 인증 필요",
  PENDING_REVIEW: "검토 대기",
  ACCOUNT_REVIEW: "계좌 검토 필요",
};

function TransactionStatusBadge({ status }) {
  if (!status) return null;

  return (
    <span aria-label={`거래 상태: ${LABELS[status] ?? status}`}>
      {LABELS[status] ?? status}
    </span>
  );
}

export default TransactionStatusBadge;