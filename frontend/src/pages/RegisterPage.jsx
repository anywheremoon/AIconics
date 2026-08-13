//회원가입 화면
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
    <main>
      <h1>회원가입</h1>

      <form onSubmit={handleSubmit}>
        <div>
          <label>사용자명</label>
          <input
            name="username"
            value={form.username}
            onChange={handleChange}
            disabled={loading}
          />
        </div>

        <div>
          <label>비밀번호</label>
          <input
            type="password"
            name="password"
            value={form.password}
            onChange={handleChange}
            disabled={loading}
          />
        </div>

        <div>
          <label>비밀번호 확인</label>
          <input
            type="password"
            name="passwordConfirm"
            value={form.passwordConfirm}
            onChange={handleChange}
            disabled={loading}
          />
        </div>

        <div>
          <label>장치 ID</label>
          <input
            name="deviceId"
            value={form.deviceId}
            onChange={handleChange}
            placeholder="device-001"
            disabled={loading}
          />
        </div>

        <div>
          <label>지역</label>
          <input
            name="location"
            value={form.location}
            onChange={handleChange}
            placeholder="Seoul"
            disabled={loading}
          />
        </div>

        {error && <p className="error-message">{error}</p>}

        <button type="submit" disabled={loading}>
          {loading ? "가입 중..." : "회원가입"}
        </button>
      </form>

      <p>
        이미 계정이 있나요? <Link to="/login">로그인</Link>
      </p>
    </main>
  );
}

export default RegisterPage;