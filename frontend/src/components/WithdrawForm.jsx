//출금 입력 폼 구현
import { useState } from "react";

function WithdrawForm({ onSubmit, loading = false }) {
  const [amount, setAmount] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!amount || Number(amount) <= 0) {
      setError("출금 금액은 0원보다 커야 합니다.");
      return;
    }

    await onSubmit({
      amount,
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label>출금 금액</label>
        <input
          type="number"
          min="1"
          step="0.01"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="출금할 금액"
          disabled={loading}
        />
      </div>

      {error && <p className="error-message">{error}</p>}

      <button type="submit" disabled={loading}>
        {loading ? "출금 처리 중..." : "출금하기"}
      </button>
    </form>
  );
}

export default WithdrawForm;