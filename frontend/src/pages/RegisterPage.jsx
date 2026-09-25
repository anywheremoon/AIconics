// 회원가입 화면
import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";

import { register } from "../api/authApi.js";

function RegisterPage() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    username: "",
    password: "",
    passwordConfirm: "",
    deviceId: "",
    location: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (e) => {
    const { name, value } = e.target;

    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (
      !form.username.trim() ||
      !form.password ||
      !form.passwordConfirm ||
      !form.deviceId.trim() ||
      !form.location.trim()
    ) {
      setError("모든 항목을 입력해주세요.");
      return;
    }

    if (form.password !== form.passwordConfirm) {
      setError("비밀번호가 일치하지 않습니다.");
      return;
    }

    setLoading(true);

    try {
      await register({
        username: form.username.trim(),
        password: form.password,
        device_id: form.deviceId.trim(),
        location: form.location.trim(),
      });

      navigate("/login", {
        state: {
          message: "회원가입이 완료되었습니다.",
        },
      });
    } catch (err) {
      setError(err.message || "회원가입에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="auth-page">
      <div className="auth-card">
        <h1 className="auth-title">회원가입</h1>
        <p className="auth-description">
          계정을 생성하고 서비스를 이용해보세요.
        </p>

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="auth-field">
            <label htmlFor="username">사용자명</label>
            <input
              id="username"
              name="username"
              value={form.username}
              onChange={handleChange}
              placeholder="사용자명을 입력하세요"
              disabled={loading}
            />
          </div>

          <div className="auth-field">
            <label htmlFor="password">비밀번호</label>
            <input
              id="password"
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              placeholder="비밀번호를 입력하세요"
              disabled={loading}
            />
          </div>

          <div className="auth-field">
            <label htmlFor="passwordConfirm">비밀번호 확인</label>
            <input
              id="passwordConfirm"
              type="password"
              name="passwordConfirm"
              value={form.passwordConfirm}
              onChange={handleChange}
              placeholder="비밀번호를 다시 입력하세요"
              disabled={loading}
            />
          </div>

          <div className="auth-field">
            <label htmlFor="deviceId">장치 ID</label>
            <input
              id="deviceId"
              name="deviceId"
              value={form.deviceId}
              onChange={handleChange}
              placeholder="device-001"
              disabled={loading}
            />
          </div>

          <div className="auth-field">
            <label htmlFor="location">지역</label>
            <input
              id="location"
              name="location"
              value={form.location}
              onChange={handleChange}
              placeholder="Seoul"
              disabled={loading}
            />
          </div>

          {error && <p className="error-message">{error}</p>}

          <button
            className="auth-submit-button"
            type="submit"
            disabled={loading}
          >
            {loading ? "가입 중..." : "회원가입"}
          </button>
        </form>

        <p className="auth-footer">
          이미 계정이 있나요?{" "}
          <Link to="/login" className="auth-link">
            로그인
          </Link>
        </p>
      </div>
    </main>
  );
}

export default RegisterPage;