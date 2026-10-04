import { useState } from "react";

import {
  NavLink,
  useNavigate,
} from "react-router-dom";

import { useAuth } from "../auth/AuthContext.jsx";

function AppNavigation() {
  const { user, logout } = useAuth();

  const navigate = useNavigate();
  const [loggingOut, setLoggingOut] = useState(false);

  if (!user) {
    return null;
  }

  const handleLogout = async () => {
    if (loggingOut) return;

    setLoggingOut(true);

    try {
      // 서버 세션 종료와 인증정보 제거가 끝날 때까지 기다린다.
      const { agentCleared } = await logout();

      if (!agentCleared) {
        window.alert(
          "서버 로그아웃은 완료됐지만 Agent 인증정보 제거에 실패했습니다. " +
          "Agent를 종료해 주세요."
        );
      }

      navigate("/login", { replace: true });
    } catch (error) {
      window.alert(
        "서버 로그아웃을 완료하지 못했습니다. " +
        (error.message || "잠시 후 다시 시도해 주세요.")
      );
    } finally {
      setLoggingOut(false);
    }
  };

  const getNavLinkClass = ({ isActive }) => {
    return isActive
      ? "nav-link nav-link-active"
      : "nav-link";
  };

  return (
    <header className="app-header">
      <div className="app-header-inner">
        {/* 왼쪽 로고 */}
        <NavLink
          to={
            user.role === "ADMIN"
              ? "/dashboard"
              : "/account"
          }
          className="app-logo"
        >
          AIconics
        </NavLink>

        {/* 오른쪽 메뉴 */}
        <nav className="app-navigation">
          <NavLink
            to="/account"
            className={getNavLinkClass}
          >
            내 계좌
          </NavLink>

          {user.role === "ADMIN" && (
            <>
              <NavLink
                to="/dashboard"
                className={getNavLinkClass}
              >
                대시보드
              </NavLink>

              <NavLink
                to="/suspicious-users"
                className={getNavLinkClass}
              >
                의심 사용자
              </NavLink>

              <NavLink
                to="/event-logs"
                className={getNavLinkClass}
              >
                행동 로그
              </NavLink>
            </>
          )}

          <button
            type="button"
            className="logout-button"
            onClick={handleLogout}
            disabled={loggingOut}
          >
            {loggingOut ? "로그아웃 중..." : "로그아웃"}
          </button>
        </nav>
      </div>
    </header>
  );
}

export default AppNavigation;