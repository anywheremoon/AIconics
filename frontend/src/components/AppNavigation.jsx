import {
  NavLink,
  useNavigate,
} from "react-router-dom";

import { useAuth } from "../auth/AuthContext.jsx";

function AppNavigation() {
  const {
    user,
    logout,
  } = useAuth();

  const navigate = useNavigate();

  if (!user) {
    return null;
  }

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav>
      <NavLink to="/account">
        내 계좌
      </NavLink>

      {user.role === "ADMIN" && (
        <>
          <NavLink to="/dashboard">
            대시보드
          </NavLink>

          <NavLink to="/suspicious-users">
            의심 사용자
          </NavLink>

          <NavLink to="/event-logs">
            행동 로그
          </NavLink>
        </>
      )}

      <button
        type="button"
        onClick={handleLogout}
      >
        로그아웃
      </button>
    </nav>
  );
}

export default AppNavigation;