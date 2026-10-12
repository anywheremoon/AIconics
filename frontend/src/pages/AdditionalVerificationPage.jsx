import { useState } from "react";

import {
  Navigate,
  useNavigate,
} from "react-router-dom";

import {
  LOGIN_STATUS,
  requestVerification,
  confirmVerification,
} from "../api/authApi.js";

import { useAuth } from "../auth/AuthContext.jsx";
import { useLoginGuidance } from "../hooks/useLoginGuidance.js";
import AuthLoading from "../components/AuthLoading.jsx";


function AdditionalVerificationPage() {
  const navigate = useNavigate();

  const {
    loading,
    isAuthenticated,
    user,
    pendingLogin,
    login: saveLogin,
    clearPendingLogin,
  } = useAuth();

  const {
    guidance,
    guidanceLoading,
  } = useLoginGuidance(pendingLogin);

  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(null);
  const [requested, setRequested] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleRequest = async () => {
    if (busy || !pendingLogin) {
      return;
    }

    setBusy("request");
    setError("");
    setMessage("");

    try {
      const result = await requestVerification(
        pendingLogin.verification_token,
        pendingLogin.session_id
      );

      setRequested(true);
      setCode("");

      setMessage(
        typeof result?.message === "string"
          ? result.message
          : "인증번호를 요청했습니다. 등록된 인증 수단을 확인해주세요."
      );
    } catch (err) {
      setError(
        err.message || "인증번호 요청에 실패했습니다."
      );
    } finally {
      setBusy(null);
    }
  };

  const handleConfirm = async (event) => {
    event.preventDefault();

    if (busy || !pendingLogin) {
      return;
    }

    if (!code.trim()) {
      setError("인증번호를 입력해주세요.");
      return;
    }

    setBusy("confirm");
    setError("");
    setMessage("");

    try {
      const result = await confirmVerification(
        pendingLogin.verification_token,
        pendingLogin.session_id,
        code
      );

      // 최종 응답의 토큰·세션으로 로그인 저장 및 Agent 연결
      await saveLogin(result);

      navigate(
        result.user.role === "ADMIN"
          ? "/dashboard"
          : "/account",
        { replace: true }
      );
    } catch (err) {
      setError(
        err.message || "추가 인증에 실패했습니다."
      );
    } finally {
      setBusy(null);
    }
  };

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
    LOGIN_STATUS.PENDING_REVIEW
  ) {
    return (
      <Navigate
        to="/login-pending"
        replace
      />
    );
  }

  if (
    pendingLogin?.login_status !==
      LOGIN_STATUS.REQUIRE_VERIFICATION ||
    !pendingLogin.verification_token ||
    !pendingLogin.session_id
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
            ADDITIONAL VERIFICATION
          </p>

          <h1 className="auth-title">
            추가 인증
          </h1>

          <p className="auth-description">
            {guidance.summary}
          </p>

          <p>
            {guidance.next_action}
          </p>

          {guidanceLoading && (
            <p role="status">
              보안 안내를 확인하고 있습니다...
            </p>
          )}
        </div>

        <div className="auth-form">
          <button
            type="button"
            className="auth-submit-button"
            onClick={handleRequest}
            disabled={busy !== null}
          >
            {busy === "request"
              ? "인증번호 요청 중..."
              : requested
                ? "인증번호 재요청"
                : "인증번호 요청"}
          </button>
        </div>

        <form
          className="auth-form"
          onSubmit={handleConfirm}
        >
          <label className="auth-field">
            <span>인증번호</span>

            <input
              type="text"
              value={code}
              onChange={(event) =>
                setCode(event.target.value)
              }
              placeholder="인증번호를 입력하세요"
              autoComplete="one-time-code"
              disabled={busy !== null}
              required
            />
          </label>

          {message && (
            <p role="status">
              {message}
            </p>
          )}

          {error && (
            <p
              className="auth-error"
              role="alert"
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            className="auth-submit-button"
            disabled={
              busy !== null || !code.trim()
            }
          >
            {busy === "confirm"
              ? "인증 확인 중..."
              : "인증 확인"}
          </button>
        </form>

        <div className="auth-footer">
          <button
            type="button"
            className="auth-link"
            onClick={handleBackToLogin}
            disabled={busy !== null}
          >
            로그인 화면으로 돌아가기
          </button>
        </div>
      </section>
    </main>
  );
}

export default AdditionalVerificationPage;