import useWallet from "../hooks/useWallet";
import useEthVault from "../hooks/useEthVault";

import EthVaultForm from "../components/EthVaultForm";
import EthVaultStatus from "../components/EthVaultStatus";
import EthVaultTimeline from "../components/EthVaultTimeline";

import {
  getExecutionBlockReason,
  shortAddress,
} from "../utils/ethVaultContract";

const EXPECTED_CHAIN_ID = 31337;

export default function EthVaultPage() {
  const wallet = useWallet();
  const vault = useEthVault();

  const connected = Boolean(wallet.account);
  const correctNetwork = wallet.chainId === EXPECTED_CHAIN_ID;
  const walletReady = connected && correctNetwork;

  const myTransfers = vault.transfers.filter(
    (row) =>
      row.sender.toLowerCase() === wallet.account.toLowerCase()
  );

  async function createTransfer(input) {
    if (!walletReady) return false;

    return vault.create({
      ...input,
      sender: wallet.account,
    });
  }

  return (
    <main className="ev-page">
      <h1>ETH Risk Vault</h1>

      <p className="ev-notice">
        지갑 연결 정보를 사용하는 Mock 테스트 모드입니다.
        실제 ETH 예치·송금·환불이나 가스비 지출은 발생하지 않습니다.
      </p>

      <section className="ev-card">
        <h2>지갑 연결</h2>

        {connected ? (
          <>
            <p className="ev-id">
              연결 주소: {wallet.account}
            </p>

            <p>
              현재 체인 ID: {wallet.chainId ?? "확인 중"}
            </p>

            {correctNetwork ? (
              <p>로컬 테스트 네트워크에 연결되었습니다.</p>
            ) : (
              <p className="ev-error" role="alert">
                MetaMask에서 체인 ID {EXPECTED_CHAIN_ID}인
                로컬 테스트 네트워크로 변경해 주세요.
              </p>
            )}

            <p>
              계정을 변경하려면 MetaMask에서 계정을 전환해 주세요.
            </p>
          </>
        ) : (
          <button
            type="button"
            disabled={wallet.connecting}
            onClick={wallet.connect}
          >
            {wallet.connecting ? "연결 중..." : "MetaMask 연결"}
          </button>
        )}

        {wallet.error && (
          <p className="ev-error" role="alert">
            {wallet.error}
          </p>
        )}
      </section>

      {vault.error && (
        <p className="ev-error" role="alert">
          {vault.error}
        </p>
      )}

      <EthVaultForm
        busy={vault.busy || wallet.connecting}
        onSubmit={createTransfer}
        sender={wallet.account}
        walletReady={walletReady}
      />

      <div className="ev-heading">
        <h2>연결된 지갑의 Mock 거래</h2>

        <button
          type="button"
          disabled={vault.busy}
          onClick={vault.refresh}
        >
          새로고침
        </button>
      </div>

      {!connected && (
        <p>지갑을 연결하면 해당 주소의 Mock 거래가 표시됩니다.</p>
      )}

      {connected && myTransfers.length === 0 && (
        <p>이 지갑으로 생성한 Mock 거래가 없습니다.</p>
      )}

      {myTransfers.map((row) => {
        const blockReason = getExecutionBlockReason(row, vault.now);
        const pending = row.status === "PENDING";
        const expired = vault.now >= row.expiresAt;

        return (
          <article className="ev-card" key={row.id}>
            <EthVaultStatus transfer={row} />

            <p className="ev-id">
              요청 ID: {row.id}
            </p>

            <p>
              {shortAddress(row.sender)}
              {" → "}
              {shortAddress(row.recipient)}
            </p>

            <strong>{row.amount} ETH</strong>

            <EthVaultTimeline
              transfer={row}
              now={vault.now}
            />

            <div className="ev-actions">
              {pending &&
                !expired &&
                row.riskLevel === "MEDIUM" &&
                !row.authCompleted && (
                  <button
                    type="button"
                    disabled={vault.busy || !walletReady}
                    onClick={() => vault.completeAuth(row.id)}
                  >
                    Mock 추가 인증 완료
                  </button>
                )}

              {pending && (
                <button
                  type="button"
                  disabled={
                    vault.busy ||
                    !walletReady ||
                    Boolean(blockReason)
                  }
                  onClick={() => vault.execute(row.id)}
                >
                  {blockReason || "Mock 송금 실행"}
                </button>
              )}

              {pending && expired && (
                <button
                  type="button"
                  disabled={vault.busy || !walletReady}
                  onClick={() => vault.cancelExpired(row.id)}
                >
                  만료 취소 및 Mock 환불
                </button>
              )}
            </div>
          </article>
        );
      })}
    </main>
  );
}