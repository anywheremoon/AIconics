import { useState } from "react";

export default function EthVaultForm({
  busy,
  onSubmit,
  sender,
  walletReady,
}) {
  const [recipient, setRecipient] = useState(
    "0x2222222222222222222222222222222222222222"
  );
  const [amount, setAmount] = useState("0.01");
  const [riskLevel, setRiskLevel] = useState("LOW");

  async function submit(event) {
    event.preventDefault();

    if (!walletReady || busy) return;

    await onSubmit({
      sender,
      recipient: recipient.trim(),
      amount: amount.trim(),
      riskLevel,
    });
  }

  return (
    <form className="ev-card ev-form" onSubmit={submit}>
      <h2>ETH 송금 요청 · Mock</h2>

      <label>
        연결된 송신 지갑
        <input
          value={sender || ""}
          placeholder="먼저 지갑을 연결해 주세요."
          readOnly
        />
      </label>

      <label>
        수신 주소
        <input
          value={recipient}
          onChange={(event) => setRecipient(event.target.value)}
          required
        />
      </label>

      <label>
        금액 · ETH
        <input
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
          inputMode="decimal"
          required
        />
      </label>

      <label>
        테스트 위험 등급
        <select
          value={riskLevel}
          onChange={(event) => setRiskLevel(event.target.value)}
        >
          {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((level) => (
            <option key={level} value={level}>
              {level}
            </option>
          ))}
        </select>
      </label>

      <button
        disabled={busy || !walletReady}
        type="submit"
      >
        {busy ? "처리 중..." : "Mock 송금 요청"}
      </button>
    </form>
  );
}