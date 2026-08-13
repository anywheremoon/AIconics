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

// 금융 기능 페이지
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import AccountPage from "./pages/AccountPage.jsx";
import TransferPage from "./pages/TransferPage.jsx";
import WithdrawPage from "./pages/WithdrawPage.jsx";
import TransactionResultPage from "./pages/TransactionResultPage.jsx";

function getNavigationClass({ isActive }) {
  return isActive
    ? "nav-link nav-link-active"
    : "nav-link";
}

function NotFoundPage() {
  return (
    <main className="page-container">
      <h1 className="page-title">
        페이지를 찾을 수 없습니다.
      </h1>

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

            <NavLink
              to="/account"
              className={getNavigationClass}
            >
              내 계좌
            </NavLink>
          </nav>
        </div>
      </header>

      <Routes>
        <Route
          path="/"
          element={<Navigate to="/dashboard" replace />}
        />

        {/* 기존 페이지 */}
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

        {/* 금융 기능 */}
        <Route
          path="/login"
          element={<LoginPage />}
        />

        <Route
          path="/register"
          element={<RegisterPage />}
        />

        <Route
          path="/account"
          element={<AccountPage />}
        />

        <Route
          path="/transfer"
          element={<TransferPage />}
        />

        <Route
          path="/withdraw"
          element={<WithdrawPage />}
        />

        <Route
          path="/transaction-result"
          element={<TransactionResultPage />}
        />

        <Route
          path="*"
          element={<NotFoundPage />}
        />
      </Routes>
    </BrowserRouter>
  );
}