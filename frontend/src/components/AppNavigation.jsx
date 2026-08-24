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
          >
            로그아웃
          </button>

        </nav>
      </div>
    </header>
  );
}

export default AppNavigation;