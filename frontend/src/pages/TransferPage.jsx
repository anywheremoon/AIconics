//이체 화면 구현
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { transferMoney } from "../api/transactionApi.js";
import TransferForm from "../components/TransferForm.jsx";

function TransferPage() {
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleTransfer = async (formData) => {
    if (loading) {
      return;
    }

    setLoading(true);
    setError("");

    const requestId = crypto.randomUUID();

    const requestData = {
      request_id: requestId,
      recipient_account_number:
        formData.recipient_account_number,
      amount: String(formData.amount),
    };

    try {
      const result = await transferMoney(requestData);

      navigate("/transaction-result", {
        state: {
          success: true,
          type: "TRANSFER",
          amount: formData.amount,
          requestId,
          createdAt:
            result?.created_at || new Date().toISOString(),
          result,
        },
      });
    } catch (err) {
      setError(err.message || "이체에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main>
      <h1>계좌 이체</h1>

      {error && <p className="error-message">{error}</p>}

      <TransferForm
        onSubmit={handleTransfer}
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

export default TransferPage;