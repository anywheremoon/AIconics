import { useState } from "react";
import { useLocation } from "react-router-dom";

import {
  Navigate,
  useNavigate,
  Link,
} from "react-router-dom";

import {
  LOGIN_STATUS,
  login as loginApi,
  getAgentDeviceInfo,
} from "../api/authApi.js";

import { useAuth } from "../auth/AuthContext.jsx";
import AuthLoading from "../components/AuthLoading.jsx";


function LoginPage() {
  const navigate = useNavigate();
  const successMessage = location.state?.message;

  const {
    loading: authLoading,
    isAuthenticated,
    user,
    login: saveLogin,
    savePendingLogin,
    clearPendingLogin,
  } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (submitting || authLoading) {
      return;
    }

    setError("");

    if (!username.trim() || !password) {
      setError(
        "사용자명과 비밀번호를 입력해주세요."
      );
      return;
    }

    setSubmitting(true);

    try {
      // 이전 인증 대기 정보를 제거한다.
      clearPendingLogin();

      // 1. 현재 PC의 Agent 장치 정보 조회
      const deviceInfo = await getAgentDeviceInfo();

      const result = await loginApi({
        username: username.trim(),
        password,
        device_id: deviceInfo.device_id,
        location: deviceInfo.location,
      });

      // 응답 수신 후 비밀번호 입력값 제거
      setPassword("");

      // 3. 서버가 반환한 로그인 상태에 따라 처리
      switch (result.login_status) {
        case LOGIN_STATUS.AUTHENTICATED:
          // AuthContext에서 로그인 저장과 Agent 전달
          await saveLogin(result);

          navigate(
            result.user.role === "ADMIN"
              ? "/dashboard"
              : "/account",
            { replace: true }
          );
          break;

        case LOGIN_STATUS.REQUIRE_VERIFICATION:
          // 일반 토큰 저장·Agent 인증 전달 없음
          await savePendingLogin(result);

          navigate(
            "/additional-verification",
            { replace: true }
          );
          break;

        case LOGIN_STATUS.PENDING_REVIEW:
          // 보류 정보만 저장
          await savePendingLogin(result);

          navigate(
            "/login-pending",
            { replace: true }
          );
          break;

        default:
          throw new Error(
            "지원하지 않는 로그인 상태입니다."
          );
      }
    } catch (err) {
      setError(
        err.message || "로그인에 실패했습니다."
      );
    } finally {
      setSubmitting(false);
    }
  };

  // 기존 로그인 상태 복원이 끝날 때까지 대기
  if (authLoading) {
    return <AuthLoading />;
  }

  // 이미 로그인한 사용자는 기존 화면으로 이동
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

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-header">
          <p className="auth-eyebrow">
            SECURE ACCESS
          </p>

          <h1 className="auth-title">
            로그인
          </h1>

          <p className="auth-description">
            계정에 로그인하여 서비스를 이용하세요.
            접속 환경에 따라 추가 인증이 필요할 수 있습니다.
          </p>
        </div>

        {successMessage && (
          <p className="auth-success" role="status">
            {successMessage}
          </p>
        )}

        <form
          className="auth-form"
          onSubmit={handleSubmit}
        >
          <label className="auth-field">
            <span>사용자명</span>

            <input
              type="text"
              value={username}
              onChange={(event) =>
                setUsername(event.target.value)
              }
              placeholder="사용자명을 입력하세요"
              disabled={submitting}
              autoComplete="username"
              required
            />
          </label>

          <label className="auth-field">
            <span>비밀번호</span>

            <input
              type="password"
              value={password}
              onChange={(event) =>
                setPassword(event.target.value)
              }
              placeholder="비밀번호를 입력하세요"
              disabled={submitting}
              autoComplete="current-password"
              required
            />
          </label>

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
            disabled={submitting}
          >
            {submitting
              ? "로그인 중..."
              : "로그인"}
          </button>
        </form>

        <div className="auth-footer">
          <span>계정이 없나요?</span>

          <Link
            to="/register"
            className="auth-link"
          >
            회원가입
          </Link>
        </div>
      </section>
    </main>
  );
}

export default LoginPage;