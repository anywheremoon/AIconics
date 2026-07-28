import {
  BrowserRouter,
  NavLink,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import DashboardPage from "./pages/DashboardPage";
import SuspiciousUsersPage from "./pages/SuspiciousUsersPage";
import EventLogsPage from "./pages/EventLogsPage";

function getNavigationClass({ isActive }) {
  return isActive
    ? "nav-link nav-link-active"
    : "nav-link";
}

function NotFoundPage() {
  return (
    <main className="page-container">
      <h1 className="page-title">페이지를 찾을 수 없습니다.</h1>
      <p className="page-description">
        입력한 주소가 올바른지 확인해주세요.
      </p>

      <NavLink to="/dashboard" className="action-button">
        대시보드로 이동
      </NavLink>
    </main>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <header className="app-header">
        <div className="app-header-inner">
          <NavLink to="/dashboard" className="app-logo">
            AIconics
          </NavLink>

          <nav className="app-navigation">
            <NavLink
              to="/dashboard"
              className={getNavigationClass}
            >
              대시보드
            </NavLink>

            <NavLink
              to="/suspicious-users"
              className={getNavigationClass}
            >
              의심 사용자
            </NavLink>

            <NavLink
              to="/event-logs"
              className={getNavigationClass}
            >
              행동 로그
            </NavLink>
          </nav>
        </div>
      </header>

      <Routes>
        <Route
          path="/"
          element={<Navigate to="/dashboard" replace />}
        />

        <Route
          path="/dashboard"
          element={<DashboardPage />}
        />

        <Route
          path="/suspicious-users"
          element={<SuspiciousUsersPage />}
        />

        <Route
          path="/event-logs"
          element={<EventLogsPage />}
        />

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}
