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
    <main>
      <h1>로그인</h1>

      <form onSubmit={handleSubmit}>
        <div>
          <label>사용자명</label>
          <input
            value={username}
            onChange={(e) =>
              setUsername(e.target.value)
            }
            disabled={loading}
          />
        </div>

        <div>
          <label>비밀번호</label>
          <input
            type="password"
            value={password}
            onChange={(e) =>
              setPassword(e.target.value)
            }
            disabled={loading}
          />
        </div>

        {error && (
          <p className="error-message">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
        >
          {loading
            ? "로그인 중..."
            : "로그인"}
        </button>
      </form>

      <p>
        계정이 없나요?{" "}
        <Link to="/register">
          회원가입
        </Link>
      </p>
    </main>
  );
}

export default LoginPage;