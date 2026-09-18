import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getMyAccount } from "../api/accountApi.js";
import { withdrawMoney } from "../api/transactionApi.js";
import WithdrawForm from "../components/WithdrawForm.jsx";

function WithdrawPage() {
  const navigate = useNavigate();
  const [account, setAccount] = useState(null);
  const [loading, setLoading] = useState(false);
  const [accountLoading, setAccountLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getMyAccount()
      .then(setAccount)
      .catch((err) => setError(err.message || "계좌 정보를 불러오지 못했습니다."))
      .finally(() => setAccountLoading(false));
  }, []);

  const handleWithdraw = async ({ amount }) => {
    if (loading) return;

    setLoading(true);
    setError("");
    const requestId = crypto.randomUUID();

    try {
      const result = await withdrawMoney({
        request_id: requestId,
        amount: String(amount),
      });

      navigate("/transaction-result", {
        state: {
          success: true,
          type: "WITHDRAW",
          amount,
          requestId,
          createdAt: result.created_at,
          balanceAfter: result.balance_after,
          result,
        },
      });
    } catch (err) {
      setError(err.message || "출금에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="page-container transaction-page">
      <h1 className="page-title">출금</h1>
      <p className="page-description">
        현재 잔액: {accountLoading
          ? "조회 중..."
          : `${Number(account?.balance ?? 0).toLocaleString("ko-KR")}원`}
      </p>

      {error && <p className="error-message" role="alert">{error}</p>}

      <WithdrawForm
        onSubmit={handleWithdraw}
        loading={loading || accountLoading}
        availableBalance={account?.balance}
      />

      <div className="transaction-page-actions">
        <button
          type="button"
          className="secondary-button"
          onClick={() => navigate("/account")}
          disabled={loading}
        >
          취소
        </button>
      </div>
    </main>
  );
}

export default WithdrawPage;
