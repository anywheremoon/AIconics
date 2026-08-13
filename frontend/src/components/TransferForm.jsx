//이체 입력 폼을 구현함
import { useState } from "react";

function TransferForm({ onSubmit, loading = false }) {
  const [recipientAccountNumber, setRecipientAccountNumber] =
    useState("");
  const [amount, setAmount] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    const cleanAccountNumber = recipientAccountNumber.replace(
      /[^0-9]/g,
      ""
    );

    if (!cleanAccountNumber) {
      setError("수취 계좌번호를 입력해주세요.");
      return;
    }

    if (!amount || Number(amount) <= 0) {
      setError("이체 금액은 0원보다 커야 합니다.");
      return;
    }

    await onSubmit({
      recipient_account_number: cleanAccountNumber,
      amount,
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label>수취 계좌번호</label>
        <input
          type="text"
          value={recipientAccountNumber}
          onChange={(e) =>
            setRecipientAccountNumber(e.target.value)
          }
          placeholder="계좌번호 입력"
          disabled={loading}
        />
      </div>

      <div>
        <label>이체 금액</label>
        <input
          type="number"
          min="1"
          step="0.01"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="이체 금액"
          disabled={loading}
        />
      </div>

      {error && <p className="error-message">{error}</p>}

      <button type="submit" disabled={loading}>
        {loading ? "이체 처리 중..." : "이체하기"}
      </button>
    </form>
  );
}

export default TransferForm;