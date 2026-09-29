import { useLocation, useNavigate } from "react-router-dom";

import TransactionStatusBadge from "../components/TransactionStatusBadge.jsx";

function VerificationPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const transaction = location.state?.transaction;

  if (!transaction) {
    return (
      <main className="page-container transaction-page">
        <h1 className="page-title">추가 인증</h1>
        <p>표시할 거래 정보가 없습니다.</p>
        <button type="button" onClick={() => navigate("/account")}>
          계좌 화면으로 이동
        </button>
      </main>
    );
  }

  return (
    <main className="page-container transaction-page">
      <h1 className="page-title">추가 인증이 필요합니다</h1>
      <p className="page-description">
        이 거래는 추가 인증이 필요하여 아직 처리되지 않았습니다.
      </p>

      <TransactionStatusBadge status={transaction.status} />

      <p>
        <strong>거래 금액:</strong>{" "}
        {Number(transaction.amount).toLocaleString("ko-KR")}원
      </p>
      <p>
        <strong>Request ID:</strong> {transaction.request_id}
      </p>

      <button type="button" onClick={() => navigate("/account")}>
        계좌 화면으로 이동
      </button>
    </main>
  );
}

export default VerificationPage;