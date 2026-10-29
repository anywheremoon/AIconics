import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import RiskTransferPage from "./pages/RiskTransferPage";
import useWallet from "./hooks/useWallet";

function WalletTest() {
  const {
    account,
    chainId,
    connecting,
    error,
    connect,
  } = useWallet();

  return (
    <main
      style={{
        maxWidth: 640,
        margin: "40px auto",
        padding: 20,
        border: "1px solid #ddd",
        borderRadius: 12,
      }}
    >
      <h1>MetaMask 연결 테스트</h1>

      <p>
        이 화면은 실제 지갑 연결만 확인합니다.
        송금이나 토큰 사용 승인은 요청하지 않습니다.
      </p>

      <button
        type="button"
        onClick={connect}
        disabled={connecting}
        style={{ padding: "10px 16px" }}
      >
        {connecting ? "연결 요청 중..." : "MetaMask 연결 요청"}
      </button>

      <dl>
        <dt>연결 상태</dt>
        <dd>{account ? "연결됨" : "연결되지 않음"}</dd>

        <dt>지갑 주소</dt>
        <dd style={{ overflowWrap: "anywhere" }}>
          {account || "-"}
        </dd>

        <dt>Chain ID</dt>
        <dd>{chainId ?? "-"}</dd>
      </dl>

      {connecting && (
        <p role="status">
          MetaMask에서 연결 요청을 확인해 주세요.
        </p>
      )}

      {error && (
        <p role="alert" style={{ color: "#b91c1c" }}>
          {error}
        </p>
      )}
    </main>
  );
}

function TestApp() {
  const [screen, setScreen] = useState("wallet");

  return (
    <>
      <nav
        style={{
          display: "flex",
          gap: 12,
          justifyContent: "center",
          padding: 20,
        }}
      >
        <button onClick={() => setScreen("wallet")}>
          지갑 연결 테스트
        </button>

        <button onClick={() => setScreen("mock")}>
          Mock 송금 테스트
        </button>
      </nav>

      {screen === "wallet" ? (
        <WalletTest />
      ) : (
        <RiskTransferPage />
      )}
    </>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <TestApp />
  </React.StrictMode>
);