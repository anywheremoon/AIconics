export default function RiskTransferForm({
  recipient,
  amount,
  onRecipientChange,
  onAmountChange,
  onSubmit,
  disabled,
  symbol,
}) {
  return (
    <form onSubmit={onSubmit} style={{ display: "grid", gap: 12 }}>
      <label>
        수신 지갑 주소
        <input
          value={recipient}
          onChange={(event) => onRecipientChange(event.target.value)}
          placeholder="0x..."
          required
          disabled={disabled}
          style={{ display: "block", width: "100%", padding: 10 }}
        />
      </label>

      <label>
        송금 금액 ({symbol})
        <input
          type="text"
          inputMode="decimal"
          value={amount}
          onChange={(event) => onAmountChange(event.target.value)}
          placeholder="예: 10"
          required
          disabled={disabled}
          style={{ display: "block", width: "100%", padding: 10 }}
        />
      </label>

      <button type="submit" disabled={disabled}>
        위험 분석 요청
      </button>
    </form>
  );
}