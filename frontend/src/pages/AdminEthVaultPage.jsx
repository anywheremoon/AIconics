import useEthVault from "../hooks/useEthVault";
import EthVaultStatus from "../components/EthVaultStatus";
import EthVaultTimeline from "../components/EthVaultTimeline";

export default function AdminEthVaultPage() {
  const vault = useEthVault();

  return (
    <main className="ev-page">
      <h1>ETH Vault 관리자</h1>

      <p className="ev-notice">
        Mock 관리자 테스트 화면입니다. 실제 승인이나 환불은 발생하지 않습니다.
      </p>

      {vault.error && (
        <p className="ev-error" role="alert">{vault.error}</p>
      )}

      <button disabled={vault.busy} onClick={vault.refresh}>
        목록 새로고침
      </button>

      {vault.transfers.length === 0 && <p>거래가 없습니다.</p>}

      {vault.transfers.map((row) => {
        const pending = row.status === "PENDING";
        const expired = vault.now >= row.expiresAt;

        return (
          <article className="ev-card" key={row.id}>
            <EthVaultStatus transfer={row} />

            <p className="ev-id">요청 ID: {row.id}</p>
            <p className="ev-id">송신: {row.sender}</p>
            <p className="ev-id">수신: {row.recipient}</p>
            <strong>{row.amount} ETH</strong>

            <EthVaultTimeline transfer={row} now={vault.now} />

            {pending && !expired && (
              <div className="ev-actions">
                {row.riskLevel === "HIGH" && !row.adminApproved && (
                  <button
                    disabled={vault.busy}
                    onClick={() => vault.approve(row.id)}
                  >
                    Mock 승인
                  </button>
                )}

                <button
                  className="ev-danger"
                  disabled={vault.busy}
                  onClick={() => vault.reject(row.id)}
                >
                  Mock 거절 및 환불
                </button>
              </div>
            )}

            {pending && expired && (
              <button
                disabled={vault.busy}
                onClick={() => vault.cancelExpired(row.id)}
              >
                만료 취소 및 Mock 환불
              </button>
            )}
          </article>
        );
      })}
    </main>
  );
}