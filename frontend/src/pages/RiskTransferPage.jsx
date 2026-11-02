import { useEffect, useRef, useState } from "react";
import useWallet from "../hooks/useWallet";
import RiskTransferForm from "../components/RiskTransferForm";
import RiskTransferResult from "../components/RiskTransferResult";
import {
  analyzeRiskTransfer,
  USE_RISK_TRANSFER_MOCK,
} from "../api/riskTransferApi";
import {
  amountToUnits,
  executeRiskTransfer,
  getTokenInfo,
  isAddress,
  validateAnalysis,
} from "../utils/riskTransferContract";

const MOCK_ADDRESS = "0x1111111111111111111111111111111111111111";

const CONTRACT_ADDRESS =
  import.meta.env.VITE_RISK_TRANSFER_CONTRACT_ADDRESS || "";

const TOKEN_ADDRESS =
  import.meta.env.VITE_RISK_TRANSFER_TOKEN_ADDRESS || "";

const TARGET_CHAIN_ID = Number(
  import.meta.env.VITE_RISK_TRANSFER_CHAIN_ID || 31337
);

export default function RiskTransferPage({ accessToken = "" }) {
  const wallet = useWallet();
  const mock = USE_RISK_TRANSFER_MOCK;

  const [recipient, setRecipient] = useState("");
  const [amount, setAmount] = useState("");
  const [mockRiskLevel, setMockRiskLevel] = useState(0);
  const [tokenInfo, setTokenInfo] = useState(null);

  const [analysis, setAnalysis] = useState(null);
  const [expected, setExpected] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState("");

  const operation = useRef(0);
  const inFlight = useRef(false);

  const account = mock ? MOCK_ADDRESS : wallet.account;
  const chainId = mock ? TARGET_CHAIN_ID : wallet.chainId;

  // 계정·네트워크가 바뀌면 이전 분석 결과를 사용하지 않습니다.
  useEffect(() => {
    operation.current += 1;
    setAnalysis(null);
    setExpected(null);
    setResult(null);
    setError("");

    return () => {
      operation.current += 1;
    };
  }, [account, chainId]);

  useEffect(() => {
    let active = true;
    setTokenInfo(null);

    if (mock) {
      setTokenInfo({ decimals: 18, symbol: "TEST" });
      return;
    }

    if (!account || chainId !== TARGET_CHAIN_ID) return;

    getTokenInfo(TOKEN_ADDRESS)
      .then((info) => {
        if (active) setTokenInfo(info);
      })
      .catch((err) => {
        if (active) setError(err.message);
      });

    return () => {
      active = false;
    };
  }, [mock, account, chainId]);

  function invalidateResult() {
    operation.current += 1;
    setAnalysis(null);
    setExpected(null);
    setResult(null);
    setError("");
  }

  async function handleAnalyze(event) {
    event.preventDefault();

    if (inFlight.current) return;

    let payload;

    try {
      if (!account) throw new Error("먼저 지갑을 연결해 주세요.");

      if (chainId !== TARGET_CHAIN_ID) {
        throw new Error(`Chain ID ${TARGET_CHAIN_ID}로 연결해 주세요.`);
      }

      if (!tokenInfo) {
        throw new Error("토큰 정보를 확인한 뒤 다시 시도해 주세요.");
      }

      const address = recipient.trim();

      if (
        !isAddress(address) ||
        /^0x0{40}$/i.test(address)
      ) {
        throw new Error("올바른 수신 지갑 주소를 입력해 주세요.");
      }

      if (address.toLowerCase() === account.toLowerCase()) {
        throw new Error("본인 지갑과 다른 수신 주소를 입력해 주세요.");
      }

      if (!mock && !isAddress(CONTRACT_ADDRESS)) {
        throw new Error("송금 컨트랙트 주소 설정을 확인해 주세요.");
      }

      payload = {
        sender: account,
        recipient: address,
        amount: amountToUnits(amount.trim(), tokenInfo.decimals),
        chainId,
        verifyingContract: mock ? MOCK_ADDRESS : CONTRACT_ADDRESS,
      };
    } catch (err) {
      setError(err.message);
      return;
    }

    const current = ++operation.current;
    inFlight.current = true;
    setBusy(true);
    setStage("위험 분석 중");
    setError("");
    setAnalysis(null);
    setExpected(null);
    setResult(null);

    try {
      const data = await analyzeRiskTransfer(payload, {
        accessToken,
        mockRiskLevel,
      });

      validateAnalysis(data, payload, !mock);

      if (operation.current !== current) return;

      setExpected(payload);
      setAnalysis(data);
    } catch (err) {
      if (operation.current === current) setError(err.message);
    } finally {
      inFlight.current = false;
      setBusy(false);
      setStage("");
    }
  }

  async function handleExecute() {
    if (inFlight.current || !analysis || !expected) return;

    const current = ++operation.current;
    inFlight.current = true;
    setBusy(true);
    setError("");
    setStage("송금 준비 중");

    try {
      validateAnalysis(analysis, expected, !mock);

      if (analysis.transfer.riskLevel !== 0) {
        throw new Error("LOW 등급 거래만 송금할 수 있습니다.");
      }

      const transactionResult = mock
        ? { mock: true }
        : await executeRiskTransfer({
            analysis,
            expected,
            tokenAddress: TOKEN_ADDRESS,
            contractAddress: CONTRACT_ADDRESS,
            onStage: (message) => {
              if (operation.current === current) setStage(message);
            },
          });

      if (operation.current === current) {
        setResult(transactionResult);
      }
    } catch (err) {
      if (operation.current === current) {
        setError(
          err.code === 4001 || err.code === "ACTION_REJECTED"
            ? "지갑 요청을 취소했습니다."
            : err.shortMessage || err.message || "송금에 실패했습니다."
        );

        // 실패 후 재시도는 새로운 분석 결과로 진행합니다.
        setAnalysis(null);
        setExpected(null);
      }
    } finally {
      inFlight.current = false;
      setBusy(false);
      setStage("");
    }
  }

  return (
    <main style={{ maxWidth: 640, margin: "40px auto", padding: 20 }}>
      <h1>위험 분석 기반 토큰 송금</h1>

      {mock ? (
        <p>Mock 모드: 실제 지갑 승인과 토큰 송금은 실행하지 않습니다.</p>
      ) : (
        <div>
          <button
            onClick={wallet.connect}
            disabled={wallet.connecting || busy}
          >
            {wallet.connecting
              ? "지갑 연결 중..."
              : wallet.account
              ? "지갑 연결됨"
              : "MetaMask 연결"}
          </button>

          <p style={{ overflowWrap: "anywhere" }}>
            지갑: {wallet.account || "연결되지 않음"}
          </p>
          <p>Chain ID: {wallet.chainId ?? "-"}</p>
          {wallet.error && <p role="alert">{wallet.error}</p>}
        </div>
      )}

      {mock && (
        <label style={{ display: "block", marginBottom: 16 }}>
          테스트할 위험 등급{" "}
          <select
            value={mockRiskLevel}
            disabled={busy}
            onChange={(event) => {
              invalidateResult();
              setMockRiskLevel(Number(event.target.value));
            }}
          >
            <option value={0}>LOW</option>
            <option value={1}>MEDIUM</option>
            <option value={2}>HIGH</option>
            <option value={3}>CRITICAL</option>
          </select>
        </label>
      )}

      <RiskTransferForm
        recipient={recipient}
        amount={amount}
        onRecipientChange={(value) => {
          invalidateResult();
          setRecipient(value);
        }}
        onAmountChange={(value) => {
          invalidateResult();
          setAmount(value);
        }}
        onSubmit={handleAnalyze}
        disabled={
          busy ||
          !account ||
          chainId !== TARGET_CHAIN_ID ||
          !tokenInfo
        }
        symbol={tokenInfo?.symbol || "TOKEN"}
      />

      <RiskTransferResult
        analysis={analysis}
        result={result}
        busy={busy}
        stage={stage}
        error={error}
        mock={mock}
        onExecute={handleExecute}
      />
    </main>
  );
}