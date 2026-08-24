// 로그인 화면
import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";

import { login as loginApi } from "../api/authApi.js";
import { useAuth } from "../auth/AuthContext.jsx";

function LoginPage() {
  const navigate = useNavigate();

  // AuthContext의 login 함수
  const { login: saveLogin } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();

    setError("");

    if (!username.trim() || !password) {
      setError("사용자명과 비밀번호를 입력해주세요.");
      return;
    }

    setLoading(true);

    try {
      // 백엔드 로그인 API 호출
      const result = await loginApi({
        username: username.trim(),
        password,
      });

      // 로그인 응답 확인
      if (!result?.access_token) {
        throw new Error("JWT가 반환되지 않았습니다.");
      }

      if (!result?.user) {
        throw new Error("사용자 정보가 반환되지 않았습니다.");
      }

      // AuthContext에 로그인 정보 저장
      saveLogin(result);

      // 역할에 따라 이동
      if (result.user.role === "ADMIN") {
        navigate("/dashboard");
      } else {
        navigate("/account");
      }
    } catch (err) {
      setError(
        err.message || "로그인에 실패했습니다."
      );
    } finally {
      setLoading(false);
    }
  };

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
          </p>
        </div>

        <form
          className="auth-form"
          onSubmit={handleSubmit}
        >
          <label className="auth-field">
            <span>사용자명</span>

            <input
              type="text"
              value={username}
              onChange={(e) =>
                setUsername(e.target.value)
              }
              placeholder="사용자명을 입력하세요"
              disabled={loading}
              autoComplete="username"
            />
          </label>

          <label className="auth-field">
            <span>비밀번호</span>

            <input
              type="password"
              value={password}
              onChange={(e) =>
                setPassword(e.target.value)
              }
              placeholder="비밀번호를 입력하세요"
              disabled={loading}
              autoComplete="current-password"
            />
          </label>

          {error && (
            <p className="auth-error">
              {error}
            </p>
          )}

          <button
            type="submit"
            className="auth-submit-button"
            disabled={loading}
          >
            {loading
              ? "로그인 중..."
              : "로그인"}
          </button>
        </form>

        <div className="auth-footer">
          <span>
            계정이 없나요?
          </span>

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