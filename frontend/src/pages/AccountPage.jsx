//계좌 화면 구현
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getMyAccount } from "../api/accountApi.js";
import { getTransactions } from "../api/transactionApi.js";

import AccountCard from "../components/AccountCard.jsx";
import TransactionHistoryTable from "../components/TransactionHistoryTable.jsx";

function AccountPage() {
  const navigate = useNavigate();

  const [account, setAccount] = useState(null);
  const [transactions, setTransactions] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [accountData, transactionData] =
        await Promise.all([
          getMyAccount(),
          getTransactions(),
        ]);

      setAccount(accountData);

      setTransactions(
        Array.isArray(transactionData)
          ? transactionData
          : transactionData?.transactions || []
      );
    } catch (err) {
      setError(err.message || "계좌 조회에 실패했습니다.");

      if (
        err.message?.includes("로그인") ||
        err.message?.includes("만료")
      ) {
        navigate("/login");
      }
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    if (!localStorage.getItem("access_token")) {
      navigate("/login");
      return;
    }

    loadData();
  }, [loadData, navigate]);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    navigate("/login");
  };

  if (loading) {
    return <p>계좌 정보를 불러오는 중입니다...</p>;
  }

  return (
    <main>
      <h1>내 계좌</h1>

      {error && <p className="error-message">{error}</p>}

      <AccountCard account={account} />

      <div>
        <button onClick={() => navigate("/transfer")}>
          이체
        </button>

        <button onClick={() => navigate("/withdraw")}>
          출금
        </button>

        <button onClick={loadData}>
          새로고침
        </button>

        <button onClick={handleLogout}>
          로그아웃
        </button>
      </div>

      <section>
        <h2>최근 거래 내역</h2>

        <TransactionHistoryTable
          transactions={transactions}
          myAccountId={account?.id}
          myAccountNumber={account?.account_number}
        />
      </section>
    </main>
  );
}

export default AccountPage;