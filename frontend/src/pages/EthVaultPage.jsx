import { useEffect, useState } from "react";
import { formatEther } from "ethers";

import { useAuth } from "../auth/AuthContext";
import useWallet from "../hooks/useWallet";

import {
  requestLiveTransfer,
  readLiveTransfer,
  executeLiveTransfer,
} from "../utils/ethVaultLive";

const BASE = (
  import.meta.env.VITE_API_BASE_URL || ""
).replace(/\/$/, "");

const DEPLOYMENT =
  import.meta.env.VITE_ETH_VAULT_DEPLOYMENT_ID;

const ADDRESS =
  import.meta.env.VITE_ETH_VAULT_CONTRACT_ADDRESS;

const CHAIN = Number(
  import.meta.env.VITE_ETH_VAULT_CHAIN_ID
);

const LEVELS = [
  "LOW",
  "MEDIUM",
  "HIGH",
  "CRITICAL",
];

const STATES = [
  "REQUESTED",
  "ANALYZED",
  "AUTHENTICATED",
  "APPROVED",
  "EXECUTED",
  "REJECTED",
  "CANCELLED",
];


export default function EthVaultPage() {
  const { token, sessionId, user } = useAuth();
  const wallet = useWallet();

  const [recipient, setRecipient] = useState("");
  const [amount, setAmount] = useState("0.001");
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [verificationCodes, setVerificationCodes] =
    useState({});

  const key =
    `vault_live:${DEPLOYMENT}:${CHAIN}:${ADDRESS}:${user?.id}`;

  const ready = Boolean(
    token && sessionId && user
  );

  const walletReady = Boolean(
    wallet.account && wallet.chainId === CHAIN && CHAIN === 31337
  );

  useEffect(() => {
    setRows([]);
    setError("");
    setMessage("");
    setVerificationCodes({});

    if (!ready) return;

    try {
      const saved = JSON.parse(
        localStorage.getItem(key) || "[]"
      );

      if (!Array.isArray(saved)) {
        throw new Error("Invalid saved transfers");
      }

      setRows(saved);
    } catch {
      setError(
        "저장된 예치 목록을 읽지 못했습니다. " +
        "새로 예치하지 말고 기존 거래를 확인하세요."
      );
    }
  }, [key, ready]);

  function save(next) {
    localStorage.setItem(
      key,
      JSON.stringify(next)
    );
    setRows(next);
  }

  function patch(id, values) {
    const current = JSON.parse(
      localStorage.getItem(key) || "[]"
    );

    save(
      current.map(row =>
        row.requestId === id
          ? { ...row, ...values }
          : row
      )
    );
  }

  async function api(path, body) {
    if (!ready) {
      throw new Error("로그인이 필요합니다.");
    }

    const response = await fetch(
      `${BASE}/api/eth-vault${path}`,
      {
        method: body === undefined ? "GET" : "POST",

        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },

        ...(body === undefined
          ? {}
          : { body: JSON.stringify(body) }),
      }
    );

    const data = await response
      .json()
      .catch(() => null);

    if (!response.ok) {
      const failure = new Error(
        typeof data?.detail === "string"
          ? data.detail
          : `API 오류: ${response.status}`
      );

      failure.status = response.status;
      throw failure;
    }

    return data;
  }

  async function run(action) {
    if (busy) return;

    setBusy(true);
    setError("");
    setMessage("");

    try {
      await action();
    } catch (err) {
      setError(
        err.shortMessage ||
        err.message ||
        "처리 중 오류가 발생했습니다."
      );
    } finally {
      setBusy(false);
    }
  }

  async function inspect(row) {
    const live = await readLiveTransfer(
      row.requestId
    );

    patch(row.requestId, { live });
    return live;
  }

  async function deposit(event) {
    event.preventDefault();

    if (!ready || !walletReady) return;

    await run(async () => {
      // 저장 목록이 손상됐다면 예치 전에 중단한다.
      const current = JSON.parse(
        localStorage.getItem(key) || "[]"
      );

      if (!Array.isArray(current)) {
        throw new Error(
          "저장된 예치 목록을 확인해야 합니다."
        );
      }

      const row = await requestLiveTransfer({
        sender: wallet.account,
        recipient: recipient.trim(),
        amount: amount.trim(),
      });

      // 분석 API 호출 전에 예치 영수증을 보관한다.
      try {
        save([row, ...current]);
      } catch {
        throw new Error(
          "예치는 성공했지만 목록 저장에 실패했습니다. " +
          "재예치하지 마세요. " +
          `요청 ID: ${row.requestId}, ` +
          `TX: ${row.depositTxHash}`
        );
      }

      setMessage(
        "예치 완료. 아래 거래에서 체인 상태 조회와 " +
        "위험 분석을 진행하세요."
      );
    });
  }

  async function analyze(row) {
    await run(async () => {
      let transfer;

      try {
        transfer = await api(
          `/requests/${row.requestId}`
        );
      } catch (err) {
        // 본인 거래가 없을 때만 신규 분석을 요청한다.
        if (err.status !== 404) {
          throw err;
        }
      }

      if (!transfer) {
        const result = await api("/analyze", {
          request_id: row.requestId,
          session_id: sessionId,
          sender_address: row.sender,
          recipient_address: row.recipient,
          amount_wei: row.amountWei,
          chain_id: row.chainId,
          verifying_contract: row.verifyingContract,
        });

        transfer = result.transfer;
      }

      patch(row.requestId, {
        analysis: transfer,
      });

      await inspect(row);

      setMessage(
        "분석 결과를 확인했습니다. " +
        "온체인 제출 전이라면 서명 만료 전에 제출하세요."
      );
    });
  }

  async function submit(row) {
    await run(async () => {
      const result = await api(
        `/requests/${row.requestId}/submit-risk`,
        {}
      );

      patch(row.requestId, {
        riskTxHash: result.transaction_hash,
      });

      await inspect(row);

      setMessage(
        "위험 분석 결과가 체인에 제출됐습니다."
      );
    });
  }

  async function requestEmailCode(row) {
    await run(async () => {
      const result = await api(
        `/requests/${row.requestId}/verification/request`,
        {
          session_id: sessionId,
        }
      );

      setMessage(
        `${result.delivery_destination}로 인증번호를 보냈습니다. ` +
        `${result.expires_in_seconds}초 안에 입력하세요. ` +
        `재요청은 ${result.retry_after_seconds}초 후 가능합니다.`
      );
    });
  }

  async function confirmEmailCode(row) {
    await run(async () => {
      const code = (
        verificationCodes[row.requestId] || ""
      ).trim();

      if (!/^[0-9]{6}$/.test(code)) {
        throw new Error(
          "이메일로 받은 인증번호 6자리를 입력하세요."
        );
      }

      const result = await api(
        `/requests/${row.requestId}/verification/confirm`,
        {
          session_id: sessionId,
          code,
        }
      );

      patch(row.requestId, {
        authTxHash: result.auth_transaction_hash,
      });

      setVerificationCodes(current => ({
        ...current,
        [row.requestId]: "",
      }));

      await inspect(row);

      setMessage(
        "이메일 확인과 온체인 추가 인증이 완료됐습니다."
      );
    });
  }

  async function execute(row) {
    await run(async () => {
      const hash = await executeLiveTransfer(
        row.requestId
      );

      patch(row.requestId, {
        executionTxHash: hash,
      });

      await inspect(row);
      setMessage(`송금 완료: ${hash}`);
    });
  }

  const mine = rows.filter(row =>
    row.sender?.toLowerCase() ===
    wallet.account.toLowerCase()
  );

  return (
    <main className="ev-page">
      <h1>ETH Risk Vault · 로컬 체인</h1>

      <p>
        MetaMask로 테스트 ETH를 실제 예치·송금합니다.
      </p>

      <section className="ev-card">
        <button
          type="button"
          disabled={busy || wallet.connecting}
          onClick={wallet.connect}
        >
          {wallet.connecting
            ? "연결 중..."
            : wallet.account
              ? "MetaMask 연결 확인"
              : "MetaMask 연결"}
        </button>

        <p>
          지갑: {wallet.account || "미연결"}
        </p>

        <p>
          체인 ID: {wallet.chainId ?? "미확인"}
        </p>

        <p className="ev-id">
          컨트랙트: {ADDRESS}
        </p>

        {!walletReady && (
          <p className="ev-error">
            AIconics Local(31337)에 연결하세요.
          </p>
        )}

        {!ready && (
          <p className="ev-error">
            로그인과 필요한 이메일 인증을 완료하세요.
          </p>
        )}
      </section>

      {(error || wallet.error) && (
        <p role="alert" className="ev-error">
          {error || wallet.error}
        </p>
      )}

      {message && (
        <p role="status">
          {message}
        </p>
      )}

      <form
        className="ev-card ev-form"
        onSubmit={deposit}
      >
        <h2>새 ETH 예치 요청</h2>

        <label>
          수신 주소
          <input
            required
            value={recipient}
            onChange={event =>
              setRecipient(event.target.value)
            }
          />
        </label>

        <label>
          금액 · ETH
          <input
            required
            value={amount}
            inputMode="decimal"
            onChange={event =>
              setAmount(event.target.value)
            }
          />
        </label>

        <button
          type="submit"
          disabled={
            busy || !ready || !walletReady
          }
        >
          {busy
            ? "처리 중..."
            : "MetaMask로 예치"}
        </button>
      </form>

      <h2>
        이 브라우저에 저장한 예치 영수증
      </h2>

      <p>
        거래의 실제 상태는 각 항목의
        ‘체인 상태 조회’로 확인하세요.
      </p>

      {walletReady && mine.length === 0 && (
        <p>
          현재 지갑으로 저장한 예치 영수증이 없습니다.
        </p>
      )}

      {mine.map(row => {
        const live = row.live;

        const analyzed = Boolean(
          live && live.status !== 0
        );

        const finished = Boolean(
          live && [4, 5, 6].includes(live.status)
        );

        const authBlocked = Boolean(
          live?.requiresAuth &&
          !live.authCompleted
        );

        const adminBlocked = Boolean(
          live?.requiresAdminApproval &&
          !live.adminApproved
        );

        return (
          <article
            className="ev-card"
            key={row.requestId}
          >
            <p className="ev-id">
              요청 ID: {row.requestId}
            </p>

            <p className="ev-id">
              수신: {row.recipient}
            </p>

            <strong>
              {formatEther(row.amountWei)} ETH
            </strong>

            <p className="ev-id">
              예치 TX: {row.depositTxHash}
            </p>

            {row.analysis && (
              <p>
                백엔드 분석:
                {" "}{row.analysis.risk_level}
                {" / "}{row.analysis.risk_score}점
              </p>
            )}

            {live && (
              <>
                <p>
                  온체인 상태:
                  {" "}{STATES[live.status]}
                </p>

                {analyzed && (
                  <p>
                    온체인 위험도:
                    {" "}{LEVELS[live.riskLevel]}
                  </p>
                )}

                <p>
                  인증 완료:
                  {" "}{live.authCompleted ? "예" : "아니오"}
                </p>

                <p>
                  관리자 승인:
                  {" "}{live.adminApproved ? "예" : "아니오"}
                </p>

                {live.timelockUntil > 0 && (
                  <p>
                    실행 가능 시각:
                    {" "}
                    {new Date(
                      live.timelockUntil * 1000
                    ).toLocaleString()}
                  </p>
                )}
              </>
            )}

            <div className="ev-actions">
              <button
                type="button"
                disabled={busy || !walletReady}
                onClick={() =>
                  run(() => inspect(row))
                }
              >
                체인 상태 조회
              </button>

              <button
                type="button"
                disabled={
                  busy ||
                  !ready ||
                  !walletReady ||
                  analyzed
                }
                onClick={() => analyze(row)}
              >
                위험 분석 / 기존 결과 조회
              </button>

              <button
                type="button"
                disabled={
                  busy ||
                  !ready ||
                  !walletReady ||
                  !row.analysis ||
                  analyzed
                }
                onClick={() => submit(row)}
              >
                {row.analysis?.risk_level === "CRITICAL"
                  ? "CRITICAL 결과 제출 및 자동 환불"
                  : "분석 결과 온체인 제출"}
              </button>

              <button
                type="button"
                disabled={
                  busy ||
                  !ready ||
                  !walletReady ||
                  !analyzed ||
                  finished ||
                  authBlocked ||
                  adminBlocked
                }
                onClick={() => execute(row)}
              >
                MetaMask로 송금 실행
              </button>
            </div>

            {authBlocked && !finished && (
              <section>
                <h3>거래 추가 인증</h3>

                <p>
                  이 거래에 대한 이메일 인증이 필요합니다.
                </p>

                <div className="ev-actions">
                  <button
                    type="button"
                    disabled={
                      busy || !ready || !walletReady
                    }
                    onClick={() =>
                      requestEmailCode(row)
                    }
                  >
                    이메일 인증번호 요청
                  </button>
                </div>

                <label>
                  이메일 인증번호
                  <input
                    aria-label="거래 이메일 인증번호"
                    placeholder="인증번호 6자리"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={6}
                    value={
                      verificationCodes[row.requestId] || ""
                    }
                    onChange={event => {
                      const value = event.target.value;

                      setVerificationCodes(current => ({
                        ...current,
                        [row.requestId]: value,
                      }));
                    }}
                  />
                </label>

                <div className="ev-actions">
                  <button
                    type="button"
                    disabled={
                      busy || !ready || !walletReady
                    }
                    onClick={() =>
                      confirmEmailCode(row)
                    }
                  >
                    인증 확인 및 온체인 반영
                  </button>
                </div>
              </section>
            )}

            {adminBlocked && !finished && (
              <p>
                온체인 관리자 승인이 필요합니다.
              </p>
            )}

            {row.analysis?.risk_level === "CRITICAL" &&
              !finished && (
                <p className="ev-error">
                  송금이 차단된 거래입니다.
                  CRITICAL 결과를 체인에 제출하면 예치 ETH가
                  원래 송신 지갑으로 자동 환불됩니다.
                </p>
              )}

            {live?.status === 5 && (
              <p>
                온체인 거절 처리 완료.
                환불 금액은 거래 영수증과 잔액으로 확인하세요.
              </p>
            )}

            {row.riskTxHash && (
              <p className="ev-id">
                분석 제출 TX: {row.riskTxHash}
              </p>
            )}

            {row.authTxHash && (
              <p className="ev-id">
                추가 인증 TX: {row.authTxHash}
              </p>
            )}

            {row.executionTxHash && (
              <p className="ev-id">
                송금 TX: {row.executionTxHash}
              </p>
            )}
          </article>
        );
      })}
    </main>
  );
}