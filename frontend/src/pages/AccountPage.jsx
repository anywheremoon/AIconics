import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { deleteMyAccount, getMyAccount } from "../api/accountApi.js";
import { getTransactions } from "../api/transactionApi.js";
import AccountCard from "../components/AccountCard.jsx";
import TransactionHistoryTable from "../components/TransactionHistoryTable.jsx";

function AccountPage() {
  const navigate = useNavigate();
  const [account, setAccount] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const handleDeleteAccount = async () => {
  const confirmed = window.confirm(
    "정말 회원 탈퇴하시겠습니까? 탈퇴 후에는 되돌릴 수 없습니다."
  );

  if (!confirmed) {
    return;
  }

  try {
    await deleteMyAccount();
    localStorage.removeItem("access_token");

    alert("회원 탈퇴가 완료되었습니다.");
    navigate("/login");
  } catch (err) {
    alert(err.message || "회원 탈퇴에 실패했습니다.");
  }
};

  const loadAccount = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [accountData, transactionData] = await Promise.all([
        getMyAccount(),
        getTransactions(),
      ]);
      setAccount(accountData);
      setTransactions(transactionData.slice(0, 10));
    } catch (err) {
      setAccount(null);
      setTransactions([]);
      setError(err.message || "계좌 정보를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAccount();
  }, [loadAccount]);

  if (loading) {
    return (
      <main className="page-container">
        <h1 className="page-title">내 계좌</h1>
        <p className="loading-message">계좌 정보를 불러오는 중입니다...</p>
      </main>
    );
  }

  return (
    <main className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">내 계좌</h1>
          <p className="page-description">
            DB에 저장된 계좌 잔액과 최근 거래내역입니다.
          </p>
        </div>
        <button type="button" className="secondary-button" onClick={loadAccount}>
          새로고침
        </button>
      </div>

      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      {!error && account && (
        <>
          <AccountCard account={account} />

          <div className="account-actions">
            <button
              type="button"
              className="action-button"
              onClick={() => navigate("/transfer")}
              disabled={account.status !== "ACTIVE"}
            >
              송금
            </button>
            <button
              type="button"
              className="action-button"
              onClick={() => navigate("/withdraw")}
              disabled={account.status !== "ACTIVE"}
            >
              출금
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={handleDeleteAccount}
            >
              회원 탈퇴
            </button>
          </div>

          <section className="transaction-history">
            <h2>최근 거래내역</h2>
            <div className="table-container">
              <TransactionHistoryTable
                transactions={transactions}
                myAccountId={account.id}
                myAccountNumber={account.account_number}
              />
            </div>
          </section>
        </>
      )}
    </main>
  );
}

export default AccountPage;