import { useState } from "react";

function TransferForm({ onSubmit, loading = false, availableBalance }) {
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

    const numericAmount = Number(amount);

    if (!amount || !Number.isFinite(numericAmount) || numericAmount <= 0) {
      setError("이체 금액은 0원보다 커야 합니다.");
      return;
    }

    if (
      availableBalance !== undefined &&
      numericAmount > Number(availableBalance)
    ) {
      setError("송금 금액이 현재 잔액을 초과합니다.");
      return;
    }

    await onSubmit({
      recipient_account_number: cleanAccountNumber,
      amount,
    });
  };

  return (
    <form className="transaction-form" onSubmit={handleSubmit}>
      <div className="form-field">
        <label htmlFor="transfer-account-number">수취 계좌번호</label>
        <input
          id="transfer-account-number"
          type="text"
          inputMode="numeric"
          value={recipientAccountNumber}
          onChange={(e) =>
            setRecipientAccountNumber(e.target.value)
          }
          placeholder="계좌번호 입력"
          disabled={loading}
        />
      </div>

      <div className="form-field">
        <label htmlFor="transfer-amount">송금 금액</label>
        <input
          id="transfer-amount"
          type="number"
          min="0.01"
          step="0.01"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="송금할 금액"
          disabled={loading}
        />
      </div>

      {error && <p className="error-message" role="alert">{error}</p>}

      <button type="submit" className="action-button" disabled={loading}>
        {loading ? "송금 처리 중..." : "송금하기"}
      </button>
    </form>
  );
}

export default TransferForm;