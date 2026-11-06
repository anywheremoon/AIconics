import { useCallback, useEffect, useRef, useState } from "react";
import { formatEther } from "ethers";

import { useAuth } from "../auth/AuthContext";
import useWallet from "../hooks/useWallet";
import {
  approveLiveTransfer,
  readLiveTransfer,
} from "../utils/ethVaultLive";

const BASE = (
  import.meta.env.VITE_API_BASE_URL || ""
).replace(/\/$/, "");

const CHAIN = Number(
  import.meta.env.VITE_ETH_VAULT_CHAIN_ID
);

const ADDRESS = (
  import.meta.env.VITE_ETH_VAULT_CONTRACT_ADDRESS || ""
).toLowerCase();

const STATES = [
  "REQUESTED",
  "ANALYZED",
  "AUTHENTICATED",
  "APPROVED",
  "EXECUTED",
  "REJECTED",
  "CANCELLED",
];

export default function AdminEthVaultPage() {
  const { token, user } = useAuth();
  const wallet = useWallet();

  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const locked = useRef(false);
  const isAdmin = user?.role === "ADMIN";
  const walletReady = Boolean(
    wallet.account &&
    wallet.chainId === CHAIN &&
    CHAIN === 31337
  );

  const load = useCallback(async () => {
    if (!token || !isAdmin) {
      setRows([]);
      return;
    }

    const response = await fetch(
      `${BASE}/api/eth-vault/admin/pending`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/json",
        },
      }
    );

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      throw new Error(
        typeof data?.detail === "string"
          ? data.detail
          : `관리자 목록 조회 실패: ${response.status}`
      );
    }

    if (!Array.isArray(data)) {
      throw new Error("관리자 목록 응답 형식이 잘못됐습니다.");
    }

    const next = await Promise.all(
      data.map(async row => {
        try {
          if (
            Number(row.chain_id) !== CHAIN ||
            row.verifying_contract.toLowerCase() !== ADDRESS
          ) {
            throw new Error("현재 배포와 다른 거래입니다.");
          }

          const live = await readLiveTransfer(row.request_id);

          if (
            live.sender.toLowerCase() !==
              row.sender_address.toLowerCase() ||
            live.recipient.toLowerCase() !==
              row.recipient_address.toLowerCase() ||
            live.riskLevel !== 2 ||
            !live.requiresAdminApproval
          ) {
            throw new Error("DB와 온체인 거래 정보가 다릅니다.");
          }

          // 실행 후 컨트랙트의 amount는 0으로 바뀐다.
          if (
            [0, 1, 2, 3].includes(live.status) &&
            live.amountWei !== String(row.amount_wei)
          ) {
            throw new Error("DB와 온체인 금액이 다릅니다.");
          }

          return { ...row, live };
        } catch (err) {
          return {
            ...row,
            readError: err.shortMessage || err.message,
          };
        }
      })
    );

    setRows(next);
  }, [token, isAdmin]);

  useEffect(() => {
    let active = true;

    load().catch(err => {
      if (active) setError(err.message);
    });

    return () => {
      active = false;
    };
  }, [load]);

  async function run(action) {
    if (locked.current) return;

    locked.current = true;
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
      locked.current = false;
      setBusy(false);
    }
  }

  async function approve(row) {
    await run(async () => {
      if (!isAdmin) {
        throw new Error("웹 관리자 로그인이 필요합니다.");
      }

      if (!walletReady) {
        throw new Error(
          "MetaMask를 AIconics Local에 연결하세요."
        );
      }

      const hash = await approveLiveTransfer(row.request_id);
      setMessage(`온체인 관리자 승인 완료. TX: ${hash}`);
      await load();
    });
  }

  if (!isAdmin) {
    return (
      <main className="ev-page">
        <h1>ETH Vault 관리자</h1>
        <p>ADMIN 계정으로 로그인해야 합니다.</p>
      </main>
    );
  }

  return (
    <main className="ev-page">
      <h1>ETH Vault 관리자 · 로컬 체인</h1>

      <p>
        실제 승인은 컨트랙트 소유자 지갑으로 서명합니다.
      </p>

      <section className="ev-card">
        <button
          type="button"
          disabled={busy || wallet.connecting}
          onClick={wallet.connect}
        >
          MetaMask 연결 확인
        </button>

        <p className="ev-id">
          연결 지갑: {wallet.account || "미연결"}
        </p>

        <p>체인 ID: {wallet.chainId ?? "미확인"}</p>
        <p className="ev-id">컨트랙트: {ADDRESS}</p>
      </section>

      {(error || wallet.error) && (
        <p className="ev-error" role="alert">
          {error || wallet.error}
        </p>
      )}

      {message && <p role="status">{message}</p>}

      <button
        type="button"
        disabled={busy}
        onClick={() => run(load)}
      >
        목록 새로고침
      </button>

      {!busy && rows.length === 0 && (
        <p>현재 배포의 관리자 검토 거래가 없습니다.</p>
      )}

      {rows.map(row => {
        const live = row.live;

        const canApprove = Boolean(
          live &&
          live.status === 2 &&
          live.authCompleted &&
          !live.adminApproved &&
          !row.readError
        );

        return (
          <article className="ev-card" key={row.request_id}>
            <h2>HIGH · {row.risk_score}점</h2>

            <p className="ev-id">
              요청 ID: {row.request_id}
            </p>

            <p className="ev-id">
              송신: {row.sender_address}
            </p>

            <p className="ev-id">
              수신: {row.recipient_address}
            </p>

            <strong>
              {formatEther(String(row.amount_wei))} ETH
            </strong>

            {row.readError && (
              <p className="ev-error">{row.readError}</p>
            )}

            {live && (
              <>
                <p>온체인 상태: {STATES[live.status]}</p>
                <p>
                  추가 인증: {live.authCompleted ? "완료" : "미완료"}
                </p>
                <p>
                  관리자 승인: {live.adminApproved ? "완료" : "미완료"}
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

            <button
              type="button"
              disabled={busy || !walletReady || !canApprove}
              onClick={() => approve(row)}
            >
              {live?.adminApproved
                ? "온체인 승인 완료"
                : "MetaMask로 HIGH 승인"}
            </button>
          </article>
        );
      })}
    </main>
  );
}