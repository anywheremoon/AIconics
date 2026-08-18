//계좌 화면 구현
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getMyAccount } from "../api/accountApi.js";
import { useAuth } from "../auth/AuthContext.jsx";

function AccountPage() {
  const navigate = useNavigate();

  const { user, logout } = useAuth();

  const [account, setAccount] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadAccount() {
      setLoading(true);
      setError("");

      try {
        const data = await getMyAccount();

        if (!cancelled) {
          setAccount(data);
        }
      } catch (err) {
        if (!cancelled) {
          setAccount(null);

          setError(
            err.message ||
              "계좌 정보를 불러오지 못했습니다."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadAccount();

    return () => {
      cancelled = true;
    };
  }, []);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const handleTransfer = () => {
    navigate("/transfer");
  };

  const handleWithdraw = () => {
    navigate("/withdraw");
  };

  if (loading) {
    return (
      <main className="page-container">
        <h1 className="page-title">
          내 계좌
        </h1>

        <p>
          계좌 정보를 불러오는 중입니다...
        </p>
      </main>
    );
  }

  return (
    <main className="page-container">
      <div className="account-page">
        <div className="account-header">
          <div>
            <h1 className="page-title">
              내 계좌
            </h1>

            {user && (
              <p className="page-description">
                {user.username}님의 계좌입니다.
              </p>
            )}
          </div>
        </div>

        {error && (
          <div
            className="error-message"
            role="alert"
          >
            {error}
          </div>
        )}

        {!error && account && (
          <>
            <section className="account-card">
              <div className="account-info-row">
                <span className="account-label">
                  계좌번호
                </span>

                <strong className="account-value">
                  {account.account_number}
                </strong>
              </div>

              <div className="account-info-row">
                <span className="account-label">
                  잔액
                </span>

                <strong className="account-balance">
                  {Number(
                    account.balance ?? 0
                  ).toLocaleString()}
                  원
                </strong>
              </div>

              {account.opened_at && (
                <div className="account-info-row">
                  <span className="account-label">
                    개설일
                  </span>

                  <span className="account-value">
                    {new Date(
                      account.opened_at
                    ).toLocaleString()}
                  </span>
                </div>
              )}
            </section>

            <div className="account-actions">
              <button
                type="button"
                className="action-button"
                onClick={handleTransfer}
              >
                송금
              </button>

              <button
                type="button"
                className="action-button"
                onClick={handleWithdraw}
              >
                출금
              </button>
            </div>
          </>
        )}

        {!loading &&
          !error &&
          !account && (
            <p>
              계좌 정보를 찾을 수 없습니다.
            </p>
          )}

        <div className="account-footer">
          <button
            type="button"
            className="action-button"
            onClick={handleLogout}
          >
            로그아웃
          </button>
        </div>
      </div>
    </main>
  );
}

export default AccountPage;