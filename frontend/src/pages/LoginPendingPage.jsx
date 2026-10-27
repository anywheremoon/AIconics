import {
  Navigate,
  useNavigate,
} from "react-router-dom";

import { LOGIN_STATUS } from "../api/authApi.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { useLoginGuidance } from "../hooks/useLoginGuidance.js";
import AuthLoading from "../components/AuthLoading.jsx";


function LoginPendingPage() {
  const navigate = useNavigate();

  const {
    loading,
    isAuthenticated,
    user,
    pendingLogin,
    clearPendingLogin,
  } = useAuth();

  const {
    guidance,
    guidanceLoading,
  } = useLoginGuidance(pendingLogin);

  const handleBackToLogin = () => {
    clearPendingLogin();
    navigate("/login", { replace: true });
  };

  if (loading) {
    return <AuthLoading />;
  }

  if (isAuthenticated) {
    return (
      <Navigate
        to={
          user.role === "ADMIN"
            ? "/dashboard"
            : "/account"
        }
        replace
      />
    );
  }

  if (
    pendingLogin?.login_status ===
    LOGIN_STATUS.REQUIRE_VERIFICATION
  ) {
    return (
      <Navigate
        to="/additional-verification"
        replace
      />
    );
  }

  if (
    pendingLogin?.login_status !==
    LOGIN_STATUS.PENDING_REVIEW
  ) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-header">
          <p className="auth-eyebrow">
            LOGIN PENDING
          </p>

          <h1 className="auth-title">
            로그인 보류
          </h1>

          <p className="auth-description">
            {guidance.summary}
          </p>

          <p className="auth-description">
            현재는 계좌와 거래 기능을 이용할 수 없습니다.
          </p>
        </div>

        <div>
          <p>
            {guidance.next_action}
          </p>

          {guidanceLoading && (
            <p role="status">
              보안 안내를 확인하고 있습니다...
            </p>
          )}
        </div>

        <div className="auth-footer">
          <button
            type="button"
            className="auth-link"
            onClick={handleBackToLogin}
          >
            로그인 화면으로 돌아가기
          </button>
        </div>
      </section>
    </main>
  );
}

export default LoginPendingPage;