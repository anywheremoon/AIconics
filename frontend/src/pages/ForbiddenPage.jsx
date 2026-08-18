import { useNavigate } from "react-router-dom";

function ForbiddenPage() {
  const navigate = useNavigate();

  return (
    <main>
      <h1>접근 권한이 없습니다.</h1>

      <p>
        관리자만 접근할 수 있는 페이지입니다.
      </p>

      <button
        type="button"
        onClick={() => navigate("/account")}
      >
        내 계좌로 이동
      </button>
    </main>
  );
}

export default ForbiddenPage;