//거래 처리 결과 보여줌
import { useLocation, useNavigate } from "react-router-dom";

function TransactionResultPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const data = location.state;

  if (!data) {
    return (
      <main>
        <h1>거래 결과</h1>

        <p>표시할 거래 정보가 없습니다.</p>

        <button onClick={() => navigate("/account")}>
          계좌 화면으로 이동
        </button>
      </main>
    );
  }

  const transactionType =
    data.type === "TRANSFER"
      ? "계좌 이체"
      : data.type === "WITHDRAW"
        ? "출금"
        : data.type;

  return (
    <main>
      <h1>거래 결과</h1>

      <h2>
        {data.success
          ? "거래가 완료되었습니다."
          : "거래에 실패했습니다."}
      </h2>

      <div>
        <p>
          <strong>거래 유형:</strong> {transactionType}
        </p>

        <p>
          <strong>거래 금액:</strong>{" "}
          {Number(data.amount).toLocaleString("ko-KR")}원
        </p>

        <p>
          <strong>Request ID:</strong> {data.requestId}
        </p>

        <p>
          <strong>처리 시각:</strong>{" "}
          {data.createdAt
            ? new Date(data.createdAt).toLocaleString("ko-KR")
            : "-"}
        </p>

        {!data.success && (
          <p>
            <strong>실패 사유:</strong>{" "}
            {data.error || "알 수 없는 오류"}
          </p>
        )}
      </div>

      <button onClick={() => navigate("/account")}>
        계좌 화면으로 이동
      </button>

      <button onClick={() => navigate("/account")}>
        거래 내역 확인
      </button>
    </main>
  );
}

export default TransactionResultPage;