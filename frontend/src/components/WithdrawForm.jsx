//출금 입력 폼 구현
import { useState } from "react";

function WithdrawForm({ onSubmit, loading = false, availableBalance }) {
  const [amount, setAmount] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    const numericAmount = Number(amount);

    if (!amount || !Number.isFinite(numericAmount) || numericAmount <= 0) {
      setError("출금 금액은 0원보다 커야 합니다.");
      return;
    }

    if (
      availableBalance !== undefined &&
      numericAmount > Number(availableBalance)
    ) {
      setError("출금 금액이 현재 잔액을 초과합니다.");
      return;
    }

    await onSubmit({
      amount,
    });
  };

  return (
    <form className="transaction-form" onSubmit={handleSubmit}>
      <div className="form-field">
        <label htmlFor="withdraw-amount">출금 금액</label>
        <input
          id="withdraw-amount"
          type="number"
          min="0.01"
          step="0.01"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="출금할 금액"
          disabled={loading}
        />
      </div>

      {error && <p className="error-message" role="alert">{error}</p>}

      <button type="submit" className="action-button" disabled={loading}>
        {loading ? "출금 처리 중..." : "출금하기"}
      </button>
    </form>
  );
}

export default WithdrawForm;
