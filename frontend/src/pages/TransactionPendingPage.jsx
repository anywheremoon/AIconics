import { useLocation, useNavigate } from "react-router-dom";

import TransactionStatusBadge from
  "../components/TransactionStatusBadge.jsx";

const MESSAGES = {
  PENDING_VERIFICATION:
    "추가 인증이 필요한 거래입니다. 인증 전에는 이체가 완료되지 않습니다.",
  PENDING_REVIEW:
    "거래가 검토 대기 중입니다. 검토가 끝나면 처리 결과를 확인할 수 있습니다.",
  ACCOUNT_REVIEW:
    "계좌 검토가 필요한 거래입니다. 현재 이체는 완료되지 않았습니다.",
};

function TransactionPendingPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const transaction = location.state?.transaction;
  const message = MESSAGES[transaction?.status];

  if (!transaction || !message) {
    return (
      <main className="page-container transaction-page">
        <h1 className="page-title">거래 상태</h1>
        <p>표시할 대기 거래 정보가 없습니다.</p>
        <button type="button" onClick={() => navigate("/account")}>
          계좌 화면으로 이동
        </button>
      </main>
    );
  }

  return (
    <main className="page-container transaction-page">
      <h1 className="page-title">거래 처리 대기</h1>

      <p>
        <TransactionStatusBadge status={transaction.status} />
      </p>
      <p>{message}</p>

      <dl>
        <div>
          <dt>거래 번호</dt>
          <dd>{transaction.id}</dd>
        </div>
        <div>
          <dt>금액</dt>
          <dd>
            {Number(transaction.amount).toLocaleString("ko-KR")}원
          </dd>
        </div>
        <div>
          <dt>요청 ID</dt>
          <dd>{transaction.request_id}</dd>
        </div>
      </dl>

      <button type="button" onClick={() => navigate("/account")}>
        계좌 화면으로 이동
      </button>
    </main>
  );
}

export default TransactionPendingPage;