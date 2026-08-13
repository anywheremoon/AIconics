//출금 화면 구현
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { withdrawMoney } from "../api/transactionApi.js";
import WithdrawForm from "../components/WithdrawForm.jsx";

function WithdrawPage() {
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleWithdraw = async (formData) => {
    if (loading) {
      return;
    }

    setLoading(true);
    setError("");

    const requestId = crypto.randomUUID();

    const requestData = {
      request_id: requestId,
      amount: String(formData.amount),
    };

    try {
      const result = await withdrawMoney(requestData);

      navigate("/transaction-result", {
        state: {
          success: true,
          type: "WITHDRAW",
          amount: formData.amount,
          requestId,
          createdAt:
            result?.created_at || new Date().toISOString(),
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
    <main>
      <h1>출금</h1>

      {error && <p className="error-message">{error}</p>}

      <WithdrawForm
        onSubmit={handleWithdraw}
        loading={loading}
      />

      <button
        type="button"
        onClick={() => navigate("/account")}
        disabled={loading}
      >
        취소
      </button>
    </main>
  );
}

export default WithdrawPage;